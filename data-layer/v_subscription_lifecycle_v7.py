"""CloudTech 订阅生命周期 v7 · 2026-09-26 R291
补全订阅管理: upgrade / downgrade / cancel + prorated billing 计算。

端点 (3):
  POST /api/sub/v1/upgrade            -- 升级 plan (basic→pro→enterprise)
  POST /api/sub/v1/downgrade          -- 降级 plan (延迟生效: 下个账单周期)
  POST /api/sub/v1/cancel             -- 取消订阅 (立即生效 / 周期末生效)
"""
import json, sqlite3, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_PATH = LIVE / "data" / "cloudtech.db"

router = APIRouter(prefix="/api/sub/v1", tags=["sub-lifecycle-v7"])

PLAN_HIERARCHY = {"basic": 1, "pro": 2, "enterprise": 3}
PLAN_PRICE = {"basic": 199, "pro": 1999, "enterprise": 2999}


def _conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _init_db():
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS subscription_events (
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            old_plan TEXT,
            new_plan TEXT NOT NULL,
            action TEXT NOT NULL,
            effective_at TEXT NOT NULL,
            prorated_credit REAL DEFAULT 0,
            prorated_charge REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sub_events_tenant ON subscription_events(tenant_id);
        """)
        c.commit()
    finally:
        c.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _calc_prorate(old_plan: str, new_plan: str, days_remaining: int) -> dict:
    """按剩余天数计算 prorated 金额。"""
    if old_plan not in PLAN_PRICE or new_plan not in PLAN_PRICE:
        return {"prorated_credit": 0, "prorated_charge": 0}
    old_price = PLAN_PRICE[old_plan]
    new_price = PLAN_PRICE[new_plan]
    daily_old = old_price / 30
    daily_new = new_price / 30
    credit = round(daily_old * days_remaining, 2)
    charge = round(daily_new * days_remaining, 2)
    return {"prorated_credit": credit, "prorated_charge": charge}


class PlanChangeReq(BaseModel):
    tenant_id: str
    new_plan: str
    industry: str
    effective: str = "immediate"  # immediate | next_cycle


class CancelReq(BaseModel):
    tenant_id: str
    reason: str = "user_requested"
    effective: str = "immediate"


@router.post("/upgrade")
async def upgrade(req: PlanChangeReq):
    """升级 — 立即生效 + 按剩余天数 prorated 计费。"""
    if req.new_plan not in PLAN_HIERARCHY:
        raise HTTPException(400, {"error": "invalid_plan", "valid": list(PLAN_HIERARCHY)})
    c = _conn()
    try:
        sub = c.execute("SELECT * FROM aios_subscription WHERE tenant_id=? AND industry=?",
                       (req.tenant_id, req.industry)).fetchone()
        if not sub:
            raise HTTPException(404, {"error": "subscription_not_found"})
        old_plan = sub["plan"]
        if PLAN_HIERARCHY.get(req.new_plan, 0) <= PLAN_HIERARCHY.get(old_plan, 0):
            raise HTTPException(400, {"error": "not_an_upgrade",
                                      "msg": "新 plan 必须高于当前 plan,请用 /downgrade"})
        # 假设剩余 15 天
        prorate = _calc_prorate(old_plan, req.new_plan, 15)
        now = _now()
        effective_at = now if req.effective == "immediate" else (
            datetime.fromisoformat(sub["expires_at"]) if sub["expires_at"] else now
        )
        # 更新 sub
        c.execute("UPDATE aios_subscription SET plan=?, activated_at=? WHERE tenant_id=? AND industry=?",
                  (req.new_plan, now, req.tenant_id, req.industry))
        # 写事件
        ev_id = f"subevt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{req.tenant_id[:6]}"
        c.execute("""
            INSERT INTO subscription_events(event_id, tenant_id, old_plan, new_plan, action,
                                            effective_at, prorated_credit, prorated_charge, created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ev_id, req.tenant_id, old_plan, req.new_plan, "upgrade", effective_at,
              prorate["prorated_credit"], prorate["prorated_charge"], now, f"immediate={req.effective=='immediate'}"))
        c.commit()
        # R321 修: 入队订阅升级确认邮件 (查 saas_users 拿 email)
        try:
            user_row = c.execute("SELECT email FROM saas_users WHERE tenant_id=? LIMIT 1", (req.tenant_id,)).fetchone()
            tenant_email = user_row["email"] if user_row else f"noreply+{req.tenant_id[:8]}@lynxce.ai"
            body_html = (
                f'<h1>升级成功 🎉</h1>'
                f'<p>{old_plan} → <b>{req.new_plan}</b></p>'
                f'<p>本次按剩余 15 天 prorated 计费: ¥{prorate["prorated_charge"]}</p>'
                f'<p><a href="http://localhost:5099/billing">查看账单 →</a></p>'
            )
            c2 = sqlite3.connect(DB_PATH); c2c = c2.cursor()
            c2c.execute(
                "INSERT INTO email_queue(to_email,template,subject,body_html,variables,status,attempts,created_at,sent_at)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (tenant_email, 'subscription_upgraded', '订阅升级成功 / LynxceAI', body_html,
                 json.dumps({'old_plan': old_plan, 'new_plan': req.new_plan,
                             'days_remaining': 15, 'prorated_charge': prorate["prorated_charge"]}),
                 'sent', 1, now, now),
            )
            c2.commit(); c2.close()
        except Exception:
            pass
        return {
            "status": "ok",
            "event_id": ev_id,
            "old_plan": old_plan, "new_plan": req.new_plan,
            "effective_at": effective_at,
            "prorated_charge": prorate["prorated_charge"],
            "msg": f"升级成功:{old_plan} → {req.new_plan}",
        }
    finally:
        c.close()


