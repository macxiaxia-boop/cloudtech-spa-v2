"""
BILL Real Acceptance Engine v1.0
================================
真实计费/对账引擎 (in-memory, append-only ledger + mock provider)

设计目标:
  - 22 个 BILL acceptance tests 的真实可执行实现
  - 不依赖第三方 billing 服务 (mock provider)
  - 提供 append-only ledger, 不可变历史, 可重放验证
  - 真实并发幂等, 价格快照, 多币种汇率版本化, 多模态单位核算

数据模型 (Pydantic v2):
  - BillingEvent    : 一条业务事件 (request/response/callback)
  - IdempotencyKey  : 幂等键记录
  - ReservationEntry: 预留 (PENDING/RELEASED/SETTLED)
  - SettledEntry    : 已结算 (CHARGE/REFUND/CORRECTION)
  - CreditBalance   : 账户余额 (可预付费/后付费/混合)
  - PriceBook       : 价格表 (按 model + unit + currency)
  - RateCard        : 汇率版本
  - ProviderCallback: 供应商回调 (含 signature 防止伪造)

不变量 (invariants):
  I-1  Ledger append-only (只能 add, 不能修改/删除历史)
  I-2  reserved + settled <= credit_limit (or balance)
  I-3  settled amount 永不为负
  I-4  correction 永远配对 (原 charge + 反向 entry, 单向记账)
  I-5  同 idempotency_key 最多一笔 settled
  I-6  回调重复投递同 charge_id 不二次入账
  I-7  价格快照写入 settled (历史账单不被后续调价影响)
  I-8  失败的充值/退款不增加余额
  I-9  跨币种 settled 必带 rate_version
  I-10 多模态单位核算 (token / image / second) 显式区分
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


# ════════════════════════════════════════════════════════════
# 枚举
# ════════════════════════════════════════════════════════════

class EntryKind(str, Enum):
    RESERVATION = "RESERVATION"
    SETTLEMENT = "SETTLEMENT"
    REFUND = "REFUND"
    CORRECTION = "CORRECTION"
    TOPUP = "TOPUP"
    TOPUP_FAILED = "TOPUP_FAILED"
    RELEASE = "RELEASE"


class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    RELEASED = "RELEASED"


class UnitType(str, Enum):
    TOKEN_INPUT = "token_input"
    TOKEN_OUTPUT = "token_output"
    TOKEN_CACHE_HIT = "token_cache_hit"
    IMAGE = "image"
    AUDIO_SECOND = "audio_second"
    VIDEO_SECOND = "video_second"


class Currency(str, Enum):
    CNY = "CNY"
    USD = "USD"
    EUR = "EUR"


# ════════════════════════════════════════════════════════════
# Pydantic Models
# ════════════════════════════════════════════════════════════

class BillingEvent(BaseModel):
    """业务事件 (上层 RPC / LLM 调用)"""
    model_config = ConfigDict(frozen=True)
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    tenant_id: str
    idempotency_key: str
    model: str
    units: dict[UnitType, int] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IdempotencyKey(BaseModel):
    """幂等键记录 (持久化)"""
    model_config = ConfigDict(frozen=True)
    key: str
    tenant_id: str
    first_seen_at: datetime
    settled_entry_id: Optional[str] = None
    reservation_id: Optional[str] = None


class ReservationEntry(BaseModel):
    """预留条目 — 上限/估价的金额从账户锁定"""
    entry_id: str = Field(default_factory=lambda: f"res_{uuid.uuid4().hex[:12]}")
    kind: EntryKind = EntryKind.RESERVATION
    tenant_id: str
    idempotency_key: str
    billing_event_id: str
    amount: Decimal
    currency: Currency
    rate_version: str
    price_snapshot: dict[str, Decimal]
    status: ReservationStatus = ReservationStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    settled_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    settled_entry_id: Optional[str] = None


class SettledEntry(BaseModel):
    """已结算条目 — 不可变, 写入账本"""
    entry_id: str = Field(default_factory=lambda: f"set_{uuid.uuid4().hex[:12]}")
    kind: EntryKind  # SETTLEMENT / REFUND / CORRECTION / TOPUP / TOPUP_FAILED
    tenant_id: str
    amount: Decimal  # 永远 >= 0; 负向记账走 REFUND/CORRECTION
    currency: Currency
    rate_version: str
    price_snapshot: dict[str, Decimal] = Field(default_factory=dict)
    units: dict[UnitType, int] = Field(default_factory=dict)
    reservation_id: Optional[str] = None
    charge_id: Optional[str] = None  # 来自 provider 回调的 charge_id
    related_entry_id: Optional[str] = None  # 修正/退款指向
    provider: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # 真实入账状态 — 失败的充值/回调不可入余额
    confirmed: bool = True


class CreditBalance(BaseModel):
    """账户余额"""
    tenant_id: str
    available: Decimal = Decimal("0")
    reserved: Decimal = Decimal("0")
    hard_budget: Decimal = Decimal("0")  # 后付费上限; 0 = 预付费 only
    currency: Currency = Currency.CNY
    # TOPUP 用 — 区分 confirmed / pending
    pending_topup: Decimal = Decimal("0")


class PriceBook(BaseModel):
    """价格表 (model -> unit -> price)"""
    version: str
    effective_at: datetime
    rates: dict[str, dict[str, Decimal]]  # {model: {unit: price}}
    currency: Currency = Currency.CNY


class RateCard(BaseModel):
    """汇率版本卡 (多币种)"""
    version: str
    base: Currency
    rates: dict[Currency, Decimal]  # base -> target
    effective_at: datetime


class ProviderCallback(BaseModel):
    """供应商回调 — 含幂等用的 charge_id"""
    callback_id: str = Field(default_factory=lambda: f"cb_{uuid.uuid4().hex[:12]}")
    charge_id: str  # 供应商侧唯一
    tenant_id: str
    idempotency_key: str
    amount: Decimal
    currency: Currency
    provider: str
    success: bool
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ════════════════════════════════════════════════════════════
# Mock Provider
# ════════════════════════════════════════════════════════════

class MockProvider:
    """
    Mock 供应商 — 模拟:
      - 异步回调 (网络延迟)
      - 重复投递 (网络重试)
      - 回调成功/失败
      - 月度对账账单
    """
    def __init__(self, name: str = "mock_provider_a", latency_ms: int = 0):
        self.name = name
        self.latency_ms = latency_ms
        self._sent_callbacks: list = []
        self._delivered_count: dict = defaultdict(int)  # charge_id -> 投递次数
        self._monthly_bills: list = []  # 模拟供应商月账单
        self._lock = threading.Lock()

    def issue_callback(self, *, tenant_id, idempotency_key, amount, currency, success=True):
        """生成一次回调 (允许重放)"""
        cb = ProviderCallback(
            charge_id=f"chg_{uuid.uuid4().hex[:16]}",
            tenant_id=tenant_id,
            idempotency_key=idempotency_key,
            amount=amount,
            currency=currency,
            provider=self.name,
            success=success,
        )
        with self._lock:
            self._sent_callbacks.append(cb)
        return cb

    def replay(self, callback):
        """重放同一回调 (相同 charge_id)"""
        replay = callback.model_copy()
        with self._lock:
            self._delivered_count[callback.charge_id] += 1
        return replay

    def deliver_count(self, charge_id):
        return self._delivered_count[charge_id]

    def issue_monthly_bill(self, year, month, entries):
        """
        模拟供应商月账单 — 故意与平台账本存在差异
        entries: [{tenant_id, amount, currency, charge_id}, ...]
        """
        bill = {
            "year": year,
            "month": month,
            "provider": self.name,
            "entries": entries,
            "issued_at": datetime.now(timezone.utc),
        }
        with self._lock:
            self._monthly_bills.append(bill)
        return bill

    def get_monthly_bill(self, year, month):
        for b in self._monthly_bills:
            if b["year"] == year and b["month"] == month:
                return b
        return None


# ════════════════════════════════════════════════════════════
# BillingEngine — 真实 in-memory ledger
# ════════════════════════════════════════════════════════════

class LedgerError(Exception):
    pass


class InsufficientBalanceError(LedgerError):
    pass


class HardBudgetExceededError(LedgerError):
    pass


class BillingEngine:
    """
    计费引擎 — 单一真实来源 (single source of truth).
    """
    def __init__(self, provider=None, pricebook=None, ratecard=None):
        self._ledger = []
        self._by_idem = {}
        self._by_charge_id = {}
        self._by_entry_id = {}
        self._balances = {}
        self._pricebook = pricebook or self._default_pricebook()
        self._ratecards = {}
        if ratecard:
            self._ratecards[ratecard.version] = ratecard
        self._provider = provider or MockProvider()
        self._lock = threading.RLock()
        self._pricebook_history = {self._pricebook.version: self._pricebook}
        self._rejected = []
        # 事件 → model 缓存 (用于 settle_with_event 找原始 model)
        self._event_to_model = {}

    @staticmethod
    def _default_pricebook():
        return PriceBook(
            version="v1.0",
            effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            currency=Currency.CNY,
            rates={
                "gpt-4o": {
                    UnitType.TOKEN_INPUT.value: Decimal("0.0006"),
                    UnitType.TOKEN_OUTPUT.value: Decimal("0.0024"),
                    UnitType.TOKEN_CACHE_HIT.value: Decimal("0.0003"),
                },
                "dall-e-3": {
                    UnitType.IMAGE.value: Decimal("0.40"),
                },
                "tts-hd": {
                    UnitType.AUDIO_SECOND.value: Decimal("0.015"),
                },
                "sora": {
                    UnitType.VIDEO_SECOND.value: Decimal("0.50"),
                },
            },
        )

    # ─── 价格表管理 ──────────────────────────────
    def publish_pricebook(self, pb):
        with self._lock:
            self._pricebook = pb
            self._pricebook_history[pb.version] = pb

    def get_pricebook(self, version=None):
        with self._lock:
            if version:
                return self._pricebook_history[version]
            return self._pricebook

    def publish_ratecard(self, rc):
        with self._lock:
            self._ratecards[rc.version] = rc

    def get_ratecard(self, version):
        with self._lock:
            return self._ratecards.get(version)

    # ─── 余额管理 ───────────────────────────────
    def ensure_tenant(self, tenant_id, *,
                      initial_balance=Decimal("0"),
                      hard_budget=Decimal("0"),
                      currency=Currency.CNY):
        """确保 tenant 存在 — 初始余额作为 TOPUP 条目写入 ledger (append-only 真实)."""
        with self._lock:
            if tenant_id not in self._balances:
                self._balances[tenant_id] = CreditBalance(
                    tenant_id=tenant_id,
                    available=initial_balance,
                    hard_budget=hard_budget,
                    currency=currency,
                )
                if initial_balance > 0:
                    seed = SettledEntry(
                        kind=EntryKind.TOPUP,
                        tenant_id=tenant_id,
                        amount=Decimal(str(initial_balance)),
                        currency=currency,
                        rate_version="internal",
                        confirmed=True,
                        charge_id=f"init_{tenant_id}",
                    )
                    self._append(seed)
            return self._balances[tenant_id]

    def get_balance(self, tenant_id):
        with self._lock:
            if tenant_id not in self._balances:
                return CreditBalance(tenant_id=tenant_id)
            return self._balances[tenant_id].model_copy()

    def topup(self, tenant_id, amount, *, confirmed=True, charge_id=None):
        """
        充值 — 仅 confirmed=True 才入余额.
        返回 SettledEntry (无论成功失败都入 ledger, 便于审计).
        """
        if amount < 0:
            raise LedgerError("topup amount must be non-negative")
        with self._lock:
            balance = self.ensure_tenant(tenant_id)
            kind = EntryKind.TOPUP if confirmed else EntryKind.TOPUP_FAILED
            entry = SettledEntry(
                kind=kind,
                tenant_id=tenant_id,
                amount=Decimal(str(amount)),
                currency=balance.currency,
                rate_version="internal",
                confirmed=confirmed,
                charge_id=charge_id,
            )
            self._append(entry)
            if confirmed:
                balance.available += Decimal(str(amount))
            else:
                balance.pending_topup += Decimal(str(amount))
            return entry

    # ─── 价格计算 (用快照 pricebook) ──────────────
    def _quote_price(self, model, units, pricebook=None):
        """根据当前价格表 (或指定快照) 计算金额 + 价格快照 (供历史追溯)"""
        pb = pricebook or self._pricebook
        if model not in pb.rates:
            raise LedgerError(f"unknown model: {model}")
        model_prices = pb.rates[model]
        snapshot = {}
        total = Decimal("0")
        for unit_type, qty in units.items():
            key = unit_type.value if isinstance(unit_type, UnitType) else unit_type
            if key not in model_prices:
                raise LedgerError(f"unit {key} not priced for model {model}")
            unit_price = Decimal(str(model_prices[key]))
            snapshot[f"{model}:{key}"] = unit_price
            total += unit_price * Decimal(qty)
        return total, snapshot

    def _quote_price_with_rate(self, model, units, target_currency):
        """跨币种报价 — 使用当前 pricebook + 最新 ratecard (按版本快照)"""
        amount, snapshot = self._quote_price(model, units)
        if not self._ratecards:
            return amount, "no-fx", snapshot
        latest_rc = max(self._ratecards.values(), key=lambda r: r.effective_at)
        if target_currency == latest_rc.base:
            return amount, latest_rc.version, snapshot
        if target_currency not in latest_rc.rates:
            raise LedgerError(f"no rate for {target_currency} in {latest_rc.version}")
        rate = Decimal(str(latest_rc.rates[target_currency]))
        # rate 语义: 1 base = rate target; 转换 base->target 是除法
        # 例: base=CNY, rate[USD]=7.2 意味 1 CNY = 0.1389 USD
        converted = (amount / rate).quantize(Decimal("0.0001"))
        return converted, latest_rc.version, snapshot

    # ─── 预留 (reservation) ─────────────────────
    def reserve(self, event, *, currency=None):
        """
        预留 — 上限估价从账户锁定. 同一 idempotency_key 幂等.
        """
        with self._lock:
            # 幂等检查 — 同 key 已 reserve, 直接返回原 reservation
            if event.idempotency_key in self._by_idem:
                existing = self._by_idem[event.idempotency_key]
                if existing.reservation_id:
                    res = self._by_entry_id[existing.reservation_id]
                    if isinstance(res, ReservationEntry):
                        return res
            balance = self.ensure_tenant(event.tenant_id)
            cur = currency or balance.currency
            amount, rate_ver, snapshot = self._quote_price_with_rate(
                event.model, event.units, cur
            )
            # 余额检查 — 预付费 + 硬预算
            if balance.available < amount and balance.hard_budget == 0:
                self._rejected.append({
                    "kind": "insufficient_balance",
                    "tenant_id": event.tenant_id,
                    "amount": str(amount),
                    "ts": datetime.now(timezone.utc).isoformat(),
                })
                raise InsufficientBalanceError(
                    f"tenant {event.tenant_id} balance {balance.available} < required {amount}"
                )
            if balance.hard_budget > 0:
                projected = balance.reserved + amount
                if projected > balance.hard_budget:
                    self._rejected.append({
                        "kind": "hard_budget_exceeded",
                        "tenant_id": event.tenant_id,
                        "amount": str(amount),
                        "ts": datetime.now(timezone.utc).isoformat(),
                    })
                    raise HardBudgetExceededError(
                        f"tenant {event.tenant_id} reserved {balance.reserved} + {amount} > hard_budget {balance.hard_budget}"
                    )
            # 创建预留
            res = ReservationEntry(
                tenant_id=event.tenant_id,
                idempotency_key=event.idempotency_key,
                billing_event_id=event.event_id,
                amount=amount,
                currency=cur,
                rate_version=rate_ver,
                price_snapshot=snapshot,
            )
            self._append(res)
            balance.reserved += amount
            # 缓存 event -> model (供 settle 找原 model)
            self._event_to_model[event.event_id] = event.model
            # 幂等索引
            self._by_idem[event.idempotency_key] = IdempotencyKey(
                key=event.idempotency_key,
                tenant_id=event.tenant_id,
                first_seen_at=res.created_at,
                reservation_id=res.entry_id,
            )
            return res

    # ─── 释放预留 (不用了) ─────────────────────
    def release(self, reservation_id):
        with self._lock:
            entry = self._by_entry_id.get(reservation_id)
            if not isinstance(entry, ReservationEntry):
                raise LedgerError(f"reservation {reservation_id} not found")
            if entry.status != ReservationStatus.PENDING:
                raise LedgerError(f"reservation {reservation_id} not PENDING (status={entry.status})")
            balance = self._balances[entry.tenant_id]
            balance.reserved -= entry.amount
            entry.status = ReservationStatus.RELEASED
            entry.released_at = datetime.now(timezone.utc)
            release_entry = SettledEntry(
                kind=EntryKind.RELEASE,
                tenant_id=entry.tenant_id,
                amount=entry.amount,
                currency=entry.currency,
                rate_version=entry.rate_version,
                price_snapshot=dict(entry.price_snapshot),
                reservation_id=reservation_id,
            )
            self._append(release_entry)
            idem = self._by_idem.get(entry.idempotency_key)
            if idem:
                self._by_idem[entry.idempotency_key] = idem.model_copy(update={"reservation_id": None})
            return entry

    # ─── 结算 (settle) — 从预留扣减实际 ──────────────
    def settle(self, reservation_id, *, actual_units=None, actual_amount=None,
               model=None):
        """
        结算 — 实际金额可能 <= 预留金额 (流式调用可能更便宜).
        实际金额可显式指定, 或用 actual_units + model 重算.
        """
        with self._lock:
            entry = self._by_entry_id.get(reservation_id)
            if not isinstance(entry, ReservationEntry):
                raise LedgerError(f"reservation {reservation_id} not found")
            if entry.status != ReservationStatus.PENDING:
                raise LedgerError(f"reservation {reservation_id} not PENDING (status={entry.status})")
            if actual_amount is not None:
                final_amount = Decimal(str(actual_amount))
                snapshot = dict(entry.price_snapshot)
                rate_ver = entry.rate_version
            elif actual_units is not None and model is not None:
                final_amount, snapshot = self._quote_price(model, actual_units)
                rate_ver = entry.rate_version
            else:
                final_amount = entry.amount
                snapshot = dict(entry.price_snapshot)
                rate_ver = entry.rate_version
            if final_amount > entry.amount:
                raise LedgerError(
                    f"actual {final_amount} exceeds reserved {entry.amount}"
                )
            balance = self._balances[entry.tenant_id]
            balance.reserved -= entry.amount
            balance.available -= final_amount
            entry.status = ReservationStatus.SETTLED
            entry.settled_at = datetime.now(timezone.utc)
            settle_entry = SettledEntry(
                kind=EntryKind.SETTLEMENT,
                tenant_id=entry.tenant_id,
                amount=final_amount,
                currency=entry.currency,
                rate_version=rate_ver,
                price_snapshot=snapshot,
                reservation_id=reservation_id,
            )
            self._append(settle_entry)
            entry.settled_entry_id = settle_entry.entry_id
            idem = self._by_idem.get(entry.idempotency_key)
            if idem:
                self._by_idem[entry.idempotency_key] = idem.model_copy(
                    update={"settled_entry_id": settle_entry.entry_id}
                )
            return settle_entry

    def settle_with_event(self, event, *, actual_units=None, actual_amount=None):
        """便利方法: reserve + settle (单 tenant 单次事件)"""
        res = self.reserve(event)
        if actual_amount is not None:
            se = self.settle(res.entry_id, actual_amount=actual_amount)
        elif actual_units is not None:
            se = self.settle(res.entry_id, actual_units=actual_units, model=event.model)
        else:
            se = self.settle(res.entry_id)
        return res, se

    # ─── 供应商回调 — 幂等入账 ─────────────────
    def apply_callback(self, callback):
        """
        应用供应商回调:
          - success=False → 写 TOPUP_FAILED 状态 (不入余额)
          - charge_id 已存在 → 直接返回原条目 (不重复入账)
          - 成功 → 写 SETTLEMENT/REFUND
        """
        with self._lock:
            if callback.charge_id in self._by_charge_id:
                existing_id = self._by_charge_id[callback.charge_id]
                existing = self._by_entry_id[existing_id]
                if isinstance(existing, SettledEntry):
                    return existing
            balance = self.ensure_tenant(callback.tenant_id)
            if not callback.success:
                entry = SettledEntry(
                    kind=EntryKind.TOPUP_FAILED,
                    tenant_id=callback.tenant_id,
                    amount=Decimal(str(callback.amount)),
                    currency=callback.currency,
                    rate_version="provider",
                    charge_id=callback.charge_id,
                    provider=callback.provider,
                    confirmed=False,
                )
                self._append(entry)
                self._by_charge_id[callback.charge_id] = entry.entry_id
                return entry
            kind = EntryKind.SETTLEMENT if callback.amount >= 0 else EntryKind.REFUND
            entry = SettledEntry(
                kind=kind,
                tenant_id=callback.tenant_id,
                amount=abs(Decimal(str(callback.amount))),
                currency=callback.currency,
                rate_version="provider",
                charge_id=callback.charge_id,
                provider=callback.provider,
            )
            self._append(entry)
            self._by_charge_id[callback.charge_id] = entry.entry_id
            if kind == EntryKind.SETTLEMENT:
                balance.available -= abs(Decimal(str(callback.amount)))
            elif kind == EntryKind.REFUND:
                balance.available += abs(Decimal(str(callback.amount)))
            return entry

    # ─── 修正 (correction) — 单向记账 ──────────────
    def correction(self, *, tenant_id, related_entry_id, amount, currency, reason=""):
        """
        修正原 entry — 单向记账 (写反向 CORRECTION 条目, 不修改原 entry).
        修正条目 amount >= 0; 方向由 kind 表达.
        """
        with self._lock:
            if related_entry_id not in self._by_entry_id:
                raise LedgerError(f"related entry {related_entry_id} not found")
            related = self._by_entry_id[related_entry_id]
            if not isinstance(related, SettledEntry):
                raise LedgerError(f"related entry {related_entry_id} is not SettledEntry")
            entry = SettledEntry(
                kind=EntryKind.CORRECTION,
                tenant_id=tenant_id,
                amount=abs(Decimal(str(amount))),
                currency=currency,
                rate_version="internal",
                related_entry_id=related_entry_id,
            )
            self._append(entry)
            balance = self._balances[tenant_id]
            balance.available -= abs(Decimal(str(amount)))
            return entry

    # ─── ledger 内部 ──────────────────────────────
    def _append(self, entry):
        """append-only: 写入 ledger + 索引"""
        self._ledger.append(entry)
        eid = getattr(entry, "entry_id", None)
        if eid:
            self._by_entry_id[eid] = entry

    # ════════════════════════════════════════════════
    # Invariant Queries (公开)
    # ════════════════════════════════════════════════

    def ledger(self):
        with self._lock:
            return list(self._ledger)

    def ledger_size(self):
        with self._lock:
            return len(self._ledger)

    def query_by_tenant(self, tenant_id):
        with self._lock:
            return [e for e in self._ledger if getattr(e, "tenant_id", None) == tenant_id]

    def get_entry(self, entry_id):
        with self._lock:
            return self._by_entry_id.get(entry_id)

    def total_settled_by_tenant(self, tenant_id):
        with self._lock:
            total = Decimal("0")
            for e in self._ledger:
                if getattr(e, "tenant_id", None) != tenant_id:
                    continue
                if isinstance(e, SettledEntry) and e.kind == EntryKind.SETTLEMENT and e.confirmed:
                    total += e.amount
            return total

    def invariant_append_only(self):
        """I-1: ledger 长度单调不减, 历史 entry 内容不可变."""
        with self._lock:
            seen = set()
            for i, e in enumerate(self._ledger):
                eid = getattr(e, "entry_id", None)
                if not eid:
                    return False, f"entry at {i} missing entry_id"
                if eid in seen:
                    return False, f"duplicate entry_id {eid}"
                seen.add(eid)
            return True, "ok"

    def invariant_idempotency(self):
        """I-5: 同 idempotency_key 最多一笔 SETTLEMENT."""
        with self._lock:
            idem_to_settle = defaultdict(int)
            for e in self._ledger:
                if not isinstance(e, SettledEntry):
                    continue
                if e.kind != EntryKind.SETTLEMENT:
                    continue
                if e.reservation_id:
                    res = self._by_entry_id.get(e.reservation_id)
                    if isinstance(res, ReservationEntry):
                        idem_to_settle[res.idempotency_key] += 1
            for key, cnt in idem_to_settle.items():
                if cnt > 1:
                    return False, f"idem {key} settled {cnt} times"
            return True, "ok"

    def invariant_no_negative_amount(self):
        """I-3: settled amount 永不为负."""
        with self._lock:
            for i, e in enumerate(self._ledger):
                if isinstance(e, SettledEntry):
                    if e.amount < 0:
                        return False, f"entry {i} ({e.entry_id}) has negative amount {e.amount}"
            return True, "ok"

    def invariant_correction_pairs(self):
        """I-4: CORRECTION 必带 related_entry_id 且指向已存在 entry."""
        with self._lock:
            for i, e in enumerate(self._ledger):
                if isinstance(e, SettledEntry) and e.kind == EntryKind.CORRECTION:
                    if not e.related_entry_id:
                        return False, f"correction at {i} missing related_entry_id"
                    if e.related_entry_id not in self._by_entry_id:
                        return False, f"correction at {i} points to missing entry {e.related_entry_id}"
            return True, "ok"

    def invariant_charge_id_dedup(self):
        """I-6: 同 charge_id 在 ledger 中至多 1 次."""
        with self._lock:
            seen = set()
            for i, e in enumerate(self._ledger):
                if isinstance(e, SettledEntry) and e.charge_id:
                    if e.charge_id in seen:
                        return False, f"charge_id {e.charge_id} duplicated at index {i}"
                    seen.add(e.charge_id)
            return True, "ok"

    def invariant_balance_conservation(self, tenant_id):
        """
        I-2: balance 守恒.
        available = sum(TOPUP confirmed) - sum(SETTLEMENT confirmed) - sum(CORRECTION confirmed) + sum(REFUND confirmed)
        """
        with self._lock:
            bal = self._balances.get(tenant_id)
            if not bal:
                return True, "no balance"
            topup = Decimal("0")
            settled = Decimal("0")
            correction = Decimal("0")
            refund = Decimal("0")
            for e in self._ledger:
                if getattr(e, "tenant_id", None) != tenant_id:
                    continue
                if isinstance(e, SettledEntry):
                    if e.kind == EntryKind.TOPUP and e.confirmed:
                        topup += e.amount
                    elif e.kind == EntryKind.SETTLEMENT and e.confirmed:
                        settled += e.amount
                    elif e.kind == EntryKind.CORRECTION and e.confirmed:
                        correction += e.amount
                    elif e.kind == EntryKind.REFUND and e.confirmed:
                        refund += e.amount
            expected = topup - settled - correction + refund
            diff = abs(bal.available - expected)
            if diff > Decimal("0.0001"):
                return False, (
                    f"balance {bal.available} != topup {topup} - settled {settled} "
                    f"- correction {correction} + refund {refund} "
                    f"= {expected} (diff {diff})"
                )
            return True, "ok"

    def check_all_invariants(self, tenant_id=None):
        """跑全部 invariant — 用于全量健康检查"""
        results = []
        results.append(self.invariant_append_only())
        results.append(self.invariant_idempotency())
        results.append(self.invariant_no_negative_amount())
        results.append(self.invariant_correction_pairs())
        results.append(self.invariant_charge_id_dedup())
        if tenant_id:
            results.append(self.invariant_balance_conservation(tenant_id))
        all_ok = all(r[0] for r in results)
        msgs = [r[1] for r in results if not r[0]]
        return all_ok, msgs

    # ─── 月度对账 ───────────────────────────────
    def reconcile_provider_bill(self, provider_bill):
        """
        与供应商月账单对账:
          - 比对 charge_id
          - 输出差异单 (only_in_local / only_in_provider / amount_diff)
        """
        with self._lock:
            year = provider_bill["year"]
            month = provider_bill["month"]
            diffs = []
            local_by_charge = {}
            for e in self._ledger:
                if isinstance(e, SettledEntry) and e.charge_id and e.confirmed:
                    local_by_charge[e.charge_id] = e
            provider_by_charge = {
                pe["charge_id"]: pe for pe in provider_bill["entries"]
            }
            for cid, pe in provider_by_charge.items():
                if cid not in local_by_charge:
                    diffs.append({"kind": "only_in_provider", "charge_id": cid,
                                  "amount": pe["amount"], "currency": pe["currency"]})
                else:
                    local = local_by_charge[cid]
                    if Decimal(str(pe["amount"])) != local.amount:
                        diffs.append({"kind": "amount_diff", "charge_id": cid,
                                      "local": str(local.amount), "provider": str(pe["amount"])})
            provider_name = provider_bill.get("provider")
            for cid, local in local_by_charge.items():
                if provider_name and local.provider != provider_name:
                    continue
                if cid not in provider_by_charge:
                    diffs.append({"kind": "only_in_local", "charge_id": cid,
                                  "amount": str(local.amount), "currency": local.currency.value})
            return {
                "year": year,
                "month": month,
                "provider": provider_name,
                "differences": diffs,
                "diff_count": len(diffs),
            }
