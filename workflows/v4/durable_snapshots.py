"""P11: opt-in local SQLite snapshots of the EXISTING V4Orchestrator.

This is a single-writer durability bridge. Concurrent multi-process writers,
provider reconciliation, and distributed CAS execution are NOT certified.
Never store secrets inside input_bindings. No external network operations.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .node_kinds import NodeKind
from .orchestrator import NodeRunRecord, RunStatus, WorkPathRunRecord


class V4SnapshotStore:
    def __init__(self, file_path: str | Path) -> None:
        self.path = str(file_path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS v4_run_snapshots (
                run_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
                )"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS v4_snapshot_tenant "
                "ON v4_run_snapshots(tenant_id)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA busy_timeout=15000")
            db.execute("PRAGMA journal_mode=WAL")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def save(self, record: WorkPathRunRecord) -> None:
        """Persist full typed record, including nodes, before API acknowledges."""
        data = record.to_dict()
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        with self._connect() as db:
            old = db.execute(
                "SELECT tenant_id FROM v4_run_snapshots WHERE run_id=?",
                (record.run_id,),
            ).fetchone()
            if old is not None and old["tenant_id"] != record.tenant_id:
                raise ValueError("run_id is already bound to another tenant")
            db.execute(
                """INSERT INTO v4_run_snapshots
                (run_id, tenant_id, payload_json, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                   payload_json=excluded.payload_json,
                   updated_at=excluded.updated_at""",
                (record.run_id, record.tenant_id, payload, record.updated_at),
            )

    def load_all(self) -> list[WorkPathRunRecord]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT payload_json FROM v4_run_snapshots ORDER BY updated_at"
            ).fetchall()
        records = []
        for row in rows:
            raw = json.loads(row["payload_json"])
            raw["status"] = RunStatus(raw["status"])
            node_data = raw.pop("nodes", [])
            nodes = []
            interrupted = False
            for data in node_data:
                data["node_kind"] = NodeKind(data["node_kind"])
                data["status"] = RunStatus(data["status"])
                if data["status"] == RunStatus.RUNNING:
                    data["status"] = RunStatus.PARTIAL
                    data["error_code"] = "INTERRUPTED_UNCERTAIN"
                    data["error_message"] = "remote outcome must be reconciled"
                    interrupted = True
                nodes.append(NodeRunRecord(**data))
            if raw["status"] == RunStatus.RUNNING or interrupted:
                raw["status"] = RunStatus.PARTIAL
                raw["error_code"] = "INTERRUPTED_UNCERTAIN"
                raw["error_message"] = "interrupted execution needs review"
            records.append(WorkPathRunRecord(**raw, nodes=nodes))
        return records
