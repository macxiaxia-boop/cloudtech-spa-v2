#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication & Authorization System v1.0
JWT-based auth with RBAC, API key validation, rate limiting, audit logging.
Production-grade. Replaces simple API-key string comparison.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

from database import get_db

# === Configuration ===
# JWT_SECRET: must be persistent across restarts. Set via env or read from file.
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

# Simulated bcrypt (real bcrypt requires compilation on Windows)
# In production: use passlib.hash.bcrypt
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
    except:
        return False


class AuthManager:
    """Centralized authentication and authorization."""

    def __init__(self):
        self.db = get_db()

    # === User Management ===
    def create_user(self, tenant_id, email, password, name, role="user"):
        """Create a new user for web admin access."""
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
        """Authenticate user by email/password. Returns JWT token or None."""
        user = self.db.fetch_one(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (email.lower().strip(),)
        )
        if not user:
            return None

        if not verify_password(password, user["password_hash"]):
            self._audit(user["tenant_id"], user["id"], "user.login_failed", "user", user["id"])
            return None

        # Update last login
        self.db.update("users", {"last_login_at": datetime.now().isoformat()},
                       "id = ?", (user["id"],))

        token = self._generate_jwt(dict(user))
        self._audit(user["tenant_id"], user["id"], "user.login", "user", user["id"])
        return {"token": token, "user": {"id": user["id"], "email": user["email"],
                                          "name": user["name"], "role": user["role"],
                                          "tenant_id": user["tenant_id"]}}

    def change_password(self, user_id, old_password, new_password):
        """Change user password."""
        user = self.db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user or not verify_password(old_password, user["password_hash"]):
            return False

        new_hash = hash_password(new_password)
        self.db.update("users", {"password_hash": new_hash}, "id = ?", (user_id,))
        self._audit(user["tenant_id"], user_id, "user.password_changed", "user", user_id)
        return True

    # === API Key Management ===
    def create_api_key(self, tenant_id, name="Default", scopes=None):
        """Create a new API key for a tenant."""
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
        """Validate an API key. Returns tenant info or None."""
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

        # Check expiration
        if row["expires_at"] and datetime.fromisoformat(row["expires_at"]) < datetime.now():
            return None

        # Update last used
        self.db.update("api_keys", {"last_used_at": datetime.now().isoformat()},
                       "id = ?", (row["id"],))

        return {
            "tenant_id": row["tenant_id"],
            "tenant_name": row["tenant_name"],
            "plan": row["plan"],
            "scopes": json.loads(row["scopes"]) if row["scopes"] else ["read", "write"],
        }

    def revoke_api_key(self, tenant_id, key_prefix):
        """Revoke an API key."""
        self.db.update("api_keys", {"is_active": 0}, "tenant_id = ? AND key_prefix = ?",
                       (tenant_id, key_prefix))
        self._audit(tenant_id, "system", "apikey.revoked", "api_key", key_prefix)

    # === JWT ===
    def _generate_jwt(self, user_data):
        """Generate a signed JWT token."""
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "role": user_data["role"],
            "tenant_id": user_data["tenant_id"],
            "iat": int(time.time()),
            "exp": int(time.time()) + JWT_EXPIRY_HOURS * 3600,
        }

        header_b64 = self._b64encode(json.dumps(header, separators=(",", ":")))
        payload_b64 = self._b64encode(json.dumps(payload, separators=(",", ":")))
        signature = hmac.new(
            JWT_SECRET.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).hexdigest()

        return f"{header_b64}.{payload_b64}.{signature}"

    def verify_jwt(self, token):
        """Verify a JWT token. Returns payload or None."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature = parts

            # Verify signature
            expected_sig = hmac.new(
                JWT_SECRET.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return None

            # Decode payload
            payload = json.loads(self._b64decode(payload_b64))

            # Check expiration
            if payload.get("exp", 0) < int(time.time()):
                return None

            return payload
        except:
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

    # === RBAC ===
    ROLES = {
        "admin": ["read", "write", "delete", "manage_tenants", "manage_users", "view_billing"],
        "manager": ["read", "write", "view_billing"],
        "user": ["read", "write"],
        "viewer": ["read"],
    }

    def check_permission(self, user_data, required_permission):
        """Check if user has the required permission."""
        role = user_data.get("role", "user")
        allowed = self.ROLES.get(role, [])
        return required_permission in allowed

    # === Rate Limiting ===
    def check_rate_limit(self, tenant_id, action, max_requests=100, window_seconds=60):
        """Simple rate limiter based on audit log."""
        cutoff = (datetime.now() - timedelta(seconds=window_seconds)).isoformat()
        count = self.db.fetch_one(
            """SELECT COUNT(*) as c FROM audit_log
               WHERE tenant_id = ? AND action = ? AND created_at > ?""",
            (tenant_id, f"rate_limit.{action}", cutoff)
        )
        self._audit(tenant_id, "system", f"rate_limit.{action}", "rate_limit", "")
        return (count["c"] if count else 0) < max_requests

    # === Audit Logging ===
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
        """Get audit log entries."""
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


# === Decorators for API endpoints ===
def require_auth(f):
    """Decorator: require valid JWT or API key."""
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        auth_header = self.headers.get("Authorization", "")

        auth_mgr = AuthManager()

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

            # Try JWT first
            payload = auth_mgr.verify_jwt(token)
            if payload:
                self.current_user = payload
                return f(self, *args, **kwargs)

            # Try API key
            tenant = auth_mgr.validate_api_key(token)
            if tenant:
                self.current_tenant = tenant
                return f(self, *args, **kwargs)

        self._send_json({"error": "Authentication required"}, 401)
    return wrapper


# === CLI ===
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
