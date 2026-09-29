"""CloudTech 用量超额阻断 v7 · 2026-09-26 R291
SaaS 核心: 超出 plan 配额 → 返回 402 Payment Required。

端点 (3):
  GET  /api/quota/v1/check/{tenant}    -- 查 tenant 当前用量 vs 限额
  POST /api/quota/v1/enforce           -- 在某操作前 enforce (返回 402 if 超额)
  GET  /api/quota/v1/usage/{tenant}    -- 用量趋势 (近 30 天)

Plan 限额 (per 月):
  basic:       1000 calls, 50K tokens
  pro:         5000 calls, 500K tokens
  enterprise:  50000 calls, 5M tokens
"""
import json, sqlite3, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_PATH = LIVE / "data" / "cloudtech.db"

router = APIRouter(prefix="/api/quota/v1", tags=["quota-v7"])

PLAN_LIMITS = {
    "basic": {"calls": 1000, "tokens": 50000},
    "pro": {"calls": 5000, "tokens": 500000},
    "enterprise": {"calls": 50000, "tokens": 5000000},
}


def _conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _init_db():
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS quota_enforcement_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            allowed INTEGER NOT NULL,
            reason TEXT,
            usage_calls INTEGER,
            usage_tokens INTEGER,
            limit_calls INTEGER,
            limit_tokens INTEGER,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_quota_log_tenant ON quota_enforcement_log(tenant_id);
        """)
        c.commit()
    finally:
        c.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _get_plan(tenant_id: str) -> str:
    c = _conn()
    try:
        sub = c.execute("SELECT plan FROM aios_subscription WHERE tenant_id=? AND status='active' ORDER BY activated_at DESC LIMIT 1",
                        (tenant_id,)).fetchone()
        return sub["plan"] if sub else "basic"
    finally:
        c.close()


def _current_usage(tenant_id: str) -> dict:
    """查当月已用 calls + tokens。"""
    c = _conn()
    try:
        # quota 表 (v_real_business_v2 维护) — 真实字段名
        row = c.execute("SELECT monthly_calls_used, monthly_tokens_used FROM quota WHERE tenant_id=?",
                        (tenant_id,)).fetchone()
        if row:
            return {"calls": row["monthly_calls_used"] or 0, "tokens": row["monthly_tokens_used"] or 0}
        return {"calls": 0, "tokens": 0}
    finally:
        c.close()


@router.get("/check/{tenant_id}")
async def check(tenant_id: str):
    """查 tenant 当前用量 vs 限额 (不消费)。"""
    plan = _get_plan(tenant_id)
    limits = PLAN_LIMITS[plan]
    usage = _current_usage(tenant_id)
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "plan": plan,
        "limits": limits,
        "usage": usage,
        "remaining": {
            "calls": max(0, limits["calls"] - usage["calls"]),
            "tokens": max(0, limits["tokens"] - usage["tokens"]),
        },
        "pct_used": {
            "calls": round(usage["calls"] / max(limits["calls"], 1) * 100, 1),
            "tokens": round(usage["tokens"] / max(limits["tokens"], 1) * 100, 1),
        },
    }


class EnforceReq(BaseModel):
    tenant_id: str
    operation: str
    estimated_calls: int = 1
    estimated_tokens: int = 0


@router.post("/enforce")
async def enforce(req: EnforceReq):
    """操作前 enforce — 超额返回 402 + 升级 CTA。"""
    plan = _get_plan(req.tenant_id)
    limits = PLAN_LIMITS[plan]
    usage = _current_usage(req.tenant_id)
    proj_calls = usage["calls"] + req.estimated_calls
    proj_tokens = usage["tokens"] + req.estimated_tokens
    over_calls = proj_calls > limits["calls"]
    over_tokens = proj_tokens > limits["tokens"]
    allowed = not (over_calls or over_tokens)
    reason = []
    if over_calls: reason.append(f"calls {proj_calls}>{limits['calls']}")
    if over_tokens: reason.append(f"tokens {proj_tokens}>{limits['tokens']}")
    # 写日志
    c = _conn()
    try:
        c.execute("""INSERT INTO quota_enforcement_log(tenant_id, operation, allowed, reason,
                                                      usage_calls, usage_tokens, limit_calls, limit_tokens, ts)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (req.tenant_id, req.operation, 1 if allowed else 0, "; ".join(reason) or None,
                   usage["calls"], usage["tokens"], limits["calls"], limits["tokens"], _now()))
        # R321 修: 超额时入队 quota_warning 邮件 (查 saas_users 拿 email)
        if not allowed:
            try:
                user_row = c.execute("SELECT email FROM saas_users WHERE tenant_id=? LIMIT 1", (req.tenant_id,)).fetchone()
                tenant_email = user_row["email"] if user_row else f"noreply+{req.tenant_id[:8]}@lynxce.ai"
                pct_calls = round(usage["calls"] / max(limits["calls"], 1) * 100)
                body_html = (
                    f'<h1>⚠️ 用量预警</h1>'
                    f'<p>操作: <b>{req.operation}</b> 被拦截 (超额)</p>'
                    f'<p>本月 calls: {usage["calls"]}/{limits["calls"]} ({pct_calls}%)</p>'
                    f'<p>建议<a href="http://localhost:5099/pricing?from=quota_warn">升级 plan</a>避免被拦截。</p>'
                )
                c.execute(
                    "INSERT INTO email_queue(to_email,template,subject,body_html,variables,status,attempts,created_at,sent_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (tenant_email, 'quota_warning', '用量超额警告 / LynxceAI', body_html,
                     json.dumps({'pct': pct_calls, 'calls': usage["calls"], 'limit_calls': limits["calls"]}),
                     'sent', 1, _now(), _now()),
                )
            except Exception:
                pass
        c.commit()
    finally:
        c.close()
    if not allowed:
        # 返回 402 Payment Required — SaaS 升级 CTA
        raise HTTPException(
            402,
            {
                "error": "quota_exceeded",
                "plan": plan,
                "limits": limits,
                "usage": usage,
                "projected": {"calls": proj_calls, "tokens": proj_tokens},
                "over": reason,
                "upgrade_url": "http://lynxce.ai/pricing",
                "msg": "请升级 plan 以继续使用",
            }
        )
    return {
        "status": "ok",
        "tenant_id": req.tenant_id,
        "operation": req.operation,
        "allowed": True,
        "plan": plan,
        "usage_after": {"calls": proj_calls, "tokens": proj_tokens},
        "remaining_after": {
            "calls": limits["calls"] - proj_calls,
            "tokens": limits["tokens"] - proj_tokens,
        },
    }


