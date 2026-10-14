"""Real two-stage HTML -> lexical analysis through existing durable worker.

No webpage crawling, text generation, model API, invented copy, or paid call.
"""
import hashlib
import importlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from adapters.article.article_parser import parse_html
from adapters.content.local_text_analysis import analyze_user_article
from workflows.v4 import V4Orchestrator, IdempotencyStore, RunStatus
from workflows.v4.local_job_queue import LocalJobQueue
from workflows.v4.local_output_projector import LocalOutputProjector
from workflows.v4.sqlite_run_store import SQLiteRunStore

HTML = (
    "<html><head><title>实际用户素材</title></head><body>"
    "<article><h1>真实内容</h1><p>如何学习 AI 产品设计？</p>"
    "<p>先理解用户需求，再明确流程与数据。</p>"
    "<p>如果你有问题，欢迎评论或联系获取详情。</p>"
    "<img src='https://example.org/photo.jpg'></article>"
    "</body></html>"
)


def setup(tmp_path):
    store = SQLiteRunStore(tmp_path / "real-chain.sqlite3")
    orchestrator = V4Orchestrator(IdempotencyStore(), run_store=store)
    run = orchestrator.create_run(
        "WP-LOCAL-ARTICLE-ANALYZE", 1, "tenant-article",
        {"html": HTML, "source_url": "https://example.org/article"},
        idempotency_key="pipeline-article-1",
    )
    orchestrator.transition(run.run_id, RunStatus.INPUT_BOUND)
    orchestrator.transition(run.run_id, RunStatus.READY)
    return store, run.run_id


def test_actual_analysis_is_from_supplied_text_not_generated():
    parsed = parse_html(HTML, source_url="https://example.org/article")
    result = analyze_user_article(parsed)
    assert result["mock"] is False
    assert result["ai_model_used"] is False
    assert result["subjective_quality_rating_provided"] is False
    assert result["paragraph_count"] >= 3
    assert result["characters"] == len(parsed["text"])
    assert result["question_marks"] == 1
    assert any("评论" in item["matched_terms"] for item in result["cta_term_matches"])
    assert result["source_html_sha256"] == hashlib.sha256(HTML.encode()).hexdigest()
    assert result["text_sha256"] == hashlib.sha256(parsed["text"].encode()).hexdigest()


def test_cannot_pretend_heuristic_result_is_real_provider():
    with pytest.raises(ValueError):
        analyze_user_article({"text": "generated", "mock": True})
    with pytest.raises(ValueError):
        analyze_user_article({"text": "generated", "mock": False,
                              "content_sha256": "bad"})
    with pytest.raises(ValueError):
        analyze_user_article({"text": "", "mock": False,
                              "content_sha256": "0"*64})


def test_two_real_nodes_execute_in_one_transaction_then_catalog(tmp_path):
    store, run_id = setup(tmp_path)
    LocalJobQueue(store).enqueue(run_id, "tenant-article")
    from workflows.v4.local_worker import process_one
    result = process_one(store)
    assert result["outcome"] == "DONE"
    assert result["cost_cents"] == 0
    assert result["provider_called"] is False
    assert result["node_count"] == 2
    reopened = SQLiteRunStore(store.path)
    record = reopened.get(run_id)
    assert record.status == RunStatus.COMPLETED
    assert [n.operation for n in record.nodes] == [
        "article.html_parse", "content.local_text_analyze"
    ]
    assert record.nodes[0].status == record.nodes[1].status == RunStatus.COMPLETED
    assert record.nodes[0].output_ref["mock"] is False
    assert record.nodes[1].output_ref["ai_model_used"] is False
    assert record.nodes[1].input_hash == hashlib.sha256(
        record.nodes[0].output_ref["text"].encode()).hexdigest()
    assert reopened.receipt_count(run_id) == 2
    projector = LocalOutputProjector(reopened)
    assert projector.consume_one()["outcome"] == "CATALOGUED"
    assert projector.consume_one()["outcome"] == "IDLE"
    records = projector.list_for_tenant("tenant-article")
    assert len(records) == 1
    assert records[0]["artifact_kind"] == "ARTICLE_CONTENT_ANALYSIS"
    assert records[0]["node_id"] == "content_analyze"
    assert projector.list_for_tenant("other-tenant") == []
    assert LocalJobQueue(reopened).get_state(run_id, "tenant-article")["state"] == "DONE"


