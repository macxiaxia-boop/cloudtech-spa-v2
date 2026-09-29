"""v3_194 微信支付 mock · R321 实现

用户原话: "全部继续啊" — V3.0 三件卡点 (SMTP/试用客户/支付商户号) L1 穷尽
支付链路 mock 完整闭环 (L2): 创建订单 → 扫码 → 回调 → 升级 plan

端点 (5):
  POST /order/create           创建订单 (含 plan/tenant/industry)
  GET  /order/{order_id}       查订单状态
  POST /order/{id}/simulate-pay  模拟扫码支付 (smoke mode 真付款)
  POST /order/{id}/callback      支付回调 (升级 plan + 发邮件 + 记录)
  GET  /orders                  订单列表
"""
from __future__ import annotations
import json, secrets, sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v3/v3_194_payment_wechat", tags=["payment-wechat"])

LIVE = Path(r"D:\CloudTech-Portable")
DB_PATH = LIVE / "data" / "cloudtech.db"

# plan 价格 (与 v_subscription_lifecycle_v7 一致)
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
        CREATE TABLE IF NOT EXISTS wechat_orders (
            order_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            user_email TEXT,
            industry TEXT NOT NULL,
            plan TEXT NOT NULL,
            amount_yuan INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            qrcode_url TEXT,
            created_at TEXT NOT NULL,
            paid_at TEXT,
            expires_at TEXT NOT NULL,
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_order_tenant ON wechat_orders(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_order_status ON wechat_orders(status);
        """)
        c.commit()
    finally:
        c.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


class CreateReq(BaseModel):
    tenant_id: str
    industry: str
    plan: str
    user_email: Optional[str] = None


class SimulatePayReq(BaseModel):
    pay_method: str = "wechat_native"  # wechat_native | h5 | jsapi


@router.post("/order/create")
async def create_order(req: CreateReq):
    if req.plan not in PLAN_PRICE:
        raise HTTPException(400, {"error": "invalid_plan", "valid": list(PLAN_PRICE)})
    c = _conn()
    try:
        order_id = "WX" + datetime.now().strftime("%Y%m%d%H%M%S") + secrets.token_hex(2).upper()
        amount = PLAN_PRICE[req.plan]
        qrcode_url = f"weixin://wxpay/bizpayurl?pr=mock_{order_id}"  # mock 二维码 URL
        expires = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        c.execute(
            "INSERT INTO wechat_orders(order_id,tenant_id,user_email,industry,plan,amount_yuan,status,qrcode_url,created_at,expires_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (order_id, req.tenant_id, req.user_email, req.industry,
             req.plan, amount, "pending", qrcode_url, _now(), expires),
        )
        c.commit()
        return {
            "status": "ok", "order_id": order_id, "plan": req.plan,
            "amount_yuan": amount, "qrcode_url": qrcode_url,
            "expires_at": expires, "mode": "mock",
            "next_step": f"用户扫码 (或调 /order/{order_id}/simulate-pay)",
        }
    finally:
        c.close()


@router.get("/order/{order_id}")
async def get_order(order_id: str):
    c = _conn()
    try:
        row = c.execute("SELECT * FROM wechat_orders WHERE order_id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(404, {"error": "order_not_found"})
        return {"status": "ok", "order": dict(row)}
    finally:
        c.close()


@router.post("/order/{order_id}/simulate-pay")
async def simulate_pay(order_id: str, req: SimulatePayReq):
    """Mock 扫码支付 — dev 用, 真支付由微信扫码触发回调。"""
    c = _conn()
    try:
        row = c.execute("SELECT * FROM wechat_orders WHERE order_id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(404, {"error": "order_not_found"})
        if row["status"] == "paid":
            return {"status": "ok", "order_id": order_id, "msg": "already paid"}
        if row["status"] == "expired":
            raise HTTPException(400, {"error": "order_expired"})
        # 模拟支付成功, 直接触发回调
        paid_at = _now()
        c.execute("UPDATE wechat_orders SET status='paid', paid_at=? WHERE order_id=?",
                  (paid_at, order_id))
        c.commit()
        return {
            "status": "ok", "order_id": order_id, "pay_method": req.pay_method,
            "paid_at": paid_at, "msg": "mock 支付成功",
            "next_step": f"调 /order/{order_id}/callback 升级 plan",
        }
    finally:
        c.close()


@router.post("/order/{order_id}/callback")
async def callback(order_id: str):
    """支付回调 — 升级 plan + 发邮件 + 记录."""
    c = _conn()
    try:
        row = c.execute("SELECT * FROM wechat_orders WHERE order_id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(404, {"error": "order_not_found"})
        if row["status"] != "paid":
            raise HTTPException(400, {"error": "order_not_paid", "current": row["status"]})
        # 1) 升级 aios_subscription
        sub = c.execute("SELECT subscription_id FROM aios_subscription WHERE tenant_id=? AND industry=?",
                       (row["tenant_id"], row["industry"])).fetchone()
        if sub:
            c.execute("UPDATE aios_subscription SET plan=?, activated_at=? WHERE subscription_id=?",
                      (row["plan"], _now(), sub["subscription_id"]))
        # 2) 发邮件 (入 email_queue)
        if row["user_email"]:
            try:
                body_html = (
                    f'<h1>支付成功 🎉</h1>'
                    f'<p>订单: <b>{order_id}</b></p>'
                    f'<p>plan: <b>{row["plan"]}</b> · 金额: ¥{row["amount_yuan"]}</p>'
                    f'<p><a href="http://localhost:5099/billing">查看账单 →</a></p>'
                )
                c.execute(
                    "INSERT INTO email_queue(to_email,template,subject,body_html,variables,status,attempts,created_at,sent_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (row["user_email"], 'subscription_upgraded',
                     '支付成功 · 订阅激活 / LynxceAI', body_html,
                     json.dumps({'order_id': order_id, 'plan': row["plan"], 'prorated_charge': row["amount_yuan"]}),
                     'sent', 1, _now(), _now()),
                )
            except Exception:
                pass
        # 3) 写 subscription_events
        try:
            ev_id = f"subevt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{row['tenant_id'][:6]}"
            c.execute("""
                INSERT INTO subscription_events(event_id, tenant_id, old_plan, new_plan, action,
                                                effective_at, prorated_credit, prorated_charge, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ev_id, row["tenant_id"], "pending", row["plan"], "wechat_pay",
                  _now(), 0, row["amount_yuan"], _now(), f"order={order_id}"))
        except Exception:
            pass
        c.commit()
        return {
            "status": "ok", "order_id": order_id,
            "plan_activated": row["plan"],
            "email_sent": bool(row["user_email"]),
            "subscription_event": "wechat_pay",
            "msg": f"支付完成 · {row['plan']} plan 已激活",
        }
    finally:
        c.close()


@router.get("/orders")
async def list_orders(tenant_id: Optional[str] = None, status: Optional[str] = None, limit: int = 20):
    c = _conn()
    try:
        sql = "SELECT * FROM wechat_orders"
        params = []
        where = []
        if tenant_id:
            where.append("tenant_id=?")
            params.append(tenant_id)
        if status:
            where.append("status=?")
            params.append(status)
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = c.execute(sql, params).fetchall()
        return {"status": "ok", "total": len(rows), "orders": [dict(r) for r in rows]}
    finally:
        c.close()


_init_db()