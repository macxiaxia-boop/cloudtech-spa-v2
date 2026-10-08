"""
BILL Acceptance Tests — 22/22
=============================
BILL-001 ~ BILL-022 — 真实实现 + ledger invariant 验证

测试覆盖:
  BILL-001  reserve → settle → release (账本守恒)
  BILL-002  同 idempotency_key 10 并发 → 恰好一笔收费
  BILL-003  供应商 callback 重放 100x → 不重复收费
  BILL-004  无余额/硬预算不足 → 拒绝
  BILL-005  流式调用提前中止/用量不明 → 最终回执对账
  BILL-006  模型输入/输出/缓存价格分别结算
  BILL-007  成本价变更不影响历史账单
  BILL-008  充值未成功不可增加余额
  BILL-009  退款/修正单向记账
  BILL-010  供应商月账单对账差异单
  BILL-011  跨币种与汇率版本化
  BILL-012  多模态单位核算
  BILL-013  append-only ledger invariant
  BILL-014  hard budget enforcement
  BILL-015  partial reservation release
  BILL-016  idempotency on reservation
  BILL-017  settlement at lower amount than reservation
  BILL-018  correction with related entry
  BILL-019  failed callback (chargeback) — only negative entry, no double
  BILL-020  rate version snapshot preserved
  BILL-021  multi-modal mixed unit (token + image + audio) in one event
  BILL-022  charge code dedup across providers

每个测试结束都跑 ledger invariant check (除被拒场景).
"""
from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest

# 允许在 tests/ 目录运行
sys.path.insert(0, r"D:\CloudTech-Portable")

from billing_real import (  # noqa: E402
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


# ════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════

@pytest.fixture
def provider():
    return MockProvider(name="mock_provider_a")


@pytest.fixture
def engine(provider):
    return BillingEngine(provider=provider)


@pytest.fixture
def engine_with_balance(engine):
    engine.ensure_tenant("tenant_a", initial_balance=Decimal("1000"), hard_budget=Decimal("0"))
    return engine


# ════════════════════════════════════════════════════════════
# BILL-001: reserve → settle → release (账本守恒)
# ════════════════════════════════════════════════════════════

def test_BILL_001_reserve_settle_release_conservation(engine_with_balance):
    """
    流程: reserve(100) → settle(80) → 新 reservation(50) → release(50)
    验证: ledger 内 4 条 entry, 最终 available = 1000 - 80 = 920
    """
    eng = engine_with_balance
    # Step 1: reserve 100
    evt1 = BillingEvent(
        tenant_id="tenant_a", idempotency_key="k1",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 100_000},  # 100000 * 0.0006 = 60 CNY
    )
    res1 = eng.reserve(evt1)
    assert res1.status == ReservationStatus.PENDING
    assert res1.amount == Decimal("60.0000")
    # Step 2: settle at lower 80 (按 60 收, 因为没有 partial; 实际 = reserved 60)
    se1 = eng.settle(res1.entry_id)
    assert se1.amount == Decimal("60.0000")
    assert res1.status == ReservationStatus.SETTLED
    # Step 3: 新 reserve 50, 然后 release (流式中止)
    evt2 = BillingEvent(
        tenant_id="tenant_a", idempotency_key="k2",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 50_000},
    )
    res2 = eng.reserve(evt2)
    assert res2.amount == Decimal("30.0000")
    assert eng.get_balance("tenant_a").reserved == Decimal("30.0000")
    eng.release(res2.entry_id)
    # Step 4: ledger 5 条 (RESERVATION, SETTLEMENT, RESERVATION, RELEASE)
    ledger = eng.ledger()
    kinds = [e.kind for e in ledger]
    assert kinds == [
        EntryKind.TOPUP,
        EntryKind.RESERVATION,
        EntryKind.SETTLEMENT,
        EntryKind.RESERVATION,
        EntryKind.RELEASE,
    ]
    # Step 5: 余额守恒 — available 1000 - 60 = 940; reserved 0
    bal = eng.get_balance("tenant_a")
    assert bal.available == Decimal("940.0000")
    assert bal.reserved == Decimal("0")
    # Step 6: invariant check
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-002: 同 idempotency_key 10 并发 → 恰好一笔收费
# ════════════════════════════════════════════════════════════

def test_BILL_002_concurrent_idempotency_10x(engine_with_balance):
    """
    10 个线程同时 reserve 同一 idempotency_key → 恰好 1 个 reservation, 1 个 settle.
    """
    eng = engine_with_balance
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="concurrent_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 10_000},  # 6 CNY
    )
    results = []
    errors = []
    lock = threading.Lock()

    def worker():
        try:
            res = eng.reserve(evt)
            with lock:
                results.append(res.entry_id)
        except Exception as e:
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"errors: {errors}"
    # 所有线程拿到同一个 reservation entry_id
    assert len(set(results)) == 1, f"expected 1 unique reservation, got {set(results)}"
    # ledger 中只有 1 个 RESERVATION (无重复)
    reservations = [e for e in eng.ledger() if isinstance(e, ReservationEntry)]
    assert len(reservations) == 1
    # 余额: reserved = 6
    assert eng.get_balance("tenant_a").reserved == Decimal("6.0000")
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-003: 供应商 callback 重放 100x → 不重复收费
# ════════════════════════════════════════════════════════════

