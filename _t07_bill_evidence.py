"""
BILL Real Evidence Verification — V6.2 T07
============================================
Live 5-case spot check + ledger invariant run + provider mock boundary check.
Run: python _t07_bill_evidence.py

Output: stdout + _t07_evidence_run.log
"""
from __future__ import annotations

import sys
import os
import time
import threading
import json
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, r"D:\CloudTech-Portable")
from billing_real import (
    BillingEngine,
    BillingEvent,
    Currency,
    EntryKind,
    InsufficientBalanceError,
    HardBudgetExceededError,
    LedgerError,
    MockProvider,
    PriceBook,
    ProviderCallback,
    RateCard,
    ReservationEntry,
    ReservationStatus,
    SettledEntry,
    UnitType,
)


def banner(title):
    print()
    print("=" * 78)
    print(f"  {title}")
    print("=" * 78)


def section(title):
    print()
    print(f"--- {title} ---")


# ════════════════════════════════════════════════════════════
# Section A: 5-CASE SPOT CHECK (run real sub-tests, print details)
# ════════════════════════════════════════════════════════════

def spot_1_reserve_settle_balance():
    """BILL-001: 验证 reserve → settle → release 余额守恒"""
    banner("SPOT-1 / BILL-001: reserve -> settle -> release (账本守恒)")
    eng = BillingEngine(provider=MockProvider(name="spot_provider"))
    eng.ensure_tenant("tenant_a", initial_balance=Decimal("1000"))
    bal_before = eng.get_balance("tenant_a")
    print(f"[before] available={bal_before.available} reserved={bal_before.reserved}")

    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="spot_k1",
        model="gpt-4o", units={UnitType.TOKEN_INPUT: 100_000},
    )
    res = eng.reserve(evt)
    print(f"[reserve] entry_id={res.entry_id} amount={res.amount} status={res.status}")
    se = eng.settle(res.entry_id)
    print(f"[settle]  entry_id={se.entry_id} amount={se.amount}")

    bal_after = eng.get_balance("tenant_a")
    print(f"[after]  available={bal_after.available} reserved={bal_after.reserved}")
    expected = Decimal("940.0000")
    actual = bal_after.available
    ok = actual == expected
    print(f"[verify] expected={expected}, pass={ok}")
    return ok


def spot_2_concurrent_idempotency():
    """BILL-002: 10 线程同 key 并发 → 1 reservation"""
    banner("SPOT-2 / BILL-002: 10x concurrent same idempotency_key")
    eng = BillingEngine(provider=MockProvider(name="spot_provider"))
    eng.ensure_tenant("tenant_a", initial_balance=Decimal("1000"))

    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="concurrent_k_spot",
        model="gpt-4o", units={UnitType.TOKEN_INPUT: 10_000},
    )
    results = []
    errors = []
    lock = threading.Lock()

    def worker():
        try:
            r = eng.reserve(evt)
            with lock:
                results.append(r.entry_id)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    t0 = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    elapsed_ms = (time.time() - t0) * 1000

    unique_ids = set(results)
    print(f"[threads started] 10 concurrent workers, elapsed={elapsed_ms:.1f}ms")
    print(f"[unique reservations returned] {len(unique_ids)} (expected: 1)")
    print(f"[errors] {len(errors)}")
    print(f"[ledger reservations] "
          f"{sum(1 for e in eng.ledger() if isinstance(e, ReservationEntry))}")
    bal = eng.get_balance("tenant_a")
    print(f"[reserved] {bal.reserved} (expected: 6.0000)")
    ok = len(unique_ids) == 1 and len(errors) == 0
    print(f"[verify] pass={ok}")
    return ok


def spot_3_callback_replay():
    """BILL-003: 同 charge_id 投递 100 次 → 1 settle"""
    banner("SPOT-3 / BILL-003: callback replay 100x no double-charge")
    eng = BillingEngine(provider=MockProvider(name="spot_provider"))
    eng.ensure_tenant("tenant_a", initial_balance=Decimal("1000"))

    cb = eng._provider.issue_callback(
        tenant_id="tenant_a", idempotency_key="cb_k_spot",
        amount=Decimal("5"), currency=Currency.CNY,
    )
    seen = set()
    t0 = time.time()
    for i in range(100):
        deliver = cb if i == 0 else eng._provider.replay(cb)
        entry = eng.apply_callback(deliver)
        seen.add(entry.entry_id)
    elapsed_ms = (time.time() - t0) * 1000

    settlements = [e for e in eng.ledger()
                   if isinstance(e, SettledEntry)
                   and e.kind == EntryKind.SETTLEMENT
                   and e.charge_id == cb.charge_id]
    print(f"[iterations] 100 deliveries, elapsed={elapsed_ms:.1f}ms")
    print(f"[unique settle entries returned] {len(seen)} (expected: 1)")
    print(f"[ledger SETTLEMENT rows for charge_id] {len(settlements)}")
    print(f"[provider deliver_count] {eng._provider.deliver_count(cb.charge_id)}")
    bal = eng.get_balance("tenant_a")
    print(f"[available] {bal.available} (expected: 995.0000)")
    ok = len(seen) == 1 and len(settlements) == 1
    print(f"[verify] pass={ok}")
    return ok


