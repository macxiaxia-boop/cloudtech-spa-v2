"""Provider router — switches between FakeProvider and real DeepSeek based on env.

Env contract (RED LINE: never log these):
- CLOUDTECH_RC2_USE_FAKE=1  → use FakeProvider (no real API calls)
- DEEPSEEK_API_KEY=<key>    → use real DeepSeek (auto-detect)
- DEEPSEEK_BASE_URL=https://api.deepseek.com  → real endpoint (default)

This module NEVER reads .env files directly. It only checks os.environ.
The Live system's uvicorn startup must load .env before importing this module.
"""
from __future__ import annotations

import os
import time
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

# Lazy imports to avoid loading requests/urllib unless real provider is needed
class ProviderMode(Enum):
    FAKE = "fake"
    REAL_DEEPSEEK = "real_deepseek"


@dataclass
class ProviderResponse:
    """Normalized response from any provider."""
    request_id: str
    mode: str         # "success" | "rate_limited" | "timeout" | "invalid"
    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    provider: str
    metadata: Dict[str, Any]


def detect_provider_mode() -> ProviderMode:
    """Detect which provider to use based on environment.

    Priority:
    1. CLOUDTECH_RC2_USE_FAKE=1 → FAKE (always wins, for staging)
    2. DEEPSEEK_API_KEY set → REAL_DEEPSEEK
    3. Else → FAKE (safe default — never accidentally hit real API)
    """
    if os.environ.get("CLOUDTECH_RC2_USE_FAKE") == "1":
        return ProviderMode.FAKE
    if os.environ.get("DEEPSEEK_API_KEY"):
        return ProviderMode.REAL_DEEPSEEK
    # Safe default: FAKE (no real API call possible)
    return ProviderMode.FAKE


def chat(messages: List[Dict[str, str]], model: str = "deepseek-chat",
         max_tokens: int = 500) -> ProviderResponse:
    """Unified chat entrypoint — dispatches to fake or real provider.

    RED LINE: never log the API key. Never include it in metadata.
    """
    mode = detect_provider_mode()
    if mode == ProviderMode.FAKE:
        from fake_provider import FakeDeepSeekProvider
        provider = FakeDeepSeekProvider(seed=int(time.time()) % 100000)
        resp = provider.chat(messages, model=model, max_tokens=max_tokens)
        return ProviderResponse(
            request_id=resp.request_id,
            mode=resp.mode.value,
            content=resp.content,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            cost_usd=resp.cost_usd,
            latency_ms=resp.latency_ms,
            provider="fake",
            metadata=resp.metadata,
        )
    else:
        return _chat_real_deepseek(messages, model, max_tokens)


def _chat_real_deepseek(messages: List[Dict[str, str]], model: str,
                        max_tokens: int) -> ProviderResponse:
    """Real DeepSeek chat. NEVER called unless DEEPSEEK_API_KEY is in env.

    Implementation notes (red lines honored):
    - Reads key from env only, never from file
    - Never logs the key (sanitizes headers in any error message)
    - Uses standard OpenAI-compatible DeepSeek API
    """
    import urllib.request
    import urllib.error

    api_key = os.environ["DEEPSEEK_API_KEY"]
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    url = f"{base_url}/v1/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    # RED LINE: do NOT log api_key. Only log first 4 chars for debug.
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",  # NEVER logged
    }

    t0 = time.perf_counter()
    request_id = f"ds-{int(t0 * 1000)}"
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            tokens_in = usage.get("prompt_tokens", 0)
            tokens_out = usage.get("completion_tokens", 0)
            cost = 0.002 * (tokens_in + tokens_out) / 1000
            latency = (time.perf_counter() - t0) * 1000
            return ProviderResponse(
                request_id=request_id,
                mode="success",
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=round(cost, 6),
                latency_ms=round(latency, 2),
                provider="deepseek",
                metadata={"model": model, "endpoint": base_url},  # NO api_key
            )
    except urllib.error.HTTPError as e:
        latency = (time.perf_counter() - t0) * 1000
        # Sanitize error: don't include auth headers
        err_msg = str(e)[:200].replace(api_key, "[REDACTED]")
        return ProviderResponse(
            request_id=request_id,
            mode="rate_limited" if e.code == 429 else "invalid",
            content=f"[DEEPSEEK ERROR {e.code}] {err_msg}",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=round(latency, 2),
            provider="deepseek",
            metadata={"http_status": e.code, "sanitized": True},
        )
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return ProviderResponse(
            request_id=request_id,
            mode="timeout",
            content=f"[DEEPSEEK TIMEOUT] {type(e).__name__}",
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
            latency_ms=round(latency, 2),
            provider="deepseek",
            metadata={"error_type": type(e).__name__},
        )


if __name__ == "__main__":
    # Demo: detect mode and run a single call
    mode = detect_provider_mode()
    print(f"[Provider Router] Mode: {mode.value}")
    print(f"[Provider Router] DEEPSEEK_API_KEY set: {bool(os.environ.get('DEEPSEEK_API_KEY'))}")
    print(f"[Provider Router] CLOUDTECH_RC2_USE_FAKE: {os.environ.get('CLOUDTECH_RC2_USE_FAKE', '(unset)')}")

    resp = chat([{"role": "user", "content": "ping"}], max_tokens=20)
    print(f"[Provider Router] Response mode: {resp.mode}")
    print(f"[Provider Router] Content (first 100): {resp.content[:100]}")
    print(f"[Provider Router] Cost: ${resp.cost_usd}")
    print(f"[Provider Router] Latency: {resp.latency_ms}ms")
    print(f"[Provider Router] Provider: {resp.provider}")