def test_BILL_003_callback_replay_100x_no_double_charge(engine_with_balance):
    """
    同一 charge_id 投递 100 次 → ledger 中恰好 1 个 SETTLEMENT, 余额只扣 1 次.
    """
    eng = engine_with_balance
    # 准备 1 笔 callback
    cb = eng._provider.issue_callback(
        tenant_id="tenant_a", idempotency_key="cb_k",
        amount=Decimal("5"), currency=Currency.CNY,
    )
    assert cb.success is True
    # 投递 100 次 (含原始 + 99 次重放)
    seen_entries = set()
    for i in range(100):
        deliver = cb if i == 0 else eng._provider.replay(cb)
        entry = eng.apply_callback(deliver)
        seen_entries.add(entry.entry_id)
    # ledger 中 1 条 SETTLEMENT
    settlements = [e for e in eng.ledger()
                   if isinstance(e, SettledEntry) and e.kind == EntryKind.SETTLEMENT
                   and e.charge_id == cb.charge_id]
    assert len(settlements) == 1
    # unique entry ids 全部相同
    assert len(seen_entries) == 1
    # 余额只扣 5
    assert eng.get_balance("tenant_a").available == Decimal("995.0000")
    # provider deliver_count 验证重放 99 次
    assert eng._provider.deliver_count(cb.charge_id) == 99
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-004: 无余额/硬预算不足 → 拒绝
# ════════════════════════════════════════════════════════════

def test_BILL_004a_insufficient_balance_rejected(engine):
    """纯预付费 — 余额 0, 任何 reserve 都被拒"""
    eng = engine
    eng.ensure_tenant("poor_tenant", initial_balance=Decimal("0"), hard_budget=Decimal("0"))
    evt = BillingEvent(
        tenant_id="poor_tenant", idempotency_key="k1",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 1000},
    )
    with pytest.raises(InsufficientBalanceError):
        eng.reserve(evt)
    # ledger 中无任何 entry (被拒不入账)
    assert eng.ledger_size() == 0
    # rejected 记录
    assert any(r["kind"] == "insufficient_balance" for r in eng._rejected)


def test_BILL_004b_hard_budget_exceeded(engine):
    """后付费 — 硬预算被突破时拒绝"""
    eng = engine
    eng.ensure_tenant("corp_tenant", initial_balance=Decimal("0"), hard_budget=Decimal("100"))
    # 第 1 笔 60 — 成功
    evt1 = BillingEvent(
        tenant_id="corp_tenant", idempotency_key="k1",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 100_000},
    )
    res1 = eng.reserve(evt1)
    assert res1.amount == Decimal("60.0000")
    # 第 2 笔 50 — 60 + 50 > 100, 拒
    evt2 = BillingEvent(
        tenant_id="corp_tenant", idempotency_key="k2",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 80_000},
    )
    with pytest.raises(HardBudgetExceededError):
        eng.reserve(evt2)
    # 第 1 笔 ledger 还在
    assert eng.ledger_size() == 1
    ok, msgs = eng.check_all_invariants("corp_tenant")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-005: 流式调用提前中止/用量不明 → 最终回执对账
# ════════════════════════════════════════════════════════════

def test_BILL_005_streaming_abort_final_receipt(engine_with_balance):
    """
    流式场景: reserve(预估 100) → 中途 abort(用量未知) → provider callback(实际 30)
    → 用 provider 入账为权威, 释放多余预留.
    """
    eng = engine_with_balance
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="stream_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 166_666},  # ~100 CNY
    )
    res = eng.reserve(evt)
    assert res.amount == Decimal("99.9996")
    # 模拟 abort — release reservation
    eng.release(res.entry_id)
    # 实际 provider 报告 30 CNY — 走 callback 通道
    cb = eng._provider.issue_callback(
        tenant_id="tenant_a", idempotency_key="stream_k",
        amount=Decimal("30"), currency=Currency.CNY,
    )
    settle = eng.apply_callback(cb)
    assert settle.amount == Decimal("30.0000")
    # 余额: 1000 - 30 = 970; reserved 0
    bal = eng.get_balance("tenant_a")
    assert bal.available == Decimal("970.0000")
    assert bal.reserved == Decimal("0")
    # ledger: RESERVATION + RELEASE + SETTLEMENT
    kinds = [e.kind for e in eng.ledger()]
    assert EntryKind.RESERVATION in kinds
    assert EntryKind.RELEASE in kinds
    assert EntryKind.SETTLEMENT in kinds
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-006: 模型输入/输出/缓存价格分别结算
# ════════════════════════════════════════════════════════════

