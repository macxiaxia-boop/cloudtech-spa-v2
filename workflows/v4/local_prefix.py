"""Execute the already-implemented, side-effect-free prefix of a V4 path.

This is intentionally NOT another workflow scheduler. It uses the existing
V4Orchestrator and OperationRegistry. No network, models, providers or money.
It never implies a whole workpath is executable or durably persisted.
"""
from __future__ import annotations

import hashlib
import json
import threading
from typing import Any

from .capability_preflight import LOCAL_IMPLEMENTED, inspect_path
from .node_kinds import NodeKind
from .orchestrator import NodeRunRecord, RunStatus, RunStatusError, V4Orchestrator
from .paths import get_path
from .registry import OperationRegistry

# Same-instance serialization only; database-backed ownership remains a
# separate P7 AIOS capability and is not asserted by this module.
_LOCAL_LOCK = threading.Lock()


def _input_for_step(operation: str, bindings: dict[str, Any],
                    completed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if operation == "url.normalize":
        # One actual V4 workpath uses this as its first deterministic operation.
        return {"url": bindings.get("homepage_url", "")}
    if operation == "content.dedupe":
        source = completed.get("homepage_parse", {})
        return {"items": source.get("items", [])}
    raise RunStatusError(f"unapproved local operation: {operation}")


def execute_local_prefix(
    orchestrator: V4Orchestrator,
    *,
    run_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """Perform only source-audited LOCAL_IMPLEMENTED nodes, once per run.

    Returns the next blocked operation, never executes a mock adapter.
    """
    with _LOCAL_LOCK:
        rec = orchestrator.get_run(run_id)
        if rec is None or rec.tenant_id != tenant_id:
            raise KeyError("run not found")
        if rec.status not in (RunStatus.READY, RunStatus.PARTIAL):
            raise RunStatusError(f"run not executable from {rec.status.value}")
        definition = get_path(rec.path_id)
        preflight = inspect_path(rec.path_id)
        by_id = {n["id"]: n for n in preflight["nodes"]}
        completed: dict[str, dict[str, Any]] = {
            n.node_id: dict(n.produces)
            for n in rec.nodes if n.status == RunStatus.COMPLETED
        }
        performed: list[str] = []
        blocked = None
        for step in definition.steps:
            if step.id in completed:
                continue
            capability = by_id[step.id]
            if capability["capability"] != "LOCAL_IMPLEMENTED":
                blocked = {
                    "node_id": step.id,
                    "operation": step.operation,
                    "reason": capability["capability"],
                }
                break
            if not set(step.requires) <= set(completed):
                blocked = {
                    "node_id": step.id,
                    "operation": step.operation,
                    "reason": "UNMET_DEPENDENCY",
                }
                break
            op_input = _input_for_step(step.operation, rec.input_bindings, completed)
            result = OperationRegistry().dispatch(step.operation, op_input)
            if not isinstance(result, dict) or result.get("mock") or result.get("ok") is False:
                blocked = {
                    "node_id": step.id,
                    "operation": step.operation,
                    "reason": "UNVERIFIED_OPERATION_RESULT",
                }
                break
            if step.operation == "url.normalize" and not result.get("host"):
                blocked = {
                    "node_id": step.id,
                    "operation": step.operation,
                    "reason": "INVALID_URL",
                }
                break
            if rec.status != RunStatus.RUNNING:
                orchestrator.transition(run_id, RunStatus.RUNNING)
                rec.status = RunStatus.RUNNING
            input_hash = hashlib.sha256(
                json.dumps(op_input, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            orchestrator.add_node(run_id, NodeRunRecord(
                node_id=step.id,
                node_kind=NodeKind(step.node_kind),
                operation=step.operation,
                requires={dep: completed[dep] for dep in step.requires},
                produces=result,
                input_hash=input_hash,
            ))
            orchestrator.mark_node_running(run_id, step.id)
            orchestrator.mark_node_done(
                run_id, step.id, output_ref={"local_result": result}, cost_cents=0
            )
            completed[step.id] = result
            performed.append(step.id)

        if rec.status == RunStatus.RUNNING:
            orchestrator.transition(run_id, RunStatus.PARTIAL)
        latest = orchestrator.get_run(run_id)
        return {
            "run_id": run_id,
            "status": latest.status.value,
            "executed_nodes": performed,
            "completed_node_ids": list(completed),
            "blocked_at": blocked,
            "external_calls": 0,
            "charged_cents": 0,
            "durability": "IN_PROCESS_ONLY_NOT_PRODUCTION_DURABLE",
            "execution_ready": blocked is None and preflight["execution_ready"],
        }
