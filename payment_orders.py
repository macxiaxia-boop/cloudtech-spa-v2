"""
支付订单管理 — 统一支付层 (Order Management Layer)
═══════════════════════════════════════════════════════════
路由支付请求到 Stripe / WeChat Pay，管理订单完整生命周期。

Payment Flow:
  Frontend → payment_orders.create_order()
    ├── provider="stripe"  → payment.create_checkout_session()  → Stripe API (REAL)
    ├── provider="wechat"  → wechat_pay.create_native_order()   → WeChat Pay V2 (REAL)
    └── provider="mock"/"" → fallback JSON order (MOCK)

  Webhook / Callback → payment_orders.confirm_payment()
    └── billing.update_tokens()      ← 更新Token配额
    └── tenant_service.update_tenant() ← 更新租户套餐
    └── notifications.notify()       ← 发送通知
"""
import json, secrets, time
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE = Path(__file__).parent

# 主存储目录
ORDERS_DIR = BASE / "data" / "payment_orders"
ORDERS_DIR.mkdir(parents=True, exist_ok=True)

# 遗留存储目录（向后兼容）
LEGACY_DIR = Path("D:/个人文件/AI/云数科技/orders")
LEGACY_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# 套餐定义（与 billing.py 同步）
# ═══════════════════════════════════════════════════════════

PLANS = {
    "starter":    {"name": "入门版",   "price": 299,  "quota": 50,  "token_rate": 0.5},
    "pro":        {"name": "专业版",   "price": 999,  "quota": 150, "token_rate": 0.3},
    "enterprise": {"name": "企业版",   "price": 2999, "quota": 300, "token_rate": 0.2},
}


# ═══════════════════════════════════════════════════════════
# 内部工具
# ═══════════════════════════════════════════════════════════

def _generate_order_id() -> str:
    """生成唯一订单号"""
    t = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"ORD-{t}-{secrets.token_hex(4).upper()}"


def _save_order(order: dict) -> str:
    """持久化订单到主目录和遗留目录"""
    order_id = order["order_id"]
    payload = json.dumps(order, ensure_ascii=False, indent=2)

    # 主存储
    (ORDERS_DIR / f"{order_id}.json").write_text(payload, encoding="utf-8")

    # 遗留兼容
    (LEGACY_DIR / f"{order_id}.json").write_text(payload, encoding="utf-8")

    return order_id


def _load_order(order_id: str) -> Optional[dict]:
    """从任一目录加载订单"""
    for d in (ORDERS_DIR, LEGACY_DIR):
        f = d / f"{order_id}.json"
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
    return None


def _amount_to_plan(amount: float) -> str:
    """将金额映射到最接近的定价方案"""
    amount = float(amount)
    # 金额以元为单位，payment.py 方案以"分"为单位
    amount_fen = int(amount * 100)
    if amount_fen <= 0:
        return "free"
    if amount_fen <= 50000:     # ≤¥500
        return "pro"
    return "enterprise"


# ═══════════════════════════════════════════════════════════
# 核心 API：创建订单
# ═══════════════════════════════════════════════════════════

