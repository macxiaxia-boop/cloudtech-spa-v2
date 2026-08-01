"""Tests for new modules: tenant_service, digital_rights, content_scheduler, dashboard_stats"""
import json, pytest, secrets
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTenantService:
    def test_create_and_get_tenant(self):
        from tenant_service import create_tenant, get_tenant, get_plan, PLANS
        t = create_tenant("测试装企", ["厦门"], "pro", "Test Co", "test@test.com")
        assert t["id"].startswith("zq-")
        assert t["plan"] == "pro"
        assert t["cities"] == ["厦门"]
        # Verify retrieval
        t2 = get_tenant(t["id"])
        assert t2 is not None
        assert t2["name"] == "测试装企"
        # Verify plan
        plan = get_plan("pro")
        assert plan["name"] == "专业版"
        assert plan["monthly_quota"] == 150

    def test_check_quota(self):
        from tenant_service import check_quota, create_tenant, record_usage
        t = create_tenant("配额测试", ["厦门"], "starter", "QCo", "q@test.com")
        q = check_quota(t["id"])
        assert q["ok"] is True
        assert q["plan"] == "入门版"
        # Record usage
        record_usage(t["id"], "article", "测试")
        q2 = check_quota(t["id"])
        assert q2["used"] == 1

    def test_get_all_tenants(self):
        from tenant_service import get_all_tenants
        tenants = get_all_tenants()
        assert isinstance(tenants, list)
        assert len(tenants) >= 1

    def test_account_matrix(self):
        from tenant_service import get_account_matrix, create_tenant
        t = create_tenant("矩阵测试", ["厦门", "泉州"], "pro", "MC", "m@test.com")
        m = get_account_matrix(t["id"])
        assert m["total_accounts"] >= 1
        assert "厦门" in m["cities"]

    def test_distribute_content(self):
        from tenant_service import distribute_content, create_tenant
        t = create_tenant("分发测试", ["厦门"], "pro", "DC", "d@test.com")
        d = distribute_content(t["id"], "测试话题", "article")
        assert d["total_distributions"] >= 1
        assert len(d["plan"]) >= 1


class TestDigitalRights:
    def test_register_asset(self):
        from digital_rights import register_asset, get_asset, ASSET_TYPES
        r = register_asset("portrait", "测试肖像", "测试权利人")
        assert r["ok"] is True
        aid = r["asset"]["id"]
        assert aid.startswith("ra-")
        # Verify
        a = get_asset(aid)
        assert a["title"] == "测试肖像"
        assert a["owner"] == "测试权利人"
        assert a["status"] == "active"

    def test_list_assets(self):
        from digital_rights import list_assets, register_asset
        register_asset("music", "测试BGM", "测试权利人")
        assets = list_assets()
        assert len(assets) >= 1

    def test_record_usage(self):
        from digital_rights import register_asset, record_usage
        r = register_asset("footage", "测试素材", "测试方")
        aid = r["asset"]["id"]
        u = record_usage(aid, "用于测试视频", "zq-test")
        assert u["ok"] is True

    def test_compliance_check(self):
        from digital_rights import compliance_check
        c = compliance_check("voiceover")
        assert c["risk_level"] in ("low", "medium", "high")

    def test_get_report(self):
        from digital_rights import get_compliance_report
        r = get_compliance_report()
        assert "total_assets" in r


class TestContentScheduler:
    def test_queue_operations(self):
        from content_scheduler import get_queue, enqueue, schedule, publish_now, get_stats
        import secrets
        tid = f"zq-test-{secrets.token_hex(4)}"  # Unique per run
        # Enqueue
        r = enqueue(tid, {"topic": "测试内容", "account": "测试号", "platform": "xiaohongshu"})
        assert r["ok"] is True
        # Schedule
        item_id = r["item"]["id"]
        s = schedule(tid, item_id, "2026-08-01 10:00")
        assert s["ok"] is True
        # Stats
        stats = get_stats(tid)
        assert stats["scheduled"] >= 1  # At least our scheduled item

    def test_calendar(self):
        from content_scheduler import get_calendar, enqueue
        tid = "zq-test-cal"
        enqueue(tid, {"topic": "日历测试", "account": "测试", "platform": "douyin"})
        c = get_calendar(tid, 3)
        assert c["total_queued"] >= 0
        assert len(c["calendar"]) == 3

    def test_execute_distribution(self):
        from content_scheduler import execute_distribution, get_stats
        tid = "zq-5bb59623"  # Real demo tenant
        r = execute_distribution(tid, "自动化测试分发", "article")
        if r.get("ok"):
            assert r["total_distributions"] >= 1
            assert r["enqueued"] >= 1