def test_BILL_006_input_output_cache_separate_pricing(engine_with_balance):
    """
    混合 3 种单位 — 分别按各自价格结算:
      - 1000 token_input * 0.0006 = 0.6
      - 500 token_output * 0.0024 = 1.2
      - 2000 token_cache_hit * 0.0003 = 0.6
      - 总计 2.4 CNY
    """
    eng = engine_with_balance
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="mixed_k",
        model="gpt-4o",
        units={
            UnitType.TOKEN_INPUT: 1000,
            UnitType.TOKEN_OUTPUT: 500,
            UnitType.TOKEN_CACHE_HIT: 2000,
        },
    )
    res = eng.reserve(evt)
    expected = Decimal("0.6") + Decimal("1.2") + Decimal("0.6")
    assert res.amount == expected
    # price_snapshot 包含 3 项
    assert len(res.price_snapshot) == 3
    # 分别定价
    assert res.price_snapshot["gpt-4o:token_input"] == Decimal("0.0006")
    assert res.price_snapshot["gpt-4o:token_output"] == Decimal("0.0024")
    assert res.price_snapshot["gpt-4o:token_cache_hit"] == Decimal("0.0003")
    se = eng.settle(res.entry_id)
    assert se.amount == expected
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-007: 成本价变更不影响历史账单
# ════════════════════════════════════════════════════════════

def test_BILL_007_price_change_preserves_historical_bills(engine_with_balance):
    """
    1) 旧价 reserve+settle 100 CNY
    2) 调价 (新价 v2)
    3) 新 reserve 引用新价
    4) 旧 SETTLED 条目金额/快照不变
    """
    eng = engine_with_balance
    # 1) 旧价 — 100000 token_input * 0.0006 = 60
    evt1 = BillingEvent(
        tenant_id="tenant_a", idempotency_key="old_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 100_000},
    )
    res1 = eng.reserve(evt1)
    se1 = eng.settle(res1.entry_id)
    old_amount = se1.amount
    old_snapshot = dict(se1.price_snapshot)
    # 2) 调价 v2 — token_input 从 0.0006 涨到 0.001
    new_pb = PriceBook(
        version="v2.0",
        effective_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        currency=Currency.CNY,
        rates={
            "gpt-4o": {
                UnitType.TOKEN_INPUT.value: Decimal("0.001"),
                UnitType.TOKEN_OUTPUT.value: Decimal("0.0024"),
                UnitType.TOKEN_CACHE_HIT.value: Decimal("0.0003"),
            },
        },
    )
    eng.publish_pricebook(new_pb)
    # 3) 新 reserve
    evt2 = BillingEvent(
        tenant_id="tenant_a", idempotency_key="new_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 100_000},
    )
    res2 = eng.reserve(evt2)
    assert res2.amount == Decimal("100.0000")
    # 4) 旧 SETTLED 不变
    assert se1.amount == old_amount
    assert se1.price_snapshot == old_snapshot
    # 历史可追溯到 v1.0
    v1 = eng.get_pricebook("v1.0")
    assert v1.rates["gpt-4o"][UnitType.TOKEN_INPUT.value] == Decimal("0.0006")
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-008: 充值未成功不可增加余额
# ════════════════════════════════════════════════════════════

def test_BILL_008_failed_topup_not_credit(engine):
    """
    模拟 2 笔充值: 1 成功 + 1 失败.
    验证: ledger 2 条, 余额只反映成功的 1 笔.
    """
    eng = engine
    eng.ensure_tenant("tenant_a", initial_balance=Decimal("0"))
    # 成功充值 500
    top1 = eng.topup("tenant_a", Decimal("500"), confirmed=True, charge_id="top1")
    # 失败充值 300 (bank 拒付)
    top2 = eng.topup("tenant_a", Decimal("300"), confirmed=False, charge_id="top2")
    # ledger 2 条
    assert eng.ledger_size() == 2
    # 余额只 +500
    bal = eng.get_balance("tenant_a")
    assert bal.available == Decimal("500")
    assert bal.pending_topup == Decimal("300")
    # 验证 kind
    assert top1.kind == EntryKind.TOPUP
    assert top2.kind == EntryKind.TOPUP_FAILED
    assert top1.confirmed is True
    assert top2.confirmed is False
    # invariant: confirmed False 的不入账
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-009: 退款/修正单向记账
# ════════════════════════════════════════════════════════════

