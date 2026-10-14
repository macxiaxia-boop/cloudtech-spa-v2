"""V4 in-process replay-safety regressions (not a distributed DB guarantee)."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from workflows.v4 import V4Orchestrator, IdempotencyStore, RunStatus, RunStatusError
from workflows.v4.orchestrator import NodeRunRecord
from workflows.v4.node_kinds import NodeKind

def _orch_with_node():
    orch = V4Orchestrator(IdempotencyStore())
    run = orch.create_run("WP-X", 1, "t1", {}, idempotency_key="node-replay-test")
    orch.transition(run.run_id, RunStatus.INPUT_BOUND)
    orch.transition(run.run_id, RunStatus.READY)
    orch.transition(run.run_id, RunStatus.RUNNING)
    orch.add_node(run.run_id, NodeRunRecord(
        node_id="image1", node_kind=NodeKind.MEDIA_GENERATE,
        operation="image.generate", requires={}, produces={}, input_hash="h1",
    ))
    orch.mark_node_running(run.run_id, "image1")
    return orch, run.run_id

def test_same_node_receipt_replay_charges_once():
    orch, run_id = _orch_with_node()
    def finish():
        return orch.mark_node_done(run_id, "image1", {"asset_id": "a1"},
                                    provider_req_id="provider-r1", provider_name="media",
                                    cost_cents=78, cost_class="METERED_MEDIA")
    finish()
    finish()
    run = orch.get_run(run_id)
    assert run.budget_spent_cents == 78
    assert run.nodes[0].cost_cents == 78

def test_conflicting_node_receipt_rejected():
    orch, run_id = _orch_with_node()
    orch.mark_node_done(run_id, "image1", {"asset_id": "a1"},
                        provider_req_id="req1", provider_name="media",
                        cost_cents=50)
    with pytest.raises(RunStatusError):
        orch.mark_node_done(run_id, "image1", {"asset_id": "a2"},
                            provider_req_id="req2", provider_name="media",
                            cost_cents=90)
    assert orch.get_run(run_id).budget_spent_cents == 50

def test_completed_node_cannot_reopen_or_fail():
    orch, run_id = _orch_with_node()
    orch.mark_node_done(run_id, "image1", {"asset_id": "a1"}, cost_cents=10)
    with pytest.raises(RunStatusError):
        orch.mark_node_running(run_id, "image1")
    with pytest.raises(RunStatusError):
        orch.mark_node_failed(run_id, "image1", "ERROR", "late callback")
    assert orch.get_run(run_id).budget_spent_cents == 10

def test_negative_cost_rejected_before_mutation():
    orch, run_id = _orch_with_node()
    with pytest.raises(RunStatusError):
        orch.mark_node_done(run_id, "image1", {"asset_id": "a1"}, cost_cents=-1)
    assert orch.get_run(run_id).budget_spent_cents == 0

def test_concurrent_run_create_same_nonce_single_run():
    orch = V4Orchestrator(IdempotencyStore())
    def create(_):
        return orch.create_run("WP-X", 1, "tenant-1",
                               {"source": "x"}, idempotency_key="same-key").run_id
    with ThreadPoolExecutor(max_workers=16) as pool:
        ids = list(pool.map(create, range(100)))
    assert len(set(ids)) == 1
    assert len(orch.list_runs()) == 1


def test_get_run_returns_nested_copy():
    orch, run_id = _orch_with_node()
    snapshot = orch.get_run(run_id)
    snapshot.input_bindings["local"] = 1
    snapshot.nodes[0].requires["local"] = {"nested": [1]}
    snapshot.nodes[0].status = RunStatus.COMPLETED
    actual = orch.get_run(run_id)
    assert "local" not in actual.input_bindings
    assert "local" not in actual.nodes[0].requires
    assert actual.nodes[0].status == RunStatus.RUNNING


def test_list_runs_returns_nested_copy():
    orch, run_id = _orch_with_node()
    snapshot = orch.list_runs(tenant_id="t1")[0]
    snapshot.nodes[0].requires["local"] = 1
    snapshot.input_bindings["local"] = 1
    actual = orch.get_run(run_id)
    assert "local" not in actual.nodes[0].requires
    assert "local" not in actual.input_bindings
