"""Real independent local worker tests, including fencing after lease expiry."""
from concurrent.futures import ThreadPoolExecutor
import importlib
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from workflows.v4 import IdempotencyStore, V4Orchestrator, RunStatus
from workflows.v4.local_job_queue import LocalJobQueue
from workflows.v4.local_worker import process_one
from workflows.v4.sqlite_run_store import SQLiteRunStore, RunStoreConflict

HTML = "<html><title>worker</title><body><p>真实 Worker 已处理内容</p></body></html>"


def setup_run(tmp_path, tenant="t1", html=HTML):
    store = SQLiteRunStore(tmp_path / "worker.sqlite")
    orch = V4Orchestrator(IdempotencyStore(), run_store=store)
    r = orch.create_run("WP-LOCAL-ARTICLE-EXTRACT", 1, tenant,
                        {"html": html}, idempotency_key="nonce")
    orch.transition(r.run_id, RunStatus.INPUT_BOUND)
    orch.transition(r.run_id, RunStatus.READY)
    return store, orch, r.run_id


def test_queue_single_row_and_tenant_ownership(tmp_path):
    store, orch, run_id = setup_run(tmp_path)
    q = LocalJobQueue(store)
    one = q.enqueue(run_id, "t1")
    again = q.enqueue(run_id, "t1")
    assert one["state"] == again["state"] == "QUEUED"
    assert one["idempotent_hit"] is False
    assert again["idempotent_hit"] is True
    with pytest.raises(Exception):
        q.enqueue(run_id, "t-other")
    with pytest.raises(Exception, match="queued local worker"):
        orch.transition(run_id, RunStatus.RUNNING)


def test_concurrent_claim_is_exclusive(tmp_path):
    store, _, run_id = setup_run(tmp_path)
    LocalJobQueue(store).enqueue(run_id, "t1")
    def claim(_):
        return LocalJobQueue(store).claim(lease_seconds=30)
    with ThreadPoolExecutor(max_workers=14) as pool:
        leases = list(pool.map(claim, range(25)))
    winners = [item for item in leases if item is not None]
    assert len(winners) == 1
    assert winners[0].run_id == run_id
    assert winners[0].attempt == 1


def test_expired_worker_token_cannot_commit_after_steal(tmp_path):
    store, _, run_id = setup_run(tmp_path)
    queue = LocalJobQueue(store)
    queue.enqueue(run_id, "t1")
    old = queue.claim()
    assert old is not None
    with store._connect() as db:
        db.execute("UPDATE v4_local_jobs SET lease_until=? WHERE run_id=?",
                   (time.time() - 1, run_id))
    new = LocalJobQueue(store).claim()
    assert new is not None
    assert new.attempt == 2
    assert new.token != old.token
    with pytest.raises(RunStoreConflict, match="lease"):
        store.mutate(run_id, lambda r: None, lease_token=old.token)
    assert store.get(run_id).status == RunStatus.READY
    assert queue.get_state(run_id, "t1")["state"] == "LEASED"
    # The newest lease holder can legally requeue with a bounded retry.
    assert queue.fail(new, "WORKER_EXIT", retryable=True) is True


def test_worker_executes_real_html_and_commits_receipt_atomically(tmp_path):
    store, _, run_id = setup_run(tmp_path)
    q = LocalJobQueue(store)
    q.enqueue(run_id, "t1")
    result = process_one(store)
    assert result["outcome"] == "DONE", result
    assert result["cost_cents"] == 0
    assert result["provider_called"] is False
    rec = store.get(run_id)
    assert rec.status == RunStatus.COMPLETED
    assert rec.nodes[0].status == RunStatus.COMPLETED
    assert rec.nodes[0].output_ref["text"].endswith("真实 Worker 已处理内容")
    assert store.receipt_count(run_id) == 1
    assert q.get_state(run_id, "t1")["state"] == "DONE"
    assert process_one(SQLiteRunStore(store.path))["outcome"] == "IDLE"
    assert store.receipt_count(run_id) == 1


def test_abandoned_lease_is_reclaimed_after_crash(tmp_path):
    store, _, run_id = setup_run(tmp_path)
    queue = LocalJobQueue(store)
    queue.enqueue(run_id, "t1")
    first = queue.claim()
    assert first is not None
    with store._connect() as db:
        db.execute("UPDATE v4_local_jobs SET lease_until=? WHERE run_id=?",
                   (time.time() - 1, run_id))
    second_process = SQLiteRunStore(store.path)
    done = process_one(second_process)
    assert done["outcome"] == "DONE"
    assert queue.get_state(run_id, "t1")["attempts"] == 2
    assert store.receipt_count(run_id) == 1


def test_invalid_input_is_failure_not_synthetic_success(tmp_path):
    store, _, run_id = setup_run(tmp_path, html=" ")
    LocalJobQueue(store).enqueue(run_id, "t1")
    result = process_one(store)
    assert result["outcome"] == "FAILED_INPUT"
    assert store.get(run_id).status == RunStatus.FAILED
    assert LocalJobQueue(store).get_state(run_id, "t1")["state"] == "FAILED"
    assert store.receipt_count(run_id) == 0


