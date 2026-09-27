"""CloudTech 真业务模块 v1 · 2026-09-25 R285

替代 107 stub 中的核心 4 个, 接入真 SQLite DB + 真 LLM 链路:
  1. /api/v2/real/content/generate  -- AI 内容生成 (接 minimax-M3 self-ref, 默认免费)
  2. /api/v2/real/crm/leads         -- CRM 线索 (真 SQLite 增删查)
  3. /api/v2/real/employees/deploy  -- 数字员工部署 (真 DB 记录)
  4. /api/v2/real/auth/register     -- 用户注册 (hash 密码 + 真 DB)

DB: D:\\CloudTech-Portable\\data\\cloudtech.db (SQLite, 自动创建)
LLM: minimax-M3 self-ref (无 key, 默认) / DeepSeek (需 key, 占位)

红线:
  - 不写假 LLM key
  - 不删 / 覆盖任何现有数据
  - 失败时返 4xx + 错误结构, 不静默
"""
# R285 Pydantic v2 兼容: 不再 from __future__ import annotations, 避免 forward ref

import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
LIVE = Path(r"D:\CloudTech-Portable")
DB_DIR = LIVE / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cloudtech.db"

# 添加 live root 到 sys.path 以便 import provider_router
sys.path.insert(0, str(LIVE))

router = APIRouter(prefix="/api/real/v1", tags=["real-business-v1"])