def create_order(amount, currency="CNY", provider="stripe",
                 customer_id=None, description=None) -> dict:
    """
    创建支付订单 — 路由到 Stripe / WeChat Pay / Mock。

    Args:
        amount:      订单金额（元），如 99.00
        currency:    货币代码 (CNY/USD/EUR)，默认 CNY
        provider:    支付提供商 "stripe" | "wechat" | "mock"
        customer_id: 客户/租户标识
        description: 订单描述/产品名称

    Returns:
        {
            "order_id": "ORD-20260807...",
            "provider": "stripe",
            "status": "pending",
            "amount": 99.0,
            "currency": "CNY",
            "checkout_url": "https://...",     # Stripe时
            "code_url": "weixin://...",         # WeChat时
            "qr_data": "CLOUDTECH|...",         # Mock时
            "created_at": "2026-08-07T14:30:00",
        }
    """
    order_id = _generate_order_id()
    amount_f = float(amount)

    order = {
        "order_id": order_id,
        "id": order_id,                         # 向后兼容别名
        "customer_id": customer_id,
        "tenant_id": customer_id,               # 向后兼容别名
        "amount": amount_f,
        "currency": currency.upper(),
        "provider": provider,
        "payment_method": provider,             # 向后兼容别名
        "description": description or "",
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "paid_at": None,
        "refunded_at": None,
    }

    # ── 路由到对应支付提供商 ──

    if provider == "stripe":
        try:
            from payment import create_checkout_session
            plan_id = _amount_to_plan(amount_f)
            result = create_checkout_session(plan_id, customer_id)
            if "error" in result:
                order["status"] = "failed"
                order["error"] = result["error"]
            else:
                order["stripe_session_id"] = result.get("session_id")
                order["checkout_url"] = result.get("url")
                order["plan"] = result.get("plan", plan_id)
                if result.get("mock"):
                    order["mock"] = True
        except ImportError:
            order["mock"] = True
            order["status"] = "mock"
            order["hint"] = "payment.py 不可用，使用Mock模式"
            order["qr_data"] = f"STRIPE|{order_id}|{amount_f}"
        except Exception as e:
            order["status"] = "failed"
            order["error"] = f"Stripe路由失败: {e}"

    elif provider == "wechat":
        try:
            from wechat_pay import create_native_order
            result = create_native_order(
                plan_name=description or "CloudTech订阅",
                amount_yuan=amount_f,
                order_id=order_id,
                product_desc=description or "CloudTech订阅",
            )
            if result.get("success"):
                order["code_url"] = result.get("code_url")
                order["wechat_order_id"] = result.get("order_id")
                if result.get("mode") == "mock":
                    order["mock"] = True
            else:
                order["status"] = "failed"
                order["error"] = result.get("error", "微信支付下单失败")
                order["mode"] = result.get("mode")
        except ImportError:
            order["mock"] = True
            order["status"] = "mock"
            order["hint"] = "wechat_pay.py 不可用，使用Mock模式"
            order["qr_data"] = f"WECHAT|{order_id}|{amount_f}"
        except Exception as e:
            order["status"] = "failed"
            order["error"] = f"微信支付路由失败: {e}"

    else:
        # Mock/Fallback — 无提供商时
        order["mock"] = True
        order["status"] = "mock"
        order["qr_data"] = f"CLOUDTECH|{order_id}|{amount_f}|{description or 'Subscription'}"

    _save_order(order)
    return order


# ═══════════════════════════════════════════════════════════
# 核心 API：查询订单
# ═══════════════════════════════════════════════════════════

def get_order(order_id: str) -> Optional[dict]:
    """
    按ID查询订单。

    Args:
        order_id: 订单号，如 "ORD-20260807143000-abc12345"

    Returns:
        dict 或 None
    """
    return _load_order(order_id)


def list_orders(customer_id: str = None, limit: int = 20,
                status: str = None) -> list:
    """
    列出订单（可按客户/状态筛选，按创建时间倒序）。

    Args:
        customer_id: 可选，按客户ID过滤
        limit:       最大返回数
        status:      可选，按状态过滤 (pending/paid/failed/refunded/mock)

    Returns:
        list[dict]
    """
    orders = []
    # 从主目录和遗留目录收集，去重
    seen = set()
    for d in (ORDERS_DIR, LEGACY_DIR):
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            oid = f.stem
            if oid in seen:
                continue
            seen.add(oid)
            try:
                o = json.loads(f.read_text(encoding="utf-8"))
                if customer_id and o.get("customer_id") != customer_id and o.get("tenant_id") != customer_id:
                    continue
                if status and o.get("status") != status:
                    continue
                orders.append(o)
                if len(orders) >= limit:
                    break
            except (json.JSONDecodeError, OSError):
                continue
        if len(orders) >= limit:
            break
    return orders


# ═══════════════════════════════════════════════════════════
# 核心 API：确认支付（Webhook / 回调）
# ═══════════════════════════════════════════════════════════