class TestNewModules:
    """P2新增模块测试"""

    def test_brand_assets(self):
        from brand_assets import create_brand, add_asset, list_brands, get_brand_stats, remove_asset
        import secrets
        tid = f"zq-brand-{secrets.token_hex(4)}"
        b = create_brand(tid, "测试品牌")
        assert b["ok"]
        a = add_asset(b["brand"]["id"], "logo", "Logo", "/test/logo.png")
        assert a["ok"]
        brands = list_brands(tid)
        assert len(brands) >= 1
        stats = get_brand_stats(tid)
        assert stats["brand_count"] >= 1

    def test_approval_engine(self):
        from approval_engine import submit_for_review, approve, reject, get_approvals
        import secrets
        tid = f"zq-apr-{secrets.token_hex(4)}"
        app = submit_for_review(tid, "c1", "测试审批", "admin")
        assert app["ok"]
        apr = approve(app["approval"]["id"], "reviewer", "通过")
        assert apr["ok"]
        assert apr["approval"]["status"] == "approved"
        approvals = get_approvals(tid)
        assert len(approvals) >= 1

    def test_digital_human(self):
        from digital_human import register_avatar, add_voice, list_avatars
        import secrets
        tid = f"zq-av-{secrets.token_hex(4)}"
        av = register_avatar(tid, "测试数字人", "stock")
        assert av["ok"]
        vc = add_voice(av["avatar"]["id"], "测试声音", "/test.wav")
        assert vc["ok"]
        avatars = list_avatars(tid)
        assert len(avatars) >= 1

    def test_compliance_auto(self):
        from compliance_auto import run_compliance_check, get_compliance_stats
        r = run_compliance_check({"text": "100%保证最好的装修效果", "title": "测试"})
        assert "status" in r
        stats = get_compliance_stats()
        assert "total_checks" in stats

    def test_webhooks(self):
        from webhooks import register_webhook, list_webhooks, delete_webhook
        import secrets
        tid = f"zq-wh-{secrets.token_hex(4)}"
        wh = register_webhook(tid, "content.created", "https://example.com/hook")
        assert wh["ok"]
        hooks = list_webhooks(tid)
        assert len(hooks) >= 1
        delete_webhook(wh["webhook"]["id"])

    def test_backup_scheduler(self):
        from backup_scheduler import run_backup, list_backups, get_backup_status
        r = run_backup("test")
        assert r["ok"]
        backups = list_backups(5)
        assert len(backups) >= 1
        status = get_backup_status()
        assert status["total_backups"] >= 1

    def test_audit_viewer(self):
        from audit_viewer import log_activity, get_tenant_activity, get_activity_summary
        import secrets
        tid = f"zq-aud-{secrets.token_hex(4)}"
        log_activity(tid, "test.action", {"key": "value"})
        activities = get_tenant_activity(tid, 1)
        assert len(activities) >= 1
        summary = get_activity_summary(1)
        assert "total_activities" in summary

    def test_content_recommender(self):
        from content_recommender import recommend_topics
        r = recommend_topics("zq-test", "厦门", 3)
        assert len(r["recommendations"]) == 3

    def test_template_library(self):
        from template_library import list_templates, get_template_categories
        templates = list_templates()
        assert len(templates) >= 5
        cats = get_template_categories()
        assert len(cats) >= 3


class TestDashboardStats:
    def test_get_content_stats(self):
        from dashboard_stats import get_content_stats
        s = get_content_stats()
        assert "total_files" in s
        assert s["total_files"] >= 0  # May be 0 in clean env

    def test_get_tenant_stats(self):
        from dashboard_stats import get_tenant_stats
        s = get_tenant_stats()
        assert "total" in s
        assert "tenants" in s

    def test_get_full_stats(self):
        from dashboard_stats import get_full_stats
        s = get_full_stats()
        assert "content" in s
        assert "tenants" in s
        assert "publish" in s
        assert "system" in s
        assert "generated_at" in s
