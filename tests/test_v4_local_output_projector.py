"""A true local result can be indexed exactly once from a committed outbox.

No false model completion, no network, no customer content in the index.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
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
    if path_id in ("WP-LOCAL-ARTICLE-EXTRACT", "WP-LOCAL-ARTICLE-ANALYZE"):
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


def _forge_consistent_receipts(store, run_id, *, field, value):
    """Simulate corrupt but mutually consistent snapshot/receipt/outbox metadata."""
    with store._connect() as db:
        row = db.execute(
            "SELECT snapshot FROM v4_runs WHERE run_id=?", (run_id,),
        ).fetchone()
        snapshot = json.loads(row["snapshot"])
        snapshot["nodes"][0]["output_ref"][field] = value
        raw = json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
        db.execute(
            "UPDATE v4_runs SET snapshot=? WHERE run_id=?", (raw, run_id),
        )
        db.execute(
            "UPDATE v4_node_receipts SET receipt_json=? WHERE run_id=? AND node_id='html_parse'",
            (json.dumps(snapshot["nodes"][0], ensure_ascii=False, allow_nan=False), run_id),
        )
        event_payload = {
            "run_id": run_id,
            "tenant_id": snapshot["tenant_id"],
            "event_type": "LOCAL_RUN_COMPLETED",
            "snapshot_sha256": hashlib.sha256(
                json.dumps(snapshot, sort_keys=True, ensure_ascii=False,
                           allow_nan=False).encode("utf-8")
            ).hexdigest(),
        }
        db.execute(
            "UPDATE v4_local_outbox SET payload_json=? WHERE run_id=?",
            (json.dumps(event_payload, sort_keys=True, ensure_ascii=False), run_id),
        )


def test_forged_extraction_with_matching_receipts_is_not_catalogued(tmp_path):
    store, run_id = setup_completed(tmp_path)
    _forge_consistent_receipts(store, run_id, field="text",
                               value="伪造的正文；原始HTML里没有这段内容")
    projector = LocalOutputProjector(store)
    verdict = projector.consume_one()
    assert verdict["outcome"] == "BLOCKED_INVALID_EVIDENCE", verdict
    assert projector.list_for_tenant("tenant-one") == []
    with store._connect() as db:
        event = db.execute("SELECT state FROM v4_local_outbox WHERE run_id=?",
                           (run_id,)).fetchone()
        assert event["state"] == "PENDING"


def test_analysis_output_requires_original_unmodified_extraction(tmp_path):
    store, run_id = setup_completed(
        tmp_path, path_id="WP-LOCAL-ARTICLE-ANALYZE",
    )
    projector = LocalOutputProjector(store)
    assert projector.consume_one()["outcome"] == "CATALOGUED"

    # A second independent run has consistent forged receipt and event hashes.
    other_store = SQLiteRunStore(tmp_path / "corrupt.sqlite")
    orch = V4Orchestrator(IdempotencyStore(), run_store=other_store)
    rec = orch.create_run(
        "WP-LOCAL-ARTICLE-ANALYZE", 1, "tenant-one",
        {"html": "<html><h1>原始标题</h1><p>原文正文</p></html>"},
        idempotency_key="different-id",
    )
    orch.transition(rec.run_id, RunStatus.INPUT_BOUND)
    orch.transition(rec.run_id, RunStatus.READY)
    LocalJobQueue(other_store).enqueue(rec.run_id, "tenant-one")
    assert process_one(other_store)["outcome"] == "DONE"
    _forge_consistent_receipts(
        other_store, rec.run_id, field="images",
        value=[{"url": "https://example.invalid/forged.png", "alt": "伪造图片"}],
    )
    assert LocalOutputProjector(other_store).consume_one()["outcome"] == (
        "BLOCKED_INVALID_EVIDENCE"
    )
    assert LocalOutputProjector(other_store).list_for_tenant("tenant-one") == []
