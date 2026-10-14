"""P5 fail-closed checks for the existing CloudTech five-stage content pipeline.

Only isolated simulations/mocks; tests never publish anything.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import auto_pipeline as ap


@pytest.fixture
def isolated_logs(monkeypatch, tmp_path):
    monkeypatch.setattr(ap, "PIPELINE_LOG", tmp_path)
    return tmp_path


def test_missing_handler_is_a_failure(monkeypatch, isolated_logs):
    monkeypatch.setattr(ap, "PIPELINE_STAGES", [
        {"id": "missing", "name": "Missing", "handler": "_does_not_exist"},
    ])
    report = ap.AutoPipeline(dry_run=True).run({"topic": "test"})
    assert report["ok"] is False
    assert report["failed_stages"] == 1
    assert "missing stage handler" in report["stages"][0]["error"]


def test_failed_upstream_blocks_downstream_without_call(monkeypatch, isolated_logs):
    calls = []
    def first(_pipeline):
        calls.append("first")
        return {"ok": False, "error": "unavailable"}
    def second(_pipeline):
        calls.append("second")
        return {"ok": True}
    monkeypatch.setattr(ap, "_p5_first", first, raising=False)
    monkeypatch.setattr(ap, "_p5_second", second, raising=False)
    monkeypatch.setattr(ap, "PIPELINE_STAGES", [
        {"id": "first", "name": "First", "handler": "_p5_first"},
        {"id": "second", "name": "Second", "handler": "_p5_second"},
    ])
    report = ap.AutoPipeline(dry_run=True).run({})
    assert calls == ["first"]
    assert report["failed_stages"] == 2
    assert report["stages"][1]["status"] == "blocked"


def test_invalid_handler_result_cannot_claim_success(monkeypatch, isolated_logs):
    monkeypatch.setattr(ap, "_p5_invalid", lambda _: {"ok": "yes"}, raising=False)
    monkeypatch.setattr(ap, "PIPELINE_STAGES", [
        {"id": "invalid", "name": "Invalid", "handler": "_p5_invalid"},
    ])
    report = ap.AutoPipeline().run({})
    assert not report["ok"]
    assert "invalid stage result contract" in report["stages"][0]["error"]


def test_selected_empty_stages_not_a_success(isolated_logs):
    result = ap.AutoPipeline().run({}, stages=[])
    assert result["ok"] is False
    assert result["total_stages"] == 0


def test_unknown_stage_is_rejected(isolated_logs):
    with pytest.raises(ValueError, match="unknown pipeline stages"):
        ap.AutoPipeline().run({}, stages=["made-up-stage"])


def test_reused_pipeline_does_not_count_old_results(monkeypatch, isolated_logs):
    monkeypatch.setattr(ap, "_p5_simple", lambda _: {"ok": True}, raising=False)
    monkeypatch.setattr(ap, "PIPELINE_STAGES", [
        {"id": "simple", "name": "Simple", "handler": "_p5_simple"},
    ])
    pipe = ap.AutoPipeline()
    assert pipe.run({})["total_stages"] == 1
    assert pipe.run({})["total_stages"] == 1


def test_production_video_provider_must_not_be_mock():
    pipe = ap.AutoPipeline(dry_run=False)
    pipe.state = {"input": {"video_provider": "mock"}, "output": {}}
    result = ap._stage_video_production(pipe)
    assert result["ok"] is False
    assert "mock" in result["error"]


def test_partial_publication_is_not_success(monkeypatch):
    def distribute(_content, platforms, dry_run):
        assert dry_run is False
        return {
            "ok": True, "total": 2, "success": 1, "failed": 1,
            "results": [{"ok": True}, {"ok": False}],
        }
    monkeypatch.setitem(sys.modules, "platform_publisher", SimpleNamespace(
        distribute_content=distribute,
    ))
    pipe = ap.AutoPipeline(dry_run=False)
    pipe.state = {
        "input": {"platforms": ["xiaohongshu", "douyin"], "topic": "sample"},
        "output": {"xiaohongshu": {"content": "text"}},
    }
    result = ap._stage_publish_distribution(pipe)
    assert result["ok"] is False
    assert result["success_count"] == 1


def test_simulated_remote_receipt_not_accepted_in_production(monkeypatch):
    def distribute(_content, platforms, dry_run):
        return {
            "ok": True, "total": 1, "success": 1, "failed": 0,
            "results": [{"ok": True, "mode": "dry_run"}],
        }
    monkeypatch.setitem(sys.modules, "platform_publisher", SimpleNamespace(
        distribute_content=distribute,
    ))
    pipe = ap.AutoPipeline(dry_run=False)
    pipe.state = {
        "input": {"platforms": ["xiaohongshu"]},
        "output": {"xiaohongshu": {"content": "text"}},
    }
    result = ap._stage_publish_distribution(pipe)
    assert result["ok"] is False
