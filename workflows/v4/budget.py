"""V4 — 预算门禁
FREE_LOCAL / METERED_NONMEDIA / METERED_MEDIA / EXTERNAL_WRITE
估价 → reserve → user/tenant 授权 → 执行 → settle → release
重跑仅在上游状态明确后执行；严禁伪报"失败不扣费"
"""
from __future__ import annotations
import secrets
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class CostClass(str, Enum):
    FREE_LOCAL = "FREE_LOCAL"
    METERED_NONMEDIA = "METERED_NONMEDIA"
    METERED_MEDIA = "METERED_MEDIA"
    EXTERNAL_WRITE = "EXTERNAL_WRITE"


# cost_class → 默认需要授权
COST_CLASS_NEEDS_APPROVAL = {
    CostClass.FREE_LOCAL: False,
    CostClass.METERED_NONMEDIA: False,
    CostClass.METERED_MEDIA: True,
    CostClass.EXTERNAL_WRITE: True,
}


@dataclass
class BudgetReservation:
    reservation_id: str
    tenant_id: str
    run_id: str
    node_id: Optional[str]
    cost_class: CostClass
    reserve_cents: int
    settled_cents: int = 0
    released_cents: int = 0
    status: str = "reserved"  # reserved/settled/released/over
    created_at: str = field(default_factory=lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat())


class BudgetError(Exception):
    pass


class BudgetGate:
    """线程安全预算门 — 预占 → 结算 / 释放"""

    _instance: Optional["BudgetGate"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # tenant_id → 已结算 cents
        self._spent: Dict[str, int] = {}
        # reservation_id → BudgetReservation
        self._reservations: Dict[str, BudgetReservation] = {}
        self._mtx = threading.Lock()

    @classmethod
    def instance(cls) -> "BudgetGate":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = BudgetGate()
        return cls._instance

    def reserve(
        self,
        tenant_id: str,
        run_id: str,
        node_id: Optional[str],
        cost_class: CostClass,
        cents: int,
        cap_cents: int,
    ) -> BudgetReservation:
        if cost_class not in COST_CLASS_NEEDS_APPROVAL and cents <= 0:
            raise BudgetError(f"[BG-001] 非法 cents={cents} for {cost_class}")
        with self._mtx:
            spent = self._spent.get(tenant_id, 0)
            if cap_cents > 0 and (spent + cents) > cap_cents:
                raise BudgetError(
                    f"[BG-002] 预算超限 tenant={tenant_id} spent={spent} "
                    f"reserve={cents} cap={cap_cents}"
                )
            res = BudgetReservation(
                reservation_id="res_" + secrets.token_hex(6),
                tenant_id=tenant_id,
                run_id=run_id,
                node_id=node_id,
                cost_class=cost_class,
                reserve_cents=cents,
            )
            self._reservations[res.reservation_id] = res
            return res

    def settle(self, reservation_id: str, actual_cents: int) -> BudgetReservation:
        with self._mtx:
            res = self._reservations.get(reservation_id)
            if res is None:
                raise BudgetError(f"[BG-003] reservation {reservation_id} not found")
            if res.status != "reserved":
                raise BudgetError(f"[BG-004] reservation {reservation_id} already {res.status}")
            actual = max(0, min(actual_cents, res.reserve_cents))
            res.settled_cents = actual
            res.status = "settled"
            self._spent[res.tenant_id] = self._spent.get(res.tenant_id, 0) + actual
            return res

    def release(self, reservation_id: str) -> BudgetReservation:
        with self._mtx:
            res = self._reservations.get(reservation_id)
            if res is None:
                raise BudgetError(f"[BG-003] reservation {reservation_id} not found")
            if res.status == "settled":
                raise BudgetError(f"[BG-005] reservation {reservation_id} already settled")
            res.released_cents = res.reserve_cents - res.settled_cents
            res.status = "released"
            return res

    def get_spent(self, tenant_id: str) -> int:
        with self._mtx:
            return self._spent.get(tenant_id, 0)

    def reset(self) -> None:
        with self._mtx:
            self._spent.clear()
            self._reservations.clear()
