#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Tenant Manager v1.0
Phase 2: Tenant isolation, configuration management, data separation.
Each tenant = independent content pipeline, creator models, feedback loop.
Enterprise ready: $58K base plan (1 tenant) → $200K enterprise (unlimited).

Architecture:
  Tenant DB → isolated config → isolated pipeline → isolated feedback → isolated billing
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import shutil

# === Path Configuration ===
TENANT_DIR = Path(r"C:\Users\xinzh\.openclaw\tenants")
TENANT_DB = TENANT_DIR / "tenant-database.json"
STATE_DIR = Path(r"C:\Users\xinzh\.openclaw\state")

for d in [TENANT_DIR, STATE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class MultiTenantManager:
    """
    Enterprise multi-tenant system.
    Each tenant gets:
      - Isolated data directory
      - Independent creator model calibration
      - Separate feedback loop
      - Usage-based billing metrics
    """

    PLANS = {
        "starter": {
            "name": "入门版",
            "price_monthly": 299,   # RMB
            "price_annual": 2990,
            "pipelines": 1,
            "platforms": 2,
            "creators": 1,
            "content_per_month": 50,
            "support": "email",
            "features": ["auto_publish", "basic_analytics"],
        },
        "pro": {
            "name": "专业版",
            "price_monthly": 999,
            "price_annual": 9990,
            "pipelines": 3,
            "platforms": 5,
            "creators": 3,
            "content_per_month": 150,
            "support": "priority",
            "features": ["auto_publish", "advanced_analytics", "ab_testing", "model_calibration", "multi_creator"],
        },
        "enterprise": {
            "name": "企业版",
            "price_monthly": 2999,
            "price_annual": 29990,
            "pipelines": -1,  # unlimited
            "platforms": -1,
            "creators": -1,
            "content_per_month": 300,
            "support": "dedicated",
            "features": ["all_pro_features", "custom_models", "api_access", "white_label", "dedicated_support", "sla_guarantee"],
        },
    }

    def __init__(self):
        self.db = self._load_db()

    def _load_db(self):
        if TENANT_DB.exists():
            return json.loads(TENANT_DB.read_text(encoding="utf-8"))
        db = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "tenants": {},
        }
        self._save_db(db)
        return db

    def _save_db(self, db=None):
        if db is None:
            db = self.db
        db["updated_at"] = datetime.now().isoformat()
        TENANT_DB.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

    def create_tenant(self, name, email, plan="starter", company=""):
        """Create a new tenant with isolated environment."""
        tenant_id = f"tenant-{uuid.uuid4().hex[:12]}"

        # Check plan exists
        if plan not in self.PLANS:
            return {"error": f"Invalid plan: {plan}", "available": list(self.PLANS.keys())}

        plan_config = self.PLANS[plan]

        tenant = {
            "id": tenant_id,
            "name": name,
            "email": email,
            "company": company,
            "plan": plan,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "billing": {
                "plan_price_monthly": plan_config["price_monthly"],
                "plan_price_annual": plan_config["price_annual"],
                "billing_cycle": "monthly",
                "next_billing_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "payment_status": "trial",
                "trial_ends_at": (datetime.now() + timedelta(days=14)).isoformat(),
            },
            "usage": {
                "content_generated": 0,
                "platforms_connected": 0,
                "creators_configured": 0,
                "api_calls": 0,
                "storage_bytes": 0,
            },
            "limits": {
                "pipelines": plan_config["pipelines"],
                "platforms": plan_config["platforms"],
                "creators": plan_config["creators"],
                "content_per_month": plan_config["content_per_month"],
            },
            "features": plan_config["features"],
            "config": {},
            "api_key": f"ak-{uuid.uuid4().hex[:24]}",
        }

        # Create isolated directory
        tenant_path = TENANT_DIR / tenant_id
        for subdir in ["config", "data", "models", "output", "feedback"]:
            (tenant_path / subdir).mkdir(parents=True, exist_ok=True)

        # Save tenant config
        (tenant_path / "tenant-config.json").write_text(
            json.dumps(tenant, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        self.db["tenants"][tenant_id] = tenant
        self._save_db()

        print(f"[TENANT] Created: {tenant_id} ({name}) - Plan: {plan}")
        print(f"  API Key: {tenant['api_key']}")
        print(f"  Path: {tenant_path}")

        return tenant

    def get_tenant(self, tenant_id):
        return self.db["tenants"].get(tenant_id)

    def list_tenants(self):
        tenants = []
        for tid, t in self.db["tenants"].items():
            tenants.append({
                "id": tid,
                "name": t["name"],
                "plan": t["plan"],
                "status": t["status"],
                "content_generated": t["usage"]["content_generated"],
                "created_at": t["created_at"][:10],
            })
        return tenants

    def update_usage(self, tenant_id, metric, delta=1):
        """Track tenant usage for billing."""
        if tenant_id not in self.db["tenants"]:
            return None

        tenant = self.db["tenants"][tenant_id]
        if metric in tenant["usage"]:
            tenant["usage"][metric] += delta

        # Check limits
        limit = tenant["limits"].get(metric)
        if limit and limit > 0 and tenant["usage"][metric] > limit:
            print(f"[LIMIT] {tenant_id}: {metric} exceeded ({tenant['usage'][metric]} > {limit})")
            return {"warning": "limit_exceeded", "metric": metric, "current": tenant["usage"][metric], "limit": limit}

        self._save_db()
        return tenant["usage"]

    def check_limit(self, tenant_id, metric):
        """Check if tenant is within limits for a metric."""
        if tenant_id not in self.db["tenants"]:
            return False

        tenant = self.db["tenants"][tenant_id]
        limit = tenant["limits"].get(metric)
        if limit is None:
            return True
        if limit == -1:  # Unlimited
            return True

        current = tenant["usage"].get(metric, 0)
        return current < limit

    def generate_billing_report(self, tenant_id):
        """Generate billing report for a tenant."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return None

        plan_config = self.PLANS.get(tenant["plan"], {})

        report = {
            "tenant": tenant["name"],
            "plan": tenant["plan"],
            "billing_cycle": tenant["billing"]["billing_cycle"],
            "monthly_price": plan_config.get("price_monthly", 0),
            "annual_price": plan_config.get("price_annual", 0),
            "usage": tenant["usage"],
            "overage": {},
        }

        # Calculate overages
        for metric, limit in tenant["limits"].items():
            if limit and limit > 0:
                current = tenant["usage"].get(metric, 0)
                if current > limit:
                    report["overage"][metric] = {
                        "limit": limit,
                        "current": current,
                        "excess": current - limit,
                    }

        return report

    def deactivate_tenant(self, tenant_id):
        """Deactivate a tenant (soft delete)."""
        if tenant_id in self.db["tenants"]:
            self.db["tenants"][tenant_id]["status"] = "inactive"
            self.db["tenants"][tenant_id]["deactivated_at"] = datetime.now().isoformat()
            self._save_db()
            return True
        return False

    def get_dashboard_stats(self):
        """Get aggregate dashboard statistics across all tenants."""
        stats = {
            "total_tenants": len(self.db["tenants"]),
            "active_tenants": sum(1 for t in self.db["tenants"].values() if t["status"] == "active"),
            "by_plan": {},
            "total_content_generated": 0,
            "monthly_revenue_estimate": 0,
            "trial_tenants": sum(1 for t in self.db["tenants"].values()
                                if t["billing"]["payment_status"] == "trial"),
        }

        for t in self.db["tenants"].values():
            plan = t["plan"]
            stats["by_plan"][plan] = stats["by_plan"].get(plan, 0) + 1
            stats["total_content_generated"] += t["usage"]["content_generated"]
            if t["status"] == "active" and t["billing"]["payment_status"] != "trial":
                stats["monthly_revenue_estimate"] += self.PLANS.get(plan, {}).get("price_monthly", 0)

        return stats


# === CLI Entry ===
if __name__ == "__main__":
    import sys
    mgr = MultiTenantManager()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python multi-tenant-manager.py create <name> <email> [plan]")
        print("  python multi-tenant-manager.py list")
        print("  python multi-tenant-manager.py dashboard")
        print("  python multi-tenant-manager.py bill <tenant_id>")
        print("  python multi-tenant-manager.py deactivate <tenant_id>")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else "Demo Tenant"
        email = sys.argv[3] if len(sys.argv) > 3 else "demo@example.com"
        plan = sys.argv[4] if len(sys.argv) > 4 else "starter"
        tenant = mgr.create_tenant(name, email, plan)
        print(f"\nCreated: {json.dumps(tenant, ensure_ascii=False, indent=2)}")

    elif cmd == "list":
        tenants = mgr.list_tenants()
        print(f"{'ID':30s} {'Name':20s} {'Plan':15s} {'Status':10s} {'Content':8s}")
        print("-" * 90)
        for t in tenants:
            print(f"{t['id']:30s} {t['name']:20s} {t['plan']:15s} {t['status']:10s} {t['content_generated']:8d}")

    elif cmd == "dashboard":
        stats = mgr.get_dashboard_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif cmd == "bill":
        if len(sys.argv) < 3:
            print("Usage: bill <tenant_id>")
            sys.exit(1)
        report = mgr.generate_billing_report(sys.argv[2])
        if report:
            print(json.dumps(report, ensure_ascii=False, indent=2))

    elif cmd == "deactivate":
        if len(sys.argv) < 3:
            print("Usage: deactivate <tenant_id>")
            sys.exit(1)
        if mgr.deactivate_tenant(sys.argv[2]):
            print(f"Deactivated: {sys.argv[2]}")
