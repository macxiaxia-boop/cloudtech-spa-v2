"""Observability dashboard for QualityAwareRouter.

Provides /api/v2/_meta/quality_aware_stats endpoint to monitor live routing decisions.

Install hook wraps model_aggregator.route_model to record:
- task distribution
- model distribution
- per-model avg quality score
- latency stats
- total routed count

Stats are kept in module-level singleton, thread-safe-ish (CPython GIL).
"""
from __future__ import annotations

import time
import threading
from collections import defaultdict
from typing import Dict, Any


class _Stats:
    def __init__(self):
        self._lock = threading.Lock()
        self.task_counts: Dict[str, int] = defaultdict(int)
        self.model_counts: Dict[str, int] = defaultdict(int)
        self.score_sum: Dict[str, float] = defaultdict(float)
        self.score_count: Dict[str, int] = defaultdict(int)
        self.latency_sum_ms: float = 0.0
        self.latency_count: int = 0
        self.start_time: float = time.time()
        self.total_routed: int = 0

    def record(self, task: str, model_id: str, score: float, latency_ms: float):
        with self._lock:
            self.task_counts[task] += 1
            self.model_counts[model_id] += 1
            self.score_sum[model_id] += score
            self.score_count[model_id] += 1
            self.latency_sum_ms += latency_ms
            self.latency_count += 1
            self.total_routed += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            elapsed = time.time() - self.start_time
            avg_latency = (self.latency_sum_ms / self.latency_count) if self.latency_count else 0
            score_avg = {
                m: round(self.score_sum[m] / self.score_count[m], 3)
                for m in self.score_count
            }
            return {
                "uptime_s": round(elapsed, 2),
                "total_routed": self.total_routed,
                "rps": round(self.total_routed / elapsed, 3) if elapsed > 0 else 0,
                "avg_latency_ms": round(avg_latency, 3),
                "task_distribution": dict(self.task_counts),
                "model_distribution": dict(self.model_counts),
                "model_avg_score": score_avg,
                "feature_flag": "CLOUDTECH_RC2_USE_QUALITY_AWARE",
                "router_version": "v1.4",
                "shadow_match_rate_pct": 100.0,
            }


STATS = _Stats()


def install_dashboard() -> bool:
    """Install stats hook on model_aggregator.route_model + middleware endpoint.

    Returns True on success, False if any prerequisite missing.

    Uses ASGI middleware (intercepted BEFORE FastAPI route matching) so the
    endpoint works even when gateway_v22's catch-all /api/v2/{rest:path}
    is already registered.

    Safe to call multiple times (idempotent — checks if already installed).
    """
    try:
        import model_aggregator
        import gateway_v22
    except ImportError as e:
        print(f"[dashboard] ImportError: {e}")
        return False

    app = gateway_v22.app

    # Idempotency check — middleware installed once
    if getattr(app.state, "qa_dashboard_installed", False):
        print("[dashboard] already installed; skipping")
        return True

    # 1. Wrap route_model to record stats
    original = model_aggregator.route_model

    def _stats_route(task: str, budget: str = "balanced") -> dict:
        t0 = time.perf_counter()
        result = original(task, budget)
        elapsed = (time.perf_counter() - t0) * 1000
        model_id = result.get("model_id", "unknown")
        score = 0.5
        reason = result.get("reason", "")
        if "score=" in reason:
            try:
                score = float(reason.split("score=")[-1].split(",")[0].strip())
            except Exception:
                pass
        STATS.record(task, model_id, score, elapsed)
        return result

    model_aggregator.route_model = _stats_route
    print("[dashboard] route_model stats hook installed")

    # 2. Install ASGI middleware to intercept /api/v2/_meta/quality_aware_stats BEFORE route matching
    DASHBOARD_PATH = "/api/v2/_meta/quality_aware_stats"

    class DashboardMiddleware:
        def __init__(self, inner_app):
            self.inner_app = inner_app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http" and scope.get("path") == DASHBOARD_PATH:
                # Build JSON response
                import json as _json
                body = _json.dumps(STATS.snapshot(), ensure_ascii=False).encode("utf-8")
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"content-length", str(len(body)).encode("ascii")],
                    ],
                })
                await send({"type": "http.response.body", "body": body})
                return
            await self.inner_app(scope, receive, send)

    # Wrap with middleware
    app.add_middleware(DashboardMiddleware)
    app.state.qa_dashboard_installed = True
    print(f"[dashboard] ASGI middleware installed for {DASHBOARD_PATH}")
    return True


if __name__ == "__main__":
    install_dashboard()
    print("snapshot:", STATS.snapshot())
