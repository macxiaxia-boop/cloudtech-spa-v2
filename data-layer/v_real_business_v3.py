"""CloudTech 真业务模块 v3 · 2026-09-25 R287

v1 (auth/crm/emp/content) + v2 (CRM详情/更新/软删/员工invoke/计费/quota/统计/搜索) 基础上扩展:
  1. POST /api/real/v3/employees/bulk_invoke   -- 批量调多个员工 (并发)
  2. POST /api/real/v3/quota/reset_all        -- 月度 quota reset (cron/manual)
  3. POST /api/real/v3/quota/reset            -- 单租户 quota reset
  4. GET  /api/real/v3/invoice/{inv_id}/pdf   -- invoice PDF 导出 (纯 Python, 无外部 lib)
  5. GET  /api/real/v3/invoice/list/{tenant}  -- 租户 invoice 列表
  6. POST /api/real/v3/crm/leads/{id}/stage   -- 快速推进 lead stage (状态机)
  7. POST /api/real/v3/employees/{id}/stats   -- 单员工调用统计 (近 30 天)

员工批量 invoke 链路:
  - 接 [{employee_id, topic, platform?, tone?}] 列表
  - 用 asyncio.gather 并发调 _chat_minimax
  - 每条都写 history + 更新员工 invoke_count
  - 总 tokens / cost 聚合返回
"""
import asyncio
import io
import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, List

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 复用 v1/v2 的 DB / helper
sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_DIR = LIVE / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cloudtech.db"

router = APIRouter(prefix="/api/real/v3", tags=["real-business-v3"])


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
# Pydantic
# ---------------------------------------------------------------------------
class BulkInvokeItem(BaseModel):
    employee_id: str
    topic: str
    platform: str = "xhs"
    tone: str = "professional"
    length: str = "medium"


class BulkInvokeReq(BaseModel):
    items: List[BulkInvokeItem]


class StageAdvanceReq(BaseModel):
    stage: str  # consult → demo → trial → quote → signed → won/lost


# ---------------------------------------------------------------------------
# Lead stage 状态机
# ---------------------------------------------------------------------------
_LEAD_STAGES = ["consult", "demo", "trial", "quote", "signed", "won", "lost"]


# ---------------------------------------------------------------------------
# 1: 批量员工 invoke (asyncio.gather 并发)
# ---------------------------------------------------------------------------
@router.post("/employees/bulk_invoke")
async def emp_bulk_invoke(req: BulkInvokeReq, x_tenant_id: str = Header(default="t_default")):
    """批量并发调多个员工 — 高效批量内容生成."""
    if not req.items:
        raise HTTPException(400, {"error": "empty_items"})
    if len(req.items) > 20:
        raise HTTPException(400, {"error": "too_many_items", "max": 20})

    async def _one(item: BulkInvokeItem) -> dict:
        # 读员工
        c = _conn()
        try:
            row = c.execute("SELECT * FROM employees WHERE id=? AND status='deployed'", (item.employee_id,)).fetchone()
            if not row:
                return {"employee_id": item.employee_id, "ok": False, "error": "employee_not_found"}
            preset = row["preset"]
            industry = row["industry"]
            config = json.loads(row["config_json"] or "{}")
        finally:
            c.close()

        platform = item.platform or (config.get("platforms", ["xhs"])[0] if config.get("platforms") else "xhs")
        tone = item.tone or config.get("tone", "professional")
        sys_prompt = (
            f"你是一名专业{preset},行业 {industry},平台 {platform},语气 {tone}。直接输出正文,不要解释你将做什么。"
        )
        # 真调 LLM (同步阻塞, 包成 to_thread)
        try:
            from provider_router import _chat_minimax  # type: ignore
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"主题: {item.topic}"},
            ]
            # _chat_minimax 是同步函数, 包到 to_thread 避免阻塞 event loop
            result = await asyncio.to_thread(_chat_minimax, messages, "minimax-m3", 1000)
            text = getattr(result, "content", "") or ""
            provider_name = getattr(result, "provider", "minimax-m3-self")
            tokens_in = getattr(result, "tokens_in", 0)
            tokens_out = getattr(result, "tokens_out", 0)
        except Exception as e:
            return {"employee_id": item.employee_id, "ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}

        history_id = f"ch_{uuid.uuid4().hex[:12]}"
        async with _db_lock:
            c = _conn()
            try:
                c.execute("UPDATE employees SET last_invoked_at=?, invoke_count=invoke_count+1 WHERE id=?",
                          (_now(), item.employee_id))
                c.execute(
                    "INSERT INTO content_history(id, user_id, tenant_id, industry, preset, prompt, result_text, tokens_in, tokens_out, cost_usd, provider, created_at, platform, topic) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (history_id, None, x_tenant_id, industry, preset,
                     sys_prompt + "\n主题: " + item.topic, text, tokens_in, tokens_out,
                     0.0, provider_name, _now(), platform, item.topic)
                )
                c.commit()
            finally:
                c.close()
        return {
            "employee_id": item.employee_id,
            "preset": preset,
            "industry": industry,
            "platform": platform,
            "ok": True,
            "history_id": history_id,
            "text": text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "provider": provider_name,
        }

    # 并发调 (max 10 同时)
    sem = asyncio.Semaphore(10)

    async def _bound(item):
        async with sem:
            return await _one(item)

    results = await asyncio.gather(*[_bound(it) for it in req.items], return_exceptions=False)
    ok_n = sum(1 for r in results if r.get("ok"))
    err_n = len(results) - ok_n
    total_t_in = sum(r.get("tokens_in", 0) for r in results if r.get("ok"))
    total_t_out = sum(r.get("tokens_out", 0) for r in results if r.get("ok"))
    return {
        "status": "ok",
        "tenant_id": x_tenant_id,
        "total": len(results),
        "ok": ok_n,
        "err": err_n,
        "total_tokens_in": total_t_in,
        "total_tokens_out": total_t_out,
        "results": results,
    }


