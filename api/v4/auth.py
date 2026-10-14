"""V4 — Auth middleware
红线 #22 #60: /v4/* 端点必须 tenant_id 校验 + (可选) Bearer JWT 验证
默认 mode: tenant_id 仅校验非空 (开发环境)
strict mode: tenant_id + JWT signature 校验 (生产环境)
"""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path
import time
from dataclasses import dataclass
from typing import Optional

from fastapi import Header, HTTPException, Query, status


@dataclass
class AuthContext:
    tenant_id: str
    user_id: Optional[str] = None
    jwt_verified: bool = False
    permissions: list = None  # type: ignore


class AuthError(HTTPException):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"[AUTH-{code}] {msg}")


def _get_jwt_secret() -> Optional[str]:
    """从 env 读 JWT secret; 无则 None (开发模式)"""
    return os.environ.get("V4_JWT_SECRET") or os.environ.get("CLOUDTECH_SAAS_JWT_SECRET")


def _verify_jwt(token: str, secret: str, tenant_id: str) -> Optional[dict]:
    """轻量 JWT 验证 — HS256 + payload 含 tenant_id + exp
    返回 payload 或 None (失败)
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, sig_b64 = parts
    try:
        import base64
        import json
        # 签名比对: 必须用原始 (未填充) header.payload
        msg = (header_b64 + "." + payload_b64).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).digest()
        # sig_b64 可能是 url-safe (rstrip b"="), 还原
        sig_b64_padded = sig_b64 + "=" * (4 - len(sig_b64) % 4)
        sig = base64.urlsafe_b64decode(sig_b64_padded.encode("utf-8"))
        if not hmac.compare_digest(expected, sig):
            return None
        # Reject misleading/unsupported JWT algorithm metadata.
        header = json.loads(base64.urlsafe_b64decode(
            header_b64 + "=" * (-len(header_b64) % 4)
        ))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None
        # 解码 payload
        payload_b64_padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64_padded.encode("utf-8")))
        if payload.get("tenant_id") != tenant_id:
            return None
        if not (payload.get("user_id") or payload.get("sub")):
            return None
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _active_saas_member(tenant_id: str, user_id: str) -> bool:
    """Read-only membership check. Signed tokens alone are not current access."""
    db_name = os.environ.get(
        "CLOUDTECH_SAAS_DB_PATH",
        r"D:\CloudTech-Portable\data\cloudtech.db",
    )
    db_path = Path(db_name).expanduser()
    if not db_path.is_file():
        raise HTTPException(
            status_code=503,
            detail="[AUTH-008] SaaS identity database is not available",
        )
    try:
        from contextlib import closing
        with closing(sqlite3.connect(
            db_path.resolve().as_uri() + "?mode=ro",
            uri=True, timeout=5,
        )) as connection:
            user = connection.execute(
                """SELECT 1 FROM saas_users u
                   INNER JOIN saas_tenants t ON t.tenant_id=u.tenant_id
                   WHERE u.user_id=? AND u.tenant_id=? AND t.active=1
                   LIMIT 1""",
                (user_id, tenant_id),
            ).fetchone()
            return user is not None
    except sqlite3.Error as exc:
        raise HTTPException(
            status_code=503,
            detail="[AUTH-008] SaaS membership could not be verified",
        ) from exc


def auth_required(
    tenant_id: str = Query(..., description="租户 ID (query param)"),
    authorization: Optional[str] = Header(None, description="Bearer JWT (生产模式必填)"),
) -> AuthContext:
    """FastAPI Depends: 校验 tenant_id + 可选 JWT
    模式:
      1. dev mode (无 V4_JWT_SECRET): 仅校验 tenant_id 非空
      2. prod mode (有 V4_JWT_SECRET): 必须 Authorization Bearer + tenant 匹配 + 签名 + exp
    """
    # 基本 tenant_id 校验
    if not tenant_id or not tenant_id.strip():
        raise AuthError("001", "tenant_id 必填")
    tid = tenant_id.strip()
    # 黑名单/格式校验 (mock tenant 列表)
    if len(tid) > 64:
        raise AuthError("002", "tenant_id 过长 (max 64)")
    if not all(c.isalnum() or c in "_-" for c in tid):
        raise AuthError("003", "tenant_id 仅允许字母数字下划线短横线")

    ctx = AuthContext(tenant_id=tid, permissions=[])

    secret = _get_jwt_secret()
    # JWT is mandatory by default, INCLUDING when CLOUDTECH_ENV was never set.
    # An explicit test/development opt-in is required for the legacy mock API.
    dev_mode = os.environ.get("CLOUDTECH_ENV", "").strip().lower() in {"development", "test"}
    explicit_bypass = os.environ.get("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH") == "1"
    if secret is None:
        if not (dev_mode and explicit_bypass):
            raise HTTPException(
                status_code=503,
                detail="[AUTH-007] V4 authentication unavailable; JWT signing secret required",
            )
        return ctx

    # prod mode — 必须 JWT
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("004", "生产模式必须 Bearer JWT")
    token = authorization[7:].strip()
    payload = _verify_jwt(token, secret, tid)
    if payload is None:
        raise AuthError("005", "JWT 签名/tenant/exp 校验失败")
    ctx.user_id = payload.get("user_id") or payload.get("sub")
    if not isinstance(ctx.user_id, str) or not ctx.user_id:
        raise AuthError("006", "JWT 缺少可验证的用户身份")
    # Only isolated test/dev opt-in may bypass the SaaS membership database.
    if not (dev_mode and explicit_bypass):
        if not _active_saas_member(tid, ctx.user_id):
            raise HTTPException(
                status_code=403,
                detail="[AUTH-009] user membership or tenant is inactive",
            )
    ctx.jwt_verified = True
    ctx.permissions = payload.get("permissions", [])
    return ctx


def mint_jwt(tenant_id: str, user_id: Optional[str] = None, permissions: Optional[list] = None, ttl_sec: int = 3600) -> str:
    """工具函数: 生成 JWT (供测试或 user 拍后 server 端签发)
    ⚠️ 仅供受信任环境使用; 真实生产应使用 Auth Service 而非此函数
    """
    secret = _get_jwt_secret() or "dev-secret-do-not-use-in-prod"
    import base64
    import json
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "permissions": permissions or [],
        "exp": int(time.time()) + ttl_sec,
        "iat": int(time.time()),
    }
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    msg = (h_b64 + "." + p_b64).encode("utf-8")
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).digest()
    s_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{h_b64}.{p_b64}.{s_b64}"
