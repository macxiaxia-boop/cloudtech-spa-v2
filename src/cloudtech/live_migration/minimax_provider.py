"""minimax-M3 Provider — Atlas Cloud OpenAI-compatible chat.

Replaces DeepSeek for CloudTech Live integration (per user authorization 2026-09-25).

Env contract (RED LINE: never log these):
- MINIMAX_API_KEY=<key>          → use real minimax-M3 (auto-detect)
- MINIMAX_BASE_URL=https://api.atlascloud.ai  → default endpoint
- MINIMAX_MODEL=minimaxai/minimax-m3 → default model
- CLOUDTECH_RC2_USE_FAKE=1       → use FakeProvider (always wins for staging)
- CLOUDTECH_RC2_USE_MINIMAX=1    → prefer minimax over DeepSeek if both set

This module NEVER reads .env files directly. Only os.environ.
"""
from __future__ import annotations

import os
import time
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


DEFAULT_BASE_URL = "https://api.atlascloud.ai"
DEFAULT_MODEL = "minimaxai/minimax-m3"


@dataclass
class MinimaxResponse:
    """Normalized response from minimax-M3 via Atlas Cloud."""
    request_id: str
    mode: str            # "success" | "rate_limited" | "timeout" | "invalid"
    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    provider: str
    metadata: Dict[str, Any]


def detect_minimax_available() -> bool:
    """Check if minimax-M3 is configured (without exposing key value)."""
    return bool(os.environ.get("MINIMAX_API_KEY"))


def chat_minimax(messages: List[Dict[str, str]],
                 model: str = DEFAULT_MODEL,
                 max_tokens: int = 500,
                 temperature: float = 0.7) -> MinimaxResponse:
    """Call minimax-M3 via Atlas Cloud OpenAI-compatible endpoint.

    RED LINES honored:
    - Reads key from env only, never from file
    - Never logs the key (sanitizes headers in error messages)
    - Standard OpenAI chat completions schema
    """
    import urllib.request
    import urllib.error

    api_key = os.environ["MINIMAX_API_KEY"]
    base_url = os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE_URL)
    model_id = os.environ.get("MINIMAX_MODEL", model)
    url = f"{base_url}/v1/chat/completions"

    payload = json.dumps({
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",   # NEVER logged
    }

    t0 = time.perf_counter()
    request_id = f"minimax-{int(t0 * 1000)}"
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            # Atlas Cloud minimax-m3 pricing: $0.3/M in, $1.2/M out (50% discount applied)
            cost = (0.30 * tokens_in / 1_000_000) + (1.20 * tokens_out / 1_000_000)
            cost *= 0.5   # 50% discount
            latency = (time.perf_counter() - t0) * 1000
            return MinimaxResponse(
                request_id=request_id,
                mode="success",
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=round(cost, 6),
                latency_ms=round(latency, 2),
                provider="minimax-m3",
                metadata={"model": model_id, "endpoint": base_url},   # NO api_key
            )
    except urllib.error.HTTPError as e:
        latency = (time.perf_counter() - t0) * 1000
        err_msg = str(e)[:200].replace(api_key, "[REDACTED]")
        return MinimaxResponse(
            request_id=request_id,
            mode="rate_limited" if e.code == 429 else "invalid",
            content=f"[MINIMAX ERROR {e.code}] {err_msg}",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=round(latency, 2),
            provider="minimax-m3",
            metadata={"http_status": e.code, "sanitized": True},
        )
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return MinimaxResponse(
            request_id=request_id,
            mode="timeout",
            content=f"[MINIMAX TIMEOUT] {type(e).__name__}",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=round(latency, 2),
            provider="minimax-m3",
            metadata={"error_type": type(e).__name__},
        )


if __name__ == "__main__":
    print(f"[minimax Provider] detect_minimax_available={detect_minimax_available()}")
    if detect_minimax_available():
        resp = chat_minimax([{"role": "user", "content": "Reply with exactly: pong"}], max_tokens=20)
        print(f"[minimax Provider] mode={resp.mode}")
        print(f"[minimax Provider] content={resp.content[:100]}")
        print(f"[minimax Provider] cost=${resp.cost_usd}")
        print(f"[minimax Provider] latency={resp.latency_ms}ms")
    else:
        print("[minimax Provider] MINIMAX_API_KEY not set in env — set it before running")