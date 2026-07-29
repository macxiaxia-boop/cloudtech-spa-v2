#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payment Integration v1.0
Alipay + WeChat Pay + Invoice generation.
Enterprise billing system.
"""

import json
import hashlib
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from database import get_db

STATE_DIR = Path(r"C:\Users\xinzh\.openclaw\state")


class PaymentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


class InvoiceStatus(Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentManager:
    """Enterprise payment and billing management."""

    # Plan definitions
    PLANS = {
        "starter": {"monthly": 4800, "annual": 48000, "name": "Starter"},
        "professional": {"monthly": 9800, "annual": 98000, "name": "Professional"},
        "enterprise": {"monthly": 16800, "annual": 168000, "name": "Enterprise"},
    }

    def __init__(self):
        self.db = get_db()

    # === Payment Orders ===
    def create_payment_order(self, tenant_id, plan, billing_cycle="monthly", payment_method="alipay"):
        """Create a payment order for plan subscription."""
        if plan not in self.PLANS:
            return {"error": f"Invalid plan: {plan}"}

        plan_price = self.PLANS[plan]
        amount = plan_price["monthly"] if billing_cycle == "monthly" else plan_price["annual"]

        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        payment_id = f"PAY-{uuid.uuid4().hex[:12].upper()}"

        order = {
            "order_id": order_id,
            "payment_id": payment_id,
            "tenant_id": tenant_id,
            "plan": plan,
            "billing_cycle": billing_cycle,
            "amount": amount,
            "currency": "CNY",
            "payment_method": payment_method,
            "status": PaymentStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=2)).isoformat(),
            "paid_at": None,
            "payment_url": self._generate_payment_url(payment_method, order_id, amount, plan),
        }

        # Record in database
        self.db.insert("audit_log", {
            "tenant_id": tenant_id,
            "user_id": "system",
            "action": "payment.order_created",
            "resource": "payment",
            "resource_id": order_id,
            "details": json.dumps({"amount": amount, "plan": plan, "method": payment_method}),
        })

        return order

    def _generate_payment_url(self, method, order_id, amount, plan):
        """Generate payment URL for supported methods."""
        if method == "alipay":
            # In production: call Alipay API to generate QR code URL
            # For now: generate a standardized payment link
            return f"https://open.alipay.com/api/pay?orderId={order_id}&amount={amount}&subject=AI+Pipeline+{plan}"
        elif method == "wechat":
            return f"https://api.mch.weixin.qq.com/pay/unifiedorder?orderId={order_id}&amount={amount}"
        elif method == "bank_transfer":
            return f"bank://transfer?orderId={order_id}&amount={amount}"
        return ""

    def confirm_payment(self, payment_id, transaction_id=None):
        """Confirm a payment (webhook from payment provider)."""
        # Find the order
        row = self.db.fetch_one(
            "SELECT * FROM audit_log WHERE resource_id LIKE ? AND action = 'payment.order_created'",
            (f"%{payment_id}%",)
        )
        if not row:
            return {"error": "Order not found"}

        details = json.loads(row["details"] or "{}")
        tenant_id = row["tenant_id"]

        # Update tenant billing
        self.db.update("tenant_billing",
                       {"payment_status": "paid", "plan": details.get("plan", "starter")},
                       "tenant_id = ?", (tenant_id,))

        # Update tenant plan
        self.db.update("tenants",
                       {"plan": details.get("plan", "starter")},
                       "id = ?", (tenant_id,))

        # Record payment
        self.db.insert("audit_log", {
            "tenant_id": tenant_id,
            "user_id": "system",
            "action": "payment.confirmed",
            "resource": "payment",
            "resource_id": payment_id,
            "details": json.dumps({
                "transaction_id": transaction_id or f"TXN-{uuid.uuid4().hex[:16]}",
                "amount": details.get("amount", 0),
                "plan": details.get("plan", ""),
            }),
        })

        return {
            "status": "paid",
            "payment_id": payment_id,
            "tenant_id": tenant_id,
            "plan": details.get("plan", ""),
        }

    # === Invoices ===
    def generate_invoice(self, tenant_id, amount, plan, billing_period=None):
        """Generate an invoice for a tenant."""
        if billing_period is None:
            billing_period = f"{datetime.now().strftime('%Y-%m')}"

        invoice_id = f"INV-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:8].upper()}"
        invoice_number = f"AI-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # Get tenant info
        tenant = self.db.fetch_one("SELECT * FROM tenants WHERE id = ?", (tenant_id,))
        if not tenant:
            return {"error": "Tenant not found"}

        invoice = {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "tenant_id": tenant_id,
            "tenant_name": tenant["name"],
            "tenant_email": tenant["email"],
            "amount": amount,
            "tax_rate": 0.06,  # 6% VAT
            "tax_amount": round(amount * 0.06, 2),
            "total_amount": round(amount * 1.06, 2),
            "currency": "CNY",
            "plan": plan,
            "billing_period": billing_period,
            "status": InvoiceStatus.ISSUED.value,
            "issued_at": datetime.now().isoformat(),
            "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "notes": f"AI Content Pipeline - {plan.capitalize()} Plan - {billing_period}",
        }

        # Save invoice
        invoice_dir = STATE_DIR / "invoices"
        invoice_dir.mkdir(parents=True, exist_ok=True)
        inv_file = invoice_dir / f"{invoice_id}.json"
        inv_file.write_text(json.dumps(invoice, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"[INVOICE] Generated: {invoice_number} for {tenant['name']} (RMB {amount:,})")
        return invoice

    # === Revenue Reports ===
    def get_revenue_report(self, period="monthly"):
        """Generate revenue report."""
        today = datetime.now()

        if period == "monthly":
            start = today.replace(day=1).isoformat()
            end = today.isoformat()
            label = today.strftime("%Y-%m")
        elif period == "annual":
            start = today.replace(month=1, day=1).isoformat()
            end = today.isoformat()
            label = today.strftime("%Y")
        else:
            start = today.isoformat()[:7] + "-01"
            end = today.isoformat()
            label = today.strftime("%Y-%m")

        # Sum confirmed payments in this period
        rows = self.db.fetch_all(
            """SELECT details FROM audit_log
               WHERE action = 'payment.confirmed'
               AND created_at BETWEEN ? AND ?""",
            (start, end)
        )

        total_revenue = 0
        by_plan = {}
        payment_count = 0

        for row in rows:
            details = json.loads(row["details"] or "{}")
            amount = details.get("amount", 0)
            plan = details.get("plan", "unknown")

            total_revenue += amount
            payment_count += 1
            by_plan[plan] = by_plan.get(plan, 0) + amount

        return {
            "period": label,
            "total_revenue": total_revenue,
            "payment_count": payment_count,
            "by_plan": by_plan,
            "mrr": self._calculate_mrr(),
            "arr": self._calculate_arr(),
        }

    def _calculate_mrr(self):
        """Calculate Monthly Recurring Revenue."""
        tenants = self.db.fetch_all(
            "SELECT plan FROM tenants WHERE status = 'active'"
        )
        mrr = 0
        for t in tenants:
            plan = t["plan"]
            if plan in self.PLANS:
                mrr += self.PLANS[plan]["monthly"]
        return mrr

    def _calculate_arr(self):
        """Calculate Annual Recurring Revenue."""
        return self._calculate_mrr() * 12

    # === Trial Management ===
    def start_trial(self, tenant_id, days=14):
        """Start a free trial for a tenant."""
        self.db.update("tenant_billing",
                       {"payment_status": "trial",
                        "trial_ends_at": (datetime.now() + timedelta(days=days)).isoformat()},
                       "tenant_id = ?", (tenant_id,))

        return {
            "tenant_id": tenant_id,
            "trial_days": days,
            "trial_ends_at": (datetime.now() + timedelta(days=days)).isoformat(),
        }

    def check_trial_status(self, tenant_id):
        """Check trial status for a tenant."""
        billing = self.db.fetch_one(
            "SELECT * FROM tenant_billing WHERE tenant_id = ?",
            (tenant_id,)
        )
        if not billing:
            return {"status": "no_billing_record"}

        if billing["payment_status"] == "paid":
            return {"status": "paid", "plan": billing["plan"]}

        if billing["payment_status"] == "trial":
            trial_end = billing["trial_ends_at"]
            if trial_end and datetime.fromisoformat(trial_end) < datetime.now():
                return {"status": "trial_expired", "ended_at": trial_end}
            return {"status": "trial", "ends_at": trial_end, "days_left": 0}

        return {"status": billing["payment_status"]}


# === CLI ===
if __name__ == "__main__":
    import sys
    pm = PaymentManager()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "create-order":
            if len(sys.argv) < 5:
                print("Usage: create-order <tenant_id> <plan> [monthly|annual] [alipay|wechat]")
                sys.exit(1)
            order = pm.create_payment_order(sys.argv[2], sys.argv[3],
                                            sys.argv[4] if len(sys.argv) > 4 else "monthly",
                                            sys.argv[5] if len(sys.argv) > 5 else "alipay")
            print(json.dumps(order, ensure_ascii=False, indent=2))

        elif cmd == "invoice":
            if len(sys.argv) < 5:
                print("Usage: invoice <tenant_id> <amount> <plan>")
                sys.exit(1)
            inv = pm.generate_invoice(sys.argv[2], int(sys.argv[3]), sys.argv[4])
            print(json.dumps(inv, ensure_ascii=False, indent=2))

        elif cmd == "revenue":
            period = sys.argv[2] if len(sys.argv) > 2 else "monthly"
            report = pm.get_revenue_report(period)
            print(json.dumps(report, ensure_ascii=False, indent=2))

        elif cmd == "trial":
            if len(sys.argv) < 3:
                print("Usage: trial <tenant_id> [days]")
                sys.exit(1)
            trial = pm.start_trial(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 14)
            print(json.dumps(trial, ensure_ascii=False, indent=2))

        else:
            print(f"Unknown command: {cmd}")
    else:
        report = pm.get_revenue_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
