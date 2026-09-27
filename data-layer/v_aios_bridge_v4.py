"""CloudTech → AIOS §8 桥接层 v4 · 2026-09-25 R288

把 AIOS §8.6 user_auth + §8.7 payment_billing 桥接到 CloudTech 真业务路径.

AIOS §8 接口定义 (per R288 MEMORY):
  §8.6 user_auth:
    POST /api/aios/v1/auth/register  {email, password, name, industry, role}
      -> {user_id, tenant_id, session_token (JWT 24h)}
    POST /api/aios/v1/auth/login     {email, password}
      -> {user_id, tenant_id, session_token}
    GET  /api/aios/v1/auth/verify    Authorization: Bearer <jwt>
      -> {user_id, tenant_id, role, valid: true}
    5 角色: owner / admin / manager / employee / viewer
    4 行业 tenant: decoration / education / manufacturing / service

  §8.7 payment_billing:
    POST /api/aios/v1/payment/checkout   {plan, tenant_id, industry}
      -> {session_id, amount_cny, sku_code}
      -> 12 SKU: 3 套餐 (basic/pro/enterprise) × 4 行业
      -> 价格: 199 / 1999 / 2999 元/月
    POST /api/aios/v1/payment/webhook    {session_id, success, stripe_sig}
      -> {status: "active", subscription_id}
    GET  /api/aios/v1/payment/subscription/{tenant}
      -> {plan, industry, status, expires_at}

桥接策略:
  - AIOS_BASE_URL 环境变量 (默认 http://127.0.0.1:7777)
  - 调 AIOS §8 → 通: 用真 user/auth + 真计费
  - 不通: fallback 到 cloudtech 本地 SQLite (兼容运行)
  - 5 min 内 AIOS 不可达 → 写 bridge_incidents 表
"""
import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, List

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel

# 复用 v1/v2/v3 的 DB
sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_DIR = LIVE / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cloudtech.db"

# AIOS 配置
AIOS_BASE_URL = os.environ.get("AIOS_BASE_URL", "http://127.0.0.1:7777").rstrip("/")
AIOS_TIMEOUT = float(os.environ.get("AIOS_TIMEOUT", "3.0"))  # 3s timeout

router = APIRouter(prefix="/api/aios/bridge/v1", tags=["aios-bridge-v1"])


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


