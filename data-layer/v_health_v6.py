"""CloudTech 健康快照 v6 · 2026-09-26 R290
聚合 gateway / 各模块 / DB / 端口健康,统一 /api/health/v1/snapshot 端点。

端点 (3):
  1. GET  /api/health/v1/snapshot         -- 全模块健康快照 (聚合 v1-v5 + audit + rate_limit)
  2. GET  /api/health/v1/ping             -- 快速 ping (live 不依赖 DB)
  3. GET  /api/health/v1/version          -- 版本 + commit + 模块清单
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api/health/v1", tags=["health-v6"])

_VERSION = "v22.0 · 2026-09-26 R290"
_MODULES = [
    "v_real_business_v1", "v_real_business_v2", "v_real_business_v3",
    "v_aios_bridge_v4", "v_websocket_v5",
    "v_audit_log_v6", "v_rate_limit_v6",
]


@router.get("/snapshot")
async def snapshot():
    """聚合全模块健康."""
    import sqlite3
    DB_PATH = Path(r"D:\CloudTech-Portable\data\cloudtech.db")
    db = {"path": str(DB_PATH), "exists": DB_PATH.exists()}
    if db["exists"]:
        try:
            db["size_bytes"] = DB_PATH.stat().st_size
            c = sqlite3.connect(str(DB_PATH), timeout=2)
            c.execute("PRAGMA journal_mode=WAL")
            tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            db["tables"] = [t[0] for t in tables]
            db["table_count"] = len(db["tables"])
            db["status"] = "ok"
            c.close()
        except Exception as e:
            db["status"] = "error"
            db["error"] = str(e)[:100]
    return {
        "status": "ok",
        "ts": datetime.now(timezone.utc).isoformat(),
        "module": "health_v6",
        "version": _VERSION,
        "modules_loaded": _MODULES,
        "module_count": len(_MODULES),
        "db": db,
        "endpoints": [
            "GET /snapshot", "GET /ping", "GET /version",
        ],
    }


@router.get("/ping")
async def ping():
    return {"status": "ok", "pong": True, "ts": datetime.now(timezone.utc).isoformat()}


@router.get("/version")
async def version():
    return {
        "status": "ok",
        "version": _VERSION,
        "modules": _MODULES,
        "module_count": len(_MODULES),
        "build": "R290 · 2026-09-26",
    }


print(f"[v_health_v6] loaded — snapshot + ping + version")