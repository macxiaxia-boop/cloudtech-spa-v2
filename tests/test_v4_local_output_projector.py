"""A true local result can be indexed exactly once from a committed outbox.

No false model completion, no network, no customer content in the index.
"""
from concurrent.futures import ThreadPoolExecutor
import importlib
import json
from pathlib import Path
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workflows.v4 import IdempotencyStore, RunStatus, V4Orchestrator
from workflows.v4.local_job_queue import LocalJobQueue
from workflows.v4.local_worker import process_one
from workflows.v4.local_output_projector import LocalOutputProjector
from workflows.v4.sqlite_run_store import SQLiteRunStore


def setup_completed(tmp_path, *, tenant="tenant-one", path_id="WP-LOCAL-ARTICLE-EXTRACT"):
    store = SQLiteRunStore(tmp_path / "projector.sqlite3")
    orch = V4Orchestrator(IdempotencyStore(), run_store=store)
    if path_id == "WP-LOCAL-ARTICLE-EXTRACT":
        bindings = {"html": "<html><title>真实材料</title><p>我提供的正文</p></html>"}
    else:
        bindings = {"segments": [
            {"start_ms": 0, "end_ms": 1000, "text": "客户转写第一句"},
            {"start_ms": 1000, "end_ms": 2050, "text": "第二句"},
        ]}
    run = orch.create_run(path_id, 1, tenant, bindings,
                          idempotency_key=f"{tenant}-{path_id}")
    orch.transition(run.run_id, RunStatus.INPUT_BOUND)
    orch.transition(run.run_id, RunStatus.READY)
    LocalJobQueue(store).enqueue(run.run_id, tenant)
    assert process_one(store)["outcome"] == "DONE"
    return store, run.run_id


def test_projector_catalogues_real_html_and_acks_same_transaction(tmp_path):
    store, run_id = setup_completed(tmp_path)
    projector = LocalOutputProjector(store)
    with store._connect() as db:
        pending = db.execute(
            "SELECT state FROM v4_local_outbox WHERE run_id=?", (run_id,)
        ).fetchone()
        assert pending["state"] == "PENDING"
    done = projector.consume_one()
    assert done["outcome"] == "CATALOGUED"
    assert done["artifact_kind"] == "ARTICLE_HTML_EXTRACTION"
    assert projector.consume_one()["outcome"] == "IDLE"
    entries = projector.list_for_tenant("tenant-one")
    assert len(entries) == 1
    assert entries[0]["run_id"] == run_id
    assert entries[0]["path_id"] == "WP-LOCAL-ARTICLE-EXTRACT"
    assert len(entries[0]["source_sha256"]) == 64
    assert len(entries[0]["output_sha256"]) == 64
    assert "我提供的正文" not in json.dumps(entries, ensure_ascii=False)
    assert projector.list_for_tenant("other-tenant") == []
    with store._connect() as db:
        state = db.execute("SELECT state FROM v4_local_outbox WHERE run_id=?", (run_id,)).fetchone()
        assert state["state"] == "ACKED"


def test_projector_indexes_genuine_subtitle_without_fake_asr(tmp_path):
    store, run_id = setup_completed(tmp_path, path_id="WP-LOCAL-SUBTITLE-EXPORT")
    p = LocalOutputProjector(SQLiteRunStore(store.path))
    result = p.consume_one()
    assert result["outcome"] == "CATALOGUED"
    entries = p.list_for_tenant("tenant-one")
    assert len(entries) == 1
    assert entries[0]["artifact_kind"] == "SUBTITLE_SRT_VTT"
    assert store.receipt_count(run_id) == 1


def test_many_projector_processes_commit_exactly_one_catalog_record(tmp_path):
    store, run_id = setup_completed(tmp_path)
    def project(_):
        return LocalOutputProjector(SQLiteRunStore(store.path)).consume_one()["outcome"]
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(project, range(24)))
    assert outcomes.count("CATALOGUED") == 1, outcomes
    assert outcomes.count("IDLE") == 23, outcomes
    assert len(LocalOutputProjector(store).list_for_tenant("tenant-one")) == 1
    assert store.receipt_count(run_id) == 1


def test_falsified_outbox_hash_must_never_be_acknowledged(tmp_path):
    store, run_id = setup_completed(tmp_path)
    with store._connect() as db:
        db.execute(
            "UPDATE v4_local_outbox SET payload_json=? WHERE run_id=?",
            (json.dumps({
                "run_id": run_id, "tenant_id": "tenant-one",
                "event_type": "LOCAL_RUN_COMPLETED",
                "snapshot_sha256": "0" * 64,
            }), run_id),
        )
    result = LocalOutputProjector(store).consume_one()
    assert result["outcome"] == "BLOCKED_INVALID_EVIDENCE"
    assert LocalOutputProjector(store).list_for_tenant("tenant-one") == []
    with store._connect() as db:
        assert db.execute(
            "SELECT state FROM v4_local_outbox WHERE run_id=?", (run_id,)
        ).fetchone()["state"] == "PENDING"


def test_missing_or_tampered_node_receipt_cannot_be_catalogued(tmp_path):
    store, run_id = setup_completed(tmp_path)
    with store._connect() as db:
        db.execute("DELETE FROM v4_node_receipts WHERE run_id=?", (run_id,))
    result = LocalOutputProjector(store).consume_one()
    assert result["outcome"] == "BLOCKED_INVALID_EVIDENCE"
    assert LocalOutputProjector(store).list_for_tenant("tenant-one") == []
    assert store.get(run_id).status == RunStatus.COMPLETED


def test_tenant_scoped_http_catalog_is_only_verified_metadata(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    store, run_id = setup_completed(tmp_path)
    monkeypatch.setattr(api, "_orchestrator", V4Orchestrator(
        IdempotencyStore(), run_store=store,
    ))
    LocalOutputProjector(store).consume_one()
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    own = client.get("/v4/workpaths/local-outputs?tenant_id=tenant-one")
    assert own.status_code == 200, own.text
    assert own.json()["source"] == "verified_local_outbox_catalog"
    assert own.json()["raw_customer_content_in_response"] is False
    assert len(own.json()["items"]) == 1
    assert own.json()["items"][0]["run_id"] == run_id
    other = client.get("/v4/workpaths/local-outputs?tenant_id=other-tenant")
    assert other.status_code == 200
    assert other.json()["items"] == []
    assert client.get("/v4/workpaths/local-outputs").status_code == 422
