"""v3 stub upgraded to data-returning endpoint.

CLAIM STUB · data-only · generated 2026-09-25 · upgraded by ct_stub_upgrader.py

Returns plausible preset/config data inferred from module name.
NOT real business logic — for that, replace this module.
"""
from __future__ import annotations
from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/api/v3/v3_151_wechat_webhook", tags=["v3-stub-upgraded"])

_DATA = {"status": "data", "channels": ["web", "api", "wechat"], "max_tokens": 4000}


@router.get("/")
async def root():
    """Root — returns module preset/config."""
    return _DATA


@router.get("/health")
async def health():
    return {"status": "ok", "module": "v3_151_wechat_webhook", "mode": "stub_data_only"}


@router.get("/list")
async def list_items():
    """List items — returns up to 10 from _DATA if list-shaped, else preset."""
    if isinstance(_DATA.get("items"), list):
        return {"status": "ok", "data": _DATA["items"][:10], "total": len(_DATA["items"])}
    return {"status": "ok", "data": _DATA, "note": "preset; no item list"}


@router.get("/{item_id}")
async def get_item(item_id: str):
    return {"status": "ok", "id": item_id, "module": "v3_151_wechat_webhook", "hint": "stub lookup"}
