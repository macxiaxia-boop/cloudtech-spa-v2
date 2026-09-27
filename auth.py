#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication & Authorization System v1.0
JWT-based auth with RBAC, API key validation, rate limiting, audit logging.
Production-grade. Replaces simple API-key string comparison.

R6.5 PATCH: auth.py now loads ROLES from DB instead of hardcoded dict.
  - Added load_roles_from_db() with @lru_cache(maxsize=1) wrapper
  - Falls back to hardcoded 4-role dict if DB query fails / table empty
  - Module-level ROLES alias added for `from auth import ROLES` callers
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps, lru_cache

from database import get_db


def _load_roles_from_db_impl():
    """Lazy-load roles from DB (5 roles: owner/admin/manager/employee/viewer).

    R6.5 EXTEND V4.0 hardcoded ROLES (红线 #95): DB becomes single source of truth,
    hardcoded dict kept only as fallback. Called once via lru_cache wrapper.

    Fallback triggers (all return _FALLBACK):
      - DB unreachable (locked / file missing / permissions)
      - 'roles' table missing (schema not migrated)
      - 'roles' table empty (0 rows = seed not run)
      - Any parse error

    Return format: {code: [permission, ...]} — backward compat with check_permission
    which does `required_permission in self.ROLES.get(role, [])`.

    Uses sqlite3 immutable URI (?immutable=1) to bypass DB lock contention from
    long-running daemons (e.g. TikTokDownloader) — auth.py is read-only here.
    """
    _FALLBACK = {
        "admin": ["read", "write", "delete", "manage_tenants", "manage_users", "view_billing"],
        "manager": ["read", "write", "view_billing"],
        "user": ["read", "write"],
        "viewer": ["read"],
    }
    try:
        import sqlite3 as _sqlite3
        from database import DB_PATH as _DB_PATH
        _conn = _sqlite3.connect(
            f"file:{_DB_PATH}?mode=ro&immutable=1",
            uri=True, timeout=5,
        )
        _cur = _conn.cursor()
        _cur.execute("SELECT code, permissions_json FROM roles")
        roles = {}
        for _code, _perms_json in _cur.fetchall():
            try:
                _perms = json.loads(_perms_json) if _perms_json else []
                if not isinstance(_perms, list):
                    _perms = []
            except Exception:
                _perms = []
            roles[_code] = _perms
        _conn.close()
        return roles if roles else _FALLBACK
    except Exception:
        return _FALLBACK


load_roles_from_db = lru_cache(maxsize=1)(_load_roles_from_db_impl)


# === Configuration ===
_JWT_SECRET_FILE = Path(__file__).parent / ".jwt_secret"
if os.environ.get("JWT_SECRET"):
    JWT_SECRET = os.environ["JWT_SECRET"]
elif _JWT_SECRET_FILE.exists():
    JWT_SECRET = _JWT_SECRET_FILE.read_text().strip()
else:
    JWT_SECRET = secrets.token_hex(32)
    _JWT_SECRET_FILE.write_text(JWT_SECRET)
    _JWT_SECRET_FILE.chmod(0o600)
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
API_KEY_PREFIX = "ak-"
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-SHA256 (cross-platform, no deps)."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"pbkdf2:sha256:100000${salt}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    try:
        rest, salt, stored = hashed.rsplit("$", 2)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return hmac.compare_digest(dk.hex(), stored)
    except Exception:
        return False