def confirm_payment(order_id: str) -> dict:
    """
    确认支付到账 — 由Webhook或管理后台调用。

    操作：
        1. 标记订单为 paid
        2. 更新 billing Token配额 → billing.update_tokens()
        3. 更新 tenant 套餐 → tenant_service.update_tenant()
        4. 发送通知 → notifications.notify()

    Args:
        order_id: 订单号

    Returns:
        {"ok": True, "order": {...}} 或 {"ok": False, "error": "..."}
    """
    order = _load_order(order_id)
    if not order:
        return {"ok": False, "error": f"订单不存在: {order_id}"}
    if order.get("status") == "paid":
        return {"ok": False, "error": "订单已支付"}

    order["status"] = "paid"
    order["paid_at"] = datetime.now().isoformat()
    order["updated_at"] = datetime.now().isoformat()

    customer_id = order.get("customer_id") or order.get("tenant_id")
    plan_id = order.get("plan", "pro")

    # ── ① 更新 Token 配额 ──
    if customer_id:
        try:
            from billing import update_tokens
            update_tokens(customer_id, plan_id, reset_monthly=True)
        except ImportError:
            pass
        except Exception as e:
            order["billing_sync_error"] = str(e)

        # ── ② 更新租户套餐 ──
        try:
            from tenant_service import update_tenant
            plan = PLANS.get(plan_id, PLANS["pro"])
            update_tenant(customer_id, {
                "plan": plan_id,
                "monthly_quota": plan["quota"],
                "monthly_used": 0,
            })
        except ImportError:
            pass
        except Exception as e:
            order["tenant_sync_error"] = str(e)

        # ── ③ 发送通知 ──
        try:
            from notifications import notify
            plan = PLANS.get(plan_id, PLANS["pro"])
            notify(customer_id, "billing", "支付成功",
                   f"{order.get('description', plan['name'])} ¥{order.get('amount', 0)} 已到账",
                   "success")
        except ImportError:
            pass
        except Exception:
            pass

    _save_order(order)
    return {"ok": True, "order": order}


# ═══════════════════════════════════════════════════════════
# 核心 API：退款
# ═══════════════════════════════════════════════════════════

def refund_order(order_id: str, amount: float = None,
                 reason: str = "客户申请退款") -> dict:
    """
    退款（部分或全额）。

    Args:
        order_id: 订单号
        amount:   退款金额（元），None=全额退款
        reason:   退款原因

    Returns:
        {"ok": True, "order_id": "...", "refund_amount": ...}
        或 {"ok": False, "error": "..."}
    """
    order = _load_order(order_id)
    if not order:
        return {"ok": False, "error": f"订单不存在: {order_id}"}
    if order.get("status") != "paid":
        return {"ok": False, "error": f"订单状态为 {order.get('status')}，不可退款"}
    if order.get("status") == "refunded":
        return {"ok": False, "error": "订单已退款"}

    refund_amount = float(amount) if amount is not None else order.get("amount", 0)

    provider = order.get("provider", "mock")

    # ── Stripe 退款 ──
    if provider == "stripe" and order.get("stripe_session_id"):
        try:
            from payment import refund_order as stripe_refund
            result = stripe_refund(order_id, reason)
            if "error" in result:
                return {"ok": False, "error": f"Stripe退款失败: {result['error']}"}
            order["refund_id"] = result.get("refund_id")
        except ImportError:
            pass
        except Exception as e:
            return {"ok": False, "error": f"Stripe退款异常: {e}"}

    # ── WeChat 退款（V2需要证书，降级到Mock记录） ──
    elif provider == "wechat":
        order["refund_note"] = "微信支付退款需通过商户平台操作或实现V3退款API"

    order["status"] = "refunded"
    order["refund_amount"] = refund_amount
    order["refund_reason"] = reason
    order["refunded_at"] = datetime.now().isoformat()
    order["updated_at"] = datetime.now().isoformat()
    _save_order(order)

    return {
        "ok": True,
        "order_id": order_id,
        "refund_amount": refund_amount,
        "provider": provider,
    }


# ═══════════════════════════════════════════════════════════
# 统计 & 工具
# ═══════════════════════════════════════════════════════════

def get_payment_stats() -> dict:
    """支付统计（全部订单）"""
    stats = {"total_orders": 0, "paid": 0, "pending": 0,
             "failed": 0, "refunded": 0, "mock": 0, "revenue": 0}
    seen = set()
    for d in (ORDERS_DIR, LEGACY_DIR):
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            oid = f.stem
            if oid in seen:
                continue
            seen.add(oid)
            try:
                o = json.loads(f.read_text(encoding="utf-8"))
                stats["total_orders"] += 1
                status = o.get("status", "pending")
                if status in stats:
                    stats[status] += 1
                if status == "paid":
                    stats["revenue"] += o.get("amount", 0)
            except (json.JSONDecodeError, OSError):
                continue
    return stats


def get_tenant_orders(customer_id: str, limit: int = 10) -> list:
    """向后兼容：按租户ID查订单"""
    return list_orders(customer_id=customer_id, limit=limit)
