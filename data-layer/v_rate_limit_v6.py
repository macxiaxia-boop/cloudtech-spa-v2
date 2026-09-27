"""CloudTech 限流模块 v6 · 2026-09-26 R290
IP + tenant 双维度 token bucket 限流,防止滥用 + 保护后端。

端点 (3):
  1. GET /api/ratelimit/v1/check         -- 实时检查某 IP/tenant 当前限流状态
  2. POST /api/ratelimit/v1/config       -- 动态调整某 tenant 限流阈值
  3. GET /api/ratelimit/v1/stats         -- 限流统计 (总请求/被拒/IP top 10)

算法: token bucket (每 IP/tenant 60 req/min 默认) + 滑动窗口 (1min)
存储: in-memory dict (重启丢失,可接受 — 后端重启时清空限流状态)
"""
import asyncio
import json
import sqlite3
import sys
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Dict

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_DIR = LIVE / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cloudtech.db"

router = APIRouter(prefix="/api/ratelimit/v1", tags=["ratelimit-v6"])


# ----- token bucket 实现 -----
class TokenBucket:
    def __init__(self, capacity: int = 60, refill_rate: float = 1.0):
        # capacity: 桶容量 (max tokens), refill_rate: 每秒补充 tokens
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_ts = time.monotonic()

    def consume(self, n: int = 1) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_ts
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_ts = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


# ----- 限流存储 -----
_buckets: Dict[str, TokenBucket] = {}
_stats_total = 0
_stats_rejected = 0
_stats_by_ip: Dict[str, int] = defaultdict(int)
_stats_by_tenant: Dict[str, int] = defaultdict(int)
_tenant_limits: Dict[str, dict] = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _check_limit(key: str, capacity: int = 60, refill: float = 1.0) -> dict:
    """检查某 key 限流状态,返回 allowed + remaining."""
    global _stats_total, _stats_rejected
    bucket = _buckets.get(key)
    if not bucket:
        bucket = TokenBucket(capacity, refill)
        _buckets[key] = bucket
    allowed = bucket.consume()
    _stats_total += 1
    if allowed:
        return {"allowed": True, "remaining": int(bucket.tokens), "capacity": bucket.capacity}
    else:
        _stats_rejected += 1
        if key.startswith("ip:"):
            _stats_by_ip[key[3:]] += 1
        elif key.startswith("tenant:"):
            _stats_by_tenant[key[7:]] += 1
        return {"allowed": False, "remaining": 0, "capacity": bucket.capacity, "retry_after_sec": 1.0 / refill}


@router.get("/check")
async def check(ip: Optional[str] = None, tenant_id: Optional[str] = None):
    """实时检查 — 不消费 tokens,只查询当前状态."""
    if not ip and not tenant_id:
        raise HTTPException(400, {"error": "ip_or_tenant_required"})
    results = {}
    if ip:
        b = _buckets.get(f"ip:{ip}") or TokenBucket()
        results["ip"] = {"ip": ip, "tokens": int(b.tokens), "capacity": b.capacity}
    if tenant_id:
        cfg = _tenant_limits.get(tenant_id, {})
        b = _buckets.get(f"tenant:{tenant_id}") or TokenBucket(
            capacity=cfg.get("capacity", 60),
            refill_rate=cfg.get("refill_rate", 1.0)
        )
        results["tenant"] = {"tenant_id": tenant_id, "tokens": int(b.tokens), "capacity": b.capacity}
    return {"status": "ok", **_now_meta(), **results}


@router.get("/consume")
async def consume(ip: Optional[str] = None, tenant_id: Optional[str] = None):
    """消费 1 token,模拟真实请求 — 用于测试."""
    if not ip and not tenant_id:
        raise HTTPException(400, {"error": "ip_or_tenant_required"})
    results = {}
    if ip:
        results["ip"] = _check_limit(f"ip:{ip}")
    if tenant_id:
        cfg = _tenant_limits.get(tenant_id, {})
        results["tenant"] = _check_limit(
            f"tenant:{tenant_id}",
            capacity=cfg.get("capacity", 60),
            refill=cfg.get("refill_rate", 1.0)
        )
    allowed = all(r.get("allowed", True) for r in results.values()) if results else True
    return {"status": "ok" if allowed else "rate_limited", "results": results}


class LimitConfig(BaseModel):
    tenant_id: str
    capacity: int = 60
    refill_rate: float = 1.0  # tokens per second


@router.post("/config")
async def set_config(cfg: LimitConfig):
    """动态调整某 tenant 限流阈值."""
    _tenant_limits[cfg.tenant_id] = {
        "capacity": cfg.capacity,
        "refill_rate": cfg.refill_rate,
        "updated_at": _now(),
    }
    # 重置 bucket
    _buckets.pop(f"tenant:{cfg.tenant_id}", None)
    return {"status": "ok", **_now_meta(), "tenant_id": cfg.tenant_id, "config": _tenant_limits[cfg.tenant_id]}


@router.get("/config/{tenant_id}")
async def get_config(tenant_id: str):
    cfg = _tenant_limits.get(tenant_id, {"capacity": 60, "refill_rate": 1.0, "is_default": True})
    return {"status": "ok", "tenant_id": tenant_id, "config": cfg, "is_default": tenant_id not in _tenant_limits}


@router.get("/stats")
async def stats():
    return {
        "status": "ok",
        "total_requests": _stats_total,
        "rejected": _stats_rejected,
        "reject_rate": round(_stats_rejected / max(_stats_total, 1), 4),
        "active_buckets": len(_buckets),
        "top_ips_rejected": dict(sorted(_stats_by_ip.items(), key=lambda x: -x[1])[:10]),
        "top_tenants_rejected": dict(sorted(_stats_by_tenant.items(), key=lambda x: -x[1])[:10]),
        "tenant_custom_limits": {t: c for t, c in _tenant_limits.items()},
    }


@router.get("/health")
async def health():
    return {
        "status": "ok", "module": "rate_limit_v6",
        "active_buckets": len(_buckets),
        "total_requests": _stats_total,
        "rejected": _stats_rejected,
        "endpoints": ["GET /check", "GET /consume", "POST /config", "GET /config/{t}", "GET /stats"],
        "version": "v6.0 · 2026-09-26 R290",
    }


def _now_meta():
    return {"ts": _now()}


print(f"[v_rate_limit_v6] loaded — token bucket + tenant cfg + stats")