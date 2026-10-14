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
            if not isinstance(payload, dict) or not isinstance(lease.payload, dict):
                raise RunStoreConflict("outbox event payload must be a JSON object")
            if (payload != lease.payload or
                payload.get("run_id") != run.run_id or
                payload.get("tenant_id") != run.tenant_id or
                payload.get("event_type") != "LOCAL_RUN_COMPLETED" or
                payload.get("snapshot_sha256") != _json_hash(run.to_dict())):
                raise RunStoreConflict("completion event provenance does not match run")
            if not 1 <= len(run.nodes) <= 2 or run.budget_spent_cents != 0:
                raise RunStoreConflict("not an allowed zero-cost local workflow")
            for current in run.nodes:
                if (current.status != RunStatus.COMPLETED or
                    current.cost_cents != 0 or current.provider_req_id is not None or
                    not isinstance(current.output_ref, dict) or
                    current.output_ref.get("mock") is not False):
                    raise RunStoreConflict("unverified or metered node result")
                receipt = db.execute("""
                    SELECT receipt_json FROM v4_node_receipts
                    WHERE run_id=? AND node_id=? AND tenant_id=?
                """, (run.run_id, current.node_id, run.tenant_id)).fetchone()
                if receipt is None or json.loads(receipt["receipt_json"]) != current.to_dict():
                    raise RunStoreConflict("a completed node has no matching receipt")
            node = run.nodes[-1]
            result = node.output_ref

            if (len(run.nodes) == 1 and
                    run.path_id == "WP-LOCAL-ARTICLE-EXTRACT" and
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
                # Receipts and snapshot hashes can agree with each other while
                # the stored extracted text is wrong. Verify against the actual
                # user-supplied HTML, not just mutually matching metadata.
                from adapters.article.article_parser import parse_html
                expected = parse_html(
                    raw, source_url=run.input_bindings.get("source_url") or "",
                )
                if result != expected:
                    raise RunStoreConflict("HTML extraction differs from source")
                kind = "ARTICLE_HTML_EXTRACTION"
            elif (len(run.nodes) == 1 and
                  run.path_id == "WP-LOCAL-SUBTITLE-EXPORT" and
                  node.operation == "subtitle.format_supplied" and
                  node.provider_name == "local_subtitle_formatter" and
                  node.node_id == "subtitle_export"):
                from adapters.transcribe.supplied_subtitle_export import (
                    format_supplied_segments,
                )
                # The receipt and outbox can agree on forged metadata.
                # Recompute the complete deliverable from the retained source,
                # not just its source hash, before making it discoverable.
                expected = format_supplied_segments(
                    run.input_bindings.get("segments"))
                source_hash = expected["source_sha256"]
                if (node.input_hash != source_hash or result != expected):
                    raise RunStoreConflict("subtitle bytes or provenance differ from source")
                kind = "SUBTITLE_SRT_VTT"
            elif (len(run.nodes) == 2 and
                  run.path_id == "WP-LOCAL-ARTICLE-ANALYZE" and
                  node.node_id == "content_analyze" and
                  node.operation == "content.local_text_analyze" and
                  node.provider_name == "local_lexical_analyzer"):
                extraction = run.nodes[0]
                if (extraction.node_id != "html_parse" or
                    extraction.operation != "article.html_parse" or
                    extraction.provider_name != "local_html_parser"):
                    raise RunStoreConflict("first stage must be genuine HTML extraction")
                supplied = run.input_bindings.get("html")
                raw_output = extraction.output_ref
                if not isinstance(supplied, str):
                    raise RunStoreConflict("original HTML was not retained")
                source_hash = hashlib.sha256(supplied.encode("utf-8")).hexdigest()
                if (extraction.input_hash != source_hash or
                    raw_output.get("content_sha256") != source_hash):
                    raise RunStoreConflict("HTML stage provenance mismatch")
                from adapters.article.article_parser import parse_html
                expected = parse_html(
                    supplied, source_url=run.input_bindings.get("source_url") or "",
                )
                if raw_output != expected:
                    raise RunStoreConflict(
                        "analysis extraction stage differs from source HTML"
                    )
                import hashlib as _hashlib
                actual_text = raw_output.get("text")
                if not isinstance(actual_text, str):
                    raise RunStoreConflict("actual extracted text missing")
                real_text_hash = _hashlib.sha256(actual_text.encode("utf-8")).hexdigest()
                if (node.input_hash != real_text_hash or
                    result.get("text_sha256") != real_text_hash or
                    result.get("source_html_sha256") != source_hash or
                    result.get("ai_model_used") is not False):
                    raise RunStoreConflict("analysis inputs or model provenance invalid")
                from adapters.content.local_text_analysis import analyze_user_article
                if result != analyze_user_article(raw_output):
                    raise RunStoreConflict("analysis output differs from verified source text")
                kind = "ARTICLE_CONTENT_ANALYSIS"
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

    def get_for_tenant_run(self, tenant_id: str, run_id: str) -> dict | None:
        """Fetch exactly one independently ACKed deliverable by tenant and run.

        Do not rely on a latest-N catalogue window: high throughput must not
        make a real older result disappear from the caller's receipt check.
        """
        if not tenant_id or not run_id:
            raise ValueError("tenant and run id required")
        with self.store._connect() as db:
            row = db.execute("""
                SELECT c.run_id,c.node_id,c.path_id,c.artifact_kind,
                       c.source_sha256,c.output_sha256,c.created_at
                FROM v4_local_output_catalog AS c
                JOIN v4_local_outbox AS o
                  ON o.run_id=c.run_id AND o.tenant_id=c.tenant_id
                WHERE c.tenant_id=? AND c.run_id=? AND o.state='ACKED'
            """, (tenant_id, run_id)).fetchone()
        return dict(row) if row is not None else None

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
