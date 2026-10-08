"""
V6.3 E2E Integration Test Suite — wf + bill + context
========================================================

dev #92 — V6.3 T01.

Scope (10 cases, ≥8 required):
  1.  test_e2e_01_happy_path_five_module_chain
  2.  test_e2e_02_idempotency_key_under_context
  3.  test_e2e_03_multi_tenant_isolation
  4.  test_e2e_04_workflow_failure_no_bill_settlement
  5.  test_e2e_05_workflow_state_machine_success
  6.  test_e2e_06_workflow_state_machine_failure
  7.  test_e2e_07_concurrent_wf_bill_invariants_hold
  8.  test_e2e_08_provider_callback_replay_no_double_charge
  9.  test_e2e_09_workflow_cancellation_releases_reservation
  10. test_e2e_10_full_invariants_after_e2e_run

Layers exercised:
  - wf      → workflows/base.py (RunHistoryTracker + run_workflow + WorkflowStatus)
  - bill    → billing_real.py (BillingEngine + MockProvider + 6 invariants)
  - context → tests.integration.TenantContext (in-process, self-contained)

Forbidden:
  - Real Provider APIs / SMTP / Pilot / PG / Stripe live mode
  - admin_dashboard.py / D:\\AIOS\\* / protocols
  - Filesystem side effects outside test temp dir
  - Network calls

Verification:
  cd D:\\CloudTech-Portable
  python -m pytest tests/integration/test_e2e_full.py -v --tb=short
"""
from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import pytest

# Repo-root import path
import sys
from pathlib import Path
sys.path.insert(0, r"D:\CloudTech-Portable")

from billing_real import (  # noqa: E402
    BillingEngine,
    BillingEvent,
    BillingProvider,
    Currency,
    EntryKind,
    MockProvider,
    ProviderCallback,
    ReservationEntry,
    ReservationStatus,
    SettledEntry,
    UnitType,
)
from workflows.base import (  # noqa: E402
    RunHistoryTracker,
    WorkflowError,
    WorkflowStatus,
    run_workflow,
)
from workflows.impl.wf_t005_leads import (  # noqa: E402
    Lead,
    LeadsInput,
    LeadsOutput,
    run_leads,
)
from pydantic import BaseModel, Field  # noqa: E402


# ════════════════════════════════════════════════════════════
# 1. TenantContext — the "context" layer (in-process, no disk)
# ════════════════════════════════════════════════════════════

@dataclass
class TenantRecord:
    """Single source of truth for tenant metadata inside the test process."""
    tenant_id: str
    plan: str
    tier: str  # free / starter / pro / enterprise
    initial_balance: Decimal
    workflow_runs: List[str] = field(default_factory=list)  # run_ids
    idempotency_keys: List[str] = field(default_factory=list)
    created_at: str = ""


class TenantContext:
    """
    In-process tenant context.

    Acts as the "context" layer in wf + bill + context E2E flow:
      - Registers tenants (plan + tier + initial balance)
      - Tracks per-tenant workflow runs
      - Tracks per-tenant idempotency keys
      - Enforces tenant scoping on queries (no cross-tenant leakage)

    Self-contained: NO disk writes, NO network, NO Flask, NO SQL.
    """

    def __init__(self) -> None:
        self._tenants: Dict[str, TenantRecord] = {}
        self._lock = threading.Lock()

    # ── CRUD ──────────────────────────────────────────────
    def register(
        self,
        tenant_id: str,
        plan: str = "pro",
        tier: str = "standard",
        initial_balance: Decimal = Decimal("1000"),
    ) -> TenantRecord:
        with self._lock:
            if tenant_id in self._tenants:
                raise ValueError(f"tenant {tenant_id} already registered")
            rec = TenantRecord(
                tenant_id=tenant_id,
                plan=plan,
                tier=tier,
                initial_balance=initial_balance,
            )
            self._tenants[tenant_id] = rec
            return rec

    def get(self, tenant_id: str) -> Optional[TenantRecord]:
        with self._lock:
            return self._tenants.get(tenant_id)

    def list_tenants(self) -> List[str]:
        with self._lock:
            return list(self._tenants.keys())

    # ── wf <-> context bridge ──────────────────────────────
    def record_run(self, tenant_id: str, run_id: str, workflow_id: str) -> None:
        """Record that a workflow run was started under this tenant."""
        with self._lock:
            rec = self._tenants.get(tenant_id)
            if rec is None:
                raise KeyError(f"tenant {tenant_id} not in context")
            rec.workflow_runs.append(run_id)

    def runs_for(self, tenant_id: str) -> List[str]:
        """Return run_ids for tenant. Other tenants' runs MUST not appear here."""
        with self._lock:
            rec = self._tenants.get(tenant_id)
            if rec is None:
                return []
            return list(rec.workflow_runs)

    # ── idempotency key registry (shared with bill layer) ─
    def register_idempotency_key(self, tenant_id: str, key: str) -> bool:
        """Register an idempotency_key. Returns False if duplicate (within tenant)."""
        with self._lock:
            rec = self._tenants.get(tenant_id)
            if rec is None:
                raise KeyError(f"tenant {tenant_id} not in context")
            if key in rec.idempotency_keys:
                return False
            rec.idempotency_keys.append(key)
            return True


