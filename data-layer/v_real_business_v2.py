"""CloudTech 真业务模块 v2 · 2026-09-25 R286

v1 (auth/crm/emp/content) 基础上扩展 8 个端点:
  1. GET /api/real/v2/crm/leads/{id}         -- 单 lead 详情
  2. PATCH /api/real/v2/crm/leads/{id}       -- 更新 stage / 字段
  3. DELETE /api/real/v2/crm/leads/{id}       -- 删 lead (软删)
  4. POST /api/real/v2/employees/{id}/invoke -- 真调 LLM 走员工 (员工即 wrapper)
  5. POST /api/real/v2/billing/charge        -- 真计费扣 quota
  6. GET /api/real/v2/billing/quota/{tenant} -- 查 tenant quota
  7. GET /api/real/v2/stats/{tenant}         -- 统计 (leads/content/employees)
  8. POST /api/real/v2/search/leads          -- 多条件搜索 leads

员工 invoke 链路:
  - 加载员工 config + preset
  - 拼 system_prompt (根据 preset)
  - 调 _chat_minimax 真生成
  - 写 history + 更新员工 last_invoked_at + invoke_count++
"""
import asyncio
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel

# 复用 v1 的 DB / helper
sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_DIR = LIVE / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cloudtech.db"

router = APIRouter(prefix="/api/real/v2", tags=["real-business-v2"])


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


_db_lock = asyncio.Lock()


