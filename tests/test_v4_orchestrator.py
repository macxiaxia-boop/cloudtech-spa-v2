"""V4 orchestrator 测试"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workflows.v4 import V4Orchestrator, RunStatus, RunStatusError, IdempotencyStore
from workflows.v4.orchestrator import NodeRunRecord
from workflows.v4.node_kinds import NodeKind


def test_create_run_basic():
    orch = V4Orchestrator(IdempotencyStore())
    rec = orch.create_run(
        path_id="WP-BLOGGER-RESEARCH",
        path_revision=1,
        tenant_id="t1",
        input_bindings={"homepage_url": "https://example.com/u1"},
    )
    assert rec.run_id.startswith("wpr_")
    assert rec.status == RunStatus.PLANNED
    print(f"[OK] create_run_basic → run_id={rec.run_id}")


def test_idempotency_same_key_same_run():
    orch = V4Orchestrator(IdempotencyStore())
    idem_key = "idem_test_001"
    r1 = orch.create_run(path_id="WP-X", path_revision=1, tenant_id="t1", input_bindings={}, idempotency_key=idem_key)
    r2 = orch.create_run(path_id="WP-X", path_revision=1, tenant_id="t1", input_bindings={}, idempotency_key=idem_key)
    assert r1.run_id == r2.run_id, "幂等键必须返回同一 run_id, 禁止重复收费"
    print(f"[OK] idempotency same_key same_run → {r1.run_id}")


def test_state_machine_legal_transitions():
    orch = V4Orchestrator(IdempotencyStore())
    rec = orch.create_run(path_id="WP-X", path_revision=1, tenant_id="t1", input_bindings={})
    orch.transition(rec.run_id, RunStatus.INPUT_BOUND)
    orch.transition(rec.run_id, RunStatus.READY)
    orch.transition(rec.run_id, RunStatus.RUNNING)
    orch.transition(rec.run_id, RunStatus.COMPLETED)
    final = orch.get_run(rec.run_id)
    assert final.status == RunStatus.COMPLETED
    print(f"[OK] legal_transitions → {final.status.value}")


def test_state_machine_illegal_transition():
    orch = V4Orchestrator(IdempotencyStore())
    rec = orch.create_run(path_id="WP-X", path_revision=1, tenant_id="t1", input_bindings={})
    try:
        orch.transition(rec.run_id, RunStatus.COMPLETED)
        assert False, "应拒绝 PLANNED → COMPLETED"
    except RunStatusError as e:
        print(f"[OK] illegal_transition_blocked → {e}")


def test_node_lifecycle():
    orch = V4Orchestrator(IdempotencyStore())
    rec = orch.create_run(path_id="WP-X", path_revision=1, tenant_id="t1", input_bindings={})
    orch.transition(rec.run_id, RunStatus.INPUT_BOUND)
    orch.transition(rec.run_id, RunStatus.READY)
    orch.transition(rec.run_id, RunStatus.RUNNING)
    node = NodeRunRecord(
        node_id="n1",
        node_kind=NodeKind.MEDIA_GENERATE,
        operation="image.generate",
        requires={},
        produces={},
        input_hash="h1",
    )
    orch.add_node(rec.run_id, node)
    orch.mark_node_running(rec.run_id, "n1")
    orch.mark_node_done(rec.run_id, "n1", output_ref={"url": "x"}, provider_req_id="p1", provider_name="yihook", cost_cents=100, cost_class="METERED_MEDIA")
    final = orch.get_run(rec.run_id)
    assert final.budget_spent_cents == 100
    print(f"[OK] node_lifecycle → budget={final.budget_spent_cents}c")


def test_blocked_budget_branch():
    orch = V4Orchestrator(IdempotencyStore())
    rec = orch.create_run(path_id="WP-X", path_revision=1, tenant_id="t1", input_bindings={}, budget_cap_cents=100)
    orch.transition(rec.run_id, RunStatus.INPUT_BOUND)
    orch.transition(rec.run_id, RunStatus.READY)
    orch.transition(rec.run_id, RunStatus.BLOCKED_BUDGET)
    final = orch.get_run(rec.run_id)
    assert final.status == RunStatus.BLOCKED_BUDGET
    print(f"[OK] blocked_budget → {final.status.value}")


if __name__ == "__main__":
    test_create_run_basic()
    test_idempotency_same_key_same_run()
    test_state_machine_legal_transitions()
    test_state_machine_illegal_transition()
    test_node_lifecycle()
    test_blocked_budget_branch()
    print("\n=== ALL ORCHESTRATOR TESTS PASSED ===")