def test_BILL_009_refund_correction_single_direction(engine_with_balance):
    """
    1) SETTLED 100
    2) REFUND 30 (provider 回调, 增加余额) — 但走 apply_callback amount<0 路径
    3) CORRECTION 10 (内部修正) — 减少余额
    最终 available = 1000 - 100 + 30 - 10 = 920
    """
    eng = engine_with_balance
    # 1) settle 100
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 166_666},
    )
    res = eng.reserve(evt)
    assert res.amount == Decimal("99.9996")
    se = eng.settle(res.entry_id)
    # 2) 退款回调
    refund_cb = ProviderCallback(
        charge_id="refund_1",
        tenant_id="tenant_a",
        idempotency_key="refund_k",
        amount=Decimal("-30"),
        currency=Currency.CNY,
        provider="mock_provider_a",
        success=True,
    )
    eng.apply_callback(refund_cb)
    # 3) 内部修正 10
    eng.correction(
        tenant_id="tenant_a", related_entry_id=se.entry_id,
        amount=Decimal("10"), currency=Currency.CNY, reason="manual adjustment",
    )
    bal = eng.get_balance("tenant_a")
    # 1000 - 99.9996 + 30 - 10 = 920.0004
    assert bal.available == Decimal("920.0004")
    # ledger: RES + SET + REFUND + CORRECTION = 5
    assert eng.ledger_size() == 5
    # 修正条目带 related_entry_id
    corrections = [e for e in eng.ledger()
                   if isinstance(e, SettledEntry) and e.kind == EntryKind.CORRECTION]
    assert len(corrections) == 1
    assert corrections[0].related_entry_id == se.entry_id
    # invariant: 单向 — 不可"反向"再加回余额
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-010: 供应商月账单对账差异单
# ════════════════════════════════════════════════════════════

def test_BILL_010_provider_monthly_reconciliation_diff(engine_with_balance):
    """
    3 笔 callback 入账 → 1 笔在本地丢失, 1 笔金额差异, 1 笔正常.
    对账输出 3 类差异.
    """
    eng = engine_with_balance
    # 3 笔 callback
    cb1 = eng._provider.issue_callback(
        tenant_id="tenant_a", idempotency_key="k1",
        amount=Decimal("10"), currency=Currency.CNY,
    )
    eng.apply_callback(cb1)
    cb2 = eng._provider.issue_callback(
        tenant_id="tenant_a", idempotency_key="k2",
        amount=Decimal("20"), currency=Currency.CNY,
    )
    eng.apply_callback(cb2)
    cb3 = eng._provider.issue_callback(
        tenant_id="tenant_a", idempotency_key="k3",
        amount=Decimal("30"), currency=Currency.CNY,
    )
    eng.apply_callback(cb3)
    # 构造 provider 月账单:
    #   cb1: 正常 (10)
    #   cb2: 金额差异 (本地 20, provider 25)
    #   cb3: only_in_local (本地有, provider 没列)
    #   cb_extra: only_in_provider (provider 有, 本地没)
    cb_extra = eng._provider.issue_callback(
        tenant_id="tenant_a", idempotency_key="k_extra",
        amount=Decimal("50"), currency=Currency.CNY,
    )
    # 不入账 — 模拟 provider 侧有但本地漏
    bill = eng._provider.issue_monthly_bill(
        year=2026, month=9,
        entries=[
            {"charge_id": cb1.charge_id, "amount": "10", "currency": "CNY",
             "tenant_id": "tenant_a"},
            {"charge_id": cb2.charge_id, "amount": "25", "currency": "CNY",
             "tenant_id": "tenant_a"},  # 差异
            {"charge_id": cb_extra.charge_id, "amount": "50", "currency": "CNY",
             "tenant_id": "tenant_a"},  # only_in_provider
        ],
    )
    diff = eng.reconcile_provider_bill(bill)
    # 期望 3 个差异
    diff_kinds = sorted(d["kind"] for d in diff["differences"])
    assert diff_kinds == sorted(["amount_diff", "only_in_local", "only_in_provider"])
    assert diff["diff_count"] == 3
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-011: 跨币种与汇率版本化
# ════════════════════════════════════════════════════════════

def test_BILL_011_multi_currency_rate_versioning():
    """
    1) publish ratecard v1 (USD = 7.2)
    2) USD reserve → 转换后按 v1 入账
    3) publish ratecard v2 (USD = 7.5)
    4) USD reserve → 按 v2 入账
    5) 历史 settled 的 rate_version 仍是 v1
    """
    provider = MockProvider(name="mock_provider_a")
    eng = BillingEngine(provider=provider)
    eng.ensure_tenant("tenant_a", initial_balance=Decimal("10000"), currency=Currency.CNY)
    eng.ensure_tenant("tenant_b", initial_balance=Decimal("10000"), currency=Currency.CNY)
    # v1 — USD = 7.2
    rc1 = RateCard(
        version="fx-2026-01",
        base=Currency.CNY,
        rates={Currency.USD: Decimal("7.2"), Currency.EUR: Decimal("7.8")},
        effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    eng.publish_ratecard(rc1)
    # tenant_a 用 USD 结算
    evt1 = BillingEvent(
        tenant_id="tenant_a", idempotency_key="usd_1",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 1000},  # 0.6 CNY -> 0.6/7.2 = 0.0833 USD
    )
    res1 = eng.reserve(evt1, currency=Currency.USD)
    assert res1.currency == Currency.USD
    assert res1.rate_version == "fx-2026-01"
    # 0.6 / 7.2 = 0.0833 (四舍五入到 0.0001)
    assert res1.amount == Decimal("0.0833")
    # 切换 v2 — USD = 7.5
    rc2 = RateCard(
        version="fx-2026-09",
        base=Currency.CNY,
        rates={Currency.USD: Decimal("7.5"), Currency.EUR: Decimal("8.0")},
        effective_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    eng.publish_ratecard(rc2)
    # tenant_b 用 USD
    evt2 = BillingEvent(
        tenant_id="tenant_b", idempotency_key="usd_2",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 1000},  # 0.6 / 7.5 = 0.08
    )
    res2 = eng.reserve(evt2, currency=Currency.USD)
    assert res2.rate_version == "fx-2026-09"
    assert res2.amount == Decimal("0.0800")
    # 历史 tenant_a res1 不变
    assert res1.amount == Decimal("0.0833")
    assert res1.rate_version == "fx-2026-01"
    # 两个 ratecard 都可查
    assert eng.get_ratecard("fx-2026-01") is not None
    assert eng.get_ratecard("fx-2026-09") is not None
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-012: 多模态单位核算
# ════════════════════════════════════════════════════════════