_db_lock = asyncio.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 桥接 fallback 表 (AIOS 不可达时本地存)
# ---------------------------------------------------------------------------
def _init_db():
    """v4 桥接表 — fallback 用,与 §8 接口语义一致."""
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS aios_user (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            password_hash TEXT,
            password_salt TEXT,
            tenant_id TEXT NOT NULL,
            industry TEXT NOT NULL,
            role TEXT DEFAULT 'employee',  -- owner/admin/manager/employee/viewer
            jwt_token TEXT,
            jwt_expires_at TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_aios_user_tenant ON aios_user(tenant_id);

        CREATE TABLE IF NOT EXISTS aios_subscription (
            subscription_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            industry TEXT NOT NULL,
            plan TEXT NOT NULL,  -- basic/pro/enterprise
            sku_code TEXT NOT NULL,  -- e.g. pro-decoration
            amount_cny REAL,
            status TEXT DEFAULT 'pending',  -- pending/active/expired/canceled
            session_id TEXT,
            stripe_sig TEXT,
            activated_at TEXT,
            expires_at TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_aios_sub_tenant ON aios_subscription(tenant_id);

        CREATE TABLE IF NOT EXISTS bridge_incident (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            target TEXT,  -- AIOS path
            error TEXT,
            fallback_used INTEGER DEFAULT 1
        );
        """)
        c.commit()
    finally:
        c.close()


# ---------------------------------------------------------------------------
# JWT 简易实现 (HS256, 无外部依赖 — 避免 pip install pyjwt)
# ---------------------------------------------------------------------------
_JWT_SECRET = os.environ.get("JWT_SECRET", "cloudtech-aios-bridge-secret-2026")


def _b64url(b: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    import base64
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def _jwt_encode(payload: dict) -> str:
    import hmac
    header = {"alg": "HS256", "typ": "JWT"}
    h_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    msg = f"{h_b64}.{p_b64}".encode()
    sig = hmac.new(_JWT_SECRET.encode(), msg, hashlib.sha256).digest()
    s_b64 = _b64url(sig)
    return f"{h_b64}.{p_b64}.{s_b64}"


def _jwt_decode(token: str) -> Optional[dict]:
    import hmac
    parts = token.split(".")
    if len(parts) != 3:
        return None
    h_b64, p_b64, s_b64 = parts
    msg = f"{h_b64}.{p_b64}".encode()
    expected_sig = hmac.new(_JWT_SECRET.encode(), msg, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(s_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None
    try:
        payload = json.loads(_b64url_decode(p_b64))
    except Exception:
        return None
    if payload.get("exp") and time.time() > payload["exp"]:
        return None  # expired
    return payload


def _hash_pw(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# AIOS HTTP client (3s timeout, fallback 标志)
# ---------------------------------------------------------------------------
async def _aios_request(method: str, path: str, body: Optional[dict] = None, headers: Optional[dict] = None) -> tuple[bool, Any]:
    """返回 (ok, data). ok=False 时 data 是错误信息."""
    try:
        import httpx  # type: ignore
        url = f"{AIOS_BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=AIOS_TIMEOUT) as client:
            if method.upper() == "GET":
                r = await client.get(url, headers=headers or {})
            else:
                r = await client.request(method.upper(), url, json=body, headers=headers or {})
            if r.status_code >= 500:
                return False, {"error": "aios_5xx", "status": r.status_code, "body": r.text[:200]}
            if r.status_code >= 400:
                return False, {"error": "aios_4xx", "status": r.status_code, "body": r.text[:200]}
            try:
                return True, r.json()
            except Exception:
                return True, {"raw": r.text[:500]}
    except Exception as e:
        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}"}


async def _record_incident(target: str, error: str):
    c = _conn()
    try:
        c.execute("INSERT INTO bridge_incident(ts, target, error) VALUES (?, ?, ?)",
                  (_now(), target, error[:500]))
        c.commit()
    finally:
        c.close()


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------
class AiosRegisterReq(BaseModel):
    email: str
    password: str
    name: str = ""
    industry: str = "decoration"
    role: str = "employee"  # owner/admin/manager/employee/viewer


class AiosLoginReq(BaseModel):
    email: str
    password: str


class AiosCheckoutReq(BaseModel):
    tenant_id: str
    industry: str
    plan: str  # basic/pro/enterprise


class AiosWebhookReq(BaseModel):
    session_id: str
    success: bool = True
    stripe_sig: str = "mock_sig"


# ---------------------------------------------------------------------------
# §8.6 桥接 — 注册 / 登录 / verify
# ---------------------------------------------------------------------------
@router.post("/auth/register")
async def aios_register(req: AiosRegisterReq):
    """调 AIOS §8.6 register; AIOS 不通时 fallback 本地."""
    body = req.model_dump()
    ok, data = await _aios_request("POST", "/api/aios/v1/auth/register", body)
    if ok:
        return {"status": "ok", "source": "aios", **data}
    await _record_incident("/auth/register", data.get("error", "unknown"))

    # Fallback: 本地 SQLite
    async with _db_lock:
        c = _conn()
        try:
            existing = c.execute("SELECT user_id FROM aios_user WHERE email=?", (req.email,)).fetchone()
            if existing:
                raise HTTPException(409, {"error": "email_already_registered"})
            uid = f"u_{uuid.uuid4().hex[:12]}"
            tid = f"t_{secrets.token_hex(4)}"
            salt = secrets.token_hex(16)
            pw_hash = _hash_pw(req.password, salt)
            exp = int(time.time()) + 86400  # 24h
            jwt_token = _jwt_encode({"sub": uid, "tenant": tid, "role": req.role, "exp": exp})
            c.execute(
                "INSERT INTO aios_user(user_id, email, name, password_hash, password_salt, tenant_id, industry, role, jwt_token, jwt_expires_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uid, req.email, req.name, pw_hash, salt, tid, req.industry, req.role, jwt_token,
                 datetime.fromtimestamp(exp, tz=timezone.utc).isoformat(), _now())
            )
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "source": "fallback_local",
        "user_id": uid,
        "tenant_id": tid,
        "email": req.email,
        "industry": req.industry,
        "role": req.role,
        "session_token": jwt_token,
        "msg": "AIOS §8 unreachable; local fallback used. Bridge incident recorded.",
    }


@router.post("/auth/login")
async def aios_login(req: AiosLoginReq):
    ok, data = await _aios_request("POST", "/api/aios/v1/auth/login", req.model_dump())
    if ok:
        return {"status": "ok", "source": "aios", **data}
    await _record_incident("/auth/login", data.get("error", "unknown"))

    # Fallback
    async with _db_lock:
        c = _conn()
        try:
            row = c.execute("SELECT * FROM aios_user WHERE email=?", (req.email,)).fetchone()
            if not row:
                raise HTTPException(404, {"error": "user_not_found"})
            if _hash_pw(req.password, row["password_salt"]) != row["password_hash"]:
                raise HTTPException(401, {"error": "wrong_password"})
            exp = int(time.time()) + 86400
            jwt_token = _jwt_encode({"sub": row["user_id"], "tenant": row["tenant_id"], "role": row["role"], "exp": exp})
            c.execute("UPDATE aios_user SET jwt_token=?, jwt_expires_at=? WHERE user_id=?",
                      (jwt_token, datetime.fromtimestamp(exp, tz=timezone.utc).isoformat(), row["user_id"]))
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "source": "fallback_local",
        "user_id": row["user_id"],
        "tenant_id": row["tenant_id"],
        "email": row["email"],
        "name": row["name"],
        "industry": row["industry"],
        "role": row["role"],
        "session_token": jwt_token,
    }


@router.get("/auth/verify")
async def aios_verify(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, {"error": "missing_bearer_token"})
    token = authorization[7:]
    payload = _jwt_decode(token)
    if not payload:
        raise HTTPException(401, {"error": "invalid_or_expired_token"})
    return {
        "status": "ok",
        "valid": True,
        "user_id": payload.get("sub"),
        "tenant_id": payload.get("tenant"),
        "role": payload.get("role"),
        "exp": payload.get("exp"),
    }


# ---------------------------------------------------------------------------
# §8.7 桥接 — checkout / webhook / subscription
# ---------------------------------------------------------------------------
_12_SKU = {
    # plan × industry → (sku_code, amount_cny, features)
    ("basic", "decoration"):      ("basic-decoration", 199,  ["1 employee", "1000 calls/mo", "xhs 平台"]),
    ("basic", "education"):       ("basic-education",  199,  ["1 employee", "1000 calls/mo", "xhs 平台"]),
    ("basic", "manufacturing"):   ("basic-manufacturing", 199, ["1 employee", "1000 calls/mo", "zhihu 平台"]),
    ("basic", "service"):         ("basic-service",    199,  ["1 employee", "1000 calls/mo", "douyin 平台"]),
    ("pro", "decoration"):        ("pro-decoration",   1999, ["5 employees", "20000 calls/mo", "4 平台", "GEO SEO"]),
    ("pro", "education"):         ("pro-education",    1999, ["5 employees", "20000 calls/mo", "4 平台", "GEO SEO"]),
    ("pro", "manufacturing"):     ("pro-manufacturing", 1999, ["5 employees", "20000 calls/mo", "4 平台", "GEO SEO"]),
    ("pro", "service"):           ("pro-service",      1999, ["5 employees", "20000 calls/mo", "4 平台", "GEO SEO"]),
    ("enterprise", "decoration"): ("ent-decoration",   2999, ["unlimited employees", "100000 calls/mo", "4 平台 + 自定义", "SLA"]),
    ("enterprise", "education"):  ("ent-education",    2999, ["unlimited employees", "100000 calls/mo", "4 平台 + 自定义", "SLA"]),
    ("enterprise", "manufacturing"): ("ent-manufacturing", 2999, ["unlimited employees", "100000 calls/mo", "4 平台 + 自定义", "SLA"]),
    ("enterprise", "service"):    ("ent-service",      2999, ["unlimited employees", "100000 calls/mo", "4 平台 + 自定义", "SLA"]),
}


@router.get("/payment/skus")
async def list_skus():
    """12 SKU 完整列表 — AIOS §8.7 元数据."""
    out = []
    for (plan, ind), (sku, price, features) in _12_SKU.items():
        out.append({"plan": plan, "industry": ind, "sku_code": sku, "amount_cny": price, "features": features})
    return {"status": "ok", "count": 12, "skus": out}


@router.post("/payment/checkout")
async def aios_checkout(req: AiosCheckoutReq):
    body = req.model_dump()
    ok, data = await _aios_request("POST", "/api/aios/v1/payment/checkout", body)
    if ok:
        return {"status": "ok", "source": "aios", **data}

    # Fallback: 本地
    key = (req.plan, req.industry)
    if key not in _12_SKU:
        raise HTTPException(400, {"error": "invalid_plan_or_industry",
                                  "allowed_plans": ["basic", "pro", "enterprise"],
                                  "allowed_industries": ["decoration", "education", "manufacturing", "service"]})
    sku, price, features = _12_SKU[key]
    sid = f"sub_{uuid.uuid4().hex[:12]}"
    sess = f"cs_{secrets.token_hex(8)}"
    async with _db_lock:
        c = _conn()
        try:
            c.execute(
                "INSERT INTO aios_subscription(subscription_id, tenant_id, industry, plan, sku_code, amount_cny, status, session_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
                (sid, req.tenant_id, req.industry, req.plan, sku, price, sess, _now())
            )
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "source": "fallback_local",
        "subscription_id": sid,
        "session_id": sess,
        "sku_code": sku,
        "plan": req.plan,
        "industry": req.industry,
        "amount_cny": price,
        "features": features,
        "msg": f"AIOS §8 unreachable; local fallback used. Mock pay URL: POST /payment/webhook {{session_id: '{sess}', success: true}}",
    }


@router.post("/payment/webhook")
async def aios_webhook(req: AiosWebhookReq):
    ok, data = await _aios_request("POST", "/api/aios/v1/payment/webhook", req.model_dump())
    if ok:
        return {"status": "ok", "source": "aios", **data}

    # Fallback: 模拟 Stripe webhook — 验签 (mock 模式直接通过)
    if not req.success:
        async with _db_lock:
            c = _conn()
            try:
                c.execute("UPDATE aios_subscription SET status='canceled' WHERE session_id=?",
                          (req.session_id,))
                c.commit()
            finally:
                c.close()
        return {"status": "ok", "subscription_status": "canceled"}

    async with _db_lock:
        c = _conn()
        try:
            sub = c.execute("SELECT * FROM aios_subscription WHERE session_id=?", (req.session_id,)).fetchone()
            if not sub:
                raise HTTPException(404, {"error": "session_not_found"})
            activated_at = _now()
            expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            c.execute("UPDATE aios_subscription SET status='active', stripe_sig=?, activated_at=?, expires_at=? WHERE session_id=?",
                      (req.stripe_sig, activated_at, expires_at, req.session_id))
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "source": "fallback_local",
        "subscription_id": sub["subscription_id"],
        "subscription_status": "active",
        "plan": sub["plan"],
        "industry": sub["industry"],
        "sku_code": sub["sku_code"],
        "amount_cny": sub["amount_cny"],
        "activated_at": activated_at,
        "expires_at": expires_at,
    }


@router.get("/payment/subscription/{tenant_id}")
async def aios_subscription(tenant_id: str):
    ok, data = await _aios_request("GET", f"/api/aios/v1/payment/subscription/{tenant_id}")
    if ok:
        return {"status": "ok", "source": "aios", **data}
    c = _conn()
    try:
        sub = c.execute("SELECT * FROM aios_subscription WHERE tenant_id=? ORDER BY created_at DESC LIMIT 1",
                        (tenant_id,)).fetchone()
        if not sub:
            return {"status": "ok", "tenant_id": tenant_id, "subscription": None,
                    "msg": "no subscription; please checkout first"}
        return {"status": "ok", "source": "fallback_local", "subscription": dict(sub)}
    finally:
        c.close()


# ---------------------------------------------------------------------------
# Bridge 状态 — 健康 + 路由 fallback 计数
# ---------------------------------------------------------------------------
@router.get("/bridge/health")
async def bridge_health():
    # 探测 AIOS
    aios_ok, aios_info = await _aios_request("GET", "/api/aios/v1/health")
    c = _conn()
    try:
        incidents_n = c.execute("SELECT COUNT(*) AS n FROM bridge_incident").fetchone()["n"]
        sub_n = c.execute("SELECT COUNT(*) AS n FROM aios_subscription").fetchone()["n"]
        user_n = c.execute("SELECT COUNT(*) AS n FROM aios_user").fetchone()["n"]
    finally:
        c.close()
    return {
        "status": "ok",
        "bridge_module": "aios_bridge_v1",
        "aios_base_url": AIOS_BASE_URL,
        "aios_reachable": aios_ok,
        "aios_info": aios_info if aios_ok else {"error": aios_info.get("error", "unknown")},
        "fallback_strategy": "local SQLite when AIOS unreachable (incident logged)",
        "incidents_total": incidents_n,
        "local_state": {"aios_users": user_n, "aios_subscriptions": sub_n},
        "12_skus_loaded": len(_12_SKU),
        "endpoints_proxied": [
            "POST /auth/register", "POST /auth/login", "GET /auth/verify",
            "POST /payment/checkout", "POST /payment/webhook", "GET /payment/subscription/{tenant}",
        ],
        "version": "v1.0 · 2026-09-25 R288",
    }


_init_db()
print(f"[v_aios_bridge_v1] loaded. AIOS={AIOS_BASE_URL}, fallback=local SQLite, 12 SKU ready, JWT HS256, 5 roles × 4 industries.")
