"""v3_agent_loop_v1 — STUB MODULE (CLAIM STUB · 2026-09-25)

⚠️ 声称标记 (claim stub) — 此模块为最小占位 stub, 仅保证:
  1. 可被 importlib.util.spec_from_file_location 加载
  2. 暴露 `router = APIRouter()` 供 gateway_v22.load_v10_modules() 注册
  3. 提供 4 个 dummy endpoints (GET /, GET /health, GET /list, GET /{id})

🚫 NOT IMPLEMENTED:
  - 真实业务逻辑 (那不是 L1 能做的, 留待后续 sprint)
  - 数据持久化 / 外部 API 调用 / 鉴权

生成于 2026-09-25 · ct_v3_stubs_verify.py · CloudTech Live Audit v11
"""
from fastapi import APIRouter
from typing import Any, Dict

_MODULE_NAME = "agent_loop_v1"

router = APIRouter(prefix="/api/v3/agent_loop_v1", tags=["v3-stub · agent_loop_v1"])


def _stub_payload(extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "status": "stub",
        "module": _MODULE_NAME,
        "warning": "not yet implemented",
        "generated": "2026-09-25",
    }
    if extra:
        base.update(extra)
    return base


@router.get("/")
async def root() -> Dict[str, Any]:
    """Module root — stub."""
    return _stub_payload({"endpoint": "root"})


@router.get("/health")
async def health() -> Dict[str, Any]:
    """Health check — always ok for stub."""
    return _stub_payload({"endpoint": "health", "ok": True})


@router.get("/list")
async def list_items() -> Dict[str, Any]:
    """List items — returns empty stub list."""
    return _stub_payload({"endpoint": "list", "items": [], "count": 0})


@router.get("/{item_id}")
async def get_item(item_id: str) -> Dict[str, Any]:
    """Get item by id — stub."""
    return _stub_payload({"endpoint": "get", "item_id": item_id})