# ---------------------------------------------------------------------------
# 2-3: Quota 月度 reset
# ---------------------------------------------------------------------------
@router.post("/quota/reset")
async def quota_reset_one(tenant_id: str = Query(...)):
    async with _db_lock:
        c = _conn()
        try:
            row = c.execute("SELECT tenant_id FROM quota WHERE tenant_id=?", (tenant_id,)).fetchone()
            if not row:
                raise HTTPException(404, {"error": "tenant_no_quota"})
            c.execute("UPDATE quota SET monthly_calls_used=0, monthly_tokens_used=0, reset_at=? WHERE tenant_id=?",
                      (_now(), tenant_id))
            c.commit()
        finally:
            c.close()
    return {"status": "ok", "tenant_id": tenant_id, "reset_at": _now(), "msg": "monthly quota reset"}


@router.post("/quota/reset_all")
async def quota_reset_all():
    """月度 quota 自动 reset (cron 1 号 0 点跑) — 扫所有 tenant."""
    async with _db_lock:
        c = _conn()
        try:
            n = c.execute("UPDATE quota SET monthly_calls_used=0, monthly_tokens_used=0, reset_at=?",
                          (_now(),)).rowcount
            c.commit()
        finally:
            c.close()
    return {"status": "ok", "reset_tenants": n, "reset_at": _now(), "msg": "all tenant monthly quota reset"}


# ---------------------------------------------------------------------------
# 4: Invoice PDF 导出 (纯 Python, 不引入新 lib)
# ---------------------------------------------------------------------------
def _pdf_escape(s: str) -> str:
    """简化 PDF 文本转义."""
    return (s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            .encode("latin-1", errors="replace").decode("latin-1"))


def _generate_invoice_pdf(invoice: dict, tenant: str, plan: str) -> bytes:
    """手写 minimal PDF — 单页, Helvetica, 不依赖 reportlab."""
    lines = [
        f"CloudTech SaaS Invoice",
        f"",
        f"Invoice ID:    {invoice['id']}",
        f"Tenant:        {tenant}",
        f"Plan:          {plan}",
        f"Created at:    {invoice['created_at']}",
        f"",
        f"--- Usage ---",
        f"Calls:         {invoice['calls']}",
        f"Tokens in:     {invoice['tokens_in']}",
        f"Tokens out:    {invoice['tokens_out']}",
        f"Provider:      {invoice['provider']}",
        f"Description:   {invoice['description'][:60]}",
        f"",
        f"--- Billing ---",
        f"Amount:        USD {invoice['amount_usd']:.6f}",
        f"",
        f"Powered by CloudTech SaaS",
        f"CloudTech-Portable v17",
    ]
    # 构造 PDF content stream
    content_parts = ["BT", "/F1 12 Tf"]
    y = 760
    for ln in lines:
        content_parts.append(f"1 0 0 1 50 {y} Tm")
        content_parts.append(f"({_pdf_escape(ln)}) Tj")
        y -= 18
    content_parts.append("ET")
    content_stream = "\n".join(content_parts)

    # 构造 PDF objects
    objs = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj",
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj",
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj",
        f"4 0 obj\n<< /Length {len(content_stream)} >>\nstream\n{content_stream}\nendstream\nendobj",
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj",
    ]
    # 拼接 PDF body
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for o in objs:
        offsets.append(out.tell())
        out.write((o + "\n").encode("latin-1"))
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objs)+1}\n".encode("latin-1"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.write(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("latin-1"))
    return out.getvalue()


