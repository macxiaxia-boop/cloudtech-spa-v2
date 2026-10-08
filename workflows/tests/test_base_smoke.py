"""Smoke test: 验证 base.py 工作正常"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from workflows.base import (
    RunHistoryTracker,
    WorkflowStatus,
    run_workflow,
    validate_workflow_json,
    validate_workflow_yaml,
    WorkflowError,
)
from pydantic import BaseModel, Field


class SmokeInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    target: int = Field(..., gt=0)


class SmokeOutput(BaseModel):
    ok: bool
    value: int


@run_workflow(workflow_id="WF-SMOKE", tenant_field="tenant_id")
def smoke_run(inp: SmokeInput) -> SmokeOutput:
    return SmokeOutput(ok=True, value=inp.target * 2)


def test_tracker_start_and_success():
    RunHistoryTracker.instance().reset()
    out = smoke_run(SmokeInput(tenant_id="zq-smoke", target=10))
    assert out["status"] == "success"
    assert out["output"]["ok"] is True
    assert out["output"]["value"] == 20
    assert out["run_id"].startswith("run_")


def test_validate_json():
    res = validate_workflow_json('{"tenant_id": "zq-1", "target": 5}', SmokeInput)
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_workflow_json('{"tenant_id": "zq", "target": -1}', SmokeInput)
    assert res["ok"] is False


def test_validate_yaml():
    res = validate_workflow_yaml("tenant_id: zq-1\ntarget: 7\n", SmokeInput)
    assert res["ok"] is True
    assert res["parsed"]["target"] == 7


def test_workflow_error():
    @run_workflow(workflow_id="WF-ERR", tenant_field="tenant_id")
    def err_run(inp):
        raise WorkflowError("WF-X", "intentional")

    out = err_run(SmokeInput(tenant_id="zq-err", target=1))
    assert out["status"] == "failed"
    assert out["error"]["code"] == "WF-X"