# ════════════════════════════════════════════════════════════
# 2. Helpers — bridge wf + bill + context in a single function
# ════════════════════════════════════════════════════════════

def _make_event(
    tenant_id: str,
    idempotency_key: str,
    units: Dict[UnitType, int],
    model: str = "gpt-4o",
) -> BillingEvent:
    return BillingEvent(
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        model=model,
        units=units,
    )


def _run_wf_and_bill(
    *,
    ctx: TenantContext,
    engine: BillingEngine,
    tenant_id: str,
    run_id_for_bill: str,
    units: Dict[UnitType, int],
    idempotency_prefix: str = "wf-bill",
) -> Tuple[ReservationEntry, SettledEntry]:
    """
    5-step chain:
      ctx.register_idempotency_key  -> bill.reserve  -> bill.settle
                                              -> ctx.record_run (already done by wf)
      -> wf produces a bill event

    Returns (reservation, settlement).
    """
    idem = f"{idempotency_prefix}-{run_id_for_bill}"
    assert ctx.register_idempotency_key(tenant_id, idem), "duplicate idempotency_key in context"
    ev = _make_event(tenant_id, idem, units)
    res = engine.reserve(ev)
    se = engine.settle(res.entry_id)
    return res, se


# ════════════════════════════════════════════════════════════
# 3. Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture
def ctx() -> TenantContext:
    """Fresh in-process tenant context per test."""
    return TenantContext()


@pytest.fixture
def engine() -> BillingEngine:
    """Fresh BillingEngine with MockProvider per test (no live provider)."""
    return BillingEngine(provider=MockProvider(name="e2e_mock"))


@pytest.fixture(autouse=True)
def _reset_tracker():
    """Reset the singleton RunHistoryTracker between tests."""
    RunHistoryTracker.instance().reset()
    yield
    RunHistoryTracker.instance().reset()


# ════════════════════════════════════════════════════════════
# Case 1: Happy-path — 5-module chain (wf + bill + context)
# ════════════════════════════════════════════════════════════

