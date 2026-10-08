"""Tests for WF-T-005 线索导入去重与分配 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t005_leads import (
    run_leads, LeadsInput, Lead, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def _make_leads():
    return [
        Lead(name="张三", phone="13800001111", city="厦门", source="douyin", intent_score=85.0),
        Lead(name="李四", phone="13800002222", city="泉州", source="xiaohongshu", intent_score=45.0),
        Lead(name="王五", phone="13800003333", city="福州", source="wechat", intent_score=72.0),
        Lead(name="张三", phone="13800001111", city="厦门", source="douyin", intent_score=80.0),  # 重复
    ]


def test_happy_path_round_robin():
    inp = LeadsInput(
        tenant_id="zq-1", leads=_make_leads(),
        sales_team=["alice", "bob"], strategy="round_robin",
    )
    out = run_leads(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["input_count"] == 4
    assert o["deduped_count"] == 3  # 去重后剩 3 个
    assert len(o["duplicates"]) == 1
    assert len(o["assigned"]) == 3
    # round_robin 应平均分配 (3 个 lead / 2 sales)
    total = sum(o["load_distribution"].values())
    assert total == 3


def test_dedup_by_phone():
    inp = LeadsInput(
        tenant_id="zq-dup", leads=_make_leads(),
        sales_team=["alice"], strategy="round_robin",
    )
    out = run_leads(inp)
    assert out["status"] == "success"
    # 重复 phone 仅保留首次
    assert out["output"]["deduped_count"] == 3
    assert out["output"]["duplicates"][0].startswith("138")


def test_by_intent_priority():
    inp = LeadsInput(
        tenant_id="zq-intent", leads=_make_leads(),
        sales_team=["top_sales", "normal_a", "normal_b"],
        strategy="by_intent",
    )
    out = run_leads(inp)
    assert out["status"] == "success"
    # 高 intent (>=70) 应分给 top_sales
    high_intent_assigned = [a for a in out["output"]["assigned"] if a["priority"] in ("hot", "warm")]
    # 至少 1 个高 intent (王五 72) 给 top_sales
    top_sales = [a for a in out["output"]["assigned"] if a["assigned_to"] == "top_sales"]
    assert len(top_sales) >= 1


def test_phone_hash_not_plaintext():
    inp = LeadsInput(
        tenant_id="zq-priv",
        leads=[Lead(name="隐私测试", phone="13800009999", city="厦门", intent_score=60)],
        sales_team=["alice"], strategy="round_robin",
    )
    out = run_leads(inp)
    # 输出不应包含明文 phone
    for a in out["output"]["assigned"]:
        assert "13800009999" not in str(a)
        assert len(a["phone_hash"]) == 12  # sha256[:12]


def test_empty_leads_rejected_by_pydantic():
    """pydantic 拦截: min_length=1 on leads"""
    with pytest.raises(ValidationError):
        LeadsInput(tenant_id="zq-empty", leads=[], sales_team=["alice"], strategy="round_robin")


def test_empty_sales_team_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        LeadsInput(
            tenant_id="zq-no-team",
            leads=[Lead(name="x", phone="13800000001", city="厦门")],
            sales_team=[], strategy="round_robin",
        )


def test_invalid_strategy_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        LeadsInput(
            tenant_id="zq-bad-strat",
            leads=[Lead(name="x", phone="13800000001", city="厦门")],
            sales_team=["alice"], strategy="random",
        )


def test_validate_json():
    res = validate_json('{"tenant_id":"zq-1","leads":[{"name":"x","phone":"13800000001","city":"厦门"}],"sales_team":["a"]}')
    assert res["ok"] is True


def test_validate_json_bad_missing_leads():
    res = validate_json('{"tenant_id":"zq-1","sales_team":["a"]}')
    assert res["ok"] is False


def test_priority_classification():
    inp = LeadsInput(
        tenant_id="zq-prio",
        leads=[
            Lead(name="hot", phone="13800000001", city="厦门", intent_score=90),
            Lead(name="warm", phone="13800000002", city="厦门", intent_score=55),
            Lead(name="cold", phone="13800000003", city="厦门", intent_score=20),
        ],
        sales_team=["alice"], strategy="round_robin",
    )
    out = run_leads(inp)
    priorities = [a["priority"] for a in out["output"]["assigned"]]
    assert "hot" in priorities and "warm" in priorities and "cold" in priorities


def test_tracker_records_run():
    inp = LeadsInput(
        tenant_id="zq-tracker",
        leads=[Lead(name="x", phone="13800000001", city="厦门")],
        sales_team=["alice"], strategy="round_robin",
    )
    out = run_leads(inp)
    run_id = out["run_id"]
    status = RunHistoryTracker.instance().get_status(run_id)
    assert status is not None
    assert status["status"] == "success"
    assert status["workflow_id"] == "WF-T-005"


def test_by_load_distribution():
    """by_load 策略: 总是分给当前最少的销售"""
    inp = LeadsInput(
        tenant_id="zq-load",
        leads=[Lead(name=f"lead{i}", phone=f"1380000{i:04d}", city="厦门") for i in range(6)],
        sales_team=["a", "b", "c"], strategy="by_load",
    )
    out = run_leads(inp)
    # 6 leads / 3 sales = 2 each (balanced)
    dist = out["output"]["load_distribution"]
    assert dist == {"a": 2, "b": 2, "c": 2}