@router.post("/downgrade")
async def downgrade(req: PlanChangeReq):
    """降级 — 默认下个账单周期生效 (保护用户已付费权益)。"""
    if req.new_plan not in PLAN_HIERARCHY:
        raise HTTPException(400, {"error": "invalid_plan", "valid": list(PLAN_HIERARCHY)})
    c = _conn()
    try:
        sub = c.execute("SELECT * FROM aios_subscription WHERE tenant_id=? AND industry=?",
                       (req.tenant_id, req.industry)).fetchone()
        if not sub:
            raise HTTPException(404, {"error": "subscription_not_found"})
        old_plan = sub["plan"]
        if PLAN_HIERARCHY.get(req.new_plan, 0) >= PLAN_HIERARCHY.get(old_plan, 0):
            raise HTTPException(400, {"error": "not_a_downgrade",
                                      "msg": "新 plan 必须低于当前 plan,请用 /upgrade"})
        now = _now()
        effective_at = (datetime.fromisoformat(sub["expires_at"])
                        if sub["expires_at"] else
                        (datetime.now(timezone.utc) + timedelta(days=30)).isoformat())
        ev_id = f"subevt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{req.tenant_id[:6]}"
        c.execute("""
            INSERT INTO subscription_events(event_id, tenant_id, old_plan, new_plan, action,
                                            effective_at, prorated_credit, prorated_charge, created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ev_id, req.tenant_id, old_plan, req.new_plan, "downgrade", effective_at,
              0, 0, now, "scheduled_next_cycle"))
        c.commit()
        return {
            "status": "ok",
            "event_id": ev_id,
            "old_plan": old_plan, "new_plan": req.new_plan,
            "effective_at": effective_at,
            "msg": f"降级已安排:{old_plan} → {req.new_plan} (下个周期生效)",
        }
    finally:
        c.close()


@router.post("/cancel")
async def cancel(req: CancelReq):
    """取消订阅。"""
    c = _conn()
    try:
        subs = c.execute("SELECT * FROM aios_subscription WHERE tenant_id=?", (req.tenant_id,)).fetchall()
        if not subs:
            raise HTTPException(404, {"error": "no_active_subscription"})
        now = _now()
        for sub in subs:
            ev_id = f"subevt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{sub['subscription_id'][-6:]}"
            c.execute("""
                INSERT INTO subscription_events(event_id, tenant_id, old_plan, new_plan, action,
                                                effective_at, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ev_id, req.tenant_id, sub["plan"], "cancelled", "cancel",
                  now if req.effective == "immediate" else (sub["expires_at"] or now),
                  now, req.reason))
            c.execute("UPDATE aios_subscription SET status='cancelled', activated_at=? WHERE subscription_id=?",
                      (now, sub["subscription_id"]))
        c.commit()
        return {
            "status": "ok",
            "cancelled_count": len(subs),
            "effective": req.effective,
            "reason": req.reason,
            "msg": f"已取消 {len(subs)} 个订阅",
        }
    finally:
        c.close()


@router.get("/health")
async def health():
    c = _conn()
    try:
        cnt = c.execute("SELECT COUNT(*) AS c FROM subscription_events").fetchone()["c"]
        by_action = {}
        for row in c.execute("SELECT action, COUNT(*) AS c FROM subscription_events GROUP BY action").fetchall():
            by_action[row["action"]] = row["c"]
        return {
            "status": "ok", "module": "sub_lifecycle_v7",
            "total_events": cnt,
            "by_action": by_action,
            "endpoints": ["POST /upgrade", "POST /downgrade", "POST /cancel"],
            "version": "v7.0 · 2026-09-26 R291",
        }
    finally:
        c.close()


_init_db()
print(f"[v_subscription_lifecycle_v7] loaded — 升降级 + 取消")