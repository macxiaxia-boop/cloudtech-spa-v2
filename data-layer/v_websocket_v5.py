"""CloudTech 实时通知模块 v5 · 2026-09-25 R289

WebSocket + Server-Sent Events 双通道实时推送:
  1. WS  /api/ws/v1/events                  -- 全局事件流 (员工invoke/计费/订阅激活/lead推进)
  2. WS  /api/ws/v1/tenant/{tenant_id}      -- 单租户事件流
  3. GET /api/ws/v1/events/recent           -- 最近 100 事件 (SSE fallback)
  4. POST /api/ws/v1/events/emit            -- 手动 emit (测试用)
  5. GET /api/ws/v1/stream/sse             -- SSE 流 (EventSource API)

事件 schema:
  {event_id, event_type, tenant_id, payload, ts}
  event_type: "employee_invoked" / "quota_charged" / "invoice_created" /
              "lead_advanced" / "subscription_activated" / "bridge_incident"

存储: in-memory deque(1000) + DB 持久化 (events 表)
广播: asyncio.Queue per-connection
"""
import asyncio
import json
import sqlite3
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List, Deque

from fastapi import APIRouter, HTTPException, Header, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_DIR = LIVE / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cloudtech.db"

router = APIRouter(prefix="/api/ws/v1", tags=["realtime-v5"])


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _init_db():
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            tenant_id TEXT,
            payload TEXT,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_tenant ON events(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
        """)
        c.commit()
    finally:
        c.close()


# 内存事件缓冲 (最近 1000 条)
_event_buffer: Deque[dict] = deque(maxlen=1000)
_subscribers_global: List[asyncio.Queue] = []
_subscribers_tenant: dict[str, List[asyncio.Queue]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def emit_event(event_type: str, tenant_id: Optional[str] = None, payload: Optional[dict] = None):
    """Emit 一条事件 — 全局广播 + 租户广播 + DB 持久化."""
    evt = {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "event_type": event_type,
        "tenant_id": tenant_id,
        "payload": payload or {},
        "ts": _now(),
    }
    _event_buffer.append(evt)
    # 持久化
    try:
        c = _conn()
        c.execute("INSERT INTO events(event_id, event_type, tenant_id, payload, ts) VALUES (?, ?, ?, ?, ?)",
                  (evt["event_id"], event_type, tenant_id, json.dumps(payload or {}, ensure_ascii=False), evt["ts"]))
        c.commit()
        c.close()
    except Exception:
        pass
    # 全局广播
    for q in list(_subscribers_global):
        try:
            q.put_nowait(evt)
        except asyncio.QueueFull:
            pass
    # 租户广播
    if tenant_id:
        for q in _subscribers_tenant.get(tenant_id, []):
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                pass
    return evt


# ---------------------------------------------------------------------------
# Pydantic
# ---------------------------------------------------------------------------
class EmitReq(BaseModel):
    event_type: str
    tenant_id: Optional[str] = None
    payload: Optional[dict] = None


# ---------------------------------------------------------------------------
# WebSocket: 全局事件流
# ---------------------------------------------------------------------------
@router.websocket("/events")
async def ws_events(websocket: WebSocket):
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers_global.append(q)
    try:
        # 立即推最近 10 条历史
        for evt in list(_event_buffer)[-10:]:
            await websocket.send_json(evt)
        # 持续监听
        while True:
            evt = await q.get()
            await websocket.send_json(evt)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if q in _subscribers_global:
            _subscribers_global.remove(q)


@router.websocket("/tenant/{tenant_id}")
async def ws_tenant(websocket: WebSocket, tenant_id: str):
    await websocket.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers_tenant.setdefault(tenant_id, []).append(q)
    try:
        for evt in list(_event_buffer)[-10:]:
            if evt.get("tenant_id") == tenant_id:
                await websocket.send_json(evt)
        while True:
            evt = await q.get()
            await websocket.send_json(evt)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if tenant_id in _subscribers_tenant and q in _subscribers_tenant[tenant_id]:
            _subscribers_tenant[tenant_id].remove(q)


# ---------------------------------------------------------------------------
# SSE 流
# ---------------------------------------------------------------------------
@router.get("/stream/sse")
async def sse_stream():
    """Server-Sent Events 流 (浏览器 EventSource API 可直连)."""
    from fastapi.responses import StreamingResponse

    async def _gen():
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        _subscribers_global.append(q)
        try:
            for evt in list(_event_buffer)[-10:]:
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
            while True:
                evt = await q.get()
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if q in _subscribers_global:
                _subscribers_global.remove(q)
    return StreamingResponse(_gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# 历史 / emit
# ---------------------------------------------------------------------------
@router.get("/events/recent")
async def events_recent(limit: int = Query(default=50, le=500), tenant_id: Optional[str] = None,
                       event_type: Optional[str] = None):
    c = _conn()
    try:
        sql = "SELECT * FROM events WHERE 1=1"
        params = []
        if tenant_id:
            sql += " AND tenant_id=?"; params.append(tenant_id)
        if event_type:
            sql += " AND event_type=?"; params.append(event_type)
        sql += " ORDER BY ts DESC LIMIT ?"; params.append(limit)
        rows = c.execute(sql, params).fetchall()
        return {"status": "ok", "count": len(rows),
                "events": [dict(r) for r in rows],
                "buffer_size": len(_event_buffer),
                "subscribers_global": len(_subscribers_global),
                "subscribers_tenants": {t: len(qs) for t, qs in _subscribers_tenant.items()}}
    finally:
        c.close()


@router.post("/events/emit")
async def events_emit(req: EmitReq):
    evt = await emit_event(req.event_type, req.tenant_id, req.payload)
    return {"status": "ok", "event": evt}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@router.get("/health")
async def health():
    return {
        "status": "ok",
        "module": "realtime_v5",
        "buffer_size": len(_event_buffer),
        "buffer_max": 1000,
        "subscribers_global": len(_subscribers_global),
        "subscribers_by_tenant": {t: len(qs) for t, qs in _subscribers_tenant.items()},
        "endpoints": [
            "WS /events", "WS /tenant/{tenant_id}",
            "GET /stream/sse", "GET /events/recent", "POST /events/emit",
        ],
        "version": "v5.0 · 2026-09-25 R289",
    }


_init_db()
print(f"[v_websocket_v5] loaded — WS + SSE 双通道 + DB 持久化 + 1000 内存缓冲")
