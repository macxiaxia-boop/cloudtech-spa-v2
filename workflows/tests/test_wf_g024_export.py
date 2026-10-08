"""Tests for WF-G-024 企业离线导出 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
import json
import hashlib
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g024_export import (
    run_export, ExportInput, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def _cleanup_export_dirs():
    """清理测试产生的导出目录, 避免污染."""
    import shutil
    base = Path(__file__).resolve().parents[2] / "workflows" / "impl" / "_exports"
    if base.exists():
        for d in base.iterdir():
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)


def test_jsonl_export_happy_path():
    _cleanup_export_dirs()
    inp = ExportInput(
        tenant_id="zq-1",
        export_scope=["leads", "contracts"],
        format="jsonl",
        records={
            "leads": [{"id": "L1", "name": "张三"}, {"id": "L2", "name": "李四"}],
            "contracts": [{"id": "C1", "amount": 10000}],
        },
    )
    out = run_export(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["export_id"].startswith("exp-")
    files = {f["scope"]: f for f in o["files"]}
    assert files["leads"]["count"] == 2
    assert files["contracts"]["count"] == 1
    # sha256 长度 = 64 hex chars
    assert len(files["leads"]["sha256"]) == 64
    assert "manifest sha256=" in o["integrity_check"]


def test_csv_export():
    _cleanup_export_dirs()
    inp = ExportInput(
        tenant_id="zq-1",
        export_scope=["leads"],
        format="csv",
        records={
            "leads": [{"id": "L1", "name": "张三"}, {"id": "L2", "name": "李四"}],
        },
    )
    out = run_export(inp)
    o = out["output"]
    files = {f["scope"]: f for f in o["files"]}
    fpath = Path(files["leads"]["path"])
    assert fpath.exists()
    content = fpath.read_text(encoding="utf-8")
    assert "id,name" in content  # CSV header
    assert "L1,张三" in content


def test_empty_records_still_exports_manifest():
    _cleanup_export_dirs()
    inp = ExportInput(
        tenant_id="zq-1",
        export_scope=["leads"],
        records={},  # 无 records
    )
    out = run_export(inp)
    o = out["output"]
    files = {f["scope"]: f for f in o["files"]}
    assert files["leads"]["count"] == 0


def test_invalid_scope_rejected():
    with pytest.raises(ValidationError):
        ExportInput(
            tenant_id="zq-1",
            export_scope=["unknown_scope"],
        )


def test_invalid_format_rejected():
    with pytest.raises(ValidationError):
        ExportInput(
            tenant_id="zq-1",
            export_scope=["leads"],
            format="xml",
        )


def test_empty_scope_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        ExportInput(tenant_id="zq-1", export_scope=[])


def test_multi_scope_export():
    _cleanup_export_dirs()
    inp = ExportInput(
        tenant_id="zq-1",
        export_scope=["leads", "sops", "calls"],
        records={
            "leads": [{"id": "L1"}],
            "sops": [{"sid": "S1"}],
            "calls": [{"cid": "K1"}],
        },
    )
    out = run_export(inp)
    scopes = {f["scope"] for f in out["output"]["files"]}
    assert scopes == {"leads", "sops", "calls"}


def test_validate_json_ok():
    res = validate_json(
        '{"tenant_id":"zq-1","export_scope":["leads"],'
        '"format":"jsonl","records":{"leads":[{"id":"L1"}]}}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1","export_scope":[]}')
    assert res["ok"] is False


def test_tracker_records_run():
    _cleanup_export_dirs()
    inp = ExportInput(
        tenant_id="zq-tr",
        export_scope=["leads"],
        records={"leads": [{"id": "L1"}]},
    )
    out = run_export(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-G-024", tenant_id="zq-tr")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"