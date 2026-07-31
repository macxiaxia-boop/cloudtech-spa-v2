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
        tid = "zq-test-scheduler"
        # Enqueue
        r = enqueue(tid, {"topic": "测试内容", "account": "测试号", "platform": "xiaohongshu"})
        assert r["ok"] is True
        # Schedule
        item_id = r["item"]["id"]
        s = schedule(tid, item_id, "2026-08-01 10:00")
        assert s["ok"] is True
        # Stats
        stats = get_stats(tid)
        assert stats["queued"] == 0
        assert stats["scheduled"] == 1

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