@router.get("/invoice/{inv_id}/pdf")
async def invoice_pdf(inv_id: str):
    c = _conn()
    try:
        inv = c.execute("SELECT * FROM invoice WHERE id=?", (inv_id,)).fetchone()
        if not inv:
            raise HTTPException(404, {"error": "invoice_not_found", "invoice_id": inv_id})
        q = c.execute("SELECT plan FROM quota WHERE tenant_id=?", (inv["tenant_id"],)).fetchone()
        plan = q["plan"] if q else "free"
        pdf_bytes = _generate_invoice_pdf(dict(inv), inv["tenant_id"], plan)
    finally:
        c.close()
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{inv_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# 5: Invoice 列表 (按租户)
# ---------------------------------------------------------------------------
@router.get("/invoice/list/{tenant_id}")
async def invoice_list(tenant_id: str, limit: int = Query(default=50, le=200)):
    c = _conn()
    try:
        rows = c.execute(
            "SELECT id, amount_usd, calls, tokens_in, tokens_out, provider, description, created_at "
            "FROM invoice WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        ).fetchall()
        total_amount = sum(r["amount_usd"] for r in rows)
        return {
            "status": "ok",
            "tenant_id": tenant_id,
            "count": len(rows),
            "total_amount_usd": round(total_amount, 6),
            "invoices": [dict(r) for r in rows],
        }
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 6: Lead stage 快速推进 (状态机)
# ---------------------------------------------------------------------------
@router.post("/crm/leads/{lead_id}/stage")
async def crm_advance_stage(lead_id: str, req: StageAdvanceReq):
    if req.stage not in _LEAD_STAGES:
        raise HTTPException(400, {"error": "invalid_stage", "allowed": _LEAD_STAGES})
    async with _db_lock:
        c = _conn()
        try:
            row = c.execute("SELECT id, stage FROM leads WHERE id=? AND deleted_at IS NULL", (lead_id,)).fetchone()
            if not row:
                raise HTTPException(404, {"error": "lead_not_found", "lead_id": lead_id})
            old_stage = row["stage"]
            c.execute("UPDATE leads SET stage=?, updated_at=? WHERE id=?",
                      (req.stage, _now(), lead_id))
            c.commit()
        finally:
            c.close()
    return {
        "status": "ok",
        "lead_id": lead_id,
        "old_stage": old_stage,
        "new_stage": req.stage,
        "transition": f"{old_stage} → {req.stage}",
        "msg": "stage advanced",
    }


# ---------------------------------------------------------------------------
# 7: 单员工调用统计 (近 30 天)
# ---------------------------------------------------------------------------
@router.get("/employees/{employee_id}/stats")
async def emp_stats(employee_id: str, days: int = Query(default=30, le=365)):
    c = _conn()
    try:
        emp = c.execute("SELECT id, preset, industry, invoke_count, last_invoked_at, deployed_at FROM employees WHERE id=?",
                        (employee_id,)).fetchone()
        if not emp:
            raise HTTPException(404, {"error": "employee_not_found"})
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        inv = c.execute("SELECT COUNT(*) AS n, COALESCE(SUM(tokens_in),0) AS ti, COALESCE(SUM(tokens_out),0) AS to_ "
                        "FROM content_history WHERE tenant_id=(SELECT tenant_id FROM employees WHERE id=?) AND preset=? "
                        "AND created_at >= ?", (employee_id, emp["preset"], since)).fetchone()
        history = c.execute("SELECT id, topic, platform, tokens_in, tokens_out, created_at "
                            "FROM content_history WHERE tenant_id=(SELECT tenant_id FROM employees WHERE id=?) "
                            "AND preset=? ORDER BY created_at DESC LIMIT 10",
                            (employee_id, emp["preset"])).fetchall()
        return {
            "status": "ok",
            "employee_id": employee_id,
            "preset": emp["preset"],
            "industry": emp["industry"],
            "lifetime_invoke_count": emp["invoke_count"],
            "last_invoked_at": emp["last_invoked_at"],
            "deployed_at": emp["deployed_at"],
            f"last_{days}d": {
                "calls": inv["n"],
                "tokens_in": inv["ti"],
                "tokens_out": inv["to_"],
            },
            "recent_history": [dict(h) for h in history],
        }
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
            "module": "real_business_v3",
            "db": str(DB_PATH),
            "db_size_bytes": DB_PATH.stat().st_size if DB_PATH.exists() else 0,
            "new_endpoints": [
                "POST /employees/bulk_invoke",
                "POST /quota/reset",
                "POST /quota/reset_all",
                "GET /invoice/{id}/pdf",
                "GET /invoice/list/{tenant}",
                "POST /crm/leads/{id}/stage",
                "GET /employees/{id}/stats",
            ],
            "version": "v3.0 · 2026-09-25 R287",
        }
    finally:
        c.close()


print(f"[v_real_business_v3] loaded — 7 new endpoints: bulk_invoke/reset/reset_all/invoice_pdf/invoice_list/stage/emp_stats")
