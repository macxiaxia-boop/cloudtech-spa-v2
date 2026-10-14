"""A real, separately runnable worker for deterministic V4 HTML extraction.

Run once:
  python -m workflows.v4.local_worker --db <local-sqlite-file> --once
Poll in a dedicated terminal/service (explicit opt-in):
  python -m workflows.v4.local_worker --db <local-sqlite-file> --loop

Only works with user-supplied HTML. No scraping, LLM, RPA, paid APIs or media.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
import secrets
import sys
import time

from .local_job_queue import LocalJobQueue
from .local_output_projector import LocalOutputProjector
from .orchestrator import NodeRunRecord, RunStatus
from .node_kinds import NodeKind
from .sqlite_run_store import SQLiteRunStore, RunStoreConflict, RunStoreError


def process_one(store: SQLiteRunStore, *, lease_seconds: int = 120) -> dict:
    queue = LocalJobQueue(store)
    lease = queue.claim(lease_seconds=lease_seconds)
    if lease is None:
        return {"outcome": "IDLE", "provider_called": False}
    run_id = lease.run_id
    try:
        record = store.get(run_id)
        if record is None or record.tenant_id != lease.tenant_id:
            raise ValueError("TENANT_RUN_MISMATCH")
        if record.status != RunStatus.READY:
            raise ValueError("RUN_NOT_READY")
        if record.nodes:
            raise ValueError("RUN_ALREADY_HAS_NODES")

        analysis = None
        if record.path_id in ("WP-LOCAL-ARTICLE-EXTRACT", "WP-LOCAL-ARTICLE-ANALYZE"):
            html = record.input_bindings.get("html")
            source_url = record.input_bindings.get("source_url") or ""
            if not isinstance(html, str) or not html.strip():
                raise ValueError("HTML_NOT_SUPPLIED")
            if len(html.encode("utf-8")) > 1_800_000:
                raise ValueError("HTML_TOO_LARGE")
            if not isinstance(source_url, str) or len(source_url) > 2048:
                raise ValueError("SOURCE_URL_INVALID")
            from adapters.article.article_parser import parse_html
            parsed = parse_html(html, source_url=source_url)
            source_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
            if parsed.get("content_sha256") != source_hash or parsed.get("mock") is not False:
                raise ValueError("INVALID_PARSER_PROVENANCE")
            operation = "article.html_parse"
            node_id = "html_parse"
            provider_name = "local_html_parser"
            if record.path_id == "WP-LOCAL-ARTICLE-ANALYZE":
                from adapters.content.local_text_analysis import analyze_user_article
                analysis = analyze_user_article(parsed)
                if (analysis.get("source_html_sha256") != source_hash or
                    analysis.get("mock") is not False or
                    analysis.get("ai_model_used") is not False):
                    raise ValueError("INVALID_LOCAL_ANALYSIS_PROVENANCE")
        elif record.path_id == "WP-LOCAL-SUBTITLE-EXPORT":
            from adapters.transcribe.supplied_subtitle_export import format_supplied_segments
            parsed = format_supplied_segments(record.input_bindings.get("segments"))
            source_hash = parsed["source_sha256"]
            if parsed.get("mock") is not False or parsed.get("asr_performed") is not False:
                raise ValueError("INVALID_SUBTITLE_PROVENANCE")
            operation = "subtitle.format_supplied"
            node_id = "subtitle_export"
            provider_name = "local_subtitle_formatter"
        else:
            raise ValueError("OPERATION_NOT_ALLOWLISTED")

        def commit(rec):
            if rec.status != RunStatus.READY or rec.nodes:
                raise RunStoreConflict("local task changed before worker commit")
            node = NodeRunRecord(
                node_id=node_id, node_kind=NodeKind.TRANSFORM,
                operation=operation, requires={}, produces={},
                input_hash=source_hash, status=RunStatus.COMPLETED,
                output_ref=parsed, provider_name=provider_name,
                provider_req_id=None, cost_cents=0, cost_class="FREE_LOCAL",
                started_at=datetime.now(timezone.utc).isoformat(),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
            rec.nodes.append(node)
            rec.last_node_id = node.node_id
            if analysis is not None:
                # Real deterministic stages: both are committed atomically.
                stage = NodeRunRecord(
                    node_id="content_analyze", node_kind=NodeKind.TRANSFORM,
                    operation="content.local_text_analyze",
                    requires={"html_parse": node.node_id}, produces={},
                    input_hash=analysis["text_sha256"], status=RunStatus.COMPLETED,
                    output_ref=analysis, provider_name="local_lexical_analyzer",
                    provider_req_id=None, cost_cents=0, cost_class="FREE_LOCAL",
                    started_at=node.finished_at,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                )
                rec.nodes.append(stage)
                rec.last_node_id = stage.node_id
                rec.updated_at = stage.finished_at
            else:
                rec.updated_at = node.finished_at
            rec.status = RunStatus.COMPLETED
            return {"run_id": rec.run_id, "outcome": "DONE",
                    "provider_called": False, "cost_cents": 0,
                    "source_sha256": source_hash, "node_count": len(rec.nodes)}

        return store.mutate(run_id, commit, lease_token=lease.token)
    except RunStoreConflict:
        # The lease was fenced out or the run changed. Never force a transition.
        return {"run_id": run_id, "outcome": "LEASE_LOST_OR_CONFLICT",
                "provider_called": False}
    except ValueError as exc:
        # Input errors are permanent and do not merit a retry.
        try:
            queue.fail(lease, str(exc), retryable=False)
        except RunStoreConflict:
            return {"run_id": run_id, "outcome": "LEASE_LOST_OR_CONFLICT",
                    "provider_called": False}
        return {"run_id": run_id, "outcome": "FAILED_INPUT",
                "error_code": str(exc), "provider_called": False}
    except Exception:
        # Redacted errors, bounded retries with exponential delay.
        # Never include raw HTML or connector credentials in logs.
        try:
            retrying = queue.fail(lease, "LOCAL_WORKER_EXCEPTION", retryable=True)
        except RunStoreConflict:
            return {"run_id": run_id, "outcome": "LEASE_LOST_OR_CONFLICT",
                    "provider_called": False}
        return {"run_id": run_id,
                "outcome": "QUEUED_RETRY" if retrying else "FAILED",
                "provider_called": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.getenv("CLOUDTECH_V4_SQLITE_RUN_STORE"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--loop", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--lease-seconds", type=int, default=120)
    args = parser.parse_args()
    env = os.getenv("CLOUDTECH_ENV", "").lower()
    if env not in {"test", "development", "staging"}:
        parser.error("local SQLite worker allowed only in test/development/staging")
    if not args.db:
        parser.error("--db or CLOUDTECH_V4_SQLITE_RUN_STORE required")
    if not 0.1 <= args.poll_seconds <= 60:
        parser.error("poll-seconds must be 0.1..60")
    store = SQLiteRunStore(args.db)
    queue = LocalJobQueue(store)
    projector = LocalOutputProjector(store)
    worker_id = secrets.token_hex(16)
    while True:
        if args.loop:
            # A one-shot process exits and must not advertise itself as online.
            queue.note_worker(worker_id)
        result = process_one(store, lease_seconds=args.lease_seconds)
        # Structured and privacy-safe: no raw prompt, HTML or environment secret.
        print(f"V4 local job: {result['outcome']} {result.get('run_id', '')}",
              flush=True)
        # Consume committed output events independently from task execution.
        # Projection never sends customer content to external providers.
        indexed = projector.consume_one()
        if indexed["outcome"] == "BLOCKED_INVALID_EVIDENCE":
            print("V4 output projection: invalid evidence; manual review required",
                  flush=True)
        elif indexed["outcome"] == "CATALOGUED":
            print("V4 output projection: CATALOGUED", flush=True)
        if args.once:
            good_job = result["outcome"] in ("DONE", "IDLE")
            good_index = indexed["outcome"] in ("CATALOGUED", "IDLE")
            return 0 if good_job and good_index else 1
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    sys.exit(main())
