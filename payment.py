"""
云数科技 — Payment 支付系统
=============================
Stripe Checkout 集成 · 定价方案 · Webhook · 订单管理
"""
import json, os, time
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))

# ── Stripe 配置（从环境变量读取，默认测试模式） ──
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_placeholder")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_placeholder")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")

# ── 定价方案 ──
PRICING_PLANS = {
    "free": {
        "id": "free",
        "name": "免费版",
        "name_en": "Free",
        "price": 0,
        "price_display": "免费",
        "currency": "cny",
        "daily_limit": 5,
        "interval": None,
        "stripe_price_id": os.environ.get("STRIPE_PRICE_FREE", ""),
        "features": [
            "每日5次使用额度",
            "基础AI工具访问",
            "标准输出格式",
            "社区支持"
        ],
        "popular": False,
        "highlight": False
    },
    "pro": {
        "id": "pro",
        "name": "专业版",
        "name_en": "Pro",
        "price": 19800,  # ¥198.00 in cents/fen
        "price_display": "¥198/月",
        "currency": "cny",
        "daily_limit": 50,
        "interval": "month",
        "stripe_price_id": os.environ.get("STRIPE_PRICE_PRO", "price_pro_placeholder"),
        "features": [
            "每日50次使用额度",
            "全部AI工具访问",
            "高级输出格式",
            "优先技术支持",
            "风格DNA库完整访问",
            "无品牌水印"
        ],
        "popular": True,
        "highlight": True
    },
    "enterprise": {
        "id": "enterprise",
        "name": "企业版",
        "name_en": "Enterprise",
        "price": 99900,  # ¥999.00
        "price_display": "¥999/月",
        "currency": "cny",
        "daily_limit": -1,  # -1 means unlimited
        "interval": "month",
        "stripe_price_id": os.environ.get("STRIPE_PRICE_ENTERPRISE", "price_enterprise_placeholder"),
        "features": [
            "无限使用额度",
            "全部AI工具访问",
            "专属API接入",
            "7×24技术支持",
            "自定义品牌白标",
            "多租户管理",
            "私有化部署可选",
            "专属客户成功经理"
        ],
        "popular": False,
        "highlight": True
    }
}

# ── 订单存储 ──
ORDERS_DIR = HOME / ".openclaw" / "orders"
ORDERS_DIR.mkdir(parents=True, exist_ok=True)

# ── 订阅存储 ──
SUBSCRIPTIONS_FILE = HOME / ".openclaw" / "subscriptions.json"


