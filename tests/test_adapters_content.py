"""CloudTech V4 — content adapters 集成测试 (mock-only)"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.content import (
    StructureAnalyzer,
    OriginalScriptGenerator,
    SimilarityQC,
    ContentDirector,
    analyze,
    generate,
    review,
    direct,
)


# ══════════════════════════════════════════════════════════════
# Structure Analyzer — 三种模板启发式
# ══════════════════════════════════════════════════════════════

class TestStructureAnalyzerTemplates:
    """结构分析器模板启发式"""

    def test_problem_solution_cta(self):
        """problem-solution-cta 模板检测"""
        text = "很多人都有睡眠问题，晚上睡不着，白天没精神。我们发现只要掌握这三个方法，就能轻松解决失眠困扰。今天教你如何快速入睡。"
        result = analyze([], text)
        assert result["structure_template"] == "problem-solution-cta"
        assert result["mock"] is True
        assert result["hook"]["score"] > 0

    def test_listicle(self):
        """listicle 模板检测"""
        text = "第一、每天早起喝一杯温水。第二、午餐后散步十分钟。第三、睡前做深呼吸。六点建议送给你：放下手机。"
        result = analyze([], text)
        assert result["structure_template"] == "listicle"
        assert len(result["body_segments"]) >= 1

    def test_story_arc(self):
        """story-arc 模板检测"""
        text = "曾经我也经历过失败，后来有一天我决定改变。故事要从那时候说起，我开始重新规划每一天。回忆那些经历，我学会了坚持。"
        result = analyze([], text)
        assert result["structure_template"] == "story-arc"

    def test_unknown_template(self):
        """无明显模板特征 → unknown"""
        text = "今天天气不错我们去公园散步吧顺便买点东西回家做饭。"
        result = analyze([], text)
        assert result["structure_template"] == "unknown"

    def test_empty_transcript_raises(self):
        """空 transcript 抛出 ValueError"""
        with pytest.raises(ValueError, match="不能为空"):
            analyze([], "")


# ══════════════════════════════════════════════════════════════
# Original Script Generator — 拼装 + mock 字段
# ══════════════════════════════════════════════════════════════

class TestOriginalScriptGenerator:
    """原创脚本生成器"""

    def test_generate_returns_all_fields(self):
        structure = {
            "hook": {"text": "你知道吗？"},
            "body_segments": [
                {"text": "第一点：坚持运动"},
                {"text": "第二点：合理饮食"},
            ],
            "cta": {"text": "关注我"},
            "structure_template": "listicle",
        }
        result = generate(structure, "职场新人", "教育行业", "原文转写文本")
        assert "script_text" in result
        assert "hook" in result
        assert "body" in result
        assert "cta" in result
        assert result["mock"] is True
        assert "audience:职场新人" in result["novelty_markers"]
        assert "industry:教育行业" in result["novelty_markers"]

    def test_similarity_estimate_is_bounded(self):
        structure = {"hook": {"text": "短"}, "body_segments": [], "cta": {"text": ""}, "structure_template": "unknown"}
        result = generate(structure, "a", "b", "x" * 1000)
        assert 0.0 <= result["similarity_estimate"] <= 1.0

    def test_empty_structure_raises(self):
        with pytest.raises(ValueError, match="structure 不能为空"):
            generate({}, "受众", "行业", "原文")

    def test_empty_audience_raises(self):
        with pytest.raises(ValueError, match="target_audience 不能为空"):
            generate({"hook": {}, "body_segments": [], "cta": {}}, "", "行业", "原文")


# ══════════════════════════════════════════════════════════════
# Similarity QC — 三档阈值
# ══════════════════════════════════════════════════════════════

class TestSimilarityQCThresholds:
    """相似性审查阈值"""

    def test_low_similarity_pass(self):
        """< 0.30 → pass"""
        original = "今天给大家分享如何快速提升写作能力，首先要大量阅读，其次要坚持练习，最后要学会修改。"
        derivative = "提升写作水平的三个关键：第一，多读优秀作品；第二，持续写作训练；第三，仔细修改打磨。三步帮你从小白变高手。"
        result = review(original, derivative, {})
        assert result["verdict"] == "pass"
        assert result["similarity_score"] < 0.30

    def test_medium_similarity_revise(self):
        """0.30–0.60 → revise"""
        # 一半相同，一半完全不同 → 约 50% 相似度
        original = "很多人每天都很忙碌，但不知道如何管理时间。时间管理的核心是分清主次，把最重要的事情放在第一位。"
        derivative = "很多人每天都很忙碌，但不知道如何管理时间。睡眠质量差会影响第二天的工作效率，这是很多人忽视的问题。"
        result = review(original, derivative, {})
        assert 0.30 <= result["similarity_score"] <= 0.75
        assert result["verdict"] in ("revise", "pass")

    def test_high_similarity_reject(self):
        """> 0.60 → reject"""
        original = "今天分享五个让工作效率翻倍的方法，第一是制定计划，第二是集中注意力，第三是及时休息，第四是定期复盘，第五是保持健康。"
        derivative = original  # 完全相同
        result = review(original, derivative, {})
        assert result["verdict"] == "reject"
        assert result["similarity_score"] >= 0.60

    def test_identical_text_score_close_to_one(self):
        """完全相同文本 score 接近 1.0"""
        text = "这是一段完全相同的测试文本内容，用于验证算法正确性。"
        result = review(text, text, {})
        assert result["similarity_score"] >= 0.95
        assert result["verdict"] == "reject"


# ══════════════════════════════════════════════════════════════
# Similarity QC — 严格性验证
# ══════════════════════════════════════════════════════════════

class TestSimilarityQCStrictness:
    """严禁把高相似度说成低相似度"""

    def test_near_identical_is_not_low_similarity(self):
        """近义改写 ≠ 低相似度"""
        text = "学会时间管理让你的效率提升三倍"
        derivative = "学会时间管理让你的效率提升三倍，掌握核心方法让效率翻倍"
        result = review(text, derivative, {})
        assert result["similarity_score"] >= 0.50, "近义改写不應被评為低相似度"

    def test_verbatim_passage_flagged(self):
        """逐字引用必须被标记"""
        original = "首先打开设置页面，然后点击常规选项，最后找到关于本机"
        derivative = original + "，查看版本信息"  # 前半段逐字保留
        result = review(original, derivative, {})
        assert len(result["flagged_phrases"]) >= 1

    def test_empty_original_raises(self):
        with pytest.raises(ValueError, match="original 和 derivative 都不能为空"):
            review("", "something", {})

    def test_empty_derivative_raises(self):
        with pytest.raises(ValueError, match="original 和 derivative 都不能为空"):
            review("original", "", {})


# ══════════════════════════════════════════════════════════════
# Director — 串接测试
# ══════════════════════════════════════════════════════════════

class TestDirectorPipeline:
    """主编排器串接"""

    def test_direct_with_transcript(self):
        """有转写 → 完整 pipeline"""
        transcript = (
            "你有没有遇到过这样的问题？"
            "每天忙得团团转，却感觉没什么成效。"
            "今天教你三个时间管理的核心技巧，"
            "第一是分清主次，第二是批量处理，第三是定期复盘。"
            "学会了记得点赞关注哦。"
        )
        result = direct("提升工作效率", "职场人", "职业教育", source_transcript=transcript)
        assert result["mode"] == "rewrite"
        assert result["mock"] is True
        assert "script_text" in result
        assert "qc_result" in result

    def test_direct_without_transcript(self):
        """无转写 → 纯原创 stub"""
        result = direct("分享一个职场技巧", "职场新人", "教育行业")
        assert result["mode"] == "original"
        assert result["qc_result"]["verdict"] == "pass"
        assert result["qc_result"]["similarity_score"] == 0.0

    def test_direct_empty_goal_raises(self):
        with pytest.raises(ValueError, match="goal 不能为空"):
            direct("", "受众", "行业")

    def test_direct_empty_audience_raises(self):
        with pytest.raises(ValueError, match="audience 不能为空"):
            direct("目标", "", "行业")


# ══════════════════════════════════════════════════════════════
# 边界条件
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """边界测试"""

    def test_ultra_long_transcript(self):
        """10k 字符超长转写不崩溃"""
        long_text = "这是测试内容。" * 1000  # ~10k chars
        result = analyze([], long_text)
        assert result["mock"] is True
        assert result["duration_sec"] > 0

    def test_ultra_long_derivative(self):
        """超长脚本审查"""
        original = "短原文"
        derivative = "生成的原创内容。" * 2000
        result = review(original, derivative, {})
        assert 0.0 <= result["similarity_score"] <= 1.0

    def test_whitespace_only(self):
        """纯空白文本 → 抛出异常"""
        with pytest.raises(ValueError):
            analyze([], "   ")
