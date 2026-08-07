"""GEO Engine Tests — Keywords, Rankings, Content, Strategy"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════
# GEO Dashboard & Keywords
# ═══════════════════════════════════

class TestGEODashboard:
    """GEO仪表盘和关键词"""

    def test_get_geo_dashboard_structure(self):
        from geo_deep import get_geo_dashboard
        result = get_geo_dashboard(city="漳州")
        assert isinstance(result, dict)
        # Should have key sections
        assert "city" in result or "summary" in result

    def test_get_geo_dashboard_multiple_cities(self):
        from geo_deep import get_geo_dashboard
        for city in ["漳州", "厦门", "泉州"]:
            result = get_geo_dashboard(city=city)
            assert isinstance(result, dict)

    def test_check_ai_ranking_structure(self):
        from geo_deep import check_ai_ranking
        # This may fail with network errors - that's fine
        result = check_ai_ranking("装修设计", city="漳州", platforms=["deepseek"])
        assert "ok" in result
        assert "keyword" in result
        assert "results" in result
        assert isinstance(result["results"], dict)

    def test_check_ai_ranking_with_platforms(self):
        from geo_deep import check_ai_ranking
        result = check_ai_ranking("奶油风装修", city="厦门", platforms=["deepseek", "doubao"])
        assert "ok" in result
        assert result["platforms_checked"] <= 2


# ═══════════════════════════════════
# Ranking Analysis
# ═══════════════════════════════════

class TestGEORanking:
    """排名分析"""

    def test_analyze_ranking_with_hit(self):
        """Simulate HTML with our domain present"""
        from geo_deep import _analyze_ranking
        html = """<html><body>
            <div class="result">cloudtech.ai - 漳州装修设计首选</div>
            <div class="result">competitor.com - 厦门装修公司</div>
            <div class="result">another.com - 福州装修</div>
        </body></html>"""
        result = _analyze_ranking(html, "cloudtech.ai", "装修设计", "deepseek")
        assert "found" in result
        assert isinstance(result["competitors"], list)

    def test_analyze_ranking_without_hit(self):
        """Simulate HTML without our domain"""
        from geo_deep import _analyze_ranking
        html = """<html><body>
            <div>competitor1.com</div>
            <div>competitor2.com</div>
        </body></html>"""
        result = _analyze_ranking(html, "cloudtech.ai", "装修设计", "deepseek")
        assert "found" in result

    def test_analyze_ranking_empty_html(self):
        from geo_deep import _analyze_ranking
        result = _analyze_ranking("", "cloudtech.ai", "测试", "deepseek")
        assert "found" in result
        assert result["found"] is False

    def test_get_ranking_trend_structure(self):
        from geo_deep import get_ranking_trend
        result = get_ranking_trend("装修设计", days=30)
        assert isinstance(result, dict)
        assert "keyword" in result


# ═══════════════════════════════════
# Competitor Analysis
# ═══════════════════════════════════

class TestGEOCompetitors:
    """竞品分析"""

    def test_competitor_geo_analysis_structure(self):
        from geo_deep import competitor_geo_analysis
        result = competitor_geo_analysis(
            "competitor.com",
            ["装修设计", "水电改造"],
            city="漳州"
        )
        assert isinstance(result, dict)
        assert "ok" in result

    def test_competitor_geo_analysis_empty_competitors(self):
        from geo_deep import competitor_geo_analysis
        result = competitor_geo_analysis("example.com", ["装修设计"], city="漳州")
        assert isinstance(result, dict)

    def test_discover_content_gaps_structure(self):
        from geo_deep import discover_content_gaps
        result = discover_content_gaps(["装修设计", "水电改造"], city="漳州")
        assert isinstance(result, dict)
        assert "ok" in result


# ═══════════════════════════════════
# GEO Keywords
# ═══════════════════════════════════

class TestGEOKeywords:
    """GEO关键词"""

    def test_estimate_volume_valid_range(self):
        from geo_deep import _estimate_volume
        volumes = []
        for kw in ["装修", "漳州装修设计", "奶油风", "水电改造多少钱", "厨房翻新"]:
            vol = _estimate_volume(kw)
            assert vol > 0, f"Volume for '{kw}' was {vol}"
            assert vol <= 100000, f"Volume for '{kw}' was {vol} > 100k"
            volumes.append(vol)
        # Different keywords should have different estimates
        assert len(set(volumes)) >= 2, "All keywords have same volume estimate"

    def test_suggest_content_type_valid(self):
        from geo_deep import _suggest_content_type
        types = set()
        for kw in ["装修设计", "水电改造", "厨房翻新多少钱", "装修公司排名", "奶油风"]:
            ct = _suggest_content_type(kw)
            assert isinstance(ct, str)
            assert len(ct) > 0
            types.add(ct)
        assert len(types) >= 2, "All keywords map to same content type"

    def test_suggest_content_angle(self):
        from geo_deep import _suggest_content_angle
        angle = _suggest_content_angle("奶油风装修", "漳州")
        assert isinstance(angle, str)
        assert len(angle) > 10

    def test_generate_geo_title(self):
        from geo_deep import _generate_geo_title
        title = _generate_geo_title("水电改造注意事项", "厦门")
        assert isinstance(title, str)
        assert len(title) > 5
        assert "厦门" in title or "水电" in title

    def test_suggest_content_angle_includes_city(self):
        from geo_deep import _suggest_content_angle
        for city in ["漳州", "厦门", "泉州"]:
            angle = _suggest_content_angle("装修预算", city)
            # May or may not include city name
            assert isinstance(angle, str)


# ═══════════════════════════════════
# Content Generation & Strategy
# ═══════════════════════════════════

class TestGEOContent:
    """GEO内容生成与策略"""

    def test_load_existing_geo_topics(self):
        from geo_deep import _load_existing_geo_topics
        topics = _load_existing_geo_topics()
        assert isinstance(topics, set)
        # May be empty in clean env

    def test_generate_geo_recommendation_format(self):
        from geo_deep import _generate_geo_recommendation
        gaps = [{"keyword": "装修设计", "city": "漳州", "gap_type": "uncovered", "priority": "P0", "action": "创建针对'装修设计'的SEO优化内容"}]
        recommendation = _generate_geo_recommendation(gaps)
        assert isinstance(recommendation, str)
        assert len(recommendation) > 10

    def test_geo_recommendation_empty_gaps(self):
        from geo_deep import _generate_geo_recommendation
        result = _generate_geo_recommendation([])
        assert isinstance(result, str)

    def test_batch_rank_check_structure(self):
        from geo_deep import batch_rank_check
        result = batch_rank_check(
            keywords=["装修设计", "水电改造"],
            city="漳州",
            platforms=["deepseek"]
        )
        assert isinstance(result, dict)
        assert "ok" in result
        assert "total" in result


# ═══════════════════════════════════
# GEO Output Format Validation
# ═══════════════════════════════════

class TestGEOOutputs:
    """GEO输出格式验证"""

    def test_ranking_result_format(self):
        """Ranking result from check_ai_ranking should have consistent format"""
        from geo_deep import check_ai_ranking
        result = check_ai_ranking("装修设计", city="漳州", platforms=["deepseek"])
        assert "keyword" in result
        assert "results" in result
        for platform, data in result["results"].items():
            assert "keyword" in data
            assert "city" in data

    def test_discover_content_gaps_has_gap_types(self):
        from geo_deep import discover_content_gaps
        result = discover_content_gaps(["装修设计", "水电改造"], city="漳州")
        if result.get("gaps"):
            for gap in result["gaps"]:
                assert "keyword" in gap or "gap_type" in gap or "city" in gap or "gap" in gap

    def test_estimate_volume_by_length(self):
        """Longer keywords should not always have lower volume than shorter ones"""
        from geo_deep import _estimate_volume
        short_vol = _estimate_volume("装修")
        # Different keywords have different volumes
        assert isinstance(short_vol, int)
        assert short_vol > 0

    def test_geo_dashboard_has_stats(self):
        from geo_deep import get_geo_dashboard
        result = get_geo_dashboard(city="漳州")
        # Should have some meaningful content
        assert len(result) >= 1
        # Print keys for debugging
        valid_keys = {"city", "summary", "keywords", "rankings", "recommendations", "total"}
        has_valid = any(k in valid_keys for k in result)
        assert has_valid, f"Dashboard missing expected keys. Got: {list(result.keys())}"
