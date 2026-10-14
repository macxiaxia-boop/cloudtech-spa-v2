"""SQLite single-host V4 run journal integration and atomicity proof.

No payment/provider API, external service or Windows filesystem required.
"""
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from workflows.v4 import V4Orchestrator, IdempotencyStore, RunStatus, RunStatusError
from workflows.v4.orchestrator import NodeRunRecord
from workflows.v4.node_kinds import NodeKind
from workflows.v4.sqlite_run_store import SQLiteRunStore, RunStoreError


def make(tmp_path, db_name="v4-runs.sqlite3"):
    store = SQLiteRunStore(tmp_path / db_name)
    return V4Orchestrator(IdempotencyStore(), run_store=store), store


def create(orch, tenant="tenant-1", key="nonce-one", payload=None):
    return orch.create_run(
        "WP-BLOGGER-RESEARCH", 1, tenant,
        payload if payload is not None else {"url": "https://example.org/1"},
        idempotency_key=key,
    )


def test_sqlite_survives_reopening_and_preserves_state(tmp_path):
    orchestrator, _ = make(tmp_path)
    r = create(orchestrator)
    orchestrator.transition(r.run_id, RunStatus.INPUT_BOUND)
    orchestrator.transition(r.run_id, RunStatus.READY)
    fresh, _ = make(tmp_path)
    rec = fresh.get_run(r.run_id)
    assert rec is not None
    assert rec.status is RunStatus.READY
    assert rec.input_bindings == {"url": "https://example.org/1"}
    assert fresh.storage_kind == "SQLITE_LOCAL_DURABLE"
    assert fresh.list_runs(tenant_id="unrelated") == []


def test_duplicate_request_across_two_connections_is_one_run(tmp_path):
    first, _ = make(tmp_path)
    second, _ = make(tmp_path)
    def worker(i):
        return create(first if i % 2 else second).run_id
    with ThreadPoolExecutor(max_workers=12) as pool:
        ids = list(pool.map(worker, range(48)))
    assert len(set(ids)) == 1
    fresh, _ = make(tmp_path)
    assert len(fresh.list_runs(tenant_id="tenant-1")) == 1
    assert create(fresh).run_id == ids[0]


def test_same_key_different_payload_rejected_across_processes(tmp_path):
    one, _ = make(tmp_path)
    two, _ = make(tmp_path)
    original = create(one)
    with pytest.raises(RunStatusError, match="different request"):
        create(two, payload={"url": "https://different.example"})
    assert two.get_run(original.run_id) is not None
    assert len(two.list_runs("tenant-1")) == 1


def test_receipt_replay_and_restart_never_double_counts(tmp_path):
    one, store = make(tmp_path)
    run = create(one)
    for status in (RunStatus.INPUT_BOUND, RunStatus.READY, RunStatus.RUNNING):
        one.transition(run.run_id, status)
    one.add_node(run.run_id, NodeRunRecord(
        node_id="media1", node_kind=NodeKind.MEDIA_GENERATE,
        operation="image.generate", requires={}, produces={}, input_hash="input1",
    ))
    one.mark_node_running(run.run_id, "media1")
    one.mark_node_done(run.run_id, "media1", {"asset_id": "asset-a"},
                       provider_req_id="external-1", provider_name="provider-a",
                       cost_cents=23, cost_class="METERED_MEDIA")
    second, store2 = make(tmp_path)
    second.mark_node_done(run.run_id, "media1", {"asset_id": "asset-a"},
                          provider_req_id="external-1", provider_name="provider-a",
                          cost_cents=23, cost_class="METERED_MEDIA")
    assert second.get_run(run.run_id).budget_spent_cents == 23
    assert store.receipt_count(run.run_id) == store2.receipt_count(run.run_id) == 1
    with pytest.raises(RunStatusError, match="conflicting completion"):
        second.mark_node_done(run.run_id, "media1", {"asset_id": "different"},
                              provider_req_id="external-2", provider_name="provider-a",
                              cost_cents=54)
    assert second.get_run(run.run_id).budget_spent_cents == 23
    assert store.receipt_count(run.run_id) == 1


def test_duplicate_upstream_receipt_across_runs_rolls_back(tmp_path):
    orch, store = make(tmp_path)
    runs = [create(orch, key="a"), create(orch, key="b")]
    for r in runs:
        for status in (RunStatus.INPUT_BOUND, RunStatus.READY, RunStatus.RUNNING):
            orch.transition(r.run_id, status)
        orch.add_node(r.run_id, NodeRunRecord(
            node_id="n", node_kind=NodeKind.MEDIA_GENERATE,
            operation="image.generate", requires={}, produces={}, input_hash=r.run_id,
        ))
        orch.mark_node_running(r.run_id, "n")
    orch.mark_node_done(runs[0].run_id, "n", {"asset_id": "a"},
                        provider_req_id="same-upstream", provider_name="provider",
                        cost_cents=10)
    with pytest.raises(sqlite3.IntegrityError):
        orch.mark_node_done(runs[1].run_id, "n", {"asset_id": "b"},
                            provider_req_id="same-upstream", provider_name="provider",
                            cost_cents=10)
    second = orch.get_run(runs[1].run_id)
    assert second.budget_spent_cents == 0
    assert second.nodes[0].status is RunStatus.RUNNING
    assert store.receipt_count(runs[1].run_id) == 0


def test_failed_persistence_rejects_completion_without_phantom_charge(tmp_path):
    orch, _ = make(tmp_path)
    run = create(orch)
    orch.transition(run.run_id, RunStatus.INPUT_BOUND)
    with pytest.raises(RunStatusError):
        orch.transition(run.run_id, RunStatus.COMPLETED)
    assert orch.get_run(run.run_id).status == RunStatus.INPUT_BOUND


def test_missing_db_parent_is_explicit_blocker(tmp_path):
    with pytest.raises(RunStoreError, match="parent directory"):
        SQLiteRunStore(tmp_path / "missing" / "run.sqlite")


def test_empty_tenant_does_not_leak_records(tmp_path):
    orch, _ = make(tmp_path)
    a = create(orch, tenant="tenant-a", key="a")
    b = create(orch, tenant="tenant-b", key="b")
    assert [r.run_id for r in orch.list_runs("tenant-a")] == [a.run_id]
    assert [r.run_id for r in orch.list_runs("tenant-b")] == [b.run_id]
