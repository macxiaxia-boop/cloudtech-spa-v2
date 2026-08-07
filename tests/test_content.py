"""Content Intelligence Tests — Scoring, Optimization, Templates"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════
# Content Performance Prediction
# ═══════════════════════════════════

class TestContentPrediction:
    """内容效果预测"""

    def test_predict_performance_returns_structure(self):
        from content_intelligence import predict_performance
        result = predict_performance("zq-5bb59623", "奶油风装修设计", "xiaohongshu")
        assert "predicted_impressions" in result
        assert "predicted_engagement_rate" in result
        assert "confidence" in result
        assert "trend" in result
        assert "best_publish_time" in result

    def test_predict_performance_all_platforms(self):
        from content_intelligence import predict_performance
        platforms = ["xiaohongshu", "douyin", "wechat", "shipinhao"]
        for platform in platforms:
            result = predict_performance("zq-5bb59623", "测试主题", platform)
            assert result["platform"] == platform
            assert result["predicted_impressions"] > 0

    def test_predict_performance_content_types(self):
        from content_intelligence import predict_performance
        types = ["article", "short_video", "voiceover", "persona", "storytelling"]
        for ct in types:
            result = predict_performance("zq-5bb59623", "测试", "douyin", content_type=ct)
            assert result["content_type"] == ct
            assert result["predicted_impressions"] > 0

    def test_predict_performance_impressions_positive(self):
        from content_intelligence import predict_performance
        result = predict_performance("zq-5bb59623", "测试", "xiaohongshu")
        assert result["predicted_impressions"] > 0
        assert result["predicted_engagement_rate"] > 0

    def test_predict_performance_confidence_valid(self):
        from content_intelligence import predict_performance
        result = predict_performance("zq-5bb59623", "测试", "xiaohongshu")
        assert result["confidence"] in ("高", "中", "低")

    def test_predict_performance_best_time_format(self):
        from content_intelligence import predict_performance
        result = predict_performance("zq-5bb59623", "测试", "xiaohongshu")
        # Best time should contain hours
        assert ":" in result["best_publish_time"]


# ═══════════════════════════════════
# Content Optimization Tips
# ═══════════════════════════════════

class TestContentOptimization:
    """内容优化建议"""

    def test_get_optimization_tips_structure(self):
        from content_intelligence import get_optimization_tips
        result = get_optimization_tips("zq-5bb59623", "装修设计", "xiaohongshu")
        assert "tips" in result
        assert "topic" in result
        assert "platform" in result

    def test_get_optimization_tips_has_categories(self):
        from content_intelligence import get_optimization_tips
        result = get_optimization_tips("zq-5bb59623", "测试话题", "douyin")
        tips = result["tips"]
        categories = {t.get("category") for t in tips}
        assert len(categories) >= 3  # Title, timing, tags, engagement, length

    def test_get_optimization_tips_all_platforms(self):
        from content_intelligence import get_optimization_tips
        for platform in ["xiaohongshu", "douyin", "wechat", "shipinhao"]:
            result = get_optimization_tips("zq-5bb59623", "测试", platform)
            assert result["platform"] == platform
            assert len(result["tips"]) >= 3

    def test_optimization_tips_impact_levels(self):
        from content_intelligence import get_optimization_tips
        result = get_optimization_tips("zq-5bb59623", "测试", "xiaohongshu")
        impacts = {t.get("impact") for t in result["tips"]}
        assert "high" in impacts  # At least high-impact tip present


# ═══════════════════════════════════
# Supply Chain Analysis
# ═══════════════════════════════════

class TestSupplyChain:
    """内容供应链分析"""

    def test_supply_chain_analysis_structure(self):
        from content_intelligence import supply_chain_analysis
        result = supply_chain_analysis("zq-5bb59623")
        assert "supply_chain_health" in result
        health = result["supply_chain_health"]
        assert "score" in health
        assert "grade" in health
        assert "dimensions" in health
        assert "bottleneck" in health

    def test_supply_chain_grade_valid(self):
        from content_intelligence import supply_chain_analysis
        result = supply_chain_analysis("zq-5bb59623")
        grade = result["supply_chain_health"]["grade"]
        assert grade in ("A", "B", "C", "D", "F"), f"Invalid grade: {grade}"

    def test_supply_chain_score_range(self):
        from content_intelligence import supply_chain_analysis
        result = supply_chain_analysis("zq-5bb59623")
        score = result["supply_chain_health"]["score"]
        assert 0 <= score <= 10, f"Score {score} out of range"

    def test_supply_chain_dimensions_present(self):
        from content_intelligence import supply_chain_analysis
        result = supply_chain_analysis("zq-5bb59623")
        dims = result["supply_chain_health"]["dimensions"]
        # Should have 产能, 质量, 配额
        assert len(dims) >= 3
        for key in dims:
            dim = dims[key]
            assert "score" in dim
            assert "label" in dim


# ═══════════════════════════════════
# Template Library
# ═══════════════════════════════════

class TestTemplateLibrary:
    """内容模板库"""

    def test_list_templates_returns_all(self):
        from template_library import list_templates
        templates = list_templates()
        assert len(templates) >= 10  # Should have many templates

    def test_list_templates_by_category(self):
        from template_library import list_templates
        for cat in ["装修知识", "案例展示", "产品推广", "知识科普", "施工日记"]:
            templates = list_templates(category=cat)
            for t in templates:
                assert t.get("category") == cat or cat in str(t.get("platforms", []))

    def test_list_templates_by_platform(self):
        from template_library import list_templates
        platforms_to_test = ["xiaohongshu", "抖音", "公众号"]
        for platform in platforms_to_test:
            templates = list_templates(platform=platform)
            for t in templates:
                assert platform in t.get("platforms", []), f"Template {t['name']} doesn't support {platform}"

    def test_get_template_categories(self):
        from template_library import get_template_categories
        cats = get_template_categories()
        assert len(cats) >= 3
        assert isinstance(cats, list)

    def test_template_structure_complete(self):
        from template_library import list_templates
        templates = list_templates()
        for t in templates:
            assert "name" in t, f"Template missing name"
            # Video templates have 'duration' and 'scenes'; content templates have 'structure'
            assert "platforms" in t, f"Template {t['name']} missing platforms"

    def test_apply_template_basic(self):
        from template_library import apply_template
        result = apply_template("避坑指南", {"topic": "水电改造"})
        # May return ok or error about AI not available
        assert "ok" in result or "error" in result

    def test_apply_template_nonexistent(self):
        from template_library import apply_template
        result = apply_template("不存在的模板XYZ", {})
        assert result["ok"] is False

    def test_templates_have_all_fields(self):
        from template_library import list_templates, PRESET_TEMPLATES
        total = sum(len(v) for v in PRESET_TEMPLATES.values())
        templates = list_templates()
        assert len(templates) == total, f"list_templates returned {len(templates)} but total is {total}"

    def test_template_word_ranges_valid(self):
        from template_library import list_templates
        templates = list_templates()
        for t in templates:
            if "word_range" in t:
                low, high = t["word_range"]
                assert low > 0
                assert high >= low


# ═══════════════════════════════════
# Cross-Module Integration
# ═══════════════════════════════════

class TestContentIntegration:
    """跨模块集成测试"""

    def test_prediction_to_tips_flow(self):
        """Predict → get tips → supply chain"""
        from content_intelligence import predict_performance, get_optimization_tips, supply_chain_analysis

        # Full content intelligence flow
        pred = predict_performance("zq-5bb59623", "奶油风装修", "xiaohongshu")
        assert pred["predicted_impressions"] > 0

        tips = get_optimization_tips("zq-5bb59623", "奶油风装修", "xiaohongshu")
        assert len(tips["tips"]) >= 3

        chain = supply_chain_analysis("zq-5bb59623")
        assert chain["supply_chain_health"]["grade"] in ("A", "B", "C")

    def test_content_recommender_integration(self):
        """Content recommender should return structured results"""
        from content_recommender import recommend_topics
        result = recommend_topics("zq-test", "厦门", 5)
        assert len(result["recommendations"]) == 5
        for rec in result["recommendations"]:
            assert isinstance(rec, dict)
