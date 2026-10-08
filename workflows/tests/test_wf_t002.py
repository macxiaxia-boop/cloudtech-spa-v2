"""Tests for WF-T-002 本地客群与选题池 (≥5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t002_local_topics import run_local_topics, LocalTopicInput, validate_json


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_happy_path():
    inp = LocalTopicInput(
        tenant_id="zq-1", cities=["厦门", "泉州"], count=8,
        platforms=["xiaohongshu", "douyin"],
    )
    out = run_local_topics(inp)
    assert out["status"] == "success"
    assert out["output"]["total"] == 8
    assert "厦门" in out["output"]["cities_covered"]
    assert len(out["output"]["topics"]) == 8


def test_deterministic_score():
    inp = LocalTopicInput(tenant_id="zq-1", cities=["厦门"], count=3, platforms=["douyin"])
    out1 = run_local_topics(inp)
    inp2 = LocalTopicInput(tenant_id="zq-1", cities=["厦门"], count=3, platforms=["douyin"])
    out2 = run_local_topics(inp2)
    # 同样输入两次的 hotness_score 应一致 (deterministic)
    s1 = [t["hotness_score"] for t in out1["output"]["topics"]]
    s2 = [t["hotness_score"] for t in out2["output"]["topics"]]
    assert s1 == s2


def test_bad_platform():
    inp = LocalTopicInput(
        tenant_id="zq-bad", cities=["厦门"], platforms=["weibo"],
    )
    out = run_local_topics(inp)
    assert out["status"] == "failed"
    assert "WF-T002-PLAT" in out["error"]["code"]


def test_empty_cities():
    inp = LocalTopicInput(
        tenant_id="zq-empty", cities=[], platforms=["xiaohongshu"],
    )
    out = run_local_topics(inp)
    assert out["status"] == "failed"


def test_validate_json():
    res = validate_json('{"tenant_id":"zq-1","cities":["厦门"]}')
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1"}')  # missing cities
    assert res["ok"] is False


def test_max_count():
    inp = LocalTopicInput(tenant_id="zq-1", cities=["厦门"], count=51)
    with pytest.raises(Exception):
        inp.model_validate(inp.model_dump())  # pydantic 拒绝 >50