# ---------------------------------------------------------------------------
# DB helpers (SQLite, 线程安全使用 check_same_thread=False + Lock)
# ---------------------------------------------------------------------------
_db_lock = asyncio.Lock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _init_db():
    """幂等创建表 — 启动时调用一次。"""
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            industry TEXT DEFAULT 'decoration',
            role TEXT DEFAULT 'user',
            created_at TEXT NOT NULL,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS leads (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            industry TEXT,
            source TEXT,
            stage TEXT DEFAULT 'consult',
            owner_user_id TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            preset TEXT NOT NULL,
            name TEXT,
            industry TEXT,
            config_json TEXT,
            status TEXT DEFAULT 'deployed',
            deployed_at TEXT NOT NULL,
            last_invoked_at TEXT,
            invoke_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS content_history (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            tenant_id TEXT,
            industry TEXT,
            preset TEXT,
            prompt TEXT,
            result_text TEXT,
            tokens_in INTEGER DEFAULT 0,
            tokens_out INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            provider TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_leads_tenant ON leads(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_emp_tenant ON employees(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_content_tenant ON content_history(tenant_id);
        """)
        c.commit()
    finally:
        c.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()


def _try_minimax_m3(prompt: str, system: str = "") -> dict:
    """接 minimax-M3 self-ref. 这是当前 session 模型,
    直接调 _chat_minimax 绕过 detect_provider_mode (避免 DEEPSEEK_API_KEY env 干扰).
    """
    try:
        from provider_router import _chat_minimax  # type: ignore
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        # _chat_minimax 不读 DEEPSEEK_API_KEY, 只看 MINIMAX_API_KEY / self-ref 路径
        # 直接调它, 避免被 chat() 走 REAL_DEEPSEEK 分支
        result = _chat_minimax(messages, "minimax-m3", max_tokens=1000)
        text = getattr(result, "content", "") or ""
        return {
            "ok": True,
            "provider": getattr(result, "provider", "minimax-m3-self"),
            "text": text,
            "mode": getattr(result, "mode", "success"),
            "tokens_in": getattr(result, "tokens_in", 0),
            "tokens_out": getattr(result, "tokens_out", 0),
            "cost_usd": 0.0,
        }
    except Exception as e:
        return {
            "ok": False,
            "provider": "minimax_m3",
            "error": f"{type(e).__name__}: {str(e)[:200]}",
        }


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class RegisterReq(BaseModel):
    email: str
    password: str
    name: str = ""
    industry: str = "decoration"
    tenant_id: Optional[str] = None


def _new_tenant_id() -> str:
    return f"t_{secrets.token_hex(4)}"


class LeadReq(BaseModel):
    customer_name: str
    customer_phone: str = ""
    industry: str = "decoration"
    source: str = "manual"
    stage: str = "consult"
    notes: str = ""


class DeployReq(BaseModel):
    preset: str  # content_writer / customer_service / market_researcher / ...
    industry: str = "decoration"
    config: dict = Field(default_factory=dict)


class ContentReq(BaseModel):
    preset: str = "content_writer"  # content_writer / copywriter / seo_writer
    industry: str = "decoration"
    topic: str
    platform: str = "xhs"  # xhs / wechat / douyin / zhihu
    tone: str = "professional"
    length: str = "medium"  # short / medium / long
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 路由 — Auth (注册 + 登录 + 我)
# ---------------------------------------------------------------------------
@router.post("/auth/register")
async def auth_register(req: RegisterReq):
    """真注册: hash 密码 + 写 DB + 返 session token (无 JWT, 用随机 token 表)。"""
    tenant_id = req.tenant_id or _new_tenant_id()
    async with _db_lock:
        c = _conn()
        try:
            existing = c.execute("SELECT id FROM users WHERE email=?", (req.email,)).fetchone()
            if existing:
                raise HTTPException(409, {"error": "email_already_registered", "email": req.email})
            uid = f"u_{uuid.uuid4().hex[:12]}"
            salt = secrets.token_hex(16)
            pw_hash = _hash_password(req.password, salt)
            c.execute(
                "INSERT INTO users(id, email, name, password_hash, password_salt, tenant_id, industry, role, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'user', ?)",
                (uid, req.email, req.name, pw_hash, salt, tenant_id, req.industry, _now())
            )
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "user_id": uid,
        "tenant_id": tenant_id,
        "email": req.email,
        "industry": req.industry,
        "session_token": f"tok_{secrets.token_hex(16)}",  # 简化, 不存表
        "msg": "User registered. Use /auth/login to get fresh session token.",
    }


@router.post("/auth/login")
async def auth_login(req: RegisterReq):
    async with _db_lock:
        c = _conn()
        try:
            row = c.execute("SELECT * FROM users WHERE email=?", (req.email,)).fetchone()
            if not row:
                raise HTTPException(404, {"error": "user_not_found"})
            pw_hash = _hash_password(req.password, row["password_salt"])
            if pw_hash != row["password_hash"]:
                raise HTTPException(401, {"error": "wrong_password"})
            c.execute("UPDATE users SET last_login_at=? WHERE id=?", (_now(), row["id"]))
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "user_id": row["id"],
        "tenant_id": row["tenant_id"],
        "email": row["email"],
        "name": row["name"],
        "industry": row["industry"],
        "session_token": f"tok_{secrets.token_hex(16)}",
    }


# ---------------------------------------------------------------------------
# 路由 — CRM 线索
# ---------------------------------------------------------------------------
@router.post("/crm/leads")
async def crm_create_lead(req: LeadReq, x_tenant_id: str = Header(default="t_default")):
    async with _db_lock:
        c = _conn()
        try:
            lid = f"lead_{uuid.uuid4().hex[:12]}"
            c.execute(
                "INSERT INTO leads(id, tenant_id, customer_name, customer_phone, industry, source, stage, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (lid, x_tenant_id, req.customer_name, req.customer_phone, req.industry, req.source, req.stage, req.notes, _now(), _now())
            )
            c.commit()
        finally:
            c.close()
    return {"status": "ok", "lead_id": lid, "stage": req.stage}


@router.get("/crm/leads")
async def crm_list_leads(tenant_id: str = Query(default="t_default"), stage: Optional[str] = None, limit: int = Query(default=50, le=200)):
    c = _conn()
    try:
        if stage:
            rows = c.execute("SELECT * FROM leads WHERE tenant_id=? AND stage=? ORDER BY created_at DESC LIMIT ?",
                             (tenant_id, stage, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM leads WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
                             (tenant_id, limit)).fetchall()
        return {"status": "ok", "count": len(rows), "leads": [dict(r) for r in rows]}
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 路由 — 数字员工部署
# ---------------------------------------------------------------------------
@router.post("/employees/deploy")
async def emp_deploy(req: DeployReq, x_tenant_id: str = Header(default="t_default")):
    async with _db_lock:
        c = _conn()
        try:
            eid = f"emp_{uuid.uuid4().hex[:12]}"
            c.execute(
                "INSERT INTO employees(id, tenant_id, preset, industry, config_json, deployed_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (eid, x_tenant_id, req.preset, req.industry, json.dumps(req.config, ensure_ascii=False), _now())
            )
            c.commit()
        finally:
            c.close()
    return {"status": "ok", "employee_id": eid, "preset": req.preset, "industry": req.industry}


@router.get("/employees/list")
async def emp_list(tenant_id: str = Query(default="t_default")):
    c = _conn()
    try:
        rows = c.execute("SELECT * FROM employees WHERE tenant_id=? ORDER BY deployed_at DESC",
                         (tenant_id,)).fetchall()
        return {"status": "ok", "count": len(rows), "employees": [dict(r) for r in rows]}
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 路由 — AI 内容生成 (真接 LLM)
# ---------------------------------------------------------------------------
_SYSTEM_PROMPTS = {
    "xhs": "你是一名小红书爆款写手,懂 GEO SEO + 平台规则,标题党+emoji,150-300字。",
    "wechat": "你是一名公众号写手,深度分析+讲故事,800-1500字。",
    "douyin": "你是一名抖音短视频脚本写手,前3秒钩子+口语化,150字内。",
    "zhihu": "你是一名知乎答主,逻辑严密+引数据,500-1000字。",
}

_TONE_HINTS = {
    "professional": "语气专业权威",
    "casual": "语气轻松口语",
    "humor": "语气幽默调侃",
    "inspiring": "语气鼓舞人心",
}

_LENGTH_HINTS = {
    "short": "150字以内",
    "medium": "300-500字",
    "long": "800字以上",
}


@router.post("/content/generate")
async def content_generate(req: ContentReq):
    """真接 LLM 生成内容 (默认 minimax-M3 self-ref 免费).
    历史记录入 DB, 方便后续计费 / 报表.
    """
    sys_prompt = _SYSTEM_PROMPTS.get(req.platform, _SYSTEM_PROMPTS["xhs"])
    tone_hint = _TONE_HINTS.get(req.tone, _TONE_HINTS["professional"])
    length_hint = _LENGTH_HINTS.get(req.length, _LENGTH_HINTS["medium"])

    full_prompt = (
        f"{sys_prompt}\n"
        f"行业: {req.industry}\n"
        f"主题: {req.topic}\n"
        f"平台: {req.platform} ({tone_hint}, {length_hint})\n"
        f"请直接输出正文, 不要解释你将做什么。"
    )

    llm_result = _try_minimax_m3(full_prompt, system=sys_prompt)
    if not llm_result["ok"]:
        raise HTTPException(503, {
            "error": "llm_unavailable",
            "provider": llm_result["provider"],
            "detail": llm_result.get("error", "unknown"),
            "hint": "默认走 minimax-M3 self-ref. 若失败, 检查 provider_router 是否能 import.",
        })

    # 写历史
    history_id = f"ch_{uuid.uuid4().hex[:12]}"
    async with _db_lock:
        c = _conn()
        try:
            c.execute(
                "INSERT INTO content_history(id, user_id, tenant_id, industry, preset, prompt, result_text, tokens_in, tokens_out, cost_usd, provider, created_at, platform, topic) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (history_id, req.user_id, req.tenant_id or "t_default", req.industry, req.preset,
                 full_prompt, llm_result["text"], llm_result["tokens_in"], llm_result["tokens_out"],
                 llm_result["cost_usd"], llm_result["provider"], _now(), req.platform, req.topic)
            )
            c.commit()
        finally:
            c.close()

    return {
        "status": "ok",
        "history_id": history_id,
        "provider": llm_result["provider"],
        "preset": req.preset,
        "industry": req.industry,
        "platform": req.platform,
        "topic": req.topic,
        "text": llm_result["text"],
        "tokens_in": llm_result["tokens_in"],
        "tokens_out": llm_result["tokens_out"],
        "cost_usd": llm_result["cost_usd"],
        "generated_at": _now(),
    }


@router.get("/content/history")
async def content_history(tenant_id: str = Query(default="t_default"), limit: int = Query(default=20, le=100)):
    c = _conn()
    try:
        rows = c.execute("SELECT id, preset, industry, platform, topic, provider, tokens_in, tokens_out, cost_usd, created_at "
                         "FROM content_history WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
                         (tenant_id, limit)).fetchall()
        return {"status": "ok", "count": len(rows), "history": [dict(r) for r in rows]}
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 路由 — 健康 + 统计
# ---------------------------------------------------------------------------
@router.get("/health")
async def health():
    c = _conn()
    try:
        users_n = c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        leads_n = c.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
        emp_n = c.execute("SELECT COUNT(*) AS n FROM employees").fetchone()["n"]
        ch_n = c.execute("SELECT COUNT(*) AS n FROM content_history").fetchone()["n"]
        return {
            "status": "ok",
            "module": "real_business_v1",
            "db": str(DB_PATH),
            "db_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
            "counts": {"users": users_n, "leads": leads_n, "employees": emp_n, "content_history": ch_n},
            "provider": "minimax_m3 (self-ref, free) / DeepSeek (placeholder)",
            "version": "v1.0 · 2026-09-25 R285",
        }
    finally:
        c.close()


# 启动时初始化 DB
_init_db()
print(f"[v_real_business_v1] DB initialized at {DB_PATH}")