def test_two_stage_operation_fails_entire_job_on_invalid_empty_content(tmp_path):
    store = SQLiteRunStore(tmp_path / "invalid.sqlite3")
    orch = V4Orchestrator(IdempotencyStore(), run_store=store)
    run = orch.create_run("WP-LOCAL-ARTICLE-ANALYZE", 1,
                           "tenant-article", {"html": "<script>skip</script>"})
    orch.transition(run.run_id, RunStatus.INPUT_BOUND)
    orch.transition(run.run_id, RunStatus.READY)
    LocalJobQueue(store).enqueue(run.run_id, "tenant-article")
    from workflows.v4.local_worker import process_one
    outcome = process_one(store)
    assert outcome["outcome"] == "FAILED_INPUT"
    assert store.get(run.run_id).status == RunStatus.FAILED
    assert store.receipt_count(run.run_id) == 0
    assert LocalOutputProjector(store).consume_one()["outcome"] == "IDLE"


def test_two_stage_audit_rejects_tampered_analysis(tmp_path):
    store, run_id = setup(tmp_path)
    LocalJobQueue(store).enqueue(run_id, "tenant-article")
    from workflows.v4.local_worker import process_one
    assert process_one(store)["outcome"] == "DONE"
    with store._connect() as db:
        row = db.execute("SELECT snapshot FROM v4_runs WHERE run_id=?", (run_id,)).fetchone()
        import json
        payload = json.loads(row["snapshot"])
        payload["nodes"][1]["output_ref"]["paragraph_count"] = 99999
        db.execute("UPDATE v4_runs SET snapshot=? WHERE run_id=?",
                   (json.dumps(payload), run_id))
    assert LocalOutputProjector(store).consume_one()["outcome"] == "BLOCKED_INVALID_EVIDENCE"
    assert LocalOutputProjector(store).list_for_tenant("tenant-article") == []


def test_independent_python_worker_process_completes_both_nodes(tmp_path):
    store, run_id = setup(tmp_path)
    LocalJobQueue(store).enqueue(run_id, "tenant-article")
    env = dict(os.environ)
    env["CLOUDTECH_ENV"] = "test"
    result = subprocess.run([
        sys.executable, "-m", "workflows.v4.local_worker",
        "--db", str(store.path), "--once",
    ], cwd=Path(__file__).resolve().parents[1], env=env,
       capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    reopened = SQLiteRunStore(store.path)
    record = reopened.get(run_id)
    assert record.status == RunStatus.COMPLETED
    assert len(record.nodes) == 2
    assert reopened.receipt_count(run_id) == 2
    index = LocalOutputProjector(reopened).list_for_tenant("tenant-article")
    assert len(index) == 1
    assert index[0]["artifact_kind"] == "ARTICLE_CONTENT_ANALYSIS"


def test_v4_http_two_stage_workpath_uses_same_queued_execution(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    store = SQLiteRunStore(tmp_path / "http.sqlite3")
    monkeypatch.setattr(api, "_orchestrator", V4Orchestrator(
        IdempotencyStore(), run_store=store,
    ))
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    req = {
        "path_id": "WP-LOCAL-ARTICLE-ANALYZE", "revision": 1,
        "input_bindings": {"html": HTML},
    }
    created = client.post("/v4/workpaths/runs?tenant_id=owner", json=req)
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]
    denied = client.post(f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=other")
    assert denied.status_code == 404
    queued = client.post(f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=owner")
    assert queued.status_code == 200, queued.text
    from workflows.v4.local_worker import process_one
    assert process_one(store)["outcome"] == "DONE"
    assert LocalOutputProjector(store).consume_one()["outcome"] == "CATALOGUED"
    fetched = client.get(f"/v4/workpaths/runs/{run_id}?tenant_id=owner")
    assert fetched.status_code == 200
    assert len(fetched.json()["nodes"]) == 2
    catalog = client.get("/v4/workpaths/local-outputs?tenant_id=owner")
    assert catalog.status_code == 200
    assert catalog.json()["items"][0]["artifact_kind"] == "ARTICLE_CONTENT_ANALYSIS"
    assert client.get("/v4/workpaths/local-outputs?tenant_id=other").json()["items"] == []