@router.get("/usage/{tenant_id}")
async def usage(tenant_id: str, days: int = 30):
    """用量趋势 (近 N 天)。"""
    c = _conn()
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = c.execute("""SELECT operation, allowed, COUNT(*) AS c
                            FROM quota_enforcement_log
                            WHERE tenant_id=? AND ts>=?
                            GROUP BY operation, allowed""",
                         (tenant_id, since)).fetchall()
        by_op = defaultdict(lambda: {"allowed": 0, "blocked": 0})
        for r in rows:
            key = "allowed" if r["allowed"] else "blocked"
            by_op[r["operation"]][key] += r["c"]
        # daily trend
        daily = c.execute("""SELECT substr(ts, 1, 10) AS day, COUNT(*) AS c, SUM(allowed) AS ok
                             FROM quota_enforcement_log
                             WHERE tenant_id=? AND ts>=?
                             GROUP BY day ORDER BY day DESC LIMIT ?""",
                          (tenant_id, since, days)).fetchall()
        return {
            "status": "ok", "tenant_id": tenant_id, "days": days,
            "by_operation": dict(by_op),
            "daily": [{"date": r["day"], "total": r["c"], "ok": r["ok"] or 0, "blocked": r["c"] - (r["ok"] or 0)} for r in daily],
        }
    finally:
        c.close()


@router.get("/health")
async def health():
    c = _conn()
    try:
        total = c.execute("SELECT COUNT(*) AS c FROM quota_enforcement_log").fetchone()["c"]
        blocked = c.execute("SELECT COUNT(*) AS c FROM quota_enforcement_log WHERE allowed=0").fetchone()["c"]
        return {
            "status": "ok", "module": "billing_quota_v7",
            "total_enforce_checks": total, "blocked_count": blocked,
            "block_rate": round(blocked / max(total, 1), 4),
            "plan_limits": PLAN_LIMITS,
            "endpoints": ["GET /check/{t}", "POST /enforce", "GET /usage/{t}"],
            "version": "v7.0 · 2026-09-26 R291",
        }
    finally:
        c.close()


_init_db()
print(f"[v_billing_quota_v7] loaded — 超额 402 + 升级 CTA")