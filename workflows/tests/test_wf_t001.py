"""Tests for WF-T-001 企业营销业务诊断 (≥5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t001_diagnosis import (
    run_diagnosis, DiagnosisInput, validate_json, validate_yaml,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_happy_path():
    inp = DiagnosisInput(
        tenant_id="zq-test-1", industry="decoration",
        target_revenue=1000000, current_revenue=300000, sample_size=50,
    )
    out = run_diagnosis(inp)
    assert out["status"] == "success"
    assert out["output"]["diagnosis_score"] >= 0
    assert out["output"]["diagnosis_score"] <= 100
    assert len(out["output"]["gaps"]) == 4
    assert out["output"]["revenue_gap_pct"] == 70.0
    assert out["output"]["funnel_health"] in ("poor", "fair", "good", "excellent")


def test_excellent_score_when_at_target():
    inp = DiagnosisInput(
        tenant_id="zq-good", industry="decoration",
        target_revenue=1000, current_revenue=1000, sample_size=100,
    )
    out = run_diagnosis(inp)
    assert out["status"] == "success"
    assert out["output"]["funnel_health"] == "excellent"


def test_validate_json_ok():
    res = validate_json('{"tenant_id":"zq-1","industry":"decoration","target_revenue":100.0}')
    assert res["ok"] is True


def test_validate_json_bad_industry():
    res = validate_json('{"tenant_id":"zq-1","industry":"space","target_revenue":100.0}')
    assert res["ok"] is False


def test_validate_yaml():
    res = validate_yaml("tenant_id: zq-1\nindustry: decoration\ntarget_revenue: 500.0\n")
    assert res["ok"] is True


def test_tracker_records_run():
    inp = DiagnosisInput(tenant_id="zq-tracker", industry="medical", target_revenue=50000)
    out = run_diagnosis(inp)
    run_id = out["run_id"]
    status = RunHistoryTracker.instance().get_status(run_id)
    assert status is not None
    assert status["status"] == "success"
    assert status["workflow_id"] == "WF-T-001"
    assert status["tenant_id"] == "zq-tracker"