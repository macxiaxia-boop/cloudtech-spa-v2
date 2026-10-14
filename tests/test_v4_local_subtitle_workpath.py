"""Second real V4 local workpath: user-supplied timecoded transcript -> subtitles."""
import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapters.transcribe.supplied_subtitle_export import (
    SubtitleInputError, format_supplied_segments,
)
from workflows.v4 import IdempotencyStore, V4Orchestrator, RunStatus
from workflows.v4.local_job_queue import LocalJobQueue
from workflows.v4.sqlite_run_store import SQLiteRunStore


SEGMENTS = [
    {"start_ms": 0, "end_ms": 1500, "text": "欢迎来到 CloudTech"},
    {"start_ms": 1750, "end_ms": 3000, "text": "这是实际提供的时间轴"},
]


def test_actual_srt_and_vtt_content():
    result = format_supplied_segments(SEGMENTS)
    assert result["segment_count"] == 2
    assert result["duration_ms"] == 3000
    assert "00:00:00,000 --> 00:00:01,500" in result["srt"]
    assert "欢迎来到 CloudTech" in result["srt"]
    assert "00:00:01.750 --> 00:00:03.000" in result["vtt"]
    assert result["vtt"].startswith("WEBVTT\n")
    assert result["mock"] is False
    assert result["asr_performed"] is False
    assert result["model_called"] is False
    assert len(result["source_sha256"]) == 64


@pytest.mark.parametrize("bad", [
    [],
    [{"start_ms": True, "end_ms": 300, "text": "invalid"}],
    [{"start_ms": -5, "end_ms": 300, "text": "invalid"}],
    [{"start_ms": 100, "end_ms": 100, "text": "invalid"}],
    [{"start_ms": 100, "end_ms": 90000000, "text": "invalid"}],
    [{"start_ms": 0, "end_ms": 300, "text": " "}],
    [{"start_ms": 0, "end_ms": 500, "text": "one"},
     {"start_ms": 450, "end_ms": 600, "text": "overlap"}],
    "unverified transcript string",
])
def test_invalid_timing_or_content_fails_closed(bad):
    with pytest.raises(SubtitleInputError):
        format_supplied_segments(bad)


def test_untrusted_line_breaks_do_not_inject_fake_srt_cues():
    data = format_supplied_segments([
        {"start_ms": 0, "end_ms": 1000,
         "text": "Hello\n\n2\n00:00:00,000 --> 00:00:03,000\nFake"},
    ])
    assert data["segment_count"] == 1
    assert "\n2\n" not in data["srt"]
    assert "Hello 2 00:00:00,000 --> 00:00:03,000 Fake" in data["srt"]


def test_second_workpath_http_queue_and_independent_python_worker(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    store = SQLiteRunStore(tmp_path / "subtitles.sqlite3")
    monkeypatch.setattr(
        api, "_orchestrator",
        V4Orchestrator(IdempotencyStore(), run_store=store),
    )
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    req = {
        "path_id": "WP-LOCAL-SUBTITLE-EXPORT", "revision": 1,
        "input_bindings": {"segments": SEGMENTS},
        "idempotency_key": "user-subtitle-export-001",
    }
    created = client.post("/v4/workpaths/runs?tenant_id=tenant-subtitle", json=req)
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]
    assert created.json()["status"] == "READY"

    assert client.post(
        f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=another-tenant"
    ).status_code == 404

    queued = client.post(
        f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=tenant-subtitle"
    )
    assert queued.status_code == 200, queued.text
    assert queued.json()["state"] == "QUEUED"
    assert queued.json()["worker_invoked"] is False

    env = dict(os.environ)
    env["CLOUDTECH_ENV"] = "test"
    process = subprocess.run(
        [sys.executable, "-m", "workflows.v4.local_worker",
         "--db", str(store.path), "--once"],
        cwd=Path(__file__).resolve().parents[1], env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert process.returncode == 0, process.stderr
    assert "DONE" in process.stdout

    # Brand-new connection after a completely separate Python process.
    persisted = SQLiteRunStore(store.path)
    record = persisted.get(run_id)
    assert record.status is RunStatus.COMPLETED
    assert len(record.nodes) == 1
    node = record.nodes[0]
    assert node.operation == "subtitle.format_supplied"
    assert node.provider_name == "local_subtitle_formatter"
    assert node.cost_cents == 0
    assert "欢迎来到 CloudTech" in node.output_ref["srt"]
    assert node.output_ref["mock"] is False
    assert persisted.receipt_count(run_id) == 1
    assert LocalJobQueue(persisted).get_state(run_id, "tenant-subtitle")["state"] == "DONE"
    assert client.get(
        f"/v4/workpaths/runs/{run_id}?tenant_id=tenant-subtitle"
    ).json()["nodes"][0]["output_ref"]["vtt"].startswith("WEBVTT")
    assert client.get(
        f"/v4/workpaths/runs/{run_id}/export?tenant_id=tenant-subtitle"
    ).json()["ready"] is True
    again = client.post(
        f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=tenant-subtitle"
    )
    assert again.json()["idempotent_hit"] is True
    assert again.json()["state"] == "DONE"
    assert persisted.receipt_count(run_id) == 1


def test_second_workpath_refuses_invalid_real_segments_without_receipt(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    store = SQLiteRunStore(tmp_path / "bad-subtitles.sqlite3")
    monkeypatch.setattr(
        api, "_orchestrator",
        V4Orchestrator(IdempotencyStore(), run_store=store),
    )
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    bad = client.post("/v4/workpaths/runs?tenant_id=t1", json={
        "path_id": "WP-LOCAL-SUBTITLE-EXPORT", "revision": 1,
        "input_bindings": {"segments": [
            {"start_ms": 500, "end_ms": 100, "text": "invalid"},
        ]},
    })
    assert bad.status_code == 200
    run_id = bad.json()["run_id"]
    assert client.post(f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=t1").status_code == 200
    from workflows.v4.local_worker import process_one
    done = process_one(store)
    assert done["outcome"] == "FAILED_INPUT"
    assert store.get(run_id).status is RunStatus.FAILED
    assert store.receipt_count(run_id) == 0