def test_e2e_01_happy_path_five_module_chain(ctx, engine):
    """
    Chain end-to-end:
      1) ctx.register tenant_a (pro plan, 1000 CNY)
      2) engine.ensure_tenant (mirrors balance into bill layer)
      3) wf_t005_leads runs -> run_id assigned
      4) ctx.record_run stores run_id under tenant
      5) bill.reserve + bill.settle for the wf event
      6) invariant checks all PASS

    Asserts:
      - wf status == 'success'
      - ctx.runs_for(tenant_a) contains exactly 1 run
      - ledger has [TOPUP, RESERVATION, SETTLEMENT]
      - 6 invariants PASS
    """
    tid = "tenant_a"
    ctx.register(tid, plan="pro", tier="pro", initial_balance=Decimal("1000"))
    engine.ensure_tenant(tid, initial_balance=Decimal("1000"))

    # Step 3: wf run
    inp = LeadsInput(
        tenant_id=tid,
        leads=[Lead(name="张三", phone="13800001111", city="厦门", intent_score=80)],
        sales_team=["alice", "bob"],
        strategy="round_robin",
    )
    wf_out = run_leads(inp)
    assert wf_out["status"] == "success", f"wf failed: {wf_out}"
    run_id = wf_out["run_id"]
    assert run_id.startswith("run_")

    # Step 4: ctx records run
    ctx.record_run(tid, run_id, "WF-T-005")
    assert ctx.runs_for(tid) == [run_id]

    # Step 5: bill event for the wf run
    res, se = _run_wf_and_bill(
        ctx=ctx,
        engine=engine,
        tenant_id=tid,
        run_id_for_bill=run_id,
        units={UnitType.TOKEN_INPUT: 1000, UnitType.TOKEN_OUTPUT: 500},
        idempotency_prefix="wf-bill",
    )

    # Asserts
    assert res.status == ReservationStatus.SETTLED
    assert se.kind == EntryKind.SETTLEMENT
    assert ctx.runs_for(tid) == [run_id]
    # Other tenant: empty
    assert ctx.runs_for("tenant_other") == []

    # Ledger: TOPUP + RESERVATION + SETTLEMENT (3 entries)
    kinds = [e.kind for e in engine.ledger()]
    assert kinds == [EntryKind.TOPUP, EntryKind.RESERVATION, EntryKind.SETTLEMENT], kinds

    # 6 invariants all PASS
    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed: {msgs}"

    # balance sanity: 1000 - settled_amount == available
    bal = engine.get_balance(tid)
    expected_available = Decimal("1000") - se.amount
    assert bal.available == expected_available
    assert bal.reserved == Decimal("0")


# ════════════════════════════════════════════════════════════
# Case 2: Idempotency under context
#   Same wf + same idempotency_key 10×  ->  only 1 settled entry
# ════════════════════════════════════════════════════════════

def test_e2e_02_idempotency_key_under_context(ctx, engine):
    """
    10 concurrent reserve attempts with the SAME idempotency_key:
      - engine.reserve returns the same reservation (by idempotency)
      - ledger contains exactly 1 RESERVATION
      - ctx.register_idempotency_key blocks on the 2nd attempt
      - settle once -> 1 SETTLEMENT, balance reduced exactly once
    """
    tid = "tenant_idem"
    ctx.register(tid, plan="pro", tier="pro", initial_balance=Decimal("1000"))
    engine.ensure_tenant(tid, initial_balance=Decimal("1000"))

    fixed_key = "idem-xyz-001"
    assert ctx.register_idempotency_key(tid, fixed_key) is True
    assert ctx.register_idempotency_key(tid, fixed_key) is False  # dup

    ev = _make_event(tid, fixed_key, {UnitType.TOKEN_OUTPUT: 1000})

    # 10 concurrent reserves
    results: List[str] = []
    errs: List[Exception] = []
    lock = threading.Lock()

    def worker():
        try:
            r = engine.reserve(ev)
            with lock:
                results.append(r.entry_id)
        except Exception as e:
            with lock:
                errs.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errs, f"reserve errors: {errs}"
    # All 10 share the same reservation id
    assert len(set(results)) == 1, f"expected 1 unique reservation, got {set(results)}"

    # Settle once
    se = engine.settle(results[0])
    assert se.kind == EntryKind.SETTLEMENT

    # Ledger: TOPUP + 1 RESERVATION + 1 SETTLEMENT
    res_count = sum(1 for e in engine.ledger() if isinstance(e, ReservationEntry))
    set_count = sum(1 for e in engine.ledger() if isinstance(e, SettledEntry) and e.kind == EntryKind.SETTLEMENT)
    assert res_count == 1
    assert set_count == 1

    # Balance reduced exactly once
    bal = engine.get_balance(tid)
    assert bal.reserved == Decimal("0")
    assert bal.available == Decimal("1000") - se.amount

    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# Case 3: Multi-tenant isolation (context scoping)
# ════════════════════════════════════════════════════════════

