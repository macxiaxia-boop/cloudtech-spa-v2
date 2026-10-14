"""Commit verified local outputs and ACK their outbox event in ONE transaction.

No network calls, no synthetic assets, no customer content copied to the
catalog. The catalog is a searchable pointer to the authoritative run receipt.
This is an at-least-once consumer with idempotent, fenced database effects.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Optional

from .local_outbox import LocalCompletionOutbox, OutboxLease
from .orchestrator import RunStatus
from .sqlite_run_store import SQLiteRunStore, RunStoreConflict, _restore


def _json_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class LocalOutputProjector:
    def __init__(self, store: SQLiteRunStore):
        self.store = store
        self.outbox = LocalCompletionOutbox(store)

    def consume_one(self) -> dict:
        lease = self.outbox.claim(lease_seconds=60)
        if lease is None:
            return {"outcome": "IDLE"}
        try:
            return self._commit(lease)
        except (RunStoreConflict, ValueError, TypeError, KeyError):
            # Do not ACK invalid/incomplete messages and never synthesize
            # missing results. Retain the item for manual intervention.
            try:
                self.outbox.release(lease, delay_seconds=3600)
            except RunStoreConflict:
                return {"outcome": "LEASE_LOST", "event_id": lease.event_id}
            return {"outcome": "BLOCKED_INVALID_EVIDENCE",
                    "event_id": lease.event_id, "run_id": lease.run_id}

    def _commit(self, lease: OutboxLease) -> dict:
        with self.store._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            event = db.execute("""
                SELECT state,lease_token,lease_until,payload_json,event_type
                FROM v4_local_outbox
                WHERE event_id=? AND run_id=? AND tenant_id=?
            """, (lease.event_id, lease.run_id, lease.tenant_id)).fetchone()
            if (event is None or event["state"] != "LEASED"
                    or event["lease_token"] != lease.token
                    or not event["lease_until"]
                    or event["lease_until"] <= time.time()):
                raise RunStoreConflict("outbox worker token is stale or superseded")
            if event["event_type"] != "LOCAL_RUN_COMPLETED":
                raise RunStoreConflict("unknown outbox operation")
            source = db.execute("""
                SELECT snapshot FROM v4_runs
                WHERE run_id=? AND tenant_id=? AND status='COMPLETED'
            """, (lease.run_id, lease.tenant_id)).fetchone()
            if source is None:
                raise RunStoreConflict("no completed run matching event tenant")
            run = _restore(source["snapshot"])
            payload = json.loads(event["payload_json"])
            if (payload != lease.payload or
                payload.get("run_id") != run.run_id or
                payload.get("tenant_id") != run.tenant_id or
                payload.get("event_type") != "LOCAL_RUN_COMPLETED" or
                payload.get("snapshot_sha256") != _json_hash(run.to_dict())):
                raise RunStoreConflict("completion event provenance does not match run")
            if len(run.nodes) != 1 or run.budget_spent_cents != 0:
                raise RunStoreConflict("not a zero-cost single-node local run")
            node = run.nodes[0]
            result = node.output_ref
            if (node.status != RunStatus.COMPLETED or
                node.cost_cents != 0 or node.provider_req_id is not None or
                not isinstance(result, dict) or result.get("mock") is not False):
                raise RunStoreConflict("node output cannot be trusted")
            receipt = db.execute("""
                SELECT receipt_json FROM v4_node_receipts
                WHERE run_id=? AND node_id=? AND tenant_id=?
            """, (run.run_id, node.node_id, run.tenant_id)).fetchone()
            if receipt is None or json.loads(receipt["receipt_json"]) != node.to_dict():
                raise RunStoreConflict("completed node has no matching committed receipt")

            if (run.path_id == "WP-LOCAL-ARTICLE-EXTRACT" and
                    node.operation == "article.html_parse" and
                    node.provider_name == "local_html_parser" and
                    node.node_id == "html_parse"):
                raw = run.input_bindings.get("html")
                if not isinstance(raw, str):
                    raise RunStoreConflict("HTML source is unavailable")
                source_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                if (node.input_hash != source_hash or
                        result.get("content_sha256") != source_hash):
                    raise RunStoreConflict("HTML source hash does not match output")
                kind = "ARTICLE_HTML_EXTRACTION"
            elif (run.path_id == "WP-LOCAL-SUBTITLE-EXPORT" and
                  node.operation == "subtitle.format_supplied" and
                  node.provider_name == "local_subtitle_formatter" and
                  node.node_id == "subtitle_export"):
                from adapters.transcribe.supplied_subtitle_export import (
                    format_supplied_segments,
                )
                source_hash = format_supplied_segments(
                    run.input_bindings.get("segments"))["source_sha256"]
                if (result.get("source_sha256") != source_hash or
                    node.input_hash != source_hash or
                    result.get("asr_performed") is not False or
                    result.get("model_called") is not False):
                    raise RunStoreConflict("subtitle provenance or source mismatch")
                kind = "SUBTITLE_SRT_VTT"
            else:
                raise RunStoreConflict("operation is not in approved local catalog")
            out_hash = _json_hash(result)
            created = run.updated_at
            db.execute("""
                INSERT OR IGNORE INTO v4_local_output_catalog
                  (tenant_id,run_id,node_id,path_id,artifact_kind,
                   source_sha256,output_sha256,snapshot_sha256,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (run.tenant_id,run.run_id,node.node_id,run.path_id,kind,
                  source_hash,out_hash,payload["snapshot_sha256"],created))
            saved = db.execute("""
                SELECT artifact_kind,source_sha256,output_sha256,snapshot_sha256
                FROM v4_local_output_catalog
                WHERE tenant_id=? AND run_id=? AND node_id=?
            """, (run.tenant_id, run.run_id, node.node_id)).fetchone()
            if (saved is None or tuple(saved) != (
                    kind,source_hash,out_hash,payload["snapshot_sha256"])):
                raise RunStoreConflict("conflicting prior output catalog record")
            updated = db.execute("""
                UPDATE v4_local_outbox
                  SET state='ACKED',lease_token=NULL,lease_until=NULL
                WHERE event_id=? AND state='LEASED' AND lease_token=?
            """, (lease.event_id,lease.token)).rowcount
            if updated != 1:
                raise RunStoreConflict("event lease changed during projection")
            db.commit()
            return {"outcome": "CATALOGUED", "run_id": run.run_id,
                    "event_id": lease.event_id, "artifact_kind": kind,
                    "tenant_id": run.tenant_id, "catalog_entries": 1}

    def list_for_tenant(self, tenant_id: str, *, limit: int = 50) -> list[dict]:
        if not tenant_id:
            raise ValueError("tenant ID required")
        with self.store._connect() as db:
            rows = db.execute("""
                SELECT run_id,node_id,path_id,artifact_kind,source_sha256,
                       output_sha256,created_at
                FROM v4_local_output_catalog WHERE tenant_id=?
                ORDER BY created_at DESC,run_id DESC LIMIT ?
            """, (tenant_id, max(1,min(limit,100)))).fetchall()
        return [dict(row) for row in rows]