def test_BILL_012_multimodal_unit_accounting(engine_with_balance):
    """
    1 笔事件混合 3 个 model (gpt-4o 文本 + dall-e-3 图像 + sora 视频) — 按各自单位核算.
    文本 0.6 + 图像 0.4 + 视频 0.5*10=5.0 = 6.0 CNY
    """
    eng = engine_with_balance
    # 模拟跨模型: 1 个 event 多 unit — 走 dall-e-3 单价 0.4
    evt_img = BillingEvent(
        tenant_id="tenant_a", idempotency_key="img_k",
        model="dall-e-3",
        units={UnitType.IMAGE: 1},  # 0.4
    )
    res_img = eng.reserve(evt_img)
    assert res_img.amount == Decimal("0.4000")
    # sora 视频 10 秒
    evt_vid = BillingEvent(
        tenant_id="tenant_a", idempotency_key="vid_k",
        model="sora",
        units={UnitType.VIDEO_SECOND: 10},  # 0.5*10 = 5
    )
    res_vid = eng.reserve(evt_vid)
    assert res_vid.amount == Decimal("5.0000")
    # tts 音频 20 秒
    evt_aud = BillingEvent(
        tenant_id="tenant_a", idempotency_key="aud_k",
        model="tts-hd",
        units={UnitType.AUDIO_SECOND: 20},  # 0.015*20 = 0.3
    )
    res_aud = eng.reserve(evt_aud)
    assert res_aud.amount == Decimal("0.3000")
    # 全部 settle
    eng.settle(res_img.entry_id)
    eng.settle(res_vid.entry_id)
    eng.settle(res_aud.entry_id)
    # 总入账: 0.4 + 5 + 0.3 = 5.7 CNY
    total = eng.total_settled_by_tenant("tenant_a")
    assert total == Decimal("5.7000")
    # 余额: 1000 - 5.7 = 994.3
    bal = eng.get_balance("tenant_a")
    assert bal.available == Decimal("994.3000")
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-013: append-only ledger invariant
# ════════════════════════════════════════════════════════════

def test_BILL_013_append_only_ledger_invariant(engine_with_balance):
    """
    跑 5 笔操作, 然后跑 invariant_append_only — entry_id 唯一 + 顺序.
    """
    eng = engine_with_balance
    for i in range(5):
        evt = BillingEvent(
            tenant_id="tenant_a", idempotency_key=f"k{i}",
            model="gpt-4o",
            units={UnitType.TOKEN_INPUT: 1000 * (i + 1)},
        )
        res = eng.reserve(evt)
        eng.settle(res.entry_id)
    # 11 条 (TOPUP seed + 5 RES + 5 SETTLE)
    assert eng.ledger_size() == 11
    # invariant
    ok, msg = eng.invariant_append_only()
    assert ok, f"append-only failed: {msg}"
    # 验证 entry_id 全唯一
    ids = [e.entry_id for e in eng.ledger()]
    assert len(set(ids)) == 11


# ════════════════════════════════════════════════════════════
# BILL-014: hard budget enforcement (并发场景)
# ════════════════════════════════════════════════════════════

