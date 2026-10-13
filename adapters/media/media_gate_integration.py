"""MediaGate 集成层 — 门禁 + dispatch"""
from workflows.v4.media_gate import MediaGate, MediaGateError
from .types import MediaRequest, MediaResponse
from .provider_registry import ProviderRegistry


def dispatch(req: MediaRequest, registry: ProviderRegistry) -> MediaResponse:
    """严格门禁 → ProviderRegistry.dispatch

    流程:
      1. MediaGate.check (白名单/黑名单两层)
      2. ProviderRegistry.dispatch (mock stub)
    """
    MediaGate.check(req.operation, req.cost_class)
    return registry.dispatch(req)
