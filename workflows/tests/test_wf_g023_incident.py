"""Tests for WF-G-023 故障快速人工降级 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g023_incident import (
    run_incident, IncidentInput, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_p0_with_kill_switch_succeeds():
    inp = IncidentInput(
        tenant_id="zq-1",
        incident_id="INC-001",
        severity="P0",
        degraded_mode="kill_switch",
        affected_workflows=["WF-T-001", "WF-T-007"],
    )
    out = run_incident(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["status"] == "offline"
    assert o["affected_count"] == 2
    assert "tech_lead" in o["notify_list"]
    assert "product_owner" in o["notify_list"]


def test_p0_must_use_hard_mode():
    """P0 不允许 auto_only, 必须切到 half_manual 或 kill_switch"""
    inp = IncidentInput(
        tenant_id="zq-1",
        incident_id="INC-002",
        severity="P0",
        degraded_mode="auto_only",
    )
    out = run_incident(inp)
    assert out["status"] == "failed"
    assert "WF-G023-P0" in out["error"]["code"]


def test_p3_uses_light_notify():
    inp = IncidentInput(
        tenant_id="zq-1",
        incident_id="INC-003",
        severity="P3",
        degraded_mode="auto_only",
    )
    out = run_incident(inp)
    o = out["output"]
    assert o["notify_list"] == ["oncall"]
    # eta_min = 1440 (P3), post-mortem 草稿在 action_plan 中
    actions = [a["action"] for a in o["action_plan"]]
    assert any("post-mortem" in a for a in actions)


def test_invalid_severity_rejected():
    with pytest.raises(ValidationError):
        IncidentInput(tenant_id="zq-1", incident_id="x", severity="P9")


def test_invalid_degraded_mode_rejected():
    with pytest.raises(ValidationError):
        IncidentInput(
            tenant_id="zq-1", incident_id="x", severity="P1", degraded_mode="random_mode",
        )


def test_p1_with_half_manual_succeeds():
    inp = IncidentInput(
        tenant_id="zq-1",
        incident_id="INC-004",
        severity="P1",
        degraded_mode="half_manual",
        affected_workflows=["WF-T-007"],
    )
    out = run_incident(inp)
    o = out["output"]
    assert o["status"] == "degraded"
    assert o["affected_count"] == 1


def test_degraded_until_is_iso():
    inp = IncidentInput(
        tenant_id="zq-1",
        incident_id="INC-005",
        severity="P2",
        degraded_mode="half_manual",
    )
    out = run_incident(inp)
    ts = out["output"]["degraded_until"]
    # 粗校验: 是 ISO 格式
    assert "T" in ts
    assert len(ts) >= 19


def test_action_plan_eta_increases_with_severity():
    """P1 (eta=60) < P3 (eta=1440) — 高严重度 ETA 短"""
    inp_low = IncidentInput(tenant_id="zq-1", incident_id="L", severity="P1", degraded_mode="half_manual")
    inp_high = IncidentInput(tenant_id="zq-1", incident_id="H", severity="P3", degraded_mode="auto_only")
    out_low = run_incident(inp_low)
    out_high = run_incident(inp_high)
    # P1 eta_min=60 (notify step), P3 eta_min=1440
    low_eta = max(a["eta_min"] for a in out_low["output"]["action_plan"])
    high_eta = max(a["eta_min"] for a in out_high["output"]["action_plan"])
    assert low_eta < high_eta


def test_validate_json_ok():
    res = validate_json('{"tenant_id":"zq-1","incident_id":"INC-1","severity":"P1"}')
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1","incident_id":"INC-1","severity":"P9"}')
    assert res["ok"] is False


def test_tracker_records_run():
    inp = IncidentInput(
        tenant_id="zq-tr",
        incident_id="INC-X",
        severity="P1",
        degraded_mode="half_manual",
    )
    out = run_incident(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-G-023", tenant_id="zq-tr")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"