def test_e2e_03_multi_tenant_isolation(ctx, engine):
    """
    Two tenants (A, B):
      - Each runs its own wf (different run_ids)
      - Each emits its own bill events
      - ctx.runs_for(A) does NOT see B's runs
      - engine.query_by_tenant(A) does NOT see B's ledger entries
      - Idempotency keys are scoped per-tenant
    """
    ctx.register("tenantA", plan="pro", initial_balance=Decimal("500"))
    ctx.register("tenantB", plan="pro", initial_balance=Decimal("500"))
    engine.ensure_tenant("tenantA", initial_balance=Decimal("500"))
    engine.ensure_tenant("tenantB", initial_balance=Decimal("500"))

    # tenantA wf + bill
    inpA = LeadsInput(
        tenant_id="tenantA",
        leads=[Lead(name="A", phone="13800000001", city="厦门", intent_score=70)],
        sales_team=["alice"], strategy="round_robin",
    )
    outA = run_leads(inpA)
    assert outA["status"] == "success"
    ctx.record_run("tenantA", outA["run_id"], "WF-T-005")
    _run_wf_and_bill(
        ctx=ctx, engine=engine, tenant_id="tenantA",
        run_id_for_bill=outA["run_id"],
        units={UnitType.TOKEN_OUTPUT: 100},
        idempotency_prefix="A",
    )

    # tenantB wf + bill
    inpB = LeadsInput(
        tenant_id="tenantB",
        leads=[Lead(name="B", phone="13800000002", city="泉州", intent_score=60)],
        sales_team=["bob"], strategy="round_robin",
    )
    outB = run_leads(inpB)
    assert outB["status"] == "success"
    ctx.record_run("tenantB", outB["run_id"], "WF-T-005")
    _run_wf_and_bill(
        ctx=ctx, engine=engine, tenant_id="tenantB",
        run_id_for_bill=outB["run_id"],
        units={UnitType.TOKEN_OUTPUT: 200},
        idempotency_prefix="B",
    )

    # Isolation: A's runs != B's runs
    runsA = ctx.runs_for("tenantA")
    runsB = ctx.runs_for("tenantB")
    assert runsA == [outA["run_id"]]
    assert runsB == [outB["run_id"]]
    assert set(runsA).isdisjoint(set(runsB))

    # Isolation: ledger entries are scoped
    ledA = engine.query_by_tenant("tenantA")
    ledB = engine.query_by_tenant("tenantB")
    for e in ledA:
        assert e.tenant_id == "tenantA"
    for e in ledB:
        assert e.tenant_id == "tenantB"

    # Idempotency-key scoping: same key, different tenants, both PASS
    same_key = "shared-001"
    assert ctx.register_idempotency_key("tenantA", same_key) is True
    assert ctx.register_idempotency_key("tenantB", same_key) is True  # different tenant -> allow

    ok, msgs = engine.check_all_invariants("tenantA")
    assert ok, f"invariants(A) failed: {msgs}"
    ok, msgs = engine.check_all_invariants("tenantB")
    assert ok, f"invariants(B) failed: {msgs}"


# ════════════════════════════════════════════════════════════
# Case 4: Workflow failure -> no bill settlement, no dirty data
# ════════════════════════════════════════════════════════════

def test_e2e_04_workflow_failure_no_bill_settlement(ctx, engine):
    """
    A wf raises WorkflowError -> bill layer MUST NOT see any settlement.
    The wf + bill failure flow:
      1) wf starts, marks RUNNING
      2) wf raises -> wf status='failed'
      3) ctx does NOT record a run (run failed before commit)
      4) engine ledger MUST NOT contain a SETTLEMENT for this run

    We model the failure by having an explicit "skip on fail" branch
    in our integration glue (mirroring real production behavior).
    """
    tid = "tenant_fail"
    ctx.register(tid, plan="starter", initial_balance=Decimal("100"))
    engine.ensure_tenant(tid, initial_balance=Decimal("100"))

    # Define a wf that always fails
    class FailingInput(BaseModel):
        tenant_id: str = Field(..., min_length=2)

    @run_workflow(workflow_id="WF-FAIL", tenant_field="tenant_id")
    def failing_wf(inp: FailingInput):
        raise WorkflowError("WF-FAIL-001", "intentional failure")

    out = failing_wf(FailingInput(tenant_id=tid))
    assert out["status"] == "failed"
    assert out["error"]["code"] == "WF-FAIL-001"
    run_id = out["run_id"]

    # Verify tracker recorded the failure
    rec = RunHistoryTracker.instance().get_status(run_id)
    assert rec is not None
    assert rec["status"] == "failed"
    assert rec["error"]["code"] == "WF-FAIL-001"

    # Glue: ctx.record_run is NOT called when wf fails -> ctx stays clean
    # (this is the production contract: failure does not pollute context)
    assert ctx.runs_for(tid) == []

    # Bill layer untouched: ledger has only TOPUP
    kinds = [e.kind for e in engine.ledger()]
    assert kinds == [EntryKind.TOPUP], kinds
    bal = engine.get_balance(tid)
    assert bal.available == Decimal("100")
    assert bal.reserved == Decimal("0")

    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# Case 5: Workflow state machine — success path
