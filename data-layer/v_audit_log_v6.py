"""CloudTech 审计日志 v6 · 2026-09-26 R290
事件溯源 + 合规查询 + 红线 #68 件套必带 trace 块治本。

端点 (4):
  1. POST /api/audit/v1/log                  -- 写审计日志 (带 trace 块)
  2. GET  /api/audit/v1/query                -- 查审计日志 (tenant/actor/action/time 过滤)
  3. GET  /api/audit/v1/stats/{tenant}       -- 审计统计 (按 action 分布 + 按 actor 分布)
  4. GET  /api/audit/v1/trace/{trace_id}     -- 单 trace 链路查询 (整链路所有事件)
"""
import asyncio
import json
import sqlite3
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(r"D:\CloudTech-Portable")
DB_DIR = LIVE / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "cloudtech.db"

router = APIRouter(prefix="/api/audit/v1", tags=["audit-v6"])


def _conn():
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def _init_db():
    c = _conn()
    try:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            span_id TEXT,
            parent_span_id TEXT,
            ts TEXT NOT NULL,
            tenant_id TEXT,
            actor_id TEXT,
            actor_role TEXT,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            payload TEXT,
            result TEXT,
            error TEXT,
            ip TEXT,
            ua TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_log(trace_id);
        CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
        CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts DESC);
        """)
        c.commit()
    finally:
        c.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


class LogReq(BaseModel):
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    tenant_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    payload: Optional[dict] = None
    result: Optional[str] = None
    error: Optional[str] = None
    ip: Optional[str] = None
    ua: Optional[str] = None


def _write_log(req: LogReq) -> dict:
    c = _conn()
    try:
        trace_id = req.trace_id or f"tr_{uuid.uuid4().hex[:16]}"
        span_id = req.span_id or f"sp_{uuid.uuid4().hex[:8]}"
        c.execute("""
            INSERT INTO audit_log(
                trace_id, span_id, parent_span_id, ts, tenant_id, actor_id,
                actor_role, action, resource_type, resource_id, payload,
                result, error, ip, ua
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trace_id, span_id, req.parent_span_id, _now(), req.tenant_id,
            req.actor_id, req.actor_role, req.action, req.resource_type,
            req.resource_id, json.dumps(req.payload or {}, ensure_ascii=False),
            req.result, req.error, req.ip, req.ua
        ))
        c.commit()
        return {"status": "ok", "trace_id": trace_id, "span_id": span_id, "ts": _now()}
    finally:
        c.close()


@router.post("/log")
async def log_event(req: LogReq):
    """写一条审计事件 — 红线 #68 件套必带 trace 块治本."""
    return _write_log(req)


@router.get("/query")
async def query(
    tenant_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
):
    """复合过滤查询审计日志."""
    c = _conn()
    try:
        sql = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if tenant_id: sql += " AND tenant_id=?"; params.append(tenant_id)
        if actor_id: sql += " AND actor_id=?"; params.append(actor_id)
        if action: sql += " AND action=?"; params.append(action)
        if resource_type: sql += " AND resource_type=?"; params.append(resource_type)
        if start: sql += " AND ts>=?"; params.append(start)
        if end: sql += " AND ts<=?"; params.append(end)
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = c.execute(sql, params).fetchall()
        total = c.execute("SELECT COUNT(*) AS c FROM audit_log WHERE 1=1" + sql[sql.find("WHERE 1=1")+10:sql.find("ORDER BY")], [p for p in params[:-2] if p is not None]).fetchone()["c"]
        return {
            "status": "ok", "count": len(rows), "total": total, "limit": limit, "offset": offset,
            "events": [dict(r) for r in rows],
        }
    finally:
        c.close()


@router.get("/stats/{tenant_id}")
async def stats(tenant_id: str, days: int = Query(default=30, le=365)):
    """审计统计 — 按 action + actor 分布 + 24h 时序."""
    c = _conn()
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        rows = c.execute("""
            SELECT action, actor_id, COUNT(*) AS c
            FROM audit_log
            WHERE tenant_id=? AND ts>=?
            GROUP BY action, actor_id
        """, (tenant_id, since)).fetchall()
        by_action = defaultdict(int)
        by_actor = defaultdict(int)
        for r in rows:
            by_action[r["action"]] += r["c"]
            by_actor[r["actor_id"] or "anonymous"] += r["c"]
        # 24h 时序
        hours = c.execute("""
            SELECT strftime('%Y-%m-%d %H:00', ts) AS hour, COUNT(*) AS c
            FROM audit_log
            WHERE tenant_id=? AND ts>=?
            GROUP BY hour
            ORDER BY hour DESC
            LIMIT 24
        """, (tenant_id, since)).fetchall()
        return {
            "status": "ok", "tenant_id": tenant_id, "days": days,
            "by_action": dict(sorted(by_action.items(), key=lambda x: -x[1])[:20]),
            "by_actor": dict(sorted(by_actor.items(), key=lambda x: -x[1])[:20]),
            "hourly_24h": [dict(r) for r in hours],
        }
    finally:
        c.close()


@router.get("/trace/{trace_id}")
async def trace(trace_id: str):
    """单 trace 链路查询 — 整链路所有 span."""
    c = _conn()
    try:
        rows = c.execute("""
            SELECT * FROM audit_log
            WHERE trace_id=?
            ORDER BY id ASC
        """, (trace_id,)).fetchall()
        if not rows:
            raise HTTPException(404, {"error": "trace_not_found", "trace_id": trace_id})
        spans = [dict(r) for r in rows]
        # 构建 span tree
        span_map = {s["span_id"]: {**s, "children": []} for s in spans}
        root = None
        for s in spans:
            if s["parent_span_id"] and s["parent_span_id"] in span_map:
                span_map[s["parent_span_id"]]["children"].append(span_map[s["span_id"]])
            else:
                root = span_map[s["span_id"]]
        return {
            "status": "ok", "trace_id": trace_id, "span_count": len(spans),
            "root": root, "spans": spans,
        }
    finally:
        c.close()


@router.get("/health")
async def health():
    c = _conn()
    try:
        cnt = c.execute("SELECT COUNT(*) AS c FROM audit_log").fetchone()["c"]
        latest = c.execute("SELECT ts FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        return {
            "status": "ok", "module": "audit_log_v6",
            "total_events": cnt,
            "latest_event_ts": latest["ts"] if latest else None,
            "endpoints": ["POST /log", "GET /query", "GET /stats/{tenant}", "GET /trace/{trace_id}"],
            "version": "v6.0 · 2026-09-26 R290",
        }
    finally:
        c.close()


_init_db()
print(f"[v_audit_log_v6] loaded — 审计 + trace + 红线 #68 治本")