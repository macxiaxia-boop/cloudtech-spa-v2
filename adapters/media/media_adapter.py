"""MediaAdapter — 主入口，集成门禁+幂等+预算"""
from __future__ import annotations
import uuid

from workflows.v4.media_gate import MediaGate
from workflows.v4.budget import BudgetGate, CostClass, BudgetError
from workflows.v4.idempotency import IdempotencyStore

from .types import MediaRequest, MediaResponse, ProviderError
from .provider_registry import ProviderRegistry
from .media_gate_integration import dispatch as _dispatch


class MediaAdapter:
    """媒体生成主适配器

    流程:
      1. MediaGate.check     — 白名单/黑名单门禁
      2. IdempotencyStore   — 同 key 返回已有结果，不重做
      3. BudgetGate.reserve — 预算预占
      4. ProviderRegistry   — mock stub dispatch
      5. BudgetGate.settle — 结算
      6. IdempotencyStore.bind — 持久化 hit (首次请求)
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        budget_gate: BudgetGate,
        idempotency_store: IdempotencyStore,
    ) -> None:
        self.registry = registry
        self.budget = budget_gate
        self.idem = idempotency_store

    def request(self, req: MediaRequest) -> MediaResponse:
        # ── 1. 门禁 ──────────────────────────────────────────
        MediaGate.check(req.operation, req.cost_class)

        # ── 2. 幂等检查 ────────────────────────────────────
        hit = self.idem.check(req.idempotency_key)
        if hit is not None and hit.provider_req_id is not None:
            return MediaResponse(
                request_id=hit.provider_req_id,
                provider="cached",
                operation=req.operation,
                output_assets=[{"url": "mock://cached", "mime": "image/png",
                                 "sha256": "cached", "mock": True}],
                actual_cost_cents=0,
                duration_ms=0,
                mock=True,
            )

        # ── 3. 预算预占 ────────────────────────────────────
        cost_cls = CostClass(req.cost_class)
        cap = 10_000
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        reservation = self.budget.reserve(
            tenant_id=req.tenant_id,
            run_id=run_id,
            node_id=None,
            cost_class=cost_cls,
            cents=req.estimated_cost_cents,
            cap_cents=cap,
        )

        try:
            # ── 4. Provider dispatch ─────────────────────────
            resp = _dispatch(req, self.registry)

            # ── 5. 结算 ────────────────────────────────────
            self.budget.settle(reservation.reservation_id, resp.actual_cost_cents)

            # ── 6. 持久化 idempotency hit ──────────────────
            self.idem.bind(req.idempotency_key, run_id, None)
            self.idem.set_provider_req_id(req.idempotency_key, resp.request_id)

            return resp

        except Exception:
            self.budget.release(reservation.reservation_id)
            raise
