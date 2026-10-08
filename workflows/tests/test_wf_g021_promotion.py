"""Tests for WF-G-021 SOP 候选受控晋升 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g021_promotion import (
    run_promotion, PromotionInput, SOPCandidate, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_high_confidence_promoted_with_evidence():
    inp = PromotionInput(
        tenant_id="zq-1",
        candidates=[
            SOPCandidate(sid="s1", title="小红书爆款脚本模板", source="exp-1",
                         confidence="high", evidence_count=5),
        ],
        promotion_threshold="high",
    )
    out = run_promotion(inp)
    o = out["output"]
    assert o["promoted"] == ["s1"]
    assert o["on_hold"] == []
    assert o["rejected"] == []


def test_high_confidence_low_evidence_on_hold():
    inp = PromotionInput(
        tenant_id="zq-1",
        candidates=[
            SOPCandidate(sid="s1", title="标题模板", source="exp-1",
                         confidence="high", evidence_count=2),
        ],
    )
    out = run_promotion(inp)
    o = out["output"]
    assert o["on_hold"] == ["s1"]
    assert o["promoted"] == []


def test_low_confidence_rejected():
    inp = PromotionInput(
        tenant_id="zq-1",
        candidates=[
            SOPCandidate(sid="s1", title="未验证假设", source="obs-1",
                         confidence="low", evidence_count=10),
        ],
    )
    out = run_promotion(inp)
    o = out["output"]
    assert o["rejected"] == ["未验证假设"]
    assert o["promoted"] == []


def test_medium_threshold_promotes_medium():
    inp = PromotionInput(
        tenant_id="zq-1",
        candidates=[
            SOPCandidate(sid="s1", title="中等置信", source="exp-1",
                         confidence="medium", evidence_count=3),
        ],
        promotion_threshold="medium",
    )
    out = run_promotion(inp)
    assert "s1" in out["output"]["promoted"]


def test_invalid_confidence_rejected():
    with pytest.raises(ValidationError):
        SOPCandidate(sid="s1", title="测试", source="x", confidence="very_high")


def test_short_title_rejected():
    with pytest.raises(ValidationError):
        SOPCandidate(sid="s1", title="x", source="x", confidence="high")


def test_empty_candidates_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        PromotionInput(tenant_id="zq-1", candidates=[])


def test_audit_includes_all_decisions():
    inp = PromotionInput(
        tenant_id="zq-1",
        candidates=[
            SOPCandidate(sid="s1", title="高置信足证据", source="e1", confidence="high", evidence_count=5),
            SOPCandidate(sid="s2", title="高置信低证据", source="e2", confidence="high", evidence_count=1),
            SOPCandidate(sid="s3", title="低置信", source="e3", confidence="low", evidence_count=5),
        ],
    )
    out = run_promotion(inp)
    audit = out["output"]["audit"]
    assert len(audit) == 3
    decisions = {a["sid"]: a["decision"] for a in audit}
    assert decisions == {"s1": "promoted", "s2": "on_hold", "s3": "rejected"}


def test_validate_json_ok():
    res = validate_json(
        '{"tenant_id":"zq-1","candidates":[{"sid":"s1","title":"测试标题","source":"e1","confidence":"high","evidence_count":5}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1"}')  # 缺 candidates
    assert res["ok"] is False


def test_tracker_records_run():
    inp = PromotionInput(
        tenant_id="zq-tr",
        candidates=[SOPCandidate(sid="s1", title="测试候选", source="e1", confidence="high", evidence_count=3)],
    )
    out = run_promotion(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-G-021", tenant_id="zq-tr")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"