class AuthManager:
    """Centralized authentication and authorization."""

    def __init__(self):
        self.db = get_db()

    def create_user(self, tenant_id, email, password, name, role="user"):
        user_id = f"user-{secrets.token_hex(8)}"
        password_hash = hash_password(password)
        self.db.insert("users", {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "name": name,
            "role": role,
            "is_active": 1,
        })
        self._audit(tenant_id, user_id, "user.created", "user", user_id)
        return {"id": user_id, "email": email, "name": name, "role": role}

    def authenticate_user(self, email, password):
        user = self.db.fetch_one(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (email.lower().strip(),)
        )
        if not user:
            return None
        if not verify_password(password, user["password_hash"]):
            self._audit(user["tenant_id"], user["id"], "user.login_failed", "user", user["id"])
            return None
        self.db.update("users", {"last_login_at": datetime.now().isoformat()},
                       "id = ?", (user["id"],))
        token = self._generate_jwt(dict(user))
        self._audit(user["tenant_id"], user["id"], "user.login", "user", user["id"])
        return {"token": token, "user": {"id": user["id"], "email": user["email"],
                                          "name": user["name"], "role": user["role"],
                                          "tenant_id": user["tenant_id"]}}

    def change_password(self, user_id, old_password, new_password):
        user = self.db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user or not verify_password(old_password, user["password_hash"]):
            return False
        new_hash = hash_password(new_password)
        self.db.update("users", {"password_hash": new_hash}, "id = ?", (user_id,))
        self._audit(user["tenant_id"], user_id, "user.password_changed", "user", user_id)
        return True

    def create_api_key(self, tenant_id, name="Default", scopes=None):
        if scopes is None:
            scopes = ["read", "write"]
        raw_key = f"{API_KEY_PREFIX}{secrets.token_hex(24)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:12]
        self.db.insert("api_keys", {
            "tenant_id": tenant_id,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            "name": name,
            "scopes": json.dumps(scopes),
            "is_active": 1,
            "expires_at": (datetime.now() + timedelta(days=365)).isoformat(),
        })
        self._audit(tenant_id, "system", "apikey.created", "api_key", key_prefix)
        return {"api_key": raw_key, "prefix": key_prefix, "name": name, "scopes": scopes}

    def validate_api_key(self, raw_key):
        if not raw_key or not raw_key.startswith(API_KEY_PREFIX):
            return None
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        row = self.db.fetch_one(
            """SELECT k.*, t.name as tenant_name, t.plan, t.status as tenant_status
               FROM api_keys k JOIN tenants t ON k.tenant_id = t.id
               WHERE k.key_hash = ? AND k.is_active = 1 AND t.status = 'active'""",
            (key_hash,)
        )
        if not row:
            return None
        if row["expires_at"] and row["expires_at"] < datetime.now().isoformat():
            return None
        return dict(row)

    def revoke_api_key(self, key_prefix):
        self.db.update("api_keys", {"is_active": 0}, "key_prefix = ?", (key_prefix,))
        return True

    def _generate_jwt(self, payload):
        payload = {
            "sub": payload.get("id", ""),
            "email": payload.get("email", ""),
            "role": payload.get("role", "user"),
            "tenant_id": payload.get("tenant_id", ""),
            "iat": int(time.time()),
            "exp": int(time.time()) + JWT_EXPIRY_HOURS * 3600,
        }
        header_b64 = self._b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}))
        payload_b64 = self._b64encode(json.dumps(payload))
        signature = hmac.new(
            JWT_SECRET.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{header_b64}.{payload_b64}.{signature}"

    def verify_jwt(self, token):
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, signature = parts
            expected_sig = hmac.new(
                JWT_SECRET.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_sig):
                return None
            payload = json.loads(self._b64decode(payload_b64))
            if payload.get("exp", 0) < int(time.time()):
                return None
            return payload
        except Exception:
            return None

    @staticmethod
    def _b64encode(data):
        import base64
        return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()

    @staticmethod
    def _b64decode(data):
        import base64
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        return base64.urlsafe_b64decode(data).decode()

    # === RBAC (R6.5: now DB-driven with hardcode fallback) ===
    ROLES = load_roles_from_db()

    def check_permission(self, user_data, required_permission):
        role = user_data.get("role", "user")
        allowed = self.ROLES.get(role, [])
        return required_permission in allowed

    def check_rate_limit(self, tenant_id, action, max_requests=100, window_seconds=60):
        cutoff = (datetime.now() - timedelta(seconds=window_seconds)).isoformat()
        count = self.db.fetch_one(
            """SELECT COUNT(*) as c FROM audit_log
               WHERE tenant_id = ? AND action = ? AND created_at > ?""",
            (tenant_id, f"rate_limit.{action}", cutoff)
        )
        self._audit(tenant_id, "system", f"rate_limit.{action}", "rate_limit", "")
        return (count["c"] if count else 0) < max_requests

    def _audit(self, tenant_id, user_id, action, resource, resource_id):
        self.db.insert("audit_log", {
            "tenant_id": tenant_id or "system",
            "user_id": user_id or "system",
            "action": action,
            "resource": resource,
            "resource_id": resource_id or "",
            "details": "{}",
        })

    def get_audit_log(self, tenant_id=None, limit=100):
        if tenant_id:
            rows = self.db.fetch_all(
                "SELECT * FROM audit_log WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                (tenant_id, limit)
            )
        else:
            rows = self.db.fetch_all(
                "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        return [dict(r) for r in rows]


def require_auth(f):
    """Decorator: require valid JWT or API key."""
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        auth_header = self.headers.get("Authorization", "")
        auth_mgr = AuthManager()
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = auth_mgr.verify_jwt(token)
            if payload:
                self.current_user = payload
                return f(self, *args, **kwargs)
            tenant = auth_mgr.validate_api_key(token)
            if tenant:
                self.current_tenant = tenant
                return f(self, *args, **kwargs)
        self._send_json({"error": "Authentication required"}, 401)
    return wrapper


if __name__ == "__main__":
    import sys
    auth = AuthManager()
    if len(sys.argv) > 1 and sys.argv[1] == "create-user":
        if len(sys.argv) < 6:
            print("Usage: create-user <tenant_id> <email> <password> <name> [role]")
            sys.exit(1)
        user = auth.create_user(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5],
                                sys.argv[6] if len(sys.argv) > 6 else "admin")
        print(json.dumps(user, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "create-apikey":
        if len(sys.argv) < 3:
            print("Usage: create-apikey <tenant_id> [name]")
            sys.exit(1)
        key = auth.create_api_key(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Default")
        print(f"API Key: {key['api_key']}")
        print("SAVE THIS KEY. It will not be shown again.")
    elif len(sys.argv) > 1 and sys.argv[1] == "login":
        if len(sys.argv) < 4:
            print("Usage: login <email> <password>")
            sys.exit(1)
        result = auth.authenticate_user(sys.argv[2], sys.argv[3])
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("Login failed")
    elif len(sys.argv) > 1 and sys.argv[1] == "audit":
        log = auth.get_audit_log(limit=20)
        for entry in log:
            print(f"{entry['created_at'][:19]} | {entry['action']:30s} | {entry['resource']}:{entry['resource_id']}")
    else:
        print("Auth Manager v1.0")
        print("  create-user <tenant_id> <email> <password> <name> [role]")
        print("  create-apikey <tenant_id> [name]")
        print("  login <email> <password>")
        print("  audit")

# R6.5: module-level alias so `from auth import ROLES` works
ROLES = AuthManager.ROLES