def _load_subscriptions():
    """加载所有订阅数据"""
    if SUBSCRIPTIONS_FILE.exists():
        try:
            return json.loads(SUBSCRIPTIONS_FILE.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_subscriptions(data):
    """保存订阅数据"""
    SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUBSCRIPTIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def _load_order(order_id):
    """加载订单"""
    order_file = ORDERS_DIR / f"{order_id}.json"
    if order_file.exists():
        return json.loads(order_file.read_text("utf-8"))
    return None


def _save_order(order):
    """保存订单"""
    order_id = order["order_id"]
    order_file = ORDERS_DIR / f"{order_id}.json"
    order_file.write_text(json.dumps(order, ensure_ascii=False, indent=2), "utf-8")


def _generate_order_id():
    """生成唯一订单号: yyyyMMddHHmmss-xxxx"""
    t = datetime.now().strftime("%Y%m%d%H%M%S")
    import secrets
    return f"ORD-{t}-{secrets.token_hex(4).upper()}"


def get_pricing_plans():
    """返回定价方案（不含敏感字段）"""
    plans = {}
    for pid, plan in PRICING_PLANS.items():
        plans[pid] = {
            "id": plan["id"],
            "name": plan["name"],
            "price": plan["price"],
            "price_display": plan["price_display"],
            "currency": plan["currency"],
            "daily_limit": plan["daily_limit"],
            "interval": plan["interval"],
            "features": plan["features"],
            "popular": plan["popular"],
            "highlight": plan["highlight"],
        }
    return plans


def create_checkout_session(plan_id, user_id, success_url=None, cancel_url=None):
    """
    创建 Stripe Checkout Session
    返回: {"session_id": "...", "url": "..."} 或 {"error": "..."}
    """
    plan = PRICING_PLANS.get(plan_id)
    if not plan:
        return {"error": f"定价方案不存在: {plan_id}"}

    if plan_id == "free":
        # 免费版无需支付，直接激活
        subs = _load_subscriptions()
        subs[user_id] = {
            "user_id": user_id,
            "plan": "free",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "stripe_subscription_id": None,
            "current_period_end": None
        }
        _save_subscriptions(subs)
        return {"session_id": None, "url": None, "plan": "free", "status": "active"}

    if not success_url:
        success_url = "http://localhost:8888/payment/success"
    if not cancel_url:
        cancel_url = "http://localhost:8888/payment/cancel"

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY

        # 查找或创建 price
        price_id = plan["stripe_price_id"]
        if not price_id or "placeholder" in price_id:
            # 自动创建 price（测试模式）
            try:
                price = stripe.Price.create(
                    currency=plan["currency"],
                    unit_amount=plan["price"],
                    recurring={"interval": plan["interval"]} if plan["interval"] else None,
                    product_data={
                        "name": f"云数科技 - {plan['name']}",
                    }
                )
                price_id = price.id
            except Exception as e:
                return {"error": f"创建 Stripe Price 失败: {str(e)}"}

        session = stripe.checkout.Session.create(
            mode="subscription" if plan["interval"] else "payment",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user_id,
            metadata={
                "plan_id": plan_id,
                "user_id": user_id,
            }
        )

        return {
            "session_id": session.id,
            "url": session.url,
            "plan": plan_id,
            "status": "pending"
        }

    except ImportError:
        # 无 stripe SDK — 模拟 checkout（测试/开发模式）
        return _mock_checkout(plan_id, user_id, success_url)
    except Exception as e:
        return {"error": f"创建 Stripe Session 失败: {str(e)}"}


def _mock_checkout(plan_id, user_id, success_url=None):
    """无 Stripe SDK 时的模拟 checkout（仅开发测试用）"""
    session_id = f"cs_mock_{int(time.time())}_{user_id[:8]}"

    # 创建一条待支付订单
    plan = PRICING_PLANS.get(plan_id, {})
    order = {
        "order_id": _generate_order_id(),
        "user_id": user_id,
        "plan": plan_id,
        "amount": plan.get("price", 0),
        "currency": plan.get("currency", "cny"),
        "status": "pending",
        "stripe_session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    _save_order(order)

    return {
        "session_id": session_id,
        "url": f"/payment/mock?session_id={session_id}&plan={plan_id}",
        "plan": plan_id,
        "status": "pending",
        "mock": True,
        "hint": "Stripe SDK 未安装，使用模拟模式"
    }


def handle_webhook(payload, sig_header):
    """
    处理 Stripe Webhook 事件
    payload: bytes, sig_header: str
    """
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return {"error": "Invalid payload"}, 400
    except stripe.error.SignatureVerificationError:
        return {"error": "Invalid signature"}, 400

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    result = {"event": event_type, "status": "received"}

    if event_type == "checkout.session.completed":
        result.update(_handle_checkout_completed(data))
    elif event_type == "invoice.paid":
        result.update(_handle_invoice_paid(data))
    elif event_type == "invoice.payment_failed":
        result.update(_handle_payment_failed(data))
    elif event_type == "customer.subscription.deleted":
        result.update(_handle_subscription_deleted(data))

    result["processed_at"] = datetime.now().isoformat()
    return result, 200


def _handle_checkout_completed(session):
    """处理 checkout.session.completed 事件"""
    user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id", "")
    plan_id = session.get("metadata", {}).get("plan_id", "pro")

    if not user_id:
        return {"error": "No user_id in session"}

    # 创建订单
    order = {
        "order_id": _generate_order_id(),
        "user_id": user_id,
        "plan": plan_id,
        "amount": session.get("amount_total", 0),
        "currency": session.get("currency", "cny"),
        "status": "paid",
        "stripe_session_id": session.get("id", ""),
        "stripe_subscription_id": session.get("subscription", ""),
        "customer_id": session.get("customer", ""),
        "payment_status": session.get("payment_status", ""),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    _save_order(order)

    # 更新订阅
    subs = _load_subscriptions()
    current_period_end = None
    if session.get("subscription"):
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            subscription = stripe.Subscription.retrieve(session["subscription"])
            current_period_end = datetime.fromtimestamp(subscription.current_period_end).isoformat()
        except Exception:
            pass

    subs[user_id] = {
        "user_id": user_id,
        "plan": plan_id,
        "status": "active",
        "order_id": order["order_id"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "stripe_subscription_id": session.get("subscription", ""),
        "stripe_customer_id": session.get("customer", ""),
        "current_period_end": current_period_end
    }
    _save_subscriptions(subs)

    return {"order_id": order["order_id"], "plan": plan_id, "status": "active"}


def _handle_invoice_paid(invoice):
    """处理 invoice.paid 事件"""
    subscription_id = invoice.get("subscription", "")
    user_id = invoice.get("metadata", {}).get("user_id", "")
    if not subscription_id:
        return {"status": "skipped", "reason": "no subscription_id"}

    subs = _load_subscriptions()
    for uid, sub in subs.items():
        if sub.get("stripe_subscription_id") == subscription_id:
            sub["status"] = "active"
            sub["updated_at"] = datetime.now().isoformat()
            if invoice.get("period_end"):
                sub["current_period_end"] = datetime.fromtimestamp(invoice["period_end"]).isoformat()
            _save_subscriptions(subs)
            return {"user_id": uid, "status": "active"}

    return {"status": "unknown_subscription"}


def _handle_payment_failed(invoice):
    """处理 invoice.payment_failed 事件"""
    subscription_id = invoice.get("subscription", "")
    subs = _load_subscriptions()
    for uid, sub in subs.items():
        if sub.get("stripe_subscription_id") == subscription_id:
            sub["status"] = "past_due"
            sub["updated_at"] = datetime.now().isoformat()
            _save_subscriptions(subs)
            return {"user_id": uid, "status": "past_due"}
    return {"status": "unknown_subscription"}


def _handle_subscription_deleted(subscription):
    """处理 customer.subscription.deleted 事件"""
    subscription_id = subscription.get("id", "")
    subs = _load_subscriptions()
    for uid, sub in subs.items():
        if sub.get("stripe_subscription_id") == subscription_id:
            sub["status"] = "cancelled"
            sub["updated_at"] = datetime.now().isoformat()
            _save_subscriptions(subs)
            return {"user_id": uid, "status": "cancelled"}
    return {"status": "unknown_subscription"}


def get_subscription_status(user_id):
    """查询用户订阅状态"""
    subs = _load_subscriptions()
    sub = subs.get(user_id, {
        "user_id": user_id,
        "plan": "free",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    })

    # 检查订阅是否过期
    if sub.get("current_period_end"):
        try:
            period_end = datetime.fromisoformat(sub["current_period_end"])
            if datetime.now() > period_end:
                # 过期，降级为免费
                sub["status"] = "expired"
                sub["plan"] = "free"
        except (ValueError, TypeError):
            pass

    plan = PRICING_PLANS.get(sub.get("plan", "free"), PRICING_PLANS["free"])
    daily_limit = plan.get("daily_limit", 5)
    if daily_limit == -1:
        daily_limit_display = "无限"
    else:
        daily_limit_display = f"{daily_limit}次/天"

    return {
        "user_id": sub["user_id"],
        "plan": sub.get("plan", "free"),
        "plan_name": plan.get("name", "免费版"),
        "status": sub.get("status", "active"),
        "daily_limit": daily_limit,
        "daily_limit_display": daily_limit_display,
        "current_period_end": sub.get("current_period_end"),
        "created_at": sub.get("created_at"),
        "updated_at": sub.get("updated_at"),
        "features": plan.get("features", []),
        "is_paid": sub.get("plan") != "free"
    }


def create_order(user_id, plan_id, amount, currency="cny"):
    """创建订单"""
    order = {
        "order_id": _generate_order_id(),
        "user_id": user_id,
        "plan": plan_id,
        "amount": amount,
        "currency": currency,
        "status": "pending",
        "stripe_session_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    _save_order(order)
    return order


def get_order(order_id):
    """查询订单"""
    order = _load_order(order_id)
    if not order:
        return None
    return order


def list_orders(user_id=None, limit=20):
    """列出订单"""
    orders = []
    for f in sorted(ORDERS_DIR.glob("*.json"), reverse=True)[:limit * 3]:
        try:
            order = json.loads(f.read_text("utf-8"))
            if user_id and order.get("user_id") != user_id:
                continue
            orders.append(order)
            if len(orders) >= limit:
                break
        except (json.JSONDecodeError, OSError):
            continue
    return orders


def refund_order(order_id, reason="客户申请退款"):
    """退款订单"""
    order = _load_order(order_id)
    if not order:
        return {"error": "订单不存在"}

    if order.get("status") != "paid":
        return {"error": "只能退款已支付订单"}

    # 通过 Stripe API 退款
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY

        if order.get("stripe_session_id"):
            # 获取 PaymentIntent
            session = stripe.checkout.Session.retrieve(order["stripe_session_id"])
            payment_intent = session.get("payment_intent")
            if payment_intent:
                refund = stripe.Refund.create(
                    payment_intent=payment_intent,
                    reason="requested_by_customer",
                    metadata={"order_id": order_id, "reason": reason}
                )
                order["status"] = "refunded"
                order["refund_id"] = refund.id
                order["refund_reason"] = reason
                order["updated_at"] = datetime.now().isoformat()
                _save_order(order)
                return {"success": True, "refund_id": refund.id, "order_id": order_id}

        # 模拟退款
        order["status"] = "refunded"
        order["refund_reason"] = reason
        order["updated_at"] = datetime.now().isoformat()
        _save_order(order)
        return {"success": True, "order_id": order_id, "mock": True}

    except ImportError:
        # 无 Stripe SDK，模拟退款
        order["status"] = "refunded"
        order["refund_reason"] = reason
        order["updated_at"] = datetime.now().isoformat()
        _save_order(order)
        return {"success": True, "order_id": order_id, "mock": True}
    except Exception as e:
        return {"error": f"退款失败: {str(e)}"}


def get_stripe_publishable_key():
    """获取 Stripe publishable key"""
    return STRIPE_PUBLISHABLE_KEY
