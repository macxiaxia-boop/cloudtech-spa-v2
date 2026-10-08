"""Tests for WF-G-017 长流程与人工批准 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g017_long_flow import (
    run_long_flow, LongFlowInput, Step, Checkpoint, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_all_done_100_pct():
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[
            Step(name="s1", status="done"),
            Step(name="s2", status="done"),
            Step(name="s3", status="done"),
        ],
        checkpoints=[],
    )
    out = run_long_flow(inp)
    o = out["output"]
    assert o["total_steps"] == 3
    assert o["done_steps"] == 3
    assert o["progress_pct"] == 100.0
    assert o["awaiting_approval"] == []


def test_partial_progress():
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[
            Step(name="s1", status="done"),
            Step(name="s2", status="running"),
            Step(name="s3", status="pending"),
        ],
        checkpoints=[],
    )
    out = run_long_flow(inp)
    o = out["output"]
    assert o["done_steps"] == 1
    assert o["progress_pct"] == pytest.approx(33.3, abs=0.1)


def test_approved_checkpoint():
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[Step(name="s1", status="waiting_approval")],
        checkpoints=[Checkpoint(step="s1", needs_approval=True, approved=True, note="OK")],
    )
    out = run_long_flow(inp)
    o = out["output"]
    assert o["approval_summary"]["approved"] == 1
    assert o["approval_summary"]["pending"] == 0
    assert o["awaiting_approval"] == []


def test_pending_approval_counted():
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[Step(name="s1", status="waiting_approval")],
        checkpoints=[Checkpoint(step="s1", needs_approval=True, approved=None)],
    )
    out = run_long_flow(inp)
    o = out["output"]
    assert o["approval_summary"]["pending"] == 1
    assert "s1" in o["awaiting_approval"][0]


def test_rejected_checkpoint_in_awaiting():
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[Step(name="s1", status="blocked")],
        checkpoints=[Checkpoint(step="s1", needs_approval=True, approved=False, note="数据不全")],
    )
    out = run_long_flow(inp)
    o = out["output"]
    assert o["approval_summary"]["rejected"] == 1
    assert "s1" in o["awaiting_approval"][0]
    assert "数据不全" in o["awaiting_approval"][0]
    # next_actions 包含 "复盘 1 个被驳回 checkpoint"
    assert any("复盘" in a for a in o["next_actions"])


def test_no_approval_needed_skipped():
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[Step(name="s1", status="done")],
        checkpoints=[Checkpoint(step="s1", needs_approval=False)],
    )
    out = run_long_flow(inp)
    o = out["output"]
    assert o["approval_summary"]["approved"] == 0
    assert o["approval_summary"]["pending"] == 0


def test_orphan_checkpoint_fails():
    """checkpoint 引用未注册的 step → 失败 (pydantic v2 修: 唯一错误码是 ORPHAN)"""
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[Step(name="s1", status="done")],
        checkpoints=[Checkpoint(step="unknown_step", needs_approval=True)],
    )
    out = run_long_flow(inp)
    assert out["status"] == "failed"
    # WF-G017-ORPHAN 唯一错误码 (steps 非空, 不会触发 WF-G017-STEPS)
    assert "WF-G017-ORPHAN" in out["error"]["code"]


def test_blocked_step_in_next_actions():
    inp = LongFlowInput(
        tenant_id="zq-1",
        steps=[Step(name="s1", status="done"), Step(name="s2", status="blocked", approver="manager")],
        checkpoints=[],
    )
    out = run_long_flow(inp)
    actions = out["output"]["next_actions"]
    assert any("s2" in a and "blocked" in a for a in actions)


def test_validate_json_ok():
    res = validate_json('{"tenant_id":"zq-1","steps":[{"name":"s1","status":"done"}],"checkpoints":[]}')
    assert res["ok"] is True


def test_empty_steps_rejected_pydantic():
    """min_length=1 → pydantic 直接拒"""
    with pytest.raises(ValidationError):
        LongFlowInput(tenant_id="zq-1", steps=[], checkpoints=[])