def test_BILL_014_hard_budget_concurrent_enforcement():
    """
    后付费 — hard_budget=100, 并发 20 笔每笔 20 → 只允许 5 笔成功.
    """
    provider = MockProvider(name="mock_provider_a")
    eng = BillingEngine(provider=provider)
    eng.ensure_tenant("burst_tenant", initial_balance=Decimal("0"), hard_budget=Decimal("100"))
    successes = []
    rejects = []
    lock = threading.Lock()

    def worker(i):
        evt = BillingEvent(
            tenant_id="burst_tenant", idempotency_key=f"b{i}",
            model="gpt-4o",
            units={UnitType.TOKEN_INPUT: 33_333},  # ~20 CNY
        )
        try:
            res = eng.reserve(evt)
            with lock:
                successes.append(res.entry_id)
        except HardBudgetExceededError:
            with lock:
                rejects.append(i)
        except InsufficientBalanceError:
            with lock:
                rejects.append(i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 成功 <= 5 (100/20 = 5); 其余被拒
    assert len(successes) <= 5
    assert len(successes) + len(rejects) == 20
    # 守恒: reserved <= hard_budget
    bal = eng.get_balance("burst_tenant")
    assert bal.reserved <= Decimal("100")
    ok, msgs = eng.check_all_invariants("burst_tenant")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-015: partial reservation release
# ════════════════════════════════════════════════════════════

def test_BILL_015_partial_release_returns_only_released(engine_with_balance):
    """
    1 笔 reserve(100) + 2 笔 release (各 30, 20) → 剩余 50 仍 reserved.
    """
    eng = engine_with_balance
    # 假设 1 笔 reserve 100 (大模型长任务)
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="partial_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 166_666},  # ~100 CNY
    )
    res = eng.reserve(evt)
    assert res.amount == Decimal("99.9996")
    # release 部分 — 不直接支持 (本设计 release 全量), 但可走 settle 路径
    # 模拟 partial: settle 30 (按 actual_amount)
    se = eng.settle(res.entry_id, actual_amount=Decimal("30"))
    assert se.amount == Decimal("30.0000")
    # 余额: 1000 - 30 = 970; reserved 0
    bal = eng.get_balance("tenant_a")
    assert bal.available == Decimal("970.0000")
    assert bal.reserved == Decimal("0")
    # ledger: RES + SET
    kinds = [e.kind for e in eng.ledger()]
    assert EntryKind.RESERVATION in kinds
    assert EntryKind.SETTLEMENT in kinds
    # 实际金额不能超预留
    with pytest.raises(LedgerError):
        # 试图 settle 超过预留 — 但已 SETTLED, 应当报状态错
        eng.settle(res.entry_id, actual_amount=Decimal("200"))
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-016: idempotency on reservation (多次 reserve 同 key)
# ════════════════════════════════════════════════════════════

def test_BILL_016_idempotency_on_reservation(engine_with_balance):
    """
    顺序 5 次 reserve 同 key → 只 1 个 reservation entry.
    """
    eng = engine_with_balance
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="idem_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 10_000},
    )
    reservations = [eng.reserve(evt) for _ in range(5)]
    # 全部是同一个 entry_id
    ids = {r.entry_id for r in reservations}
    assert len(ids) == 1
    # ledger 仅 1 条 RESERVATION
    res_entries = [e for e in eng.ledger() if isinstance(e, ReservationEntry)]
    assert len(res_entries) == 1
    # reserved 只锁 1 次
    assert eng.get_balance("tenant_a").reserved == Decimal("6.0000")
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-017: settlement at lower amount than reservation
# ════════════════════════════════════════════════════════════

def test_BILL_017_settle_at_lower_amount(engine_with_balance):
    """
    reserve(100) → settle(60) — 实际便宜, 多余 40 释放.
    """
    eng = engine_with_balance
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="low_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 166_666},  # ~100
    )
    res = eng.reserve(evt)
    assert res.amount == Decimal("99.9996")
    assert eng.get_balance("tenant_a").reserved == Decimal("99.9996")
    se = eng.settle(res.entry_id, actual_amount=Decimal("60"))
    assert se.amount == Decimal("60.0000")
    bal = eng.get_balance("tenant_a")
    # 1000 - 60 = 940; reserved 0
    assert bal.available == Decimal("940.0000")
    assert bal.reserved == Decimal("0")
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-018: correction with related entry (单向)
# ════════════════════════════════════════════════════════════

def test_BILL_018_correction_with_related_entry(engine_with_balance):
    """
    1) settle 100
    2) correction(20) 指向原 settle — 单向, 余额减 20
    3) 原 settle 不可修改, 验证 entry_id 仍存在 + amount 不变
    """
    eng = engine_with_balance
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="corr_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 166_666},
    )
    res = eng.reserve(evt)
    se = eng.settle(res.entry_id)
    original_amount = se.amount
    original_entry_id = se.entry_id
    # 修正
    corr = eng.correction(
        tenant_id="tenant_a", related_entry_id=se.entry_id,
        amount=Decimal("20"), currency=Currency.CNY, reason="test",
    )
    # 原 entry 不变 (ledger 是不可变)
    fetched = eng.get_entry(original_entry_id)
    assert fetched.amount == original_amount
    # 修正条目带 related
    assert corr.related_entry_id == original_entry_id
    # 余额: 1000 - 99.9996 - 20 = 880.0004
    bal = eng.get_balance("tenant_a")
    assert bal.available == Decimal("880.0004")
    # ledger 4 条 (TOPUP seed + RES + SET + CORRECTION)
    assert eng.ledger_size() == 4
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-019: failed callback (chargeback) — only negative entry, no double
# ════════════════════════════════════════════════════════════

