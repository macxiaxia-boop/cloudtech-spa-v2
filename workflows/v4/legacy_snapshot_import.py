"""Quarantine PR1 legacy V4 snapshots before reconciling with PR2 durable runs.

Migration does NOT execute tasks, infer receipts, resume provider calls, or
insert unverified legacy results into authoritative v4_runs. Default is read-
only inspection. --apply is restricted to explicit non-production environment
and requires an EXISTING, qualified PR2 SQLite database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

_ALLOWED = {"PLANNED", "INPUT_BOUND", "READY", "RUNNING", "REVIEW_REQUIRED",
            "APPROVED", "COMPLETED", "BLOCKED_PERMISSION", "BLOCKED_BUDGET",
            "RETRY_WAIT", "FAILED", "CANCELED", "PARTIAL"}
_MAX_ROWS = 50000
_MAX_PAYLOAD = 2_000_000


def inspect_legacy(source: str | Path) -> list[dict]:
    """Validate all records before any target transaction begins."""
    source = Path(source).resolve(strict=True)
    if not source.is_file():
        raise ValueError("legacy snapshot source must be an existing SQLite file")
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        table = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='v4_run_snapshots'"
        ).fetchone()
        if table is None:
            raise ValueError("legacy v4_run_snapshots table missing")
        count = db.execute("SELECT COUNT(*) FROM v4_run_snapshots").fetchone()[0]
        if count > _MAX_ROWS:
            raise ValueError("legacy snapshot review limit exceeded")
        rows = db.execute(
            "SELECT run_id,tenant_id,payload_json,updated_at FROM v4_run_snapshots "
            "ORDER BY run_id"
        ).fetchall()
    checked = []
    for row in rows:
        raw = row["payload_json"]
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > _MAX_PAYLOAD:
            raise ValueError("invalid or oversized legacy snapshot")
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid legacy snapshot JSON; no imports applied") from exc
        if (not isinstance(parsed, dict)
                or not isinstance(row["run_id"], str) or not row["run_id"]
                or not isinstance(row["tenant_id"], str) or not row["tenant_id"]
                or parsed.get("run_id") != row["run_id"]
                or parsed.get("tenant_id") != row["tenant_id"]
                or parsed.get("status") not in _ALLOWED
                or not isinstance(parsed.get("nodes", []), list)):
            raise ValueError("legacy snapshot identity/status invalid; refuse import")
        checked.append({
            "run_id": row["run_id"], "tenant_id": row["tenant_id"],
            "legacy_status": parsed["status"], "source_updated_at": row["updated_at"],
            "payload_json": raw, "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        })
    return checked


def quarantine_legacy(source: str | Path, target: str | Path,
                      *, apply: bool = False, environment: str | None = None) -> dict:
    """All-or-nothing, idempotent quarantine with zero executor effects."""
    source = Path(source).resolve(strict=True)
    target = Path(target).resolve(strict=True)
    if source == target:
        raise ValueError("legacy source and PR2 target must be distinct files")
    records = inspect_legacy(source)
    overview = {"inspected": len(records), "quarantined_new": 0,
                "idempotent_existing": 0, "active_runs_imported": 0,
                "worker_invoked": False, "production_ready": False,
                "applied": False}
    if not apply:
        return overview
    if (environment or os.getenv("CLOUDTECH_ENV", "")).lower() not in {
        "test", "development", "staging"
    }:
        raise PermissionError("legacy apply forbidden in production or unspecified environment")
    with sqlite3.connect(str(target), isolation_level=None, timeout=15) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA foreign_keys=ON")
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("PR2 target SQLite integrity failed")
        if db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='v4_runs'"
        ).fetchone() is None:
            raise ValueError("target must already be a valid PR2 SQLiteRunStore")
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS v4_legacy_snapshot_quarantine (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    legacy_status TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    source_updated_at TEXT,
                    imported_at INTEGER NOT NULL,
                    review_state TEXT NOT NULL DEFAULT 'PENDING'
                      CHECK(review_state IN ('PENDING','REVIEWED','REJECTED'))
                )
            """)
            for record in records:
                run_id = record["run_id"]
                if db.execute(
                    "SELECT 1 FROM v4_runs WHERE run_id=?", (run_id,)
                ).fetchone():
                    raise ValueError("active PR2 run id collision; do not mix histories")
                existing = db.execute(
                    "SELECT tenant_id,source_sha256,payload_json "
                    "FROM v4_legacy_snapshot_quarantine WHERE run_id=?", (run_id,)
                ).fetchone()
                if existing is not None:
                    if (existing["tenant_id"] != record["tenant_id"]
                            or existing["source_sha256"] != record["source_sha256"]
                            or existing["payload_json"] != record["payload_json"]):
                        raise ValueError("legacy source changed since previous quarantine")
                    overview["idempotent_existing"] += 1
                    continue
                db.execute("""
                    INSERT INTO v4_legacy_snapshot_quarantine
                      (run_id,tenant_id,legacy_status,source_sha256,payload_json,
                       source_updated_at,imported_at)
                    VALUES(?,?,?,?,?,?,?)
                """, (run_id, record["tenant_id"], record["legacy_status"],
                      record["source_sha256"], record["payload_json"],
                      record["source_updated_at"], int(time.time())))
                overview["quarantined_new"] += 1
            db.commit()
        except BaseException:
            db.rollback()
            raise
    overview["applied"] = True
    return overview


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--apply", action="store_true",
                        help="Quarantine only, non-production; NEVER promotes runs")
    args = parser.parse_args()
    print(json.dumps(quarantine_legacy(
        args.source, args.target, apply=args.apply,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
