"""CRM Pipeline Tests — CustomerManager + DeepCRM + Funnel + Attribution"""
import json
import sys
import secrets
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════
# CustomerManager (CRM Integration)
# ═══════════════════════════════════

class TestCustomerManager:
    """CRM基础客户管理 — add/get/update/list/delete"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from crm_integration import CustomerManager
        self.mgr = CustomerManager()
        self.test_ids = []

    def teardown_method(self):
        for cid in self.test_ids:
            try:
                self.mgr.delete_customer(cid)
            except Exception:
                pass

    def _add(self, name, phone=None, source="other", **kw):
        phone = phone or f"180{secrets.token_hex(4)[:8]}"
        r = self.mgr.add_customer(name=name, phone=phone, source=source, **kw)
        if r.get("ok"):
            self.test_ids.append(r["customer"]["id"])
        return r

    def test_add_customer_basic(self):
        r = self._add("张测试", source="douyin")
        assert r["ok"] is True
        assert r["customer"]["name"] == "张测试"
        assert r["customer"]["source"] == "douyin"
        assert r["customer"]["stage"] == "lead"
        assert "id" in r["customer"]

    def test_add_customer_with_all_fields(self):
        r = self._add(
            "李完整", source="referral", city="厦门",
            area=120, budget=25,
            style="奶油风", notes="急需本月开工"
        )
        assert r["ok"] is True
        c = r["customer"]
        assert c["city"] == "厦门"
        assert c["area"] == 120
        assert c["budget"] == 25
        assert c["style"] == "奶油风"

    def test_add_customer_duplicate_phone(self):
        phone = f"180{secrets.token_hex(4)[:8]}"
        r1 = self._add("重复客户A", phone=phone)
        assert r1["ok"] is True
        r2 = self._add("重复客户B", phone=phone)
        assert "ok" in r2

    def test_get_customer_exists(self):
        r = self._add("王存在")
        cid = r["customer"]["id"]
        result = self.mgr.get_customer(cid)
        assert result["ok"] is True
        assert result["customer"]["name"] == "王存在"

    def test_get_customer_nonexistent(self):
        result = self.mgr.get_customer("crm-nonexistent-id-9999")
        assert result["ok"] is False

    def test_update_stage_flow(self):
        r = self._add("赵阶段", source="geo_search")
        cid = r["customer"]["id"]

        stages = ["contacted", "measured", "quoted", "negotiating", "signed"]
        for stage in stages:
            result = self.mgr.update_stage(cid, stage, f"推进到{stage}")
            assert result["ok"] is True
            assert result["customer"]["stage"] == stage

        c = self.mgr.get_customer(cid)
        assert c["customer"]["stage"] == "signed"

    def test_update_stage_nonexistent(self):
        result = self.mgr.update_stage("bad-id-9999", "contacted")
        assert result["ok"] is False

    def test_add_tag(self):
        r = self._add("孙标签")
        cid = r["customer"]["id"]
        tag_result = self.mgr.add_tag(cid, "vip")
        assert tag_result["ok"] is True

    def test_add_tag_nonexistent(self):
        from crm_integration import CustomerManager
        mgr = CustomerManager()
        result = mgr.add_tag("bad-id-9999", "test")
        assert result["ok"] is False

    def test_list_customers_all(self):
        self._add("列表客户A", source="douyin")
        self._add("列表客户B", source="xiaohongshu")
        result = self.mgr.list_customers()
        assert result["ok"] is True
        assert result["total"] >= 2

    def test_list_customers_filter_by_stage(self):
        result = self.mgr.list_customers(stage="lead")
        assert result["ok"] is True
        for c in result["customers"]:
            assert c["stage"] == "lead"

    def test_list_customers_filter_by_source(self):
        self._add("搜索客户", source="geo_search")
        result = self.mgr.list_customers(source="geo_search")
        assert result["ok"] is True
        for c in result["customers"]:
            assert c["source"] == "geo_search"

    def test_list_customers_search_keyword(self):
        self._add("独特名字XYZ123")
        result = self.mgr.list_customers(keyword="XYZ123")
        assert result["ok"] is True
        assert result["total"] >= 1

    def test_list_customers_pagination(self):
        for i in range(5):
            self._add(f"翻页客户{i}", source="other")
        result = self.mgr.list_customers(limit=3, offset=0)
        assert result["ok"] is True
        assert result["count"] <= 3
        assert result["offset"] == 0

    def test_delete_customer(self):
        r = self._add("待删除")
        cid = r["customer"]["id"]
        del_result = self.mgr.delete_customer(cid)
        assert del_result["ok"] is True
        check = self.mgr.get_customer(cid)
        assert check["ok"] is False
        self.test_ids.remove(cid)

    def test_delete_customer_nonexistent(self):
        result = self.mgr.delete_customer("bad-id-9999")
        assert result["ok"] is False

    def test_get_funnel(self):
        self._add("漏斗客户1", source="douyin")
        funnel = self.mgr.get_funnel()
        assert funnel.get("total", 0) >= 1


# ═══════════════════════════════════
# DeepCRM — Lead Scoring & Health
# ═══════════════════════════════════

class TestDeepCRMScoring:
    """深度CRM: 智能评分、健康监控、流失检测"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from crm_deep import DeepCRM
        self.crm = DeepCRM()
        self.test_ids = []

    def teardown_method(self):
        customers = self.crm._load()
        self.crm._save([c for c in customers if c["id"] not in self.test_ids])

    def _add_customer(self, **kw):
        r = self.crm.add_customer(**kw)
        self.test_ids.append(r["customer"]["id"])
        return r

    def test_lead_scoring_referral_high(self):
        r = self._add_customer(name="高分客户", source="referral", budget=25, urgency="immediate")
        score = r["customer"]["score"]
        assert score >= 50, f"Expected score >= 50, got {score}"
        assert 0 <= score <= 100

    def test_lead_scoring_low_value(self):
        r = self._add_customer(name="低分客户", source="other", budget=0, urgency="exploring")
        score = r["customer"]["score"]
        assert score <= 25, f"Expected score <= 25, got {score}"
        assert score >= 0

    def test_lead_scoring_geo_source(self):
        r = self._add_customer(name="搜索客户", source="geo_search", budget=12, urgency="1_month")
        score = r["customer"]["score"]
        assert score >= 40, f"Expected score >= 40, got {score}"

    def test_scoring_improves_with_interactions(self):
        r = self._add_customer(name="互动客户", source="douyin", budget=15, urgency="3_months")
        cid = r["customer"]["id"]
        score_before = r["customer"]["score"]

        self.crm.add_interaction(cid, "call", "客户有明确需求", "positive")
        self.crm.add_interaction(cid, "measure", "已完成量房", "positive")

        result = self.crm.list_customers(keyword="互动客户")
        for c in result["customers"]:
            if c["id"] == cid:
                assert c["score"] > score_before, f"Expected increase, got {c['score']}"

    def test_health_healthy_new(self):
        r = self._add_customer(name="健康客户", source="douyin", budget=15, urgency="1_month")
        result = self.crm.list_customers(keyword="健康客户")
        for c in result["customers"]:
            assert c.get("health") in ("healthy", "neutral")

    def test_interaction_timeline(self):
        r = self._add_customer(name="时间线客户", source="douyin")
        cid = r["customer"]["id"]
        self.crm.add_interaction(cid, "call", "首次沟通", "positive")
        self.crm.add_interaction(cid, "wechat", "发送案例", "neutral")
        self.crm.add_interaction(cid, "visit", "客户到店", "positive")

        interactions = self.crm.get_interactions(cid)
        assert interactions["ok"] is True
        assert interactions["total_interactions"] >= 3

    def test_stage_update_creates_follow_ups(self):
        r = self._add_customer(name="跟进客户", source="geo_search", budget=20, urgency="immediate")
        cid = r["customer"]["id"]
        result = self.crm.update_stage(cid, "contacted", "已电话联系")
        assert result["ok"] is True
        for c in self.crm._load():
            if c["id"] == cid:
                assert len(c["follow_ups"]) >= 1
                break
        assert len(result.get("auto_actions", [])) >= 1

    def test_calculate_score_range(self):
        for source, budget, urgency in [
            ("referral", 30, "immediate"),
            ("douyin", 10, "exploring"),
            ("geo_search", 15, "1_month"),
            ("paid_ads", 8, "3_months"),
            ("other", 0, "unknown"),
        ]:
            r = self._add_customer(name=f"范围{source}", source=source, budget=budget, urgency=urgency)
            score = r["customer"]["score"]
            assert 0 <= score <= 100, f"Score {score} out of range for {source}/{budget}/{urgency}"

    def test_list_customers_by_score(self):
        self._add_customer(name="高分过滤", source="referral", budget=30, urgency="immediate")
        self._add_customer(name="低分过滤", source="other", budget=0, urgency="exploring")
        result = self.crm.list_customers(min_score=50)
        assert result["ok"] is True
        for c in result["customers"]:
            assert c.get("score", 0) >= 50

    def test_task_management(self):
        r = self._add_customer(name="任务客户")
        task_result = self.crm.add_task(
            customer_id=r["customer"]["id"],
            customer_name="任务客户",
            name="制作方案报价",
            stage="lead",
            due_days=3,
            priority="high"
        )
        assert task_result["ok"] is True
        assert task_result["task"]["status"] == "pending"
        assert task_result["task"]["priority"] == "high"


