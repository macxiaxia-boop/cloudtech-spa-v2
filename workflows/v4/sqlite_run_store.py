"""Durable single-host V4 run journal (SQLite) with serialized writes.

Not a distributed worker, scheduler or provider billing ledger.
The source-of-truth is a DB transaction rather than per-process memory.
For horizontal production deployment use a separately qualified PostgreSQL
implementation, never a shared network-filesystem SQLite database.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import json
import sqlite3
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Optional


class RunStoreError(RuntimeError):
    pass


class RunStoreConflict(RunStoreError):
    pass


def _fingerprint(record: Any) -> str:
    """Stable logical request identity, excluding mutable run state."""
    payload = {
        "tenant_id": record.tenant_id,
        "path_id": record.path_id,
        "path_revision": record.path_revision,
        "project_id": record.project_id,
        "conversation_id": record.conversation_id,
        "input_bindings": record.input_bindings,
        "scope": record.scope,
        "budget_cap_cents": record.budget_cap_cents,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _restore(raw: str) -> Any:
    # Import at decode time: keeps SQLite and orchestrator modules decoupled.
    from .orchestrator import NodeRunRecord, WorkPathRunRecord, RunStatus
    from .node_kinds import NodeKind
    data = json.loads(raw)
    nodes = [
        NodeRunRecord(**{**node, "status": RunStatus(node["status"]),
                         "node_kind": NodeKind(node["node_kind"])})
        for node in data.pop("nodes", [])
    ]
    return WorkPathRunRecord(
        **{**data, "status": RunStatus(data["status"]), "nodes": nodes}
    )


class SQLiteRunStore:
    """Run snapshots and node receipts persist in an ACID local database.

    BEGIN IMMEDIATE provides a writer serialization point across connections
    and processes using the same *local* SQLite database. A strict payload
    fingerprint prevents the same idempotency key being used for a different
    request. Failure to commit is propagated, not swallowed.
    """
    kind = "SQLITE_LOCAL_DURABLE"
    worker_connected = False

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        if not self.path.parent.is_dir():
            raise RunStoreError("run store parent directory does not exist")
        if self.path.is_dir():
            raise RunStoreError("run store path must be a file")
        self._create_schema()

    @contextmanager
    def _connect(self):
        """Always close DB handles; an uncommitted transaction rolls back."""
        conn = sqlite3.connect(str(self.path), timeout=15, isolation_level=None)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=15000")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
        finally:
            conn.close()

    def _create_schema(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS v4_runs (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    fingerprint TEXT NOT NULL,
                    path_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 0,
                    snapshot TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS v4_runs_tenant_idx
                  ON v4_runs (tenant_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS v4_node_receipts (
                    run_id TEXT NOT NULL REFERENCES v4_runs(run_id),
                    node_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    provider_name TEXT,
                    provider_req_id TEXT,
                    cost_cents INTEGER NOT NULL CHECK (cost_cents >= 0),
                    receipt_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, node_id)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS v4_provider_receipt_once
                  ON v4_node_receipts (tenant_id, provider_name, provider_req_id)
                  WHERE provider_req_id IS NOT NULL AND provider_name IS NOT NULL;
                CREATE TABLE IF NOT EXISTS v4_local_jobs (
                    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE REFERENCES v4_runs(run_id),
                    tenant_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK (
                        state IN ('QUEUED','LEASED','DONE','FAILED')),
                    lease_token TEXT,
                    lease_until REAL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    available_at REAL NOT NULL DEFAULT 0,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS v4_local_jobs_claim
                  ON v4_local_jobs(state,available_at,job_id);
            """)

    def create_or_get(self, record: Any) -> Any:
        fingerprint = _fingerprint(record)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if record.idempotency_key:
                old = db.execute(
                    "SELECT snapshot,fingerprint FROM v4_runs WHERE idempotency_key=?",
                    (record.idempotency_key,),
                ).fetchone()
                if old:
                    if old["fingerprint"] != fingerprint:
                        raise RunStoreConflict(
                            "idempotency key was reused with a different request"
                        )
                    result = _restore(old["snapshot"])
                    db.commit()
                    return result
            db.execute("""
                INSERT INTO v4_runs (
                  run_id,tenant_id,idempotency_key,fingerprint,path_id,status,
                  created_at,updated_at,version,snapshot
                ) VALUES (?,?,?,?,?,?,?,?,0,?)
                """,
                (record.run_id, record.tenant_id, record.idempotency_key,
                 fingerprint, record.path_id, record.status.value,
                 record.created_at, record.updated_at,
                 json.dumps(record.to_dict(), ensure_ascii=False, allow_nan=False)),
            )
            db.commit()
        return copy.deepcopy(record)

    def get(self, run_id: str) -> Optional[Any]:
        with self._connect() as db:
            row = db.execute(
                "SELECT snapshot FROM v4_runs WHERE run_id=?", (run_id,)
            ).fetchone()
        return _restore(row["snapshot"]) if row else None

    def list(self, tenant_id: Optional[str] = None, path_id: Optional[str] = None,
             status: Optional[Any] = None, limit: int = 50) -> list[Any]:
        sql = "SELECT snapshot FROM v4_runs WHERE 1=1"
        params: list[Any] = []
        if tenant_id is not None:
            sql += " AND tenant_id=?"
            params.append(tenant_id)
        if path_id is not None:
            sql += " AND path_id=?"
            params.append(path_id)
        if status is not None:
            sql += " AND status=?"
            params.append(status.value if hasattr(status, "value") else status)
        sql += " ORDER BY created_at DESC,run_id DESC LIMIT ?"
        params.append(max(0, min(limit, 1000)))
        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()
        return [_restore(row["snapshot"]) for row in rows]

    def mutate(self, run_id: str, apply: Callable[[Any], Any], *,
               lease_token: Optional[str] = None) -> Any:
        """Apply a transition and its new node receipt in one DB transaction."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT snapshot,version,fingerprint FROM v4_runs WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if row is None:
                raise RunStoreError("run not found")
            local_job = db.execute(
                "SELECT state,lease_token,lease_until FROM v4_local_jobs WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if lease_token is None:
                if local_job is not None and local_job["state"] in ("QUEUED", "LEASED"):
                    raise RunStoreConflict(
                        "run belongs to queued local worker; synchronous mutation blocked"
                    )
            elif (local_job is None or local_job["state"] != "LEASED"
                  or not local_job["lease_token"]
                  or not secrets.compare_digest(local_job["lease_token"], lease_token)
                  or not local_job["lease_until"]
                  or local_job["lease_until"] <= time.time()):
                raise RunStoreConflict("expired or superseded worker lease; result rejected")
            record = _restore(row["snapshot"])
            old_nodes = {n.node_id: n.status for n in record.nodes}
            old_tenant = record.tenant_id
            old_key = record.idempotency_key
            old_fingerprint = row["fingerprint"]
            result = apply(record)
            if (record.tenant_id != old_tenant or record.idempotency_key != old_key
                    or _fingerprint(record) != old_fingerprint):
                raise RunStoreConflict("immutable tenant, idempotency or request changed")
            # Persist only newly completed receipts. Replayed identical receipts
            # are a read-only no-op and cannot double-charge.
            from .orchestrator import RunStatus
            for node in record.nodes:
                old = old_nodes.get(node.node_id)
                if node.status != RunStatus.COMPLETED or (
                    old is not None and old == RunStatus.COMPLETED
                ):
                    continue
                try:
                    db.execute("""
                    INSERT INTO v4_node_receipts(
                      run_id,node_id,tenant_id,provider_name,provider_req_id,
                      cost_cents,receipt_json
                    ) VALUES (?,?,?,?,?,?,?)
                    """, (
                        run_id, node.node_id, record.tenant_id,
                        node.provider_name, node.provider_req_id, node.cost_cents,
                        json.dumps(node.to_dict(), ensure_ascii=False, allow_nan=False),
                    ))
                except sqlite3.IntegrityError as exc:
                    raise RunStoreConflict(
                        "provider completion receipt is already registered for another node"
                    ) from exc
            db.execute("""
                UPDATE v4_runs SET snapshot=?,status=?,updated_at=?,version=version+1
                WHERE run_id=? AND version=?
            """, (json.dumps(record.to_dict(), ensure_ascii=False, allow_nan=False),
                  record.status.value, record.updated_at, run_id, row["version"]))
            if db.execute("SELECT changes()").fetchone()[0] != 1:
                raise RunStoreConflict("concurrent run update rejected")
            if lease_token is not None:
                from .orchestrator import RunStatus
                if record.status != RunStatus.COMPLETED:
                    raise RunStoreConflict("worker did not produce a completed run")
                updated = db.execute(
                    """UPDATE v4_local_jobs
                          SET state='DONE',lease_token=NULL,lease_until=NULL,
                              error_code=NULL,updated_at=?
                         WHERE run_id=? AND state='LEASED' AND lease_token=?""",
                    (record.updated_at, run_id, lease_token),
                ).rowcount
                if updated != 1:
                    raise RunStoreConflict("worker lease changed before commit")
            db.commit()
            return result

    def receipt_count(self, run_id: str) -> int:
        with self._connect() as db:
            row = db.execute(
                "SELECT COUNT(*) AS cnt FROM v4_node_receipts WHERE run_id=?",
                (run_id,),
            ).fetchone()
        return int(row["cnt"])