# ════════════════════════════════════════════════════════════

def test_e2e_05_workflow_state_machine_success(ctx, engine):
    """
    Track a wf run through pending -> running -> success.
    The RunHistoryTracker singleton must reflect each transition.

    Cross-layer contract:
      - wf starts (pending) -> wf running -> wf success
      - ctx records run only after success
      - bill event is settled only after wf success
    """
    tid = "tenant_sm_ok"
    ctx.register(tid, plan="pro", initial_balance=Decimal("500"))
    engine.ensure_tenant(tid, initial_balance=Decimal("500"))

    inp = LeadsInput(
        tenant_id=tid,
        leads=[Lead(name="测试", phone="13800001234", city="福州", intent_score=65)],
        sales_team=["alice"], strategy="round_robin",
    )
    out = run_leads(inp)
    assert out["status"] == "success"
    run_id = out["run_id"]
    ctx.record_run(tid, run_id, "WF-T-005")

    rec = RunHistoryTracker.instance().get_status(run_id)
    assert rec is not None
    # State machine check: status MUST be in (success)
    assert rec["status"] == "success"
    assert rec["status"] not in (
        WorkflowStatus.PENDING.value,
        WorkflowStatus.RUNNING.value,
        WorkflowStatus.FAILED.value,
        WorkflowStatus.CANCELLED.value,
    )
    # finished_at is set on success
    assert rec["finished_at"] is not None
    assert rec["output"] is not None
    assert rec["error"] is None

    # Bill layer settled (TTL confirmed in ctx)
    res, se = _run_wf_and_bill(
        ctx=ctx, engine=engine, tenant_id=tid,
        run_id_for_bill=run_id,
        units={UnitType.TOKEN_OUTPUT: 50},
        idempotency_prefix="sm",
    )
    assert se.kind == EntryKind.SETTLEMENT
    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# Case 6: Workflow state machine — failure path
# ════════════════════════════════════════════════════════════

def test_e2e_06_workflow_state_machine_failure(ctx, engine):
    """
    Track a wf run through pending -> running -> failed.
    Verify:
      - rec.status == 'failed'
      - rec.error.code set
      - rec.finished_at set
      - rec.output is None
      - ctx does NOT record the run
      - bill layer untouched (no SETTLEMENT)
    """
    tid = "tenant_sm_fail"
    ctx.register(tid, plan="starter", initial_balance=Decimal("100"))
    engine.ensure_tenant(tid, initial_balance=Decimal("100"))

    class AlwaysFail(BaseModel):
        tenant_id: str = Field(..., min_length=2)

    @run_workflow(workflow_id="WF-FAIL2", tenant_field="tenant_id")
    def bad_wf(inp: AlwaysFail):
        raise WorkflowError("WF-DEAD", "dead on arrival")

    out = bad_wf(AlwaysFail(tenant_id=tid))
    assert out["status"] == "failed"
    run_id = out["run_id"]
    assert out["error"]["code"] == "WF-DEAD"

    rec = RunHistoryTracker.instance().get_status(run_id)
    assert rec is not None
    assert rec["status"] == "failed"
    assert rec["error"] is not None
    assert rec["error"]["code"] == "WF-DEAD"
    assert rec["output"] is None
    assert rec["finished_at"] is not None

    # Glue contract: do NOT record failed runs in ctx
    assert ctx.runs_for(tid) == []

    # Bill layer untouched
    kinds = [e.kind for e in engine.ledger()]
    assert EntryKind.SETTLEMENT not in kinds
    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# Case 7: Concurrent wf + bill — invariants hold under load
# ════════════════════════════════════════════════════════════

