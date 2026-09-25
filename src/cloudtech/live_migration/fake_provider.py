"""Fake DeepSeek provider — safe smoke test endpoint that does NOT make real API calls.

Used for:
- End-to-end Wave 10 smoke test without real Provider credentials
- Local validation of Candidate router + effect ledger + approval flow
- Cutover dry-run before production traffic
"""
from __future__ import annotations

import json
import time
import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class FakeResponseMode(Enum):
    SUCCESS = "success"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    INVALID = "invalid"


@dataclass
class FakeResponse:
    """Mocked LLM response."""
    request_id: str
    mode: FakeResponseMode
    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeProviderStats:
    """Aggregate stats."""
    total_requests: int
    by_mode: Dict[str, int]
    total_cost_usd: float
    avg_latency_ms: float
    success_rate_pct: float


class FakeDeepSeekProvider:
    """Safe fake provider — no network calls, deterministic responses for testing."""

    RATE = 0.002  # USD per 1K tokens

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        self.calls: List[Dict[str, Any]] = []

    def chat(self, messages: List[Dict[str, str]], model: str = "deepseek-chat",
             max_tokens: int = 500, force_mode: Optional[FakeResponseMode] = None) -> FakeResponse:
        """Simulate DeepSeek chat completion."""
        t0 = time.perf_counter()
        request_id = hashlib.sha256(f"{time.time()}{messages}".encode()).hexdigest()[:16]

        # Determine mode
        if force_mode:
            mode = force_mode
        else:
            # 95% success, 3% rate-limited, 1.5% timeout, 0.5% invalid
            r = random.random()
            if r < 0.95:
                mode = FakeResponseMode.SUCCESS
            elif r < 0.98:
                mode = FakeResponseMode.RATE_LIMITED
            elif r < 0.995:
                mode = FakeResponseMode.TIMEOUT
            else:
                mode = FakeResponseMode.INVALID

        # Construct response
        prompt_text = " ".join(m.get("content", "") for m in messages)
        tokens_in = max(1, len(prompt_text) // 4)
        tokens_out = 0
        content = ""
        cost = 0.0

        if mode == FakeResponseMode.SUCCESS:
            tokens_out = random.randint(50, max_tokens)
            content = f"[FAKE-DEEPSEEK-RESPONSE] Generated content for: {prompt_text[:50]}... [{tokens_out} tokens]"
            cost = self.RATE * (tokens_in + tokens_out) / 1000
        elif mode == FakeResponseMode.RATE_LIMITED:
            content = "[ERROR] 429 Too Many Requests"
            cost = 0.0
        elif mode == FakeResponseMode.TIMEOUT:
            content = "[ERROR] Request timed out"
            cost = 0.0
        elif mode == FakeResponseMode.INVALID:
            content = "[ERROR] Invalid request parameters"
            cost = 0.0

        latency = (time.perf_counter() - t0) * 1000 + random.uniform(50, 200)  # simulate API latency

        response = FakeResponse(
            request_id=request_id,
            mode=mode,
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(cost, 6),
            latency_ms=round(latency, 2),
            metadata={"model": model, "max_tokens": max_tokens, "seed": self.seed},
        )
        self.calls.append({
            "request_id": request_id,
            "mode": mode.value,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": response.cost_usd,
            "latency_ms": response.latency_ms,
        })
        return response

    def get_stats(self) -> FakeProviderStats:
        """Get aggregate stats."""
        if not self.calls:
            return FakeProviderStats(0, {}, 0.0, 0.0, 0.0)
        by_mode = {}
        for c in self.calls:
            by_mode[c["mode"]] = by_mode.get(c["mode"], 0) + 1
        total_cost = sum(c["cost_usd"] for c in self.calls)
        avg_latency = sum(c["latency_ms"] for c in self.calls) / len(self.calls)
        success = by_mode.get("success", 0)
        success_rate = round(100.0 * success / len(self.calls), 2)
        return FakeProviderStats(
            total_requests=len(self.calls),
            by_mode=by_mode,
            total_cost_usd=round(total_cost, 6),
            avg_latency_ms=round(avg_latency, 2),
            success_rate_pct=success_rate,
        )


def main():
    """Run Fake Provider smoke test."""
    print("[Fake Provider] Smoke test — 50 simulated requests")
    provider = FakeDeepSeekProvider(seed=42)

    test_messages = [
        [{"role": "user", "content": "写一篇关于AI的小红书文案"}],
        [{"role": "user", "content": "分析竞品:瑞幸 vs 星巴克"}],
        [{"role": "user", "content": "生成视频封面"}],
        [{"role": "user", "content": "违禁词检测"}],
        [{"role": "user", "content": "知识库查询"}],
    ] * 10  # 50 requests

    for i, messages in enumerate(test_messages, 1):
        resp = provider.chat(messages)
        if i <= 5 or i % 10 == 0:
            print(f"  [{i:3d}] {resp.mode.value:15s} | {resp.tokens_in}→{resp.tokens_out} tokens | ${resp.cost_usd:.6f} | {resp.latency_ms:.1f}ms")

    stats = provider.get_stats()
    print(f"\n[Fake Provider] Stats:")
    print(f"  Total: {stats.total_requests}")
    print(f"  By mode: {stats.by_mode}")
    print(f"  Total cost: ${stats.total_cost_usd:.6f} (REAL cost would be this much)")
    print(f"  Avg latency: {stats.avg_latency_ms:.2f} ms")
    print(f"  Success rate: {stats.success_rate_pct}%")

    output_path = Path("D:/CloudTech-Live-Execution/CloudTech_rc2_Live_Direct_Execution_20260925/artifacts/wave10_fake_provider.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "title": "Fake DeepSeek Provider — Wave 10 Smoke Test",
        "seed": 42,
        "stats": {
            "total_requests": stats.total_requests,
            "by_mode": stats.by_mode,
            "total_cost_usd_real_equivalent": stats.total_cost_usd,
            "avg_latency_ms": stats.avg_latency_ms,
            "success_rate_pct": stats.success_rate_pct,
        },
        "note": "FAKE — no real API calls. Real cost equivalent shown for budget estimation.",
        "calls_sample": provider.calls[:10],
    }
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Fake Provider] Emitted: {output_path}")
    print(f"[Fake Provider] PASS: no real API calls made (cost = $0 actual)")


if __name__ == "__main__":
    main()
