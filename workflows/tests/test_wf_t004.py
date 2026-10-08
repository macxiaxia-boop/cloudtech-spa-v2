"""Tests for WF-T-004 内容计划排期与人工发布 (≥5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t004_content_plan import run_content_plan, ContentPlanInput, ScriptSlot, validate_json


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_happy_path_with_approval():
    inp = ContentPlanInput(
        tenant_id="zq-1",
        approval_required=True,
        scripts=[
            ScriptSlot(script_id="s1", topic="旧房翻新", platform="xiaohongshu", scheduled_at="2026-10-10T09:00:00"),
            ScriptSlot(script_id="s2", topic="装修预算", platform="douyin", scheduled_at="2026-10-10T19:00:00"),
        ],
    )
    out = run_content_plan(inp)
    assert out["status"] == "success"
    assert out["output"]["total"] == 2
    assert out["output"]["pending_approval"] == 2
    assert all(s["status"] == "pending_approval" for s in out["output"]["schedule"])


def test_auto_approved():
    inp = ContentPlanInput(
        tenant_id="zq-1", approval_required=False,
        scripts=[ScriptSlot(script_id="s1", topic="x", platform="douyin", scheduled_at="2026-10-10T12:00:00")],
    )
    out = run_content_plan(inp)
    assert out["status"] == "success"
    assert out["output"]["approved"] == 1


def test_conflict_detection():
    inp = ContentPlanInput(
        tenant_id="zq-1", approval_required=False,
        scripts=[
            ScriptSlot(script_id="s1", topic="A", platform="douyin", scheduled_at="2026-10-10T09:00:00"),
            ScriptSlot(script_id="s2", topic="B", platform="douyin", scheduled_at="2026-10-10T09:00:00"),
        ],
    )
    out = run_content_plan(inp)
    assert len(out["output"]["conflicts"]) == 1
    assert "冲突" in out["output"]["conflicts"][0]


def test_publish_window_classification():
    inp = ContentPlanInput(
        tenant_id="zq-1", approval_required=False,
        scripts=[
            ScriptSlot(script_id="m", topic="t", platform="douyin", scheduled_at="2026-10-10T09:00:00"),
            ScriptSlot(script_id="n", topic="t", platform="douyin", scheduled_at="2026-10-10T14:00:00"),
            ScriptSlot(script_id="e", topic="t", platform="douyin", scheduled_at="2026-10-10T19:00:00"),
        ],
    )
    out = run_content_plan(inp)
    windows = [s["publish_window"] for s in out["output"]["schedule"]]
    assert "morning" in windows and "noon" in windows and "evening" in windows


def test_empty_scripts_fails():
    inp = ContentPlanInput(tenant_id="zq-1", scripts=[])
    out = run_content_plan(inp)
    assert out["status"] == "failed"
    assert "WF-T004-EMPTY" in out["error"]["code"]


def test_validate_json():
    res = validate_json('{"tenant_id":"zq-1","scripts":[{"script_id":"s1","topic":"x","platform":"douyin","scheduled_at":"2026-10-10T09:00:00"}]}')
    assert res["ok"] is True


def test_list_runs():
    inp = ContentPlanInput(
        tenant_id="zq-list", approval_required=False,
        scripts=[ScriptSlot(script_id="s1", topic="x", platform="douyin", scheduled_at="2026-10-10T09:00:00")],
    )
    run_content_plan(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-T-004", tenant_id="zq-list")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"