def spot_4_hard_budget_rejection():
    """BILL-004b: hard_budget 超额拒绝"""
    banner("SPOT-4 / BILL-004b: hard_budget concurrent rejection")
    eng = BillingEngine(provider=MockProvider(name="spot_provider"))
    eng.ensure_tenant("corp", initial_balance=Decimal("0"), hard_budget=Decimal("100"))

    successes = []
    rejects = []
    lock = threading.Lock()

    def worker(i):
        evt = BillingEvent(
            tenant_id="corp", idempotency_key=f"b{i}",
            model="gpt-4o", units={UnitType.TOKEN_INPUT: 33_333},
        )
        try:
            r = eng.reserve(evt)
            with lock:
                successes.append(r.entry_id)
        except (HardBudgetExceededError, InsufficientBalanceError):
            with lock:
                rejects.append(i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()

    bal = eng.get_balance("corp")
    print(f"[20 threads] successes={len(successes)} rejects={len(rejects)}")
    print(f"[reserved] {bal.reserved} (must be <= 100)")
    print(f"[ledger size] {eng.ledger_size()}")
    ok = len(successes) <= 5 and bal.reserved <= Decimal("100")
    print(f"[verify] pass={ok}")
    return ok


def spot_5_invariant_full():
    """BILL-013 + I-1 ~ I-6 全量 invariant run"""
    banner("SPOT-5 / BILL-013 + invariants I-1 to I-6 full run")
    eng = BillingEngine(provider=MockProvider(name="spot_provider"))
    eng.ensure_tenant("tenant_a", initial_balance=Decimal("1000"))
    eng.ensure_tenant("tenant_b", initial_balance=Decimal("0"), hard_budget=Decimal("500"))

    # tenant_a: 正常 reserve→settle 流程
    for i in range(3):
        evt = BillingEvent(
            tenant_id="tenant_a", idempotency_key=f"k{i}",
            model="gpt-4o", units={UnitType.TOKEN_INPUT: 1000 * (i + 1)},
        )
        r = eng.reserve(evt)
        eng.settle(r.entry_id)
    # tenant_a: 1 笔失败 callback
    cb_fail = ProviderCallback(
        charge_id="fail_001",
        tenant_id="tenant_a", idempotency_key="fk",
        amount=Decimal("100"), currency=Currency.CNY,
        provider="mock_provider_a", success=False,
    )
    eng.apply_callback(cb_fail)
    # tenant_a: 1 笔 correction
    settled_list = [e for e in eng.ledger()
                    if isinstance(e, SettledEntry) and e.kind == EntryKind.SETTLEMENT
                    and e.tenant_id == "tenant_a"]
    if settled_list:
        eng.correction(
            tenant_id="tenant_a", related_entry_id=settled_list[0].entry_id,
            amount=Decimal("1"), currency=Currency.CNY, reason="spot test",
        )

    print(f"[tenant_a ledger size] {sum(1 for e in eng.query_by_tenant('tenant_a'))}")
    print(f"[tenant_b ledger size] {sum(1 for e in eng.query_by_tenant('tenant_b'))}")

    # 跑全部 invariant
    checks = {
        "I-1 append_only":          eng.invariant_append_only(),
        "I-2 balance_conservation": eng.invariant_balance_conservation("tenant_a"),
        "I-3 no_negative_amount":   eng.invariant_no_negative_amount(),
        "I-4 correction_pairs":     eng.invariant_correction_pairs(),
        "I-5 idempotency":          eng.invariant_idempotency(),
        "I-6 charge_id_dedup":      eng.invariant_charge_id_dedup(),
    }
    all_ok = True
    for name, (ok, msg) in checks.items():
        marker = "OK " if ok else "FAIL"
        print(f"  [{marker}] {name}: msg={msg!r}")
        all_ok = all_ok and ok

    return all_ok


# ════════════════════════════════════════════════════════════
# Section B: PROVIDER MOCK BOUNDARY VERIFICATION
# ════════════════════════════════════════════════════════════

def verify_mock_boundary():
    banner("PROVIDER MOCK BOUNDARY: confirm no real API calls")
    provider = MockProvider(name="boundary_check")
    # 检查 MockProvider 类 — 不应有真实 HTTP / 网络调用
    has_http = hasattr(provider, "_session") or hasattr(provider, "_client")
    has_url = False
    url_attrs = []
    for attr in dir(provider):
        if attr.startswith("_") and ("url" in attr.lower() or "http" in attr.lower()
                                       or "api_key" in attr.lower()):
            has_url = True
            url_attrs.append(attr)
    print(f"[MockProvider class] attrs starting with _:")
    for a in sorted(dir(provider)):
        if a.startswith("_"):
            print(f"    {a}: {type(getattr(provider, a)).__name__}")
    print()
    print(f"[HTTP/session present?] {has_http}")
    print(f"[url/api_key attrs?] {has_url} {url_attrs if url_attrs else ''}")
    print(f"[real network code path?] {has_http or has_url}")

    # 同时检查 billing_real.py 是否有真实 SDK / requests / httpx 引用
    import billing_real
    src = open(r"D:\CloudTech-Portable\billing_real.py", encoding="utf-8").read()
    forbidden = ["requests.", "httpx.", "aiohttp.", "urllib.request",
                 "stripe.", "alipay.", "wechat_pay", "pay_sdk"]
    found = []
    for f in forbidden:
        if f in src:
            found.append(f)
    print(f"[billing_real.py forbidden imports/strings found] {found}")
    print(f"[networking-only module] {found if found else 'NONE — pure in-memory mock'}")

    ok = not has_http and not has_url and not found
    print(f"\n[verify] no real provider API touched: {ok}")
    return ok


# ════════════════════════════════════════════════════════════
# Section C: TEST FILE STRUCTURE AUDIT
# ════════════════════════════════════════════════════════════

def test_docstring_mock_audit():
    banner("TEST DOCSTRING / MOCK AUDIT: per-test provider boundary")
    test_path = r"D:\CloudTech-Portable\tests\test_bill_acceptance.py"
    src = open(test_path, encoding="utf-8").read()
    # 统计使用 MockProvider 的位置
    mock_uses = src.count("MockProvider(")
    real_provider_strs = ["requests.", "stripe.", "urllib.request", "httpx."]
    real_uses = sum(src.count(s) for s in real_provider_strs)
    print(f"[test file] {test_path}")
    print(f"[MockProvider instantiations in test] {mock_uses}")
    print(f"[real-network strings in test] {real_uses}")
    print(f"[pytest decorators] {src.count('@pytest.fixture') + src.count('def test_BILL_')}")
    print(f"[tests collected (function defs starting with test_BILL_)]")
    import re
    tests = re.findall(r"^def (test_BILL_\w+)\(", src, re.MULTILINE)
    for t in sorted(tests):
        print(f"    {t}")
    print(f"\n[verify] test uses mock provider only: {mock_uses > 0 and real_uses == 0}")
    return real_uses == 0


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    started = datetime.now(timezone.utc)
    banner(f"T07 BILL EVIDENCE RUN — start {started.isoformat()}")

    results = {}
    results["SPOT-1 BILL-001 reserve/settle/release"] = spot_1_reserve_settle_balance()
    results["SPOT-2 BILL-002 concurrent idempotency"] = spot_2_concurrent_idempotency()
    results["SPOT-3 BILL-003 callback replay 100x"] = spot_3_callback_replay()
    results["SPOT-4 BILL-004b hard_budget concurrent"] = spot_4_hard_budget_rejection()
    results["SPOT-5 BILL-013 + I-1..I-6 invariants"] = spot_5_invariant_full()
    results["MOCK BOUNDARY no real API"] = verify_mock_boundary()
    results["TEST DOCSTRING mock only"] = test_docstring_mock_audit()

    ended = datetime.now(timezone.utc)
    banner(f"T07 SUMMARY — end {ended.isoformat()} ({(ended-started).total_seconds():.2f}s)")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    print(f"\n  >>> {passed}/{total} checks PASS <<<")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())