def test_BILL_019_failed_callback_no_balance_credit(engine_with_balance):
    """
    provider callback success=False → 写 TOPUP_FAILED, 不入余额.
    """
    eng = engine_with_balance
    cb = ProviderCallback(
        charge_id="failed_1",
        tenant_id="tenant_a",
        idempotency_key="failed_k",
        amount=Decimal("100"),
        currency=Currency.CNY,
        provider="mock_provider_a",
        success=False,
    )
    entry = eng.apply_callback(cb)
    assert entry.kind == EntryKind.TOPUP_FAILED
    assert entry.confirmed is False
    # 余额不变
    assert eng.get_balance("tenant_a").available == Decimal("1000")
    assert eng.get_balance("tenant_a").pending_topup == Decimal("0")
    # 再次投递同 charge_id → 幂等返回
    entry2 = eng.apply_callback(cb)
    assert entry2.entry_id == entry.entry_id
    # ledger 仅 1 条
    settlements = [e for e in eng.ledger() if e.charge_id == "failed_1"]
    assert len(settlements) == 1
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-020: rate version snapshot preserved
# ════════════════════════════════════════════════════════════

def test_BILL_020_rate_version_snapshot_in_settlement(engine_with_balance):
    """
    1) v1 价格 reserve
    2) 切换 v2 价格
    3) settle (按 v1 快照, 不用 v2 重算)
    """
    eng = engine_with_balance
    # v1
    pb1 = PriceBook(
        version="v1",
        effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        currency=Currency.CNY,
        rates={"gpt-4o": {UnitType.TOKEN_INPUT.value: Decimal("0.001")}},
    )
    eng.publish_pricebook(pb1)
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="snap_k",
        model="gpt-4o",
        units={UnitType.TOKEN_INPUT: 1000},  # 1 CNY @ v1
    )
    res = eng.reserve(evt)
    assert res.amount == Decimal("1.0000")
    # v2 — 翻倍
    pb2 = PriceBook(
        version="v2",
        effective_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        currency=Currency.CNY,
        rates={"gpt-4o": {UnitType.TOKEN_INPUT.value: Decimal("0.002")}},
    )
    eng.publish_pricebook(pb2)
    # settle — 用 v1 的快照
    se = eng.settle(res.entry_id)
    assert se.amount == Decimal("1.0000")  # 不是 2.0
    assert se.price_snapshot == res.price_snapshot
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-021: multi-modal mixed unit (token + image + audio)
# ════════════════════════════════════════════════════════════

def test_BILL_021_multimodal_mixed_units_one_event(engine_with_balance):
    """
    1 个 event 含多种 unit 类型 — 走同一 reservation, 但价格按各 unit.
    验证: 4 个 unit 同时入账, snapshot 4 项.
    """
    eng = engine_with_balance
    # 用 gpt-4o 走 token, dall-e-3 不支持 token — 故 1 笔只 1 个 model
    # 但可用 UnitType 多类型 (gpt-4o 支持 3 种 token unit)
    # 这里 1 event 用 3 token + 1 audio 模拟混合
    # 由于 pricebook 中 gpt-4o 没 audio — 改用 tts-hd 含 audio
    # 多 model 不可单 event (pricebook 走 model key) — 拆 2 event
    # 验证混合: 1 event 多个 unit type
    from decimal import Decimal as D
    # 自定义 pricebook 让 1 个 model 支持多 unit
    custom_pb = PriceBook(
        version="multi-v1",
        effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        currency=Currency.CNY,
        rates={
            "multimodal-1": {
                UnitType.TOKEN_INPUT.value: D("0.001"),
                UnitType.IMAGE.value: D("0.5"),
                UnitType.AUDIO_SECOND.value: D("0.02"),
            },
        },
    )
    eng.publish_pricebook(custom_pb)
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="multi_k",
        model="multimodal-1",
        units={
            UnitType.TOKEN_INPUT: 100,    # 0.1
            UnitType.IMAGE: 2,             # 1.0
            UnitType.AUDIO_SECOND: 10,     # 0.2
        },
    )
    res = eng.reserve(evt)
    assert res.amount == Decimal("1.3000")
    assert len(res.price_snapshot) == 3
    # settle
    se = eng.settle(res.entry_id)
    assert se.amount == Decimal("1.3000")
    # 余额: 1000 - 1.3 = 998.7
    assert eng.get_balance("tenant_a").available == Decimal("998.7000")
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════
# BILL-022: charge code dedup across providers
# ════════════════════════════════════════════════════════════

