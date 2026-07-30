"""
Operations Dashboard API — MRR, Users, Usage, Churn for business owner
"""
import os, json, hashlib
from datetime import datetime, timedelta
from pathlib import Path
from database import get_db


def get_mrr() -> dict:
    """Monthly Recurring Revenue breakdown (from tenants table)"""
    try:
        db = get_db()
        subscriptions = db.fetch_all("SELECT plan, status, created_at FROM tenants")
        if not subscriptions:
            return _empty_mrr()

        # Plan pricing from billing.py PLANS
        PLAN_PRICES = {"starter": 299, "pro": 999, "enterprise": 2999}
        mrr = 0.0
        by_plan = {}
        active = 0
        churned = 0

        for sub in subscriptions:
            s = dict(sub)
            plan = s.get("plan", "starter")
            amount = PLAN_PRICES.get(plan, 299)
            status = s.get("status", "active")

            if status == "active":
                mrr += amount
                active += 1
                by_plan[plan] = by_plan.get(plan, 0) + amount
            elif status in ("cancelled", "expired", "inactive"):
                churned += 1

        return {
            "mrr": round(mrr, 2),
            "mrr_by_plan": {k: round(v, 2) for k, v in sorted(by_plan.items(), key=lambda x: -x[1])},
            "active_subscriptions": active,
            "churned": churned,
            "arpu": round(mrr / active, 2) if active > 0 else 0,
        }
    except Exception:
        return _empty_mrr()


def _empty_mrr():
    return {"mrr": 0, "mrr_by_plan": {}, "active_subscriptions": 0, "churned": 0, "arpu": 0}


def get_user_stats() -> dict:
    """User growth and engagement stats"""
    try:
        db = get_db()
        total = len(db.fetch_all("SELECT id FROM users")) if hasattr(db, 'fetch_all') else 0

        # Users this month
        month_start = datetime.now().replace(day=1).isoformat()[:10]
        new_this_month = len(db.fetch_all(
            "SELECT id FROM users WHERE created_at >= ?", [month_start]
        )) if total > 0 else 0

        return {
            "total_users": total,
            "new_this_month": new_this_month,
        }
    except Exception:
        return {"total_users": 0, "new_this_month": 0}


def get_tenant_stats() -> dict:
    """Per-tenant usage overview"""
    try:
        db = get_db()
        tenants = db.fetch_all("SELECT id, name, email, plan, status, created_at FROM tenants")
        if not tenants:
            return {"tenants": []}

        result = []
        for t in tenants:
            t = dict(t)
            result.append({
                "id": t.get("id", ""),
                "name": t.get("name", ""),
                "email": t.get("email", ""),
                "plan": t.get("plan", "starter"),
                "status": t.get("status", "active"),
                "created": t.get("created_at", "")[:10],
            })

        return {"tenants": sorted(result, key=lambda x: x["created"], reverse=True)}
    except Exception:
        return {"tenants": []}


def get_usage_overview() -> dict:
    """Aggregated platform usage (from audit_log table)"""
    try:
        db = get_db()
        api_stats = {}
        try:
            rows = db.fetch_all("SELECT resource_type, COUNT(*) as cnt FROM audit_log GROUP BY resource_type")
            api_stats["total_calls"] = sum(int(dict(r).get("cnt", 0)) for r in rows) if rows else 0
        except Exception:
            api_stats["total_calls"] = 0

        return {
            "api_calls": api_stats.get("total_calls", 0),
            "active_services": 3,
        }
    except Exception:
        return {"api_calls": 0, "active_services": 3}


def get_full_dashboard() -> dict:
    """Aggregate all ops metrics"""
    return {
        "mrr": get_mrr(),
        "users": get_user_stats(),
        "tenants": get_tenant_stats(),
        "usage": get_usage_overview(),
        "generated_at": datetime.now().isoformat(),
    }
