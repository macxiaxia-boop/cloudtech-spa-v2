"""V4 persistence hook must fail closed; not a durable DB transaction."""
import pytest

from workflows.v4 import IdempotencyStore, RunStatus, RunStatusError, V4Orchestrator


def _ready_run():
    orch = V4Orchestrator(IdempotencyStore())
    run = orch.create_run("WP-X", 1, "tenant-1", {"asset": {"ids": ["a1"]}})
    orch.transition(run.run_id, RunStatus.INPUT_BOUND)
    orch.transition(run.run_id, RunStatus.READY)
    return orch, run.run_id


def test_failed_persistence_rejects_transition_without_mutating_run():
    orch, run_id = _ready_run()
    before = orch.get_run(run_id)
    seen = []

    def broken_persistence(candidate):
        seen.append(candidate.status)
        candidate.input_bindings["asset"]["ids"].append("tampered")
        raise OSError("simulated storage unavailable")

    orch.bind_persistence(broken_persistence)
    with pytest.raises(RunStatusError, match="V4-009"):
        orch.transition(run_id, RunStatus.RUNNING)

    after = orch.get_run(run_id)
    assert seen == [RunStatus.RUNNING]
    assert after.status == RunStatus.READY
    assert after.updated_at == before.updated_at
    assert after.input_bindings == before.input_bindings

    # A later successful persistence attempt may retry the same transition.
    orch.bind_persistence(lambda candidate: None)
    assert orch.transition(run_id, RunStatus.RUNNING).status == RunStatus.RUNNING


def test_successful_persistence_receives_detached_candidate():
    orch, run_id = _ready_run()
    snapshots = []

    def persistence(candidate):
        snapshots.append((candidate.status, candidate.updated_at))
        candidate.input_bindings["asset"]["ids"].append("not-allowed")
        candidate.status = RunStatus.FAILED

    orch.bind_persistence(persistence)
    result = orch.transition(run_id, RunStatus.RUNNING)
    actual = orch.get_run(run_id)
    assert snapshots == [(RunStatus.RUNNING, actual.updated_at)]
    assert result.status == RunStatus.RUNNING
    assert actual.status == RunStatus.RUNNING
    assert actual.input_bindings == {"asset": {"ids": ["a1"]}}
