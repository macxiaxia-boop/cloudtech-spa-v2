"""Transactional local completion outbox with fenced at-least-once handoff.

Only publishes metadata for completed deterministic local runs. This is not
provider billing, an external webhook, or a PostgreSQL implementation.
Consumers must use the event_id as an idempotency key before any side effect.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import secrets
import time
from typing import Optional

from .sqlite_run_store import SQLiteRunStore, RunStoreConflict


@dataclass(frozen=True)
class OutboxLease:
    event_id: int
    run_id: str
    tenant_id: str
    event_type: str
    payload: dict
    token: str
    attempt: int


class LocalCompletionOutbox:
    def __init__(self, store: SQLiteRunStore):
        self.store = store

    def claim(self, *, lease_seconds: int = 60) -> Optional[OutboxLease]:
        if not 1 <= lease_seconds <= 3600:
            raise ValueError("lease_seconds must be 1..3600")
        now = time.time()
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""
                SELECT event_id,run_id,tenant_id,event_type,payload_json,attempts
                FROM v4_local_outbox
                WHERE (state='PENDING' OR (state='LEASED' AND lease_until<=?))
                  AND available_at<=?
                ORDER BY event_id LIMIT 1
            """, (now, now)).fetchone()
            if row is None:
                db.commit()
                return None
            token = secrets.token_urlsafe(32)
            db.execute("""
                UPDATE v4_local_outbox
                   SET state='LEASED',lease_token=?,lease_until=?,
                       attempts=attempts+1
                 WHERE event_id=?
            """, (token, now + lease_seconds, row["event_id"]))
            db.commit()
        return OutboxLease(
            event_id=row["event_id"], run_id=row["run_id"],
            tenant_id=row["tenant_id"], event_type=row["event_type"],
            payload=json.loads(row["payload_json"]), token=token,
            attempt=row["attempts"] + 1,
        )

    def acknowledge(self, lease: OutboxLease) -> None:
        """Only the unexpired current lease can mark an event delivered."""
        now = time.time()
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("""
                UPDATE v4_local_outbox
                   SET state='ACKED',lease_token=NULL,lease_until=NULL
                 WHERE event_id=? AND run_id=? AND tenant_id=?
                   AND state='LEASED' AND lease_token=? AND lease_until>?
            """, (lease.event_id, lease.run_id, lease.tenant_id,
                  lease.token, now)).rowcount
            if changed != 1:
                raise RunStoreConflict("outbox lease expired, already acked or superseded")
            db.commit()

    def release(self, lease: OutboxLease, *, delay_seconds: int = 0) -> None:
        """Retry after a consumer error; delivery remains at-least-once."""
        if not 0 <= delay_seconds <= 3600:
            raise ValueError("delay_seconds must be 0..3600")
        now = time.time()
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute("""
                UPDATE v4_local_outbox
                   SET state='PENDING',lease_token=NULL,lease_until=NULL,
                       available_at=?
                 WHERE event_id=? AND run_id=? AND tenant_id=?
                   AND state='LEASED' AND lease_token=? AND lease_until>?
            """, (now + delay_seconds, lease.event_id, lease.run_id,
                  lease.tenant_id, lease.token, now)).rowcount
            if changed != 1:
                raise RunStoreConflict("outbox lease expired or superseded")
            db.commit()

    def status(self, run_id: str, tenant_id: str) -> Optional[dict]:
        with self.store._connect() as db:
            row = db.execute("""
                SELECT event_id,event_type,state,attempts
                  FROM v4_local_outbox WHERE run_id=? AND tenant_id=?
            """, (run_id, tenant_id)).fetchone()
        return dict(row) if row else None