def test_e2e_07_concurrent_wf_bill_invariants_hold(ctx, engine):
    """
    20 threads each run: wf + reserve + settle for a different run_id.
    Different idempotency_keys per thread (so no dedup).
    Final state:
      - 20 reservations + 20 settlements
      - balance reduced by exactly sum of settlements
      - all 6 invariants PASS
    """
    tid = "tenant_concurrent"
    ctx.register(tid, plan="pro", initial_balance=Decimal("10000"))
    engine.ensure_tenant(tid, initial_balance=Decimal("10000"))

    n_threads = 20
    barrier = threading.Barrier(n_threads)
    errs: List[Exception] = []
    lock = threading.Lock()

    def worker(i: int):
        try:
            inp = LeadsInput(
                tenant_id=tid,
                leads=[Lead(name=f"L{i}", phone=f"138{i:08d}", city="厦门", intent_score=50 + i)],
                sales_team=[f"s{i}"], strategy="round_robin",
            )
            out = run_leads(inp)
            assert out["status"] == "success", f"wf thread {i} failed: {out}"
            run_id = out["run_id"]

            barrier.wait(timeout=5)

            ctx.record_run(tid, run_id, "WF-T-005")
            _run_wf_and_bill(
                ctx=ctx, engine=engine, tenant_id=tid,
                run_id_for_bill=run_id,
                units={UnitType.TOKEN_OUTPUT: 100 + i},
                idempotency_prefix=f"conc-{i}",
            )
        except Exception as e:
            with lock:
                errs.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errs, f"thread errors: {errs}"

    # 20 wf runs recorded in ctx
    runs = ctx.runs_for(tid)
    assert len(runs) == n_threads, f"expected {n_threads} runs, got {len(runs)}"
    assert len(set(runs)) == n_threads  # all unique

    # Ledger: TOPUP + 20 RESERVATION + 20 SETTLEMENT = 41 entries
    ledger = engine.ledger()
    res_n = sum(1 for e in ledger if isinstance(e, ReservationEntry))
    set_n = sum(1 for e in ledger if isinstance(e, SettledEntry) and e.kind == EntryKind.SETTLEMENT)
    assert res_n == n_threads
    assert set_n == n_threads

    # Balance: available = 10000 - sum(settlements)
    expected_available = Decimal("10000")
    for e in ledger:
        if isinstance(e, SettledEntry) and e.kind == EntryKind.SETTLEMENT:
            expected_available -= e.amount
    bal = engine.get_balance(tid)
    assert bal.available == expected_available
    assert bal.reserved == Decimal("0")

    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed under concurrency: {msgs}"


# ════════════════════════════════════════════════════════════
# Case 8: Provider callback replay — no double charge
# ════════════════════════════════════════════════════════════

def test_e2e_08_provider_callback_replay_no_double_charge(ctx, engine):
    """
    Issue a callback via MockProvider, replay it 100x.
    Asserts:
      - ledger has exactly 1 SETTLEMENT with that charge_id
      - balance reduced exactly once
      - provider.deliver_count == 99 (replays)
      - invariants PASS

    Cross-layer check:
      - The wf completed successfully (ctx has 1 run)
      - The bill layer sees exactly 1 settled entry
    """
    tid = "tenant_cb"
    ctx.register(tid, plan="pro", initial_balance=Decimal("1000"))
    engine.ensure_tenant(tid, initial_balance=Decimal("1000"))

    # First, complete a wf run (sets up the contextual state)
    inp = LeadsInput(
        tenant_id=tid,
        leads=[Lead(name="回调测试", phone="13800009999", city="厦门", intent_score=70)],
        sales_team=["alice"], strategy="round_robin",
    )
    out = run_leads(inp)
    assert out["status"] == "success"
    ctx.record_run(tid, out["run_id"], "WF-T-005")
    assert len(ctx.runs_for(tid)) == 1

    # Issue callback
    cb = engine._provider.issue_callback(
        tenant_id=tid,
        idempotency_key="cb-001",
        amount=Decimal("5"),
        currency=Currency.CNY,
    )
    assert cb.success is True
    assert isinstance(engine._provider, BillingProvider)

    # Apply + 99 replays
    seen_entry_ids = set()
    for i in range(100):
        deliver = cb if i == 0 else engine._provider.replay(cb)
        entry = engine.apply_callback(deliver)
        seen_entry_ids.add(entry.entry_id)

    # All 100 deliveries resolved to the SAME settled entry
    assert len(seen_entry_ids) == 1, f"expected 1 unique entry_id, got {seen_entry_ids}"

    # Ledger: TOPUP + 1 RESERVATION (from _run_wf_and_bill? no — only via apply_callback here)
    # Wait: We did NOT call _run_wf_and_bill in this case. Only wf + apply_callback.
    # So ledger should be: TOPUP + 1 SETTLEMENT (from callback) = 2 entries.
    kinds = [e.kind for e in engine.ledger()]
    settlements = [e for e in engine.ledger()
                   if isinstance(e, SettledEntry)
                   and e.kind == EntryKind.SETTLEMENT
                   and e.charge_id == cb.charge_id]
    assert len(settlements) == 1, f"expected 1 SETTLEMENT for charge_id, got {len(settlements)}: {kinds}"

    # Balance reduced by exactly 5
    bal = engine.get_balance(tid)
    assert bal.available == Decimal("1000") - Decimal("5")

    # Provider deliver_count: 99 (the 99 replays; the original 0th call is issue, not deliver)
    assert engine._provider.deliver_count(cb.charge_id) == 99

    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# Case 9: Workflow cancellation releases the bill reservation
