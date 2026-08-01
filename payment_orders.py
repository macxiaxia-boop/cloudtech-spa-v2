"""
支付订单管理 — 统一支付层
Mock模式: 创建订单→模拟支付→确认到账
生产模式: 接入微信支付V3 API
"""
import json, secrets
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
ORDERS_DIR = Path("D:/个人文件/AI/云数科技/orders")
ORDERS_DIR.mkdir(parents=True, exist_ok=True)

PLANS = {
    "starter": {"name": "入门版", "price": 299, "quota": 50},
    "pro": {"name": "专业版", "price": 999, "quota": 150},
    "enterprise": {"name": "企业版", "price": 2999, "quota": 300},
}


def create_order(tid: str, plan_id: str, payment_method: str = "wechat") -> dict:
    """创建支付订单"""
    plan = PLANS.get(plan_id, PLANS["pro"])
    oid = f"ord-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(4)}"

    order = {
        "id": oid, "tenant_id": tid, "plan_id": plan_id,
        "plan_name": plan["name"], "amount": plan["price"],
        "payment_method": payment_method, "status": "pending",
        "created_at": datetime.now().isoformat()[:19],
        "paid_at": None, "expires_at": (datetime.now().isoformat()[:19]),
    }

    # Mock支付二维码
    order["qr_data"] = f"CLOUDTECH|{oid}|{plan['price']}|{plan['name']}"

    of = ORDERS_DIR / f"{oid}.json"
    of.write_text(json.dumps(order, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "order": order}


def get_order(oid: str) -> dict:
    f = ORDERS_DIR / f"{oid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def confirm_payment(oid: str) -> dict:
    """确认支付（Mock模式直接确认）"""
    order = get_order(oid)
    if not order:
        return {"ok": False, "error": "订单不存在"}
    if order["status"] == "paid":
        return {"ok": False, "error": "已支付"}

    order["status"] = "paid"
    order["paid_at"] = datetime.now().isoformat()[:19]

    # 激活租户套餐
    try:
        from tenant_service import update_tenant
        update_tenant(order["tenant_id"], {
            "plan": order["plan_id"],
            "monthly_quota": PLANS[order["plan_id"]]["quota"],
            "monthly_used": 0,
        })
    except Exception: pass

    # 发送通知
    try:
        from notifications import notify
        notify(order["tenant_id"], "billing", "支付成功",
               f"{order['plan_name']} ¥{order['amount']} 已到账", "success")
    except Exception: pass

    of = ORDERS_DIR / f"{oid}.json"
    of.write_text(json.dumps(order, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "order": order}


def get_tenant_orders(tid: str, limit: int = 10) -> list:
    orders = []
    for f in sorted(ORDERS_DIR.glob("ord-*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
            if o.get("tenant_id") == tid:
                orders.append(o)
                if len(orders) >= limit: break
        except Exception: pass
    return orders


def get_payment_stats() -> dict:
    """支付统计"""
    total, paid, pending = 0, 0, 0
    revenue = 0
    for f in ORDERS_DIR.glob("ord-*.json"):
        try:
            o = json.loads(f.read_text(encoding="utf-8"))
            total += 1
            if o["status"] == "paid":
                paid += 1
                revenue += o["amount"]
            elif o["status"] == "pending":
                pending += 1
        except Exception: pass
    return {"total_orders": total, "paid": paid, "pending": pending, "revenue": revenue}