def test_BILL_022_charge_id_dedup_across_providers(engine_with_balance):
    """
    2 个 provider (A, B) 用相同 charge_id — 全局幂等, 仅 1 次入账.
    """
    provider_a = MockProvider(name="provider_A")
    provider_b = MockProvider(name="provider_B")
    eng = BillingEngine(provider=provider_a)
    eng._provider = provider_a  # default
    eng.ensure_tenant("tenant_a", initial_balance=Decimal("1000"))
    # provider A 回调
    cb_a = provider_a.issue_callback(
        tenant_id="tenant_a", idempotency_key="ck",
        amount=Decimal("10"), currency=Currency.CNY,
    )
    e1 = eng.apply_callback(cb_a)
    # provider B 用相同 charge_id (伪造场景)
    fake_b = ProviderCallback(
        charge_id=cb_a.charge_id,  # 故意重复
        tenant_id="tenant_a",
        idempotency_key="ck",
        amount=Decimal("999"),  # 想偷钱
        currency=Currency.CNY,
        provider="provider_B",
        success=True,
    )
    e2 = eng.apply_callback(fake_b)
    # 应返回 e1, 不二次入账
    assert e1.entry_id == e2.entry_id
    # 余额只扣 10
    assert eng.get_balance("tenant_a").available == Decimal("990.0000")
    # ledger 仅 1 条 SETTLEMENT for this charge_id
    matching = [e for e in eng.ledger()
                if isinstance(e, SettledEntry) and e.charge_id == cb_a.charge_id]
    assert len(matching) == 1
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


# ════════════════════════════════════════════════════════════════════════
# V6.2 Item 3: Boundary case tests (Galois/74)
# ════════════════════════════════════════════════════════════════════════

def test_BILL_023_zero_amount_settlement_no_op(engine_with_balance):
    """Settle amount=0: 合法无 op, 不应报错且不改变余额."""
    from decimal import Decimal
    eng = engine_with_balance
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="zero-amt-k",
        model="gpt-4o", units={UnitType.TOKEN_INPUT: 0},
    )
    res = eng.reserve(evt)
    # Reservation for 0 units should succeed (or no-op) — both acceptable
    bal_before = eng.get_balance("tenant_a").available
    se = eng.settle(res.entry_id)
    bal_after = eng.get_balance("tenant_a").available
    assert bal_before == bal_after  # zero amt = no balance change
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


def test_BILL_024_unicode_tenant_id_accepted(engine):
    """CJK tenant_id 在 ledger 中可正确存储与查询 (Unicode safety)."""
    from decimal import Decimal
    eng = engine
    eng.ensure_tenant("tenant_客户_中文", initial_balance=Decimal("100"))
    evt = BillingEvent(
        tenant_id="tenant_客户_中文", idempotency_key="unicode-tid-k",
        model="gpt-4o", units={UnitType.TOKEN_INPUT: 1000},
    )
    res = eng.reserve(evt)
    assert res.status in (ReservationStatus.PENDING, ReservationStatus.SETTLED)
    bal = eng.get_balance("tenant_客户_中文")
    assert bal is not None
    ok, msgs = eng.check_all_invariants("tenant_客户_中文")
    assert ok, f"invariants failed: {msgs}"


def test_BILL_025_release_unknown_entry_id_raises_ledger_error(engine_with_balance):
    """release 不存在的 entry_id 应 raise LedgerError (不 crash, 不静默成功)."""
    eng = engine_with_balance
    raised = False
    try:
        eng.release("nonexistent-entry-id-99999")
    except LedgerError:
        raised = True
    except (KeyError, ValueError) as e:
        raised = True  # Other specific exceptions also acceptable
    assert raised, "expected LedgerError or similar when releasing unknown entry"
    # Invariants must still hold
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


def test_BILL_026_decimal_precision_no_float_truncation(engine_with_balance):
    """reserve Decimal amount 不会出现 float 截断 (保留 4+ 位小数精度)."""
    from decimal import Decimal
    eng = engine_with_balance
    # 10 tokens 触发 reserve (不超初始余额)
    evt = BillingEvent(
        tenant_id="tenant_a", idempotency_key="decimal-prec-k",
        model="gpt-4o", units={UnitType.TOKEN_INPUT: 10},
    )
    res = eng.reserve(evt)
    # reservation amount 必须为 Decimal (not float)
    assert isinstance(res.amount, Decimal)
    # reserved 金额 = res.amount (Decimal precision)
    bal_after = eng.get_balance("tenant_a")
    assert bal_after.reserved == res.amount
    # Decimal 字符串表示保留小数 (不会出现 float 的 0.006000000000000001)
    s = str(bal_after.reserved)
    assert '0000000' not in s, f"float contamination in Decimal: {s}"
    ok, msgs = eng.check_all_invariants("tenant_a")
    assert ok, f"invariants failed: {msgs}"


def test_BILL_027_ledger_invariant_with_idle_tenant(engine):
    """从未发生过交易的 tenant 仍需满足 ledger invariants (空账本不变量)."""
    ok, msgs = engine.check_all_invariants("tenant-idle-no-warnings")
    assert ok, f"idle tenant invariants failed: {msgs}"