# ═══════════════════════════════════
# CRM Data Integrity
# ═══════════════════════════════════

class TestCRMIntegrity:
    """数据完整性、边界条件、异常处理"""

    def test_customer_id_uniqueness(self):
        from crm_deep import DeepCRM
        crm = DeepCRM()
        r1 = crm.add_customer(name="唯一性A")
        r2 = crm.add_customer(name="唯一性B")
        assert r1["customer"]["id"] != r2["customer"]["id"]
        customers = crm._load()
        crm._save([c for c in customers if c["id"] not in (r1["customer"]["id"], r2["customer"]["id"])])

    def test_empty_name_handled(self):
        from crm_deep import DeepCRM
        crm = DeepCRM()
        r = crm.add_customer(name="", source="other")
        assert r["ok"] is True
        customers = crm._load()
        crm._save([c for c in customers if c["id"] != r["customer"]["id"]])

    def test_max_length_fields(self):
        from crm_deep import DeepCRM
        crm = DeepCRM()
        long_name = "测" * 100
        long_notes = "注" * 500
        r = crm.add_customer(name=long_name, notes=long_notes, source="other")
        assert r["ok"] is True
        assert len(r["customer"]["name"]) == 100
        customers = crm._load()
        crm._save([c for c in customers if c["id"] != r["customer"]["id"]])

    def test_source_attribution_valid(self):
        from crm_deep import LEAD_SCORE_RULES
        valid_sources = set(LEAD_SCORE_RULES["source"].keys())
        assert "referral" in valid_sources
        assert "geo_search" in valid_sources
        assert "xiaohongshu" in valid_sources
        assert "douyin" in valid_sources
        assert len(valid_sources) >= 7

    def test_stage_timeline_complete(self):
        from crm_deep import STAGE_TIMELINE
        required_stages = ["lead", "contacted", "measured", "quoted", "negotiating", "signed"]
        for stage in required_stages:
            assert stage in STAGE_TIMELINE, f"Missing stage: {stage}"
            assert "max_days" in STAGE_TIMELINE[stage]
            assert "action" in STAGE_TIMELINE[stage]

    def test_deep_crm_list_with_filters(self):
        from crm_deep import DeepCRM
        crm = DeepCRM()
        r1 = crm.add_customer(name="过滤源A", source="douyin", budget=20, urgency="immediate")
        r2 = crm.add_customer(name="过滤源B", source="xiaohongshu", budget=5, urgency="exploring")
        ids = [r1["customer"]["id"], r2["customer"]["id"]]

        result = crm.list_customers(source="douyin")
        assert result["ok"]
        result = crm.list_customers(min_score=40)
        assert result["ok"]

        customers = crm._load()
        crm._save([c for c in customers if c["id"] not in ids])
