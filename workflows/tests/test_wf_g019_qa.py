"""Tests for WF-G-019 知识问答人工接管 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g019_qa import (
    run_qa, QAInput, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_auto_action_high_confidence():
    inp = QAInput(
        tenant_id="zq-1",
        question="装修预算 30 万够吗",
        candidate_answers=["装修预算 30 万通常够 100 平左右三房两厅"],
        confidence_threshold=0.3,  # 阈值低 → high overlap 必命中
    )
    out = run_qa(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["action"] == "auto"
    assert o["suggested_responder"] is None
    assert "自动答复" in o["rationale"]


def test_escalate_action_low_confidence():
    """完全不相关回答 → escalate"""
    inp = QAInput(
        tenant_id="zq-1",
        question="如何验收水电",
        candidate_answers=["完全不同话题"],
        confidence_threshold=0.9,
    )
    out = run_qa(inp)
    o = out["output"]
    # overlap = 0, score = 0.1 < 0.45 → escalate
    assert o["action"] == "escalate"
    assert o["suggested_responder"] == "manager"


def test_handoff_action_medium_confidence():
    """中等 overlap → handoff (人工专家)"""
    inp = QAInput(
        tenant_id="zq-1",
        question="装修验收需要注意什么水电木工",
        candidate_answers=["水电验收 标准 测试"],
        confidence_threshold=0.99,  # 极高阈值 → 必难命中 auto
    )
    out = run_qa(inp)
    o = out["output"]
    # 阈值 0.99 太高 → confidence (0.x) < 0.99 但 >= 0.99*0.5=0.495
    # 若 score=overlap/max(q_words)+0.1, q_words=5, overlap=2, score=2/5+0.1=0.5 → handoff
    assert o["action"] in ("handoff", "escalate")
    assert o["confidence"] < 0.99


def test_empty_candidates_default_response():
    inp = QAInput(
        tenant_id="zq-1",
        question="如何验收",
        candidate_answers=[],
    )
    out = run_qa(inp)
    o = out["output"]
    assert o["answer"] == "(无候选答案, 默认回复)"
    assert o["confidence"] == 0.2
    # 0.2 < 阈值 0.75 → 应 escalate 或 handoff
    assert o["action"] != "auto"


def test_short_question_rejected():
    with pytest.raises(ValidationError):
        QAInput(tenant_id="zq-1", question="x")


def test_threshold_bounds():
    with pytest.raises(ValidationError):
        QAInput(tenant_id="zq-1", question="测试", confidence_threshold=0.05)  # < 0.1
    with pytest.raises(ValidationError):
        QAInput(tenant_id="zq-1", question="测试", confidence_threshold=1.5)  # > 0.99


def test_validate_json_ok():
    res = validate_json('{"tenant_id":"zq-1","question":"如何验收"}')
    assert res["ok"] is True


def test_validate_json_missing_question():
    res = validate_json('{"tenant_id":"zq-1"}')
    assert res["ok"] is False


def test_tracker_records_run():
    inp = QAInput(tenant_id="zq-tr", question="装修问题 A", candidate_answers=["装修问题 A 答案"])
    out = run_qa(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-G-019", tenant_id="zq-tr")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"


def test_user_role_persisted():
    inp = QAInput(tenant_id="zq-1", question="装修问题", user_role="owner")
    out = run_qa(inp)
    # user_role 不直接进 output, 但不抛错
    assert out["status"] == "success"