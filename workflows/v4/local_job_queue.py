"""Durable single-host job queue for ONE allowlisted local CloudTech workpath.

SQLite DB transaction is the claim lock. Lease tokens are fencing tokens:
an expired worker cannot save a result after another worker reclaims the job.
This module neither calls external providers nor handles paid media work.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import secrets
import time
from typing import Optional

from .orchestrator import RunStatus
from .sqlite_run_store import SQLiteRunStore, RunStoreConflict, RunStoreError, _restore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class LocalJobLease:
    run_id: str
    tenant_id: str
    token: str
    attempt: int
    expires_at: float


class LocalJobQueue:
    """SQLite-only, single-machine work queue; no network filesystem support."""

    def __init__(self, store: SQLiteRunStore):
        self.store = store

    def enqueue(self, run_id: str, tenant_id: str) -> dict:
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT snapshot FROM v4_runs WHERE run_id=? AND tenant_id=?",
                (run_id, tenant_id),
            ).fetchone()
            if row is None:
                raise RunStoreError("run not found for authorized tenant")
            rec = _restore(row["snapshot"])
            if rec.path_id != "WP-LOCAL-ARTICLE-EXTRACT":
                raise RunStoreConflict("only local HTML extraction may enter this queue")
            existing = db.execute(
                "SELECT state,attempts FROM v4_local_jobs WHERE run_id=?",
                (run_id,),
            ).fetchone()
            if existing is not None:
                db.commit()
                return {
                    "run_id": run_id, "state": existing["state"],
                    "attempts": existing["attempts"], "idempotent_hit": True,
                }
            if rec.status != RunStatus.READY:
                raise RunStoreConflict("run must be READY before local enqueue")
            stamp = _utc_now()
            db.execute(
                """INSERT INTO v4_local_jobs(
                  run_id,tenant_id,state,created_at,updated_at)
                  VALUES(?,?,'QUEUED',?,?)""",
                (run_id, tenant_id, stamp, stamp),
            )
            db.commit()
        return {"run_id": run_id, "state": "QUEUED",
                "attempts": 0, "idempotent_hit": False}

    def claim(self, *, lease_seconds: int = 60,
              now: Optional[float] = None) -> Optional[LocalJobLease]:
        if lease_seconds < 1 or lease_seconds > 3600:
            raise ValueError("lease_seconds must be 1..3600")
        instant = time.time() if now is None else now
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""
                SELECT j.job_id,j.run_id,j.tenant_id,j.attempts
                FROM v4_local_jobs j
                JOIN v4_runs r ON r.run_id=j.run_id
                WHERE r.status='READY'
                  AND j.attempts<j.max_attempts
                  AND j.available_at<=?
                  AND (j.state='QUEUED'
                       OR (j.state='LEASED' AND j.lease_until<=?))
                ORDER BY j.job_id ASC LIMIT 1
            """, (instant, instant)).fetchone()
            if row is None:
                db.commit()
                return None
            token = secrets.token_urlsafe(32)
            until = instant + lease_seconds
            db.execute("""
                UPDATE v4_local_jobs
                   SET state='LEASED',lease_token=?,lease_until=?,
                       attempts=attempts+1,updated_at=?
                 WHERE job_id=?
            """, (token, until, _utc_now(), row["job_id"]))
            db.commit()
        return LocalJobLease(
            row["run_id"], row["tenant_id"], token, row["attempts"] + 1, until,
        )

    def heartbeat(self, lease: LocalJobLease, *, seconds: int = 60) -> bool:
        if not 1 <= seconds <= 3600:
            raise ValueError("heartbeat seconds must be 1..3600")
        now = time.time()
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("""
                UPDATE v4_local_jobs SET lease_until=?,updated_at=?
                 WHERE run_id=? AND lease_token=? AND state='LEASED'
                   AND lease_until>?
            """, (now + seconds, _utc_now(), lease.run_id, lease.token, now)).rowcount
            db.commit()
        return changed == 1

    def fail(self, lease: LocalJobLease, error_code: str,
             *, retryable: bool) -> bool:
        """Record a redacted error; retry only safe, deterministic local work."""
        now = time.time()
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""
                SELECT attempts,max_attempts FROM v4_local_jobs
                 WHERE run_id=? AND state='LEASED' AND lease_token=?
                   AND lease_until>?
            """, (lease.run_id, lease.token, now)).fetchone()
            if row is None:
                raise RunStoreConflict("worker lease lost; cannot mark job failed")
            will_retry = retryable and row["attempts"] < row["max_attempts"]
            if will_retry:
                db.execute("""
                    UPDATE v4_local_jobs
                       SET state='QUEUED',lease_token=NULL,lease_until=NULL,
                           available_at=?,error_code=?,updated_at=?
                     WHERE run_id=?
                """, (now + min(30, 2 ** row["attempts"]),
                      error_code[:80], _utc_now(), lease.run_id))
            else:
                db.execute("""
                    UPDATE v4_local_jobs
                       SET state='FAILED',lease_token=NULL,lease_until=NULL,
                           error_code=?,updated_at=?
                     WHERE run_id=?
                """, (error_code[:80], _utc_now(), lease.run_id))
                from .sqlite_run_store import _fingerprint
                raw = db.execute(
                    "SELECT snapshot,version FROM v4_runs WHERE run_id=?",
                    (lease.run_id,),
                ).fetchone()
                if raw is None:
                    raise RunStoreError("run missing when finishing local job")
                rec = _restore(raw["snapshot"])
                if rec.status != RunStatus.READY:
                    raise RunStoreConflict("run no longer READY at job failure")
                rec.status = RunStatus.FAILED
                rec.error_code = error_code[:80]
                rec.error_message = "Local worker failed; inspect private operator logs"
                rec.updated_at = _utc_now()
                db.execute("""
                    UPDATE v4_runs
                       SET status='FAILED',updated_at=?,snapshot=?,version=version+1
                     WHERE run_id=? AND version=?
                """, (rec.updated_at, json.dumps(rec.to_dict(), ensure_ascii=False),
                      lease.run_id, raw["version"]))
            db.commit()
            return will_retry

    def get_state(self, run_id: str, tenant_id: str) -> Optional[dict]:
        with self.store._connect() as db:
            row = db.execute("""
                SELECT state,attempts,max_attempts,error_code,updated_at
                  FROM v4_local_jobs WHERE run_id=? AND tenant_id=?
            """, (run_id, tenant_id)).fetchone()
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}

    def note_worker(self, worker_id: str) -> None:
        """A live polling process refreshes its own presence in the DB."""
        if not worker_id or len(worker_id) > 128:
            raise ValueError("invalid local worker id")
        instant = time.time()
        with self.store._connect() as db:
            db.execute("""
                INSERT INTO v4_local_worker_heartbeats(worker_id,last_seen)
                VALUES(?,?)
                ON CONFLICT(worker_id) DO UPDATE SET last_seen=excluded.last_seen
            """, (worker_id, instant))

    def active_workers(self, *, max_age_seconds: int = 15) -> int:
        """Only recently active loops count, not workers that ran --once."""
        with self.store._connect() as db:
            row = db.execute("""
                SELECT COUNT(*) AS total FROM v4_local_worker_heartbeats
                WHERE last_seen>?
            """, (time.time() - max_age_seconds,)).fetchone()
        return int(row["total"])

    def stats(self, tenant_id: str) -> dict:
        with self.store._connect() as db:
            rows = db.execute("""
                SELECT state,COUNT(*) AS total FROM v4_local_jobs
                 WHERE tenant_id=? GROUP BY state
            """, (tenant_id,)).fetchall()
        return {row["state"]: row["total"] for row in rows}
