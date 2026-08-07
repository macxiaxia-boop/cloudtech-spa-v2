"""Auto Pipeline Tests — Stage Transitions, Error Recovery, Status Reporting"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════
# Pipeline Configuration
# ═══════════════════════════════════

class TestPipelineConfig:
    """流水线配置验证"""

    def test_pipeline_stages_exist(self):
        from auto_pipeline import PIPELINE_STAGES
        assert len(PIPELINE_STAGES) == 5
        stage_ids = {s["id"] for s in PIPELINE_STAGES}
        expected = {
            "stage_1_knowledge",
            "stage_2_content",
            "stage_3_video",
            "stage_4_publish",
            "stage_5_analytics",
        }
        assert stage_ids == expected

    def test_pipeline_stages_have_handlers(self):
        from auto_pipeline import PIPELINE_STAGES
        for stage in PIPELINE_STAGES:
            assert "handler" in stage, f"Stage {stage['id']} missing handler"
            assert "name" in stage
            assert "description" in stage

    def test_pipeline_stage_order(self):
        from auto_pipeline import PIPELINE_STAGES
        expected_order = [
            "stage_1_knowledge",
            "stage_2_content",
            "stage_3_video",
            "stage_4_publish",
            "stage_5_analytics",
        ]
        actual = [s["id"] for s in PIPELINE_STAGES]
        assert actual == expected_order


# ═══════════════════════════════════
# Pipeline Execution (Dry Run — No API Calls)
# ═══════════════════════════════════

# Skip content generation which makes real DeepSeek API calls
SAFE_STAGES = ["stage_1_knowledge", "stage_5_analytics"]


class TestPipelineDryRun:
    """流水线模拟执行（不调API）"""

    def test_pipeline_knowledge_stage(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({
            "topic": "现代简约装修",
            "city": "厦门",
            "area": 120,
            "budget": 20,
            "style": "现代简约",
            "community": "万科金域蓝湾",
        }, stages=["stage_1_knowledge"])
        assert result["dry_run"] is True
        assert result["total_stages"] == 1
        assert result["pipeline_id"].startswith("pipe-")
        assert "started_at" in result
        assert "finished_at" in result

    def test_pipeline_report_structure(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({
            "topic": "测试", "city": "漳州",
            "area": 100, "budget": 15,
        }, stages=["stage_1_knowledge"])
        for key in ["pipeline_id", "ok", "total_stages", "success_stages",
                     "failed_stages", "stages", "output", "summary"]:
            assert key in result, f"Missing report field: {key}"
        assert isinstance(result["stages"], list)
        assert isinstance(result["summary"], str)

    def test_pipeline_timing(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({"topic": "测试", "city": "漳州", "area": 100, "budget": 15},
                              stages=["stage_1_knowledge"])
        for stage_result in result["stages"]:
            assert "elapsed" in stage_result
            assert stage_result["elapsed"] >= 0
            assert "stage_name" in stage_result

    def test_pipeline_selective_stages(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run(
            {"topic": "测试", "city": "漳州", "area": 100, "budget": 15},
            stages=["stage_1_knowledge", "stage_5_analytics"],
        )
        assert result["total_stages"] == 2

    def test_pipeline_log_saved(self):
        from auto_pipeline import AutoPipeline, PIPELINE_LOG
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({"topic": "测试", "city": "漳州", "area": 100, "budget": 15},
                              stages=["stage_1_knowledge"])
        log_file = PIPELINE_LOG / f"{result['pipeline_id']}.json"
        assert log_file.exists()
        log_data = json.loads(log_file.read_text(encoding="utf-8"))
        assert log_data["pipeline_id"] == result["pipeline_id"]

    def test_pipeline_knowledge_with_community(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({
            "topic": "测试", "city": "漳州",
            "area": 100, "budget": 15,
            "community": "万科",
        }, stages=["stage_1_knowledge"])
        stage = result["stages"][0]
        if stage.get("ok"):
            assert "has_community_data" in stage


# ═══════════════════════════════════
# Pipeline Status & Reporting
# ═══════════════════════════════════

class TestPipelineStatus:
    """流水线状态报告"""

    def test_pipeline_id_format(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline()
        assert pipeline.pipeline_id.startswith("pipe-")
        assert pipeline.pipeline_id[5:].isdigit()

    def test_pipeline_state_init(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline()
        assert pipeline.state == {}
        assert pipeline.results == []
        assert pipeline.dry_run is True

    def test_list_pipeline_history(self):
        from auto_pipeline import list_pipeline_history
        history = list_pipeline_history(limit=5)
        assert isinstance(history, list)

    def test_generate_summary_content(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        pipeline.run({"topic": "测试汇总", "city": "泉州", "area": 120, "budget": 18},
                     stages=["stage_1_knowledge"])
        summary = pipeline._generate_summary()
        assert "测试汇总" in summary or "自动化流水线" in summary

    def test_pipeline_summary_includes_stage_results(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({"topic": "测试", "city": "漳州", "area": 100, "budget": 15},
                              stages=["stage_1_knowledge"])
        summary = result["summary"]
        assert "✅" in summary or "❌" in summary or "产出" in summary


# ═══════════════════════════════════
# Quick Functions
# ═══════════════════════════════════

class TestPipelineQuickFunctions:
    """快捷函数"""

    def test_one_click_produce_knowledge_only(self):
        """Test only knowledge stage to avoid API calls"""
        from auto_pipeline import AutoPipeline
        result = AutoPipeline(dry_run=True).run(
            {"topic": "奶油风装修", "city": "漳州", "area": 100, "budget": 15,
             "style": "奶油风"},
            stages=["stage_1_knowledge"]
        )
        assert result["total_stages"] == 1

    def test_quick_video_publish_skip_stages(self):
        from auto_pipeline import AutoPipeline
        # Run with only safe stages
        result = AutoPipeline(dry_run=True).run(
            {"topic": "测试视频", "city": "厦门", "area": 100, "budget": 15},
            stages=["stage_1_knowledge", "stage_5_analytics"]
        )
        assert result["dry_run"] is True
        assert result["total_stages"] == 2

    def test_pipeline_with_community(self):
        from auto_pipeline import AutoPipeline
        result = AutoPipeline(dry_run=True).run({
            "topic": "测试", "city": "漳州", "area": 100, "budget": 15,
            "community": "海沧万科城",
        }, stages=["stage_1_knowledge"])
        assert result["input"]["community"] == "海沧万科城"


# ═══════════════════════════════════
# Edge Cases
# ═══════════════════════════════════

class TestPipelineEdgeCases:
    """边界条件"""

    def test_empty_topic(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({"topic": "", "city": "漳州", "area": 0, "budget": 0},
                              stages=["stage_1_knowledge"])
        assert result["total_stages"] == 1

    def test_very_large_area(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({"topic": "测试", "city": "漳州", "area": 9999, "budget": 999},
                              stages=["stage_1_knowledge"])
        assert result["total_stages"] >= 1

    def test_empty_platforms(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({
            "topic": "测试", "city": "漳州",
            "area": 100, "budget": 15,
            "platforms": [],
        }, stages=["stage_1_knowledge"])
        assert result["total_stages"] >= 1

    def test_special_characters_in_topic(self):
        from auto_pipeline import AutoPipeline
        pipeline = AutoPipeline(dry_run=True)
        result = pipeline.run({
            "topic": "测试!@#$%^&*()",
            "city": "漳州", "area": 100, "budget": 15,
        }, stages=["stage_1_knowledge"])
        assert result["total_stages"] == 1