def _init_db():
    """幂等创建 v2 新表 + v1 表增量列."""
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS quota (
            tenant_id TEXT PRIMARY KEY,
            monthly_calls_limit INTEGER DEFAULT 5000,
            monthly_calls_used INTEGER DEFAULT 0,
            monthly_tokens_limit INTEGER DEFAULT 2000000,
            monthly_tokens_used INTEGER DEFAULT 0,
            plan TEXT DEFAULT 'free',
            reset_at TEXT
        );

        CREATE TABLE IF NOT EXISTS invoice (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_id TEXT,
            amount_usd REAL,
            calls INTEGER,
            tokens_in INTEGER,
            tokens_out INTEGER,
            provider TEXT,
            description TEXT,
            created_at TEXT NOT NULL
        );

        -- v1 表增量 (软删字段 + 时间戳)
        -- leads 加 deleted_at
        """)
        c.commit()
        # ALTER (幂等 — 失败就忽略)
        for tbl, col, defval in [
            ("leads", "deleted_at", "NULL"),
            ("employees", "last_invoked_at", "NULL"),
            ("employees", "invoke_count", "0"),
            ("users", "plan", "'free'"),
        ]:
            try:
                c.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} TEXT DEFAULT {defval}")
            except Exception:
                pass  # column already exists
        c.commit()
    finally:
        c.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pydantic models (Pydantic v2 strict, no forward refs)
# ---------------------------------------------------------------------------
class LeadUpdateReq(BaseModel):
    stage: Optional[str] = None
    notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    source: Optional[str] = None


class ChargeReq(BaseModel):
    calls: int = 1
    tokens_in: int = 0
    tokens_out: int = 0
    provider: str = "minimax_m3"
    description: str = ""


class InvokeReq(BaseModel):
    topic: str
    platform: str = "xhs"
    tone: str = "professional"
    length: str = "medium"


# ---------------------------------------------------------------------------
# 1-3: CRM lead 详情/更新/软删
# ---------------------------------------------------------------------------
@router.get("/crm/leads/{lead_id}")
async def crm_get_lead(lead_id: str):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM leads WHERE id=? AND deleted_at IS NULL", (lead_id,)).fetchone()
        if not row:
            raise HTTPException(404, {"error": "lead_not_found", "lead_id": lead_id})
        return {"status": "ok", "lead": dict(row)}
    finally:
        c.close()


@router.patch("/crm/leads/{lead_id}")
async def crm_update_lead(lead_id: str, req: LeadUpdateReq):
    async with _db_lock:
        c = _conn()
        try:
            row = c.execute("SELECT id FROM leads WHERE id=? AND deleted_at IS NULL", (lead_id,)).fetchone()
            if not row:
                raise HTTPException(404, {"error": "lead_not_found", "lead_id": lead_id})
            # 拼 SET 子句 (只更新给定字段)
            fields, values = [], []
            for k, v in req.model_dump(exclude_none=True).items():
                fields.append(f"{k}=?")
                values.append(v)
            if not fields:
                return {"status": "ok", "lead_id": lead_id, "msg": "no fields to update"}
            fields.append("updated_at=?")
            values.append(_now())
            values.append(lead_id)
            c.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id=?", values)
            c.commit()
        finally:
            c.close()
    return {"status": "ok", "lead_id": lead_id, "updated_fields": list(req.model_dump(exclude_none=True).keys())}


@router.delete("/crm/leads/{lead_id}")
async def crm_delete_lead(lead_id: str):
    async with _db_lock:
        c = _conn()
        try:
            row = c.execute("SELECT id FROM leads WHERE id=? AND deleted_at IS NULL", (lead_id,)).fetchone()
            if not row:
                raise HTTPException(404, {"error": "lead_not_found", "lead_id": lead_id})
            c.execute("UPDATE leads SET deleted_at=? WHERE id=?", (_now(), lead_id))
            c.commit()
        finally:
            c.close()
    return {"status": "ok", "lead_id": lead_id, "msg": "soft-deleted", "deleted_at": _now()}


# ---------------------------------------------------------------------------
# 4: 员工 invoke (真调 LLM)
# ---------------------------------------------------------------------------
_EMPLOYEE_PROMPTS = {
    "content_writer": "你是一名专业内容写手,懂 GEO SEO + 平台规则。",
    "customer_service": "你是一名客服专员,友好专业,快速解决问题。",
    "market_researcher": "你是一名市场调研员,懂数据+用户洞察。",
    "sales_assistant": "你是一名销售助理,懂客户心理+促成技巧。",
    "seo_writer": "你是一名 SEO 写手,关键词+结构化内容。",
    "copywriter": "你是一名广告文案,短句+情绪+转化。",
}


@router.post("/employees/{employee_id}/invoke")
async def emp_invoke(employee_id: str, req: InvokeReq):
    """员工 invoke: 加载员工 config + preset → 拼 prompt → 真调 LLM."""
    async with _db_lock:
        c = _conn()
        try:
            row = c.execute("SELECT * FROM employees WHERE id=? AND status='deployed'", (employee_id,)).fetchone()
            if not row:
                raise HTTPException(404, {"error": "employee_not_found", "employee_id": employee_id})
            preset = row["preset"]
            industry = row["industry"]
            config = json.loads(row["config_json"] or "{}")
        finally:
            c.close()

    # 拼 system_prompt (preset + config)
    sys_prompt = _EMPLOYEE_PROMPTS.get(preset, _EMPLOYEE_PROMPTS["content_writer"])
    extra_platform = config.get("platforms", [req.platform])
    if isinstance(extra_platform, list) and extra_platform:
        platform = extra_platform[0]
    else:
        platform = req.platform
    tone = config.get("tone", req.tone)
    sys_prompt += f"\n行业: {industry}\n平台: {platform}\n语气: {tone}"

    # 真调 LLM
    try:
        from provider_router import _chat_minimax  # type: ignore
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"主题: {req.topic}\n请直接输出正文, 不要解释你将做什么。"},
        ]
        result = _chat_minimax(messages, "minimax-m3", max_tokens=1000)
        text = getattr(result, "content", "") or ""
        provider_name = getattr(result, "provider", "minimax-m3-self")
        tokens_in = getattr(result, "tokens_in", 0)
        tokens_out = getattr(result, "tokens_out", 0)
    except Exception as e:
        raise HTTPException(503, {"error": "llm_unavailable", "detail": str(e)[:200]})

    # 更新员工 last_invoked_at + invoke_count
    history_id = f"ch_{uuid.uuid4().hex[:12]}"
    async with _db_lock:
        c = _conn()
        try:
            c.execute("UPDATE employees SET last_invoked_at=?, invoke_count=invoke_count+1 WHERE id=?",
                      (_now(), employee_id))
            c.execute(
                "INSERT INTO content_history(id, user_id, tenant_id, industry, preset, prompt, result_text, tokens_in, tokens_out, cost_usd, provider, created_at, platform, topic) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (history_id, None, row["tenant_id"], industry, preset,
                 sys_prompt + "\n主题: " + req.topic, text, tokens_in, tokens_out,
                 0.0, provider_name, _now(), platform, req.topic)
            )
            c.commit()
        finally:
            c.close()

    return {
        "status": "ok",
        "employee_id": employee_id,
        "preset": preset,
        "industry": industry,
        "platform": platform,
        "history_id": history_id,
        "text": text,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "provider": provider_name,
    }


# ---------------------------------------------------------------------------
# 5-6: 真计费 + quota
# ---------------------------------------------------------------------------
@router.post("/billing/charge")
async def billing_charge(req: ChargeReq, x_tenant_id: str = Header(default="t_default")):
    async with _db_lock:
        c = _conn()
        try:
            # 确保 quota 行存在
            q = c.execute("SELECT * FROM quota WHERE tenant_id=?", (x_tenant_id,)).fetchone()
            if not q:
                c.execute("INSERT INTO quota(tenant_id, plan) VALUES (?, 'free')", (x_tenant_id,))
                c.commit()
                q = c.execute("SELECT * FROM quota WHERE tenant_id=?", (x_tenant_id,)).fetchone()

            # 校验 quota
            new_calls = q["monthly_calls_used"] + req.calls
            new_tokens = q["monthly_tokens_used"] + req.tokens_in + req.tokens_out
            if new_calls > q["monthly_calls_limit"]:
                raise HTTPException(402, {
                    "error": "quota_exceeded",
                    "type": "calls",
                    "used": q["monthly_calls_used"],
                    "limit": q["monthly_calls_limit"],
                })
            if new_tokens > q["monthly_tokens_limit"]:
                raise HTTPException(402, {
                    "error": "quota_exceeded",
                    "type": "tokens",
                    "used": q["monthly_tokens_used"],
                    "limit": q["monthly_tokens_limit"],
                })

            # 扣 quota + 写 invoice
            c.execute("UPDATE quota SET monthly_calls_used=?, monthly_tokens_used=? WHERE tenant_id=?",
                      (new_calls, new_tokens, x_tenant_id))
            inv_id = f"inv_{uuid.uuid4().hex[:12]}"
            cost_usd = (req.tokens_in + req.tokens_out) * 0.000001  # 估算
            c.execute(
                "INSERT INTO invoice(id, tenant_id, amount_usd, calls, tokens_in, tokens_out, provider, description, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (inv_id, x_tenant_id, cost_usd, req.calls, req.tokens_in, req.tokens_out,
                 req.provider, req.description, _now())
            )
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "invoice_id": inv_id,
        "tenant_id": x_tenant_id,
        "calls_used": new_calls,
        "calls_limit": q["monthly_calls_limit"],
        "tokens_used": new_tokens,
        "tokens_limit": q["monthly_tokens_limit"],
        "amount_usd": round(cost_usd, 6),
    }


@router.get("/billing/quota/{tenant_id}")
async def billing_quota(tenant_id: str):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM quota WHERE tenant_id=?", (tenant_id,)).fetchone()
        if not row:
            return {"status": "ok", "tenant_id": tenant_id, "plan": "free",
                    "calls_used": 0, "calls_limit": 5000,
                    "tokens_used": 0, "tokens_limit": 2000000,
                    "msg": "no quota row yet, defaults returned"}
        return {"status": "ok", "tenant_id": tenant_id, **dict(row)}
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 7: 统计
# ---------------------------------------------------------------------------
@router.get("/stats/{tenant_id}")
async def stats(tenant_id: str):
    c = _conn()
    try:
        out = {"tenant_id": tenant_id}
        out["users"] = c.execute("SELECT COUNT(*) AS n FROM users WHERE tenant_id=?", (tenant_id,)).fetchone()["n"]
        out["leads_total"] = c.execute("SELECT COUNT(*) AS n FROM leads WHERE tenant_id=?", (tenant_id,)).fetchone()["n"]
        out["leads_active"] = c.execute("SELECT COUNT(*) AS n FROM leads WHERE tenant_id=? AND deleted_at IS NULL", (tenant_id,)).fetchone()["n"]
        out["employees_deployed"] = c.execute("SELECT COUNT(*) AS n FROM employees WHERE tenant_id=?", (tenant_id,)).fetchone()["n"]
        out["content_generated"] = c.execute("SELECT COUNT(*) AS n FROM content_history WHERE tenant_id=?", (tenant_id,)).fetchone()["n"]
        out["tokens_in"] = c.execute("SELECT COALESCE(SUM(tokens_in),0) AS s FROM content_history WHERE tenant_id=?", (tenant_id,)).fetchone()["s"]
        out["tokens_out"] = c.execute("SELECT COALESCE(SUM(tokens_out),0) AS s FROM content_history WHERE tenant_id=?", (tenant_id,)).fetchone()["s"]
        out["invoices"] = c.execute("SELECT COUNT(*) AS n FROM invoice WHERE tenant_id=?", (tenant_id,)).fetchone()["n"]
        out["cost_usd"] = c.execute("SELECT COALESCE(SUM(amount_usd),0) AS s FROM invoice WHERE tenant_id=?", (tenant_id,)).fetchone()["s"]
        return {"status": "ok", **out}
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 8: 搜索 leads
# ---------------------------------------------------------------------------
@router.post("/search/leads")
async def search_leads(
    x_tenant_id: str = Header(default="t_default"),
    stage: Optional[str] = None,
    industry: Optional[str] = None,
    source: Optional[str] = None,
    q: Optional[str] = Query(default=None, description="关键词 (customer_name/notes LIKE)"),
    limit: int = Query(default=50, le=200),
):
    c = _conn()
    try:
        sql = "SELECT * FROM leads WHERE tenant_id=? AND deleted_at IS NULL"
        params = [x_tenant_id]
        if stage:
            sql += " AND stage=?"; params.append(stage)
        if industry:
            sql += " AND industry=?"; params.append(industry)
        if source:
            sql += " AND source=?"; params.append(source)
        if q:
            sql += " AND (customer_name LIKE ? OR notes LIKE ?)"
            params.extend([f"%{q}%", f"%{q}%"])
        sql += " ORDER BY created_at DESC LIMIT ?"; params.append(limit)
        rows = c.execute(sql, params).fetchall()
        return {"status": "ok", "count": len(rows), "leads": [dict(r) for r in rows]}
    finally:
        c.close()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@router.get("/health")
async def health():
    c = _conn()
    try:
        return {
            "status": "ok",
            "module": "real_business_v2",
            "db": str(DB_PATH),
            "db_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
            "tables_v2": ["quota", "invoice"],
            "v1_extensions": ["leads.deleted_at", "employees.last_invoked_at", "employees.invoke_count", "users.plan"],
            "version": "v2.0 · 2026-09-25 R286",
        }
    finally:
        c.close()


_init_db()
print(f"[v_real_business_v2] DB initialized. quota + invoice tables + v1 ALTER applied.")