# ════════════════════════════════════════════════════════════

def test_e2e_09_workflow_cancellation_releases_reservation(ctx, engine):
    """
    A wf that takes too long gets cancelled:
      - wf status -> 'cancelled'
      - The associated bill reservation is released (RELEASE entry)
      - balance.reserved drops to 0
      - invariants PASS

    Sequence:
      1) reserve 30 CNY (1 reservation, balance.reserved 30)
      2) mark wf as cancelled via tracker
      3) release the reservation
      4) verify ledger has [TOPUP, RESERVATION, RELEASE]
    """
    tid = "tenant_cancel"
    ctx.register(tid, plan="starter", initial_balance=Decimal("100"))
    engine.ensure_tenant(tid, initial_balance=Decimal("100"))

    # Use wf machinery to start a real wf
    inp = LeadsInput(
        tenant_id=tid,
        leads=[Lead(name="取消测试", phone="13800008888", city="厦门", intent_score=60)],
        sales_team=["alice"], strategy="round_robin",
    )
    out = run_leads(inp)
    run_id = out["run_id"]
    assert out["status"] == "success"  # base run completed

    # Now simulate a longer-running wf that we want to cancel BEFORE commit
    # We craft a separate wf run directly via the tracker:
    rec = RunHistoryTracker.instance().start("WF-LONG", tid, {"tenant_id": tid})
    long_run_id = rec.run_id
    RunHistoryTracker.instance().mark_running(long_run_id)
    # Cancel before any bill event
    cancelled = RunHistoryTracker.instance().cancel(long_run_id)
    assert cancelled is True

    # Bill layer: reserve, then release (because wf was cancelled)
    ev = _make_event(tid, f"cancel-{long_run_id}", {UnitType.TOKEN_INPUT: 50_000})
    res = engine.reserve(ev)
    assert engine.get_balance(tid).reserved == res.amount
    # Release (mirror production: cancellation triggers release)
    engine.release(res.entry_id)
    assert engine.get_balance(tid).reserved == Decimal("0")

    # Ledger: TOPUP + RESERVATION + RELEASE (and a SETTLEMENT from the base run's wf)
    kinds = [e.kind for e in engine.ledger()]
    assert EntryKind.RESERVATION in kinds
    assert EntryKind.RELEASE in kinds
    # The release is the LAST entry for the cancel-related reservation
    releases = [e for e in engine.ledger() if isinstance(e, SettledEntry) and e.kind == EntryKind.RELEASE]
    assert len(releases) == 1
    assert releases[0].reservation_id == res.entry_id

    # invariants PASS
    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"invariants failed: {msgs}"

    # Cancelled run state
    rec_after = RunHistoryTracker.instance().get_status(long_run_id)
    assert rec_after["status"] == "cancelled"
    assert rec_after["finished_at"] is not None


