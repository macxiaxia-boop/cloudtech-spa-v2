"""P11: opt-in CloudTech V4 run persistence, restart, and quarantine.

No real media/provider calls. Original V4Orchestrator is exercised directly.
"""
from __future__ import annotations

import pytest

from workflows.v4.durable_snapshots import V4SnapshotStore
from workflows.v4.node_kinds import NodeKind
from workflows.v4.orchestrator import (
    NodeRunRecord,
    RunStatus,
    RunStatusError,
    V4Orchestrator,
)


def _create(o):
    return o.create_run(
        "WP-BLOGGER-RESEARCH", 1, "tenant-A",
        {"homepage_url": "https://example.com/user"},
        idempotency_key="key-1",
        project_id="project-1",
    )


def _node():
    return NodeRunRecord(
        node_id="url_normalize", node_kind=NodeKind.TRANSFORM,
        operation="url.normalize", requires={}, produces={"host": "example.com"},
        input_hash="a" * 64,
    )


def test_created_and_completed_nodes_survive_v4_orchestrator_recreation(tmp_path):
    path = tmp_path / "v4.sqlite3"
    first = V4Orchestrator(durable_store=V4SnapshotStore(path))
    rec = _create(first)
    first.transition(rec.run_id, RunStatus.INPUT_BOUND)
    first.transition(rec.run_id, RunStatus.READY)
    first.add_node(rec.run_id, _node())
    first.mark_node_running(rec.run_id, "url_normalize")
    first.mark_node_done(
        rec.run_id, "url_normalize",
        {"local_result": {"host": "example.com"}},
        cost_cents=0,
    )
    second = V4Orchestrator(durable_store=V4SnapshotStore(path))
    restored = second.get_run(rec.run_id)
    assert restored.status == RunStatus.READY
    assert len(restored.nodes) == 1
    assert restored.nodes[0].status == RunStatus.COMPLETED
    assert restored.nodes[0].output_ref["local_result"]["host"] == "example.com"
    assert restored.nodes[0].input_hash == "a" * 64
    assert _create(second).run_id == rec.run_id
    with pytest.raises(RunStatusError, match="different run parameters"):
        second.create_run(
            "WP-BLOGGER-RESEARCH", 1, "tenant-A",
            {"homepage_url": "https://example.com/DIFFERENT"},
            idempotency_key="key-1", project_id="project-1",
        )


def test_crash_during_inflight_node_quarantines_restart(tmp_path):
    path = tmp_path / "inflight.sqlite3"
    one = V4Orchestrator(durable_store=V4SnapshotStore(path))
    rec = _create(one)
    one.transition(rec.run_id, RunStatus.INPUT_BOUND)
    one.transition(rec.run_id, RunStatus.READY)
    one.add_node(rec.run_id, _node())
    one.transition(rec.run_id, RunStatus.RUNNING)
    one.mark_node_running(rec.run_id, "url_normalize")
    two = V4Orchestrator(durable_store=V4SnapshotStore(path))
    recovered = two.get_run(rec.run_id)
    assert recovered.status == RunStatus.PARTIAL
    assert recovered.error_code == "INTERRUPTED_UNCERTAIN"
    assert recovered.nodes[0].status == RunStatus.PARTIAL
    assert recovered.nodes[0].error_code == "INTERRUPTED_UNCERTAIN"


def test_v4_store_rejects_cross_tenant_run_id_rebinding(tmp_path):
    db = V4SnapshotStore(tmp_path / "tenant.sqlite3")
    original = _create(V4Orchestrator(durable_store=db))
    original.tenant_id = "attacker"
    with pytest.raises(ValueError, match="another tenant"):
        db.save(original)


def test_durable_env_is_opt_in_and_not_rebuilt_when_unset(tmp_path, monkeypatch):
    dbpath = tmp_path / "optional.sqlite3"
    monkeypatch.setenv("CLOUDTECH_V4_SQLITE_PATH", str(dbpath))
    a = V4Orchestrator()
    rid = _create(a).run_id
    b = V4Orchestrator()
    assert b.get_run(rid) is not None
    monkeypatch.delenv("CLOUDTECH_V4_SQLITE_PATH")
    c = V4Orchestrator()
    assert c.get_run(rid) is None