def test_authenticated_api_enqueue_and_status(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    store, _, run_id = setup_run(tmp_path)
    monkeypatch.setattr(api, "_orchestrator",
                        V4Orchestrator(IdempotencyStore(), run_store=store))
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    assert client.post(f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=other").status_code == 404
    result = client.post(f"/v4/workpaths/runs/{run_id}/enqueue-local?tenant_id=t1")
    assert result.status_code == 200, result.text
    assert result.json()["queued_only"] is True
    assert result.json()["worker_invoked"] is False
    assert client.get(f"/v4/workpaths/runs/{run_id}/local-queue?tenant_id=other").status_code == 404
    status = client.get(f"/v4/workpaths/runs/{run_id}/local-queue?tenant_id=t1")
    assert status.status_code == 200
    assert status.json()["state"] == "QUEUED"
    assert client.post(f"/v4/workpaths/runs/{run_id}/execute-local?tenant_id=t1").status_code == 409


def test_independent_python_worker_process(tmp_path):
    store, _, run_id = setup_run(tmp_path)
    LocalJobQueue(store).enqueue(run_id, "t1")
    repo_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["CLOUDTECH_ENV"] = "test"
    result = subprocess.run(
        [sys.executable, "-m", "workflows.v4.local_worker",
         "--db", str(store.path), "--once"],
        cwd=repo_root, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "DONE" in result.stdout
    reopened = SQLiteRunStore(store.path)
    assert reopened.get(run_id).status == RunStatus.COMPLETED
    assert reopened.receipt_count(run_id) == 1
    from workflows.v4.local_output_projector import LocalOutputProjector
    indexed = LocalOutputProjector(reopened).list_for_tenant("t1")
    assert len(indexed) == 1
    assert indexed[0]["artifact_kind"] == "ARTICLE_HTML_EXTRACTION"



def test_crashed_worker_after_max_attempts_is_not_a_zombie(tmp_path):
    store, _, run_id = setup_run(tmp_path)
    q = LocalJobQueue(store)
    q.enqueue(run_id, "t1")
    with store._connect() as db:
        db.execute("UPDATE v4_local_jobs SET max_attempts=2 WHERE run_id=?", (run_id,))
    first = q.claim()
    assert first is not None
    with store._connect() as db:
        db.execute("UPDATE v4_local_jobs SET lease_until=? WHERE run_id=?",
                   (time.time() - 1, run_id))
    second = q.claim()
    assert second is not None
    assert second.attempt == 2
    with store._connect() as db:
        db.execute("UPDATE v4_local_jobs SET lease_until=? WHERE run_id=?",
                   (time.time() - 1, run_id))
    assert q.claim() is None
    state = q.get_state(run_id, "t1")
    assert state["state"] == "FAILED"
    assert state["error_code"] == "LOCAL_WORKER_LEASE_EXHAUSTED"
    assert store.get(run_id).status is RunStatus.FAILED
    assert store.receipt_count(run_id) == 0


def test_real_worker_heartbeat_has_strict_staleness_cutoff(tmp_path):
    store, _, _ = setup_run(tmp_path)
    q = LocalJobQueue(store)
    assert q.active_workers() == 0
    q.note_worker("local-loop-1")
    assert q.active_workers() == 1
    with store._connect() as db:
        db.execute("UPDATE v4_local_worker_heartbeats SET last_seen=?",
                   (time.time() - 300,))
    assert q.active_workers() == 0


def test_v4_api_reports_actual_heartbeat_only(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    store, _, run_id = setup_run(tmp_path)
    monkeypatch.setattr(api, "_orchestrator", V4Orchestrator(
        IdempotencyStore(), run_store=store,
    ))
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    before = client.get("/v4/workpaths/runs?tenant_id=t1")
    assert before.status_code == 200 and before.json()["worker_connected"] is False
    q = LocalJobQueue(store)
    q.note_worker("local-loop")
    online = client.get("/v4/workpaths/runs?tenant_id=t1")
    assert online.json()["worker_connected"] is True
    assert online.json()["active_local_workers"] == 1
    with store._connect() as db:
        db.execute("UPDATE v4_local_worker_heartbeats SET last_seen=?",
                   (time.time() - 300,))
    assert client.get("/v4/workpaths/runs?tenant_id=t1").json()["worker_connected"] is False


def test_completed_node_receipt_cannot_be_rewritten_or_deleted(tmp_path):
    """A later snapshot mutation must not rewrite previously issued evidence."""
    store, _, run_id = setup_run(tmp_path)
    LocalJobQueue(store).enqueue(run_id, "t1")
    assert process_one(store)["outcome"] == "DONE"
    original = store.get(run_id).nodes[0].to_dict()
    assert store.receipt_count(run_id) == 1

    def tamper_output(rec):
        rec.nodes[0].output_ref["text"] = "tampered content"

    def remove_completed_node(rec):
        rec.nodes.clear()

    def duplicate_completed_node(rec):
        import copy
        rec.nodes.append(copy.deepcopy(rec.nodes[0]))

    def tamper_provider_identity(rec):
        rec.nodes[0].provider_name = "unverified_provider"

    for mutation in (
        tamper_output, remove_completed_node,
        duplicate_completed_node, tamper_provider_identity,
    ):
        with pytest.raises(RunStoreConflict, match="immutable|duplicate"):
            store.mutate(run_id, mutation)
        still_saved = store.get(run_id)
        assert still_saved.status == RunStatus.COMPLETED
        assert len(still_saved.nodes) == 1
        assert still_saved.nodes[0].to_dict() == original
        assert store.receipt_count(run_id) == 1

    # A non-mutating replay must still work without minting another receipt.
    assert store.mutate(run_id, lambda rec: "unchanged") == "unchanged"
    assert store.receipt_count(run_id) == 1