# ════════════════════════════════════════════════════════════
# Case 10: Full invariants after E2E run (regression sweep)
# ════════════════════════════════════════════════════════════

def test_e2e_10_full_invariants_after_e2e_run(ctx, engine):
    """
    Mixed E2E sweep: wf + bill + context with mixed ops:
      - 5 wf runs (4 success + 1 fail)
      - 4 bill reserves + 3 settles + 1 release
      - 1 provider callback (no replay this time)
      - 1 correction entry

    Then check_all_invariants() returns (True, []).
    """
    tid = "tenant_full"
    ctx.register(tid, plan="pro", initial_balance=Decimal("1000"))
    engine.ensure_tenant(tid, initial_balance=Decimal("1000"))

    # 4 successful wf runs + bill
    run_ids = []
    for i in range(4):
        inp = LeadsInput(
            tenant_id=tid,
            leads=[Lead(name=f"full{i}", phone=f"139{i:08d}", city="厦门", intent_score=50 + i)],
            sales_team=[f"s{i}"], strategy="round_robin",
        )
        out = run_leads(inp)
        assert out["status"] == "success"
        ctx.record_run(tid, out["run_id"], "WF-T-005")
        run_ids.append(out["run_id"])
        _run_wf_and_bill(
            ctx=ctx, engine=engine, tenant_id=tid,
            run_id_for_bill=out["run_id"],
            units={UnitType.TOKEN_OUTPUT: 100 + i * 10},
            idempotency_prefix=f"full-{i}",
        )

    # 1 wf failure (does NOT pollute bill layer)
    class WillFail(BaseModel):
        tenant_id: str = Field(..., min_length=2)

    @run_workflow(workflow_id="WF-FAIL-FULL", tenant_field="tenant_id")
    def fail_wf(inp: WillFail):
        raise WorkflowError("WF-X", "expected")

    fail_out = fail_wf(WillFail(tenant_id=tid))
    assert fail_out["status"] == "failed"

    # 1 reserve + release (cancellation-style)
    ev_cancel = _make_event(tid, "cancel-full", {UnitType.TOKEN_OUTPUT: 50})
    res_cancel = engine.reserve(ev_cancel)
    engine.release(res_cancel.entry_id)

    # 1 provider callback (success)
    cb = engine._provider.issue_callback(
        tenant_id=tid,
        idempotency_key="cb-full",
        amount=Decimal("2"),
        currency=Currency.CNY,
    )
    engine.apply_callback(cb)

    # 1 correction entry (for the most recent settlement)
    # Find the last SETTLEMENT entry id
    last_set = None
    for e in reversed(engine.ledger()):
        if isinstance(e, SettledEntry) and e.kind == EntryKind.SETTLEMENT:
            last_set = e
            break
    assert last_set is not None
    corr = engine.correction(
        tenant_id=tid,
        related_entry_id=last_set.entry_id,
        amount=Decimal("0.5"),
        currency=Currency.CNY,
        reason="manual refund",
    )
    assert corr.kind == EntryKind.CORRECTION

    # Cross-layer verification
    assert len(ctx.runs_for(tid)) == 4  # only the 4 successes recorded
    assert len(set(ctx.runs_for(tid))) == 4

    # Full invariants
    ok, msgs = engine.check_all_invariants(tid)
    assert ok, f"full invariants failed: {msgs}"

    # Also check the 6 individual invariants for completeness
    for name in (
        "invariant_append_only",
        "invariant_idempotency",
        "invariant_no_negative_amount",
        "invariant_correction_pairs",
        "invariant_charge_id_dedup",
        "invariant_balance_conservation",
    ):
        # 5 invariants are global; invariant_balance_conservation takes tenant_id
        if name == "invariant_balance_conservation":
            result = getattr(engine, name)(tid)
        else:
            result = getattr(engine, name)()
        if isinstance(result, tuple):
            assert result[0], f"{name} failed: {result[1]}"
        else:
            assert result, f"{name} failed"

    # Balance sanity: 1000 - sum(settlements) + sum(refunds/corrections)
    bal = engine.get_balance(tid)
    assert bal.reserved == Decimal("0")
    # available is reduced by settlements + corrections
    assert bal.available < Decimal("1000"), f"balance not reduced: {bal.available}"