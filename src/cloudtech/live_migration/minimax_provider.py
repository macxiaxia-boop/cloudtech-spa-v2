"""minimax-M3 Provider — self-referential session model (NO API KEY, NO EXTERNAL CALL).

Per user clarification 2026-09-25:
- minimax-M3 IS the current Claude Code session model (self-referential)
- No API key required
- Atlas Cloud has been RETIRED (user said "说了几十遍了")
- This module is a structural integration point, not an HTTP client

When this provider is invoked:
- The actual chat call is made by Claude Code itself (the session model)
- This module returns a normalized ProviderResponse shape for downstream tooling
- For automated testing without Claude Code, use FakeProvider (CLOUDTECH_RC2_USE_FAKE=1)

Env contract (RED LINE: never log these):
- CLOUDTECH_RC2_USE_FAKE=1     → use FakeProvider (always wins for staging)
- CLOUDTECH_RC2_USE_MINIMAX=1  → prefer minimax-M3 (default if no DeepSeek key)
- (no MINIMAX_API_KEY needed)  → session model is self-referential

Detection logic in provider_router.detect_provider_mode():
1. CLOUDTECH_RC2_USE_FAKE=1 → FAKE
2. CLOUDTECH_RC2_USE_MINIMAX=1 → MINIMAX_M3
3. DEEPSEEK_API_KEY set → REAL_DEEPSEEK
4. Else → MINIMAX_M3 (default — session model is always available)
"""
from __future__ import annotations

import os
import time
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MinimaxResponse:
    """Normalized response from minimax-M3 session model."""
    request_id: str
    mode: str            # "success" | "rate_limited" | "timeout" | "invalid"
    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    provider: str
    metadata: Dict[str, Any]


def chat_minimax(messages: List[Dict[str, str]],
                 model: str = "minimax-m3",
                 max_tokens: int = 500) -> MinimaxResponse:
    """Compatibility shim, NOT a callable model provider.

    Being in a Claude Code session does not grant this Python process
    implicit model execution. Never echo user prompts as model output.
    """
    return MinimaxResponse(
        request_id="not-dispatched",
        mode="invalid",
        content="[MODEL_NOT_CONNECTED] MiniMax model API is not configured",
        tokens_in=0,
        tokens_out=0,
        cost_usd=0.0,
        latency_ms=0.0,
        provider="unavailable",
        metadata={
            "model": model,
            "model_call_executed": False,
            "billable": False,
            "reason": "Session model is not an HTTP or local inference API",
        },
    )


if __name__ == "__main__":
    print("[minimax Provider] self-referential session model")
    print("[minimax Provider] no API key, no Atlas Cloud, no HTTP")
    print(f"[minimax Provider] CLOUDTECH_RC2_USE_FAKE = {os.environ.get('CLOUDTECH_RC2_USE_FAKE', '(unset)')}")
    resp = chat_minimax([{"role": "user", "content": "ping"}], max_tokens=20)
    print(f"[minimax Provider] mode={resp.mode}")
    print(f"[minimax Provider] content={resp.content[:100]}")
    print(f"[minimax Provider] cost=${resp.cost_usd}")
    print(f"[minimax Provider] latency={resp.latency_ms}ms")