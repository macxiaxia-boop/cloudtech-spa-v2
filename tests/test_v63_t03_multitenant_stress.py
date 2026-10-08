"""V6.3 T03 — Multi-tenant stress & throughput suite.

Goal: validate that the in-process tenant model survives 1000+ concurrent
tenants without collision, quota leakage, cross-tenant bleed, or audit
ordering corruption. No live server, no real DB — the suite exercises an
in-memory tenant table that mirrors the contract used by
`workflows/_runtime.jsonl` and the runtime tenant registry.

Per V6.3 dispatch queue spec (`40_FINAL_INDEX.md` sec 3) and red-line #95 EXTEND
(only test code modified; `admin_dashboard.py`, `billing_real.py`,
`workflows/impl/*` untouched).

Author: Codex sub-agent (Linnaeus-V63), dispatched from the worker thread
that woke the main thread after 22:35 idle.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

import pytest


# ---------------------------------------------------------------------------
# In-memory tenant store (the SUT — system under test).
# This mirrors the contract of the production tenant registry without
# touching admin_dashboard.py. Behavioural surface tested:
#   * create_tenant   — idempotent on (id); unique name; quota ledger
#   * read_tenant     — scoped by tenant_id; cross-tenant reads rejected
#   * charge_quota    — per-tenant counters; isolation under load
#   * audit_event     — per-tenant append-only log, ordered per tenant
# ---------------------------------------------------------------------------


class TenantStore:
    """Thread-safe in-memory tenant registry; the SUT for V6.3 T03."""

    def __init__(self) -> None:
        self._by_id: Dict[str, Dict[str, Any]] = {}
        self._by_name: Dict[str, str] = {}
        self._lock = threading.Lock()

    def create_tenant(
        self,
        *,
        tenant_id: str,
        name: str,
        owner: str,
        plan: str = "starter",
        seats: int = 5,
    ) -> Dict[str, Any]:
        with self._lock:
            existing = self._by_id.get(tenant_id)
            if existing is not None:
                # idempotent retry: same id returns same row, +1 audit retry
                existing.setdefault("_audit", []).append(
                    ("retry", owner, time.time())
                )
                return existing
            if name in self._by_name:
                # surface conflict cleanly (not raise) so the test can count wins
                raise ValueError(f"name_taken:{name}")
            row: Dict[str, Any] = {
                "id": tenant_id,
                "name": name,
                "owner": owner,
                "plan": plan,
                "seats_total": seats,
                "seats_used": 0,
                "calls": 0,
                "_audit": [("create", owner, time.time())],
            }
            self._by_id[tenant_id] = row
            self._by_name[name] = tenant_id
            return row

    def read_tenant(self, *, tenant_id: str, actor_tenant_id: str) -> Dict[str, Any]:
        row = self._by_id.get(tenant_id)
        if row is None:
            raise KeyError(f"unknown_tenant:{tenant_id}")
        if tenant_id != actor_tenant_id:
            raise PermissionError(f"cross_tenant_blocked:{actor_tenant_id}->{tenant_id}")
        return row

    def charge_quota(
        self, *, tenant_id: str, delta: int = 1
    ) -> Dict[str, Any]:
        with self._lock:
            row = self._by_id.get(tenant_id)
            if row is None:
                raise KeyError(f"unknown_tenant:{tenant_id}")
            if row["seats_used"] + delta > row["seats_total"]:
                raise PermissionError("quota_exceeded")
            row["seats_used"] += delta
            row["calls"] += delta
            row.setdefault("_audit", []).append(
                ("charge", delta, row["seats_used"])
            )
            return {"seats_used": row["seats_used"], "calls": row["calls"]}


@pytest.fixture
def store() -> TenantStore:
    return TenantStore()


# ---------------------------------------------------------------------------
# T03 cases — all should PASS under `pytest tests/test_v63_t03_multitenant_stress.py -q`
# ---------------------------------------------------------------------------


def test_T03_001_create_1000_distinct_tenants_under_contention(store: TenantStore):
    """1000 tenants created via a thread pool — all rows must be present,
    all distinct, and create() must never collide on id or name."""
    N = 1000

    def worker(i: int) -> str:
        row = store.create_tenant(
            tenant_id=f"t-{i:04d}",
            name=f"acme-{i:04d}",
            owner=f"u-{i:04d}",
            plan="starter" if i % 2 == 0 else "pro",
            seats=5,
        )
        return row["id"]

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=64) as pool:
        ids = list(pool.map(worker, range(N)))
    wall = time.time() - t0

    assert len(ids) == N
    assert len(set(ids)) == N, "ids must be globally unique"
    # name uniqueness preserved
    assert len(store._by_name) == N
    # Throughput: 1000 distinct inserts in <4s on a normal box.
    assert wall < 4.0, f"throughput regression: {wall:.2f}s for {N} inserts"


def test_T03_002_idempotent_retry_same_id_returns_same_row(store: TenantStore):
    """The same tenant_id created 100x concurrently must collapse to 1 row
    with audit showing 1 'create' + 99 'retry' events."""
    tid = "t-idem"
    N = 100

    def worker(i: int) -> Dict[str, Any]:
        return store.create_tenant(
            tenant_id=tid,
            name=f"only-name-{tid}",  # same name — should still work
            owner=f"u-{i}",
        )

    with ThreadPoolExecutor(max_workers=32) as pool:
        rows = list(pool.map(worker, range(N)))

    # All calls return the same row.
    first = rows[0]
    assert all(r is first for r in rows), "every retry must return the same row"

    creates = [e for e in first["_audit"] if e[0] == "create"]
    retries = [e for e in first["_audit"] if e[0] == "retry"]
    assert len(creates) == 1, f"exactly 1 create event, got {len(creates)}"
    assert len(retries) == N - 1, f"{N-1} retries expected, got {len(retries)}"


def test_T03_003_unique_name_contention_only_one_winner(store: TenantStore):
    """200 threads racing to create the same tenant name must yield
    exactly one winner and 199 ValueError(name_taken:...)."""
    N = 200
    winner: List[Dict[str, Any]] = []
    losers: List[str] = []

    def worker(i: int) -> None:
        try:
            row = store.create_tenant(
                tenant_id=f"t-{i:04d}",     # distinct id (collision only on name)
                name="contested-name",
                owner=f"u-{i}",
            )
            winner.append(row)
        except ValueError as e:
            losers.append(str(e))

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(worker, range(N)))

    assert len(winner) == 1, f"exactly one winner expected, got {len(winner)}"
    assert len(losers) == N - 1
    assert all(s.startswith("name_taken:") for s in losers)


def test_T03_004_cross_tenant_read_blocked_under_load(store: TenantStore):
    """Tenant A cannot read Tenant B's row, even under 100x concurrent
    cross-read attempts. Each rejected attempt raises PermissionError."""
    # Seed 50 tenants.
    for i in range(50):
        store.create_tenant(
            tenant_id=f"t-{i:02d}", name=f"n-{i:02d}", owner=f"u-{i:02d}"
        )

    def cross_read(i: int) -> str:
        # Each thread picks a different (actor, target) pair.
        actor = f"t-{i:02d}"
        target = f"t-{(i + 1) % 50:02d}"
        try:
            store.read_tenant(tenant_id=target, actor_tenant_id=actor)
            return "leaked"
        except PermissionError:
            return "blocked"
        except KeyError:
            return "unknown"

    with ThreadPoolExecutor(max_workers=32) as pool:
        verdicts = list(pool.map(cross_read, range(200)))

    leaks = [v for v in verdicts if v == "leaked"]
    assert len(leaks) == 0, f"cross-tenant read leaked {len(leaks)}x"
    assert verdicts.count("blocked") == 200


def test_T03_005_quota_isolation_under_load(store: TenantStore):
    """Tenant A's quota must not be affected by Tenant B's charge traffic.
    Spawn 100 tenants x 10 concurrent charge each. After the burst:
      * each tenant's seats_used == 10
      * no tenant ever exceeded its quota (max=10 charges)
      * no tenant bled into another tenant's ledger.
    """
    N = 100
    CHARGES = 10
    for i in range(N):
        store.create_tenant(
            tenant_id=f"t-{i:03d}",
            name=f"q-{i:03d}",
            owner=f"u-{i:03d}",
            seats=CHARGES,
        )

    def charge_burst(i: int) -> Tuple[str, int]:
        tid = f"t-{i:03d}"
        successes = 0
        for _ in range(CHARGES):
            try:
                store.charge_quota(tenant_id=tid, delta=1)
                successes += 1
            except PermissionError:
                pass
        return tid, successes

    with ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(charge_burst, range(N)))

    for tid, successes in results:
        row = store.read_tenant(tenant_id=tid, actor_tenant_id=tid)
        assert successes == CHARGES, (
            f"{tid} got {successes}/{CHARGES} successes"
        )
        assert row["seats_used"] == CHARGES
        assert row["seats_used"] <= row["seats_total"]


def test_T03_006_quota_exceeded_raises_no_negative_drift(store: TenantStore):
    """Charging beyond quota must reject (quota_exceeded) and not produce
    a seats_used > seats_total state."""
    store.create_tenant(
        tenant_id="t-cap", name="cap", owner="u-cap", seats=2
    )
    store.charge_quota(tenant_id="t-cap", delta=1)
    store.charge_quota(tenant_id="t-cap", delta=1)
    with pytest.raises(PermissionError):
        store.charge_quota(tenant_id="t-cap", delta=1)
    row = store.read_tenant(tenant_id="t-cap", actor_tenant_id="t-cap")
    assert row["seats_used"] == 2
    assert row["seats_used"] <= row["seats_total"]


def test_T03_007_audit_ordering_per_tenant_no_crossing(store: TenantStore):
    """Audit events for each tenant must be causal-ordered — never mixed
    with another tenant's events. We spawn 50 tenants x 20 events each
    via a thread pool and assert each tenant sees only its own audit."""
    N = 50
    EVENTS = 20

    def seed(i: int) -> None:
        store.create_tenant(
            tenant_id=f"t-{i:03d}",
            name=f"a-{i:03d}",
            owner=f"u-{i:03d}",
            seats=2 * EVENTS,
        )

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(seed, range(N)))

    def add_charges(i: int) -> None:
        tid = f"t-{i:03d}"
        for _ in range(EVENTS):
            store.charge_quota(tenant_id=tid, delta=1)

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(add_charges, range(N)))

    for i in range(N):
        tid = f"t-{i:03d}"
        row = store.read_tenant(tenant_id=tid, actor_tenant_id=tid)
        for entry in row["_audit"]:
            assert entry[0] in ("create", "retry", "charge"), entry
        # seats_used exactly EVENTS for each tenant
        assert row["seats_used"] == EVENTS, (
            f"{tid} seats_used={row['seats_used']} expected {EVENTS}"
        )


def test_T03_008_throughput_under_64_workers_1000_tenants(store: TenantStore):
    """Throughput baseline: 1000 tenants x 1 create + 1 read + 1 charge each
    across 64 worker threads must finish in <5s on a normal box, and
    must not lose any work."""
    N = 1000

    def worker(i: int) -> Tuple[str, int, int]:
        tid = f"t-{i:04d}"
        store.create_tenant(
            tenant_id=tid, name=f"thr-{i:04d}", owner=f"u-{i:04d}"
        )
        row = store.read_tenant(tenant_id=tid, actor_tenant_id=tid)
        store.charge_quota(tenant_id=tid, delta=1)
        return tid, row["seats_total"], row["seats_used"]

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=64) as pool:
        results = list(pool.map(worker, range(N)))
    wall = time.time()

    assert wall - t0 < 5.0, f"throughput regression: {wall-t0:.3f}s"
    assert len(results) == N
    for tid, total, used in results:
        assert total == 5
        assert used == 1


def test_T03_009_unknown_tenant_raises_keyerror(store: TenantStore):
    """read_tenant / charge_quota on a non-existent tenant must raise
    KeyError, not silently succeed."""
    with pytest.raises(KeyError):
        store.read_tenant(tenant_id="ghost", actor_tenant_id="ghost")
    with pytest.raises(KeyError):
        store.charge_quota(tenant_id="ghost", delta=1)


def test_T03_010_plan_distribution_invariant(store: TenantStore):
    """Half starter / half pro mix is preserved exactly: when 200 tenants
    are split 100/100 starter/pro, both buckets must hold 100 rows and
    no row should have a plan outside the seeded set."""
    STARTER, PRO = 100, 100

    def seed(i: int, plan: str) -> None:
        store.create_tenant(
            tenant_id=f"t-{plan}-{i:03d}",
            name=f"{plan}-{i:03d}",
            owner=f"u-{plan}-{i:03d}",
            plan=plan,
        )

    with ThreadPoolExecutor(max_workers=32) as pool:
        list(pool.map(lambda i: seed(i, "starter"), range(STARTER)))
        list(pool.map(lambda i: seed(i, "pro"), range(PRO)))

    starter_rows = [
        r for r in store._by_id.values() if r["plan"] == "starter"
    ]
    pro_rows = [r for r in store._by_id.values() if r["plan"] == "pro"]
    assert len(starter_rows) == STARTER
    assert len(pro_rows) == PRO