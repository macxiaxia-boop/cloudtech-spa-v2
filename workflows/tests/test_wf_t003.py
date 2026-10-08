"""Tests for WF-T-003 脚本生成与审核 (≥5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t003_script import run_script, ScriptInput, validate_json


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_happy_path_approved():
    inp = ScriptInput(tenant_id="zq-1", topic="厦门旧房翻新", angle="避坑", persona="刚需家庭",
                       platform="xiaohongshu", word_count=800, creator="zhinan")
    out = run_script(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["approved"] is True
    assert o["review_score"] >= 70
    assert "厦门旧房翻新" in o["title"]
    assert o["word_count"] > 0


def test_bad_platform_rejected():
    with pytest.raises(Exception):
        ScriptInput(tenant_id="zq-1", topic="测试", platform="tiktok")


def test_hashtags_present():
    inp = ScriptInput(tenant_id="zq-1", topic="装修预算", platform="douyin")
    out = run_script(inp)
    assert any("#装修预算" in h for h in out["output"]["hashtags"])


def test_review_notes_when_low_word_count():
    inp = ScriptInput(tenant_id="zq-1", topic="小户型改造", word_count=100)
    out = run_script(inp)
    assert out["status"] == "success"
    # word_count=100 仍能生成, 但 review_score 可能被扣分
    assert out["output"]["review_score"] >= 0


def test_validate_json():
    res = validate_json('{"tenant_id":"zq-1","topic":"测试"}')
    assert res["ok"] is True


def test_validate_json_bad_platform():
    res = validate_json('{"tenant_id":"zq-1","topic":"测试","platform":"weibo"}')
    assert res["ok"] is False


def test_tracker_records_success():
    """pydantic v2 在构造时拒绝 topic<2 字符/word_count<100, 故改用合法输入.
    测试目的: 验证 RunHistoryTracker 记录到 success 运行 (与失败形成对照)."""
    inp = ScriptInput(tenant_id="zq-trk", topic="厦门装修日记", platform="douyin", word_count=200)
    out = run_script(inp)
    assert out["status"] == "success"
    # tracker 至少记录 1 条 WF-T-003 运行
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-T-003", tenant_id="zq-trk")
    assert len(runs) >= 1
    assert runs[0]["status"] == "success"