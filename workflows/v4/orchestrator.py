"""V4 — 状态机 + DAG 执行器
扩展 workflows/base.py:
  * 状态机: PLANNED→INPUT_BOUND→READY→RUNNING→REVIEW_REQUIRED→APPROVED→COMPLETED
  * 分支: BLOCKED_PERMISSION / BLOCKED_BUDGET / RETRY_WAIT / FAILED / CANCELED / PARTIAL
  * 节点持久化 job state, input_hash, output_ref, provider_req_id, timestamps, error_code
  * 断点续跑 — 不重复收费
"""
from __future__ import annotations
import copy
import json
import os
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .node_kinds import NodeKind, NODE_KIND_COST_CLASS
from .idempotency import IdempotencyStore, IdempotencyHit


class RunStatus(str, Enum):
    PLANNED = "PLANNED"
    INPUT_BOUND = "INPUT_BOUND"
    READY = "READY"
    RUNNING = "RUNNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    BLOCKED_PERMISSION = "BLOCKED_PERMISSION"
    BLOCKED_BUDGET = "BLOCKED_BUDGET"
    RETRY_WAIT = "RETRY_WAIT"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    PARTIAL = "PARTIAL"


# 状态转换白名单 (DAG)
ALLOWED_TRANSITIONS = {
    RunStatus.PLANNED: {RunStatus.INPUT_BOUND, RunStatus.CANCELED, RunStatus.FAILED},
    RunStatus.INPUT_BOUND: {RunStatus.READY, RunStatus.CANCELED, RunStatus.FAILED, RunStatus.BLOCKED_PERMISSION},
    RunStatus.READY: {RunStatus.RUNNING, RunStatus.CANCELED, RunStatus.BLOCKED_BUDGET, RunStatus.BLOCKED_PERMISSION},
    RunStatus.RUNNING: {RunStatus.REVIEW_REQUIRED, RunStatus.COMPLETED, RunStatus.PARTIAL, RunStatus.FAILED, RunStatus.RETRY_WAIT, RunStatus.CANCELED},
    RunStatus.REVIEW_REQUIRED: {RunStatus.APPROVED, RunStatus.FAILED, RunStatus.CANCELED},
    RunStatus.APPROVED: {RunStatus.COMPLETED, RunStatus.RUNNING, RunStatus.FAILED},
    RunStatus.RETRY_WAIT: {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELED},
    RunStatus.PARTIAL: {RunStatus.RUNNING, RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED},
    RunStatus.BLOCKED_PERMISSION: {RunStatus.READY, RunStatus.CANCELED},
    RunStatus.BLOCKED_BUDGET: {RunStatus.READY, RunStatus.CANCELED},
}


class RunStatusError(Exception):
    pass


@dataclass
class NodeRunRecord:
    node_id: str
    node_kind: NodeKind
    operation: str
    requires: Dict[str, Any]
    produces: Dict[str, Any]
    input_hash: str
    status: RunStatus = RunStatus.READY
    output_ref: Optional[Dict[str, Any]] = None
    provider_req_id: Optional[str] = None
    provider_name: Optional[str] = None
    retry_count: int = 0
    cost_cents: int = 0
    cost_class: str = "FREE_LOCAL"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["node_kind"] = self.node_kind.value
        return d


@dataclass
class WorkPathRunRecord:
    run_id: str
    path_id: str
    path_revision: int
    tenant_id: str
    project_id: Optional[str] = None
    conversation_id: Optional[str] = None
    input_bindings: Dict[str, Any] = field(default_factory=dict)
    status: RunStatus = RunStatus.PLANNED
    scope: str = "tenant"
    budget_cap_cents: int = 0
    budget_spent_cents: int = 0
    idempotency_key: Optional[str] = None
    nodes: List[NodeRunRecord] = field(default_factory=list)
    last_node_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d["status"] = self.status.value
        d["nodes"] = [n.to_dict() for n in self.nodes]
        return d


class V4Orchestrator:
    """线程安全 orchestrator — 状态机 + 节点依赖 + 幂等"""

    _instance: Optional["V4Orchestrator"] = None
    _lock = threading.Lock()

    def __init__(self, idempotency: Optional[IdempotencyStore] = None, run_store: Optional[Any] = None):
        self._runs: Dict[str, WorkPathRunRecord] = {}
        self._mtx = threading.Lock()
        self.idempotency = idempotency or IdempotencyStore()
        self._persistence: Optional[Callable[[WorkPathRunRecord], None]] = None
        self._store = run_store

    @property
    def storage_kind(self) -> str:
        return self._store.kind if self._store else "VOLATILE_MEMORY"

    def _edit(self, run_id: str, apply: Callable[[WorkPathRunRecord], Any]) -> Any:
        """Commit the full mutation or propagate persistence errors."""
        if self._store is not None:
            from .sqlite_run_store import RunStoreError
            try:
                return self._store.mutate(run_id, apply)
            except RunStoreError as exc:
                raise RunStatusError(str(exc)) from exc
        with self._mtx:
            current = self._runs.get(run_id)
            if current is None:
                raise RunStatusError(f"[V4-003] run {run_id} not found")
            updated = copy.deepcopy(current)
            result = apply(updated)
            if self._persistence:
                try:
                    self._persistence(copy.deepcopy(updated))
                except Exception as exc:
                    raise RunStatusError("[V4-009] run persistence failed") from exc
            self._runs[run_id] = updated
            return result


    @classmethod
    def instance(cls) -> "V4Orchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    sqlite_path = os.environ.get("CLOUDTECH_V4_SQLITE_RUN_STORE")
                    store = None
                    if sqlite_path:
                        env = os.environ.get("CLOUDTECH_ENV", "").lower()
                        if env not in {"development", "test", "staging"}:
                            raise RuntimeError(
                                "SQLite V4 run storage requires an explicit development/staging environment; "
                                "production must use a qualified transactional database backend"
                            )
                        from .sqlite_run_store import SQLiteRunStore
                        store = SQLiteRunStore(sqlite_path)
                    cls._instance = V4Orchestrator(run_store=store)
        return cls._instance

    def bind_persistence(self, fn: Callable[[WorkPathRunRecord], None]) -> None:
        """注入持久化回调 (默认 in-memory)"""
        if self._store is not None:
            raise RunStatusError("Persistent store already manages run writes")
        self._persistence = fn

    def create_run(
        self,
        path_id: str,
        path_revision: int,
        tenant_id: str,
        input_bindings: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        project_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        budget_cap_cents: int = 0,
    ) -> WorkPathRunRecord:
        if self._store is not None:
            rec = WorkPathRunRecord(
                run_id="wpr_" + secrets.token_hex(8),
                path_id=path_id, path_revision=path_revision, tenant_id=tenant_id,
                project_id=project_id, conversation_id=conversation_id,
                input_bindings=copy.deepcopy(input_bindings),
                idempotency_key=idempotency_key, budget_cap_cents=budget_cap_cents,
            )
            from .sqlite_run_store import RunStoreError
            try:
                return self._store.create_or_get(rec)
            except RunStoreError as exc:
                raise RunStatusError(str(exc)) from exc
        # The check, allocation and key binding MUST be one critical section.
        # Prevent duplicate in-process runs under concurrent identical requests.
        # Multi-process deployments still require a durable unique DB constraint.
        with self._mtx:
            if idempotency_key:
                hit = self.idempotency.check(idempotency_key)
                if hit and hit.run_id:
                    existing = self._runs.get(hit.run_id)
                    if existing is not None:
                        return existing
            run_id = "wpr_" + secrets.token_hex(8)
            rec = WorkPathRunRecord(
                run_id=run_id,
                path_id=path_id,
                path_revision=path_revision,
                tenant_id=tenant_id,
                project_id=project_id,
                conversation_id=conversation_id,
                input_bindings=input_bindings,
                idempotency_key=idempotency_key,
                budget_cap_cents=budget_cap_cents,
            )
            self._runs[run_id] = rec
            if idempotency_key:
                self.idempotency.bind(idempotency_key, run_id)
            return rec

    def transition(self, run_id: str, target: RunStatus) -> WorkPathRunRecord:
        def apply(rec: WorkPathRunRecord) -> WorkPathRunRecord:
            if target not in ALLOWED_TRANSITIONS.get(rec.status, set()):
                raise RunStatusError(
                    f"[V4-002] illegal transition {rec.status.value} -> {target.value}"
                )
            rec.status = target
            rec.updated_at = datetime.now(timezone.utc).isoformat()
            return copy.deepcopy(rec)
        return self._edit(run_id, apply)

    def add_node(self, run_id: str, node: NodeRunRecord) -> None:
        def apply(rec: WorkPathRunRecord) -> None:
            if any(n.node_id == node.node_id for n in rec.nodes):
                raise RunStatusError(f"[V4-010] duplicate node id: {node.node_id}")
            rec.nodes.append(copy.deepcopy(node))
            rec.last_node_id = node.node_id
            rec.updated_at = datetime.now(timezone.utc).isoformat()
        self._edit(run_id, apply)

    def get_run(self, run_id: str) -> Optional[WorkPathRunRecord]:
        if self._store is not None:
            return self._store.get(run_id)
        with self._mtx:
            rec = self._runs.get(run_id)
            return copy.deepcopy(rec) if rec is not None else None

    def list_runs(
        self,
        tenant_id: Optional[str] = None,
        path_id: Optional[str] = None,
        status: Optional[RunStatus] = None,
        limit: int = 50,
    ) -> List[WorkPathRunRecord]:
        if self._store is not None:
            return self._store.list(tenant_id=tenant_id, path_id=path_id,
                                    status=status, limit=limit)
        with self._mtx:
            items = [copy.deepcopy(rec) for rec in self._runs.values()]
        if tenant_id:
            items = [r for r in items if r.tenant_id == tenant_id]
        if path_id:
            items = [r for r in items if r.path_id == path_id]
        if status:
            items = [r for r in items if r.status == status]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[:limit]

    def mark_node_running(self, run_id: str, node_id: str) -> None:
        def apply(rec: WorkPathRunRecord) -> None:
            for node in rec.nodes:
                if node.node_id == node_id:
                    if node.status == RunStatus.COMPLETED:
                        raise RunStatusError(f"[V4-005] completed node cannot restart: {node_id}")
                    node.status = RunStatus.RUNNING
                    node.started_at = datetime.now(timezone.utc).isoformat()
                    rec.updated_at = node.started_at
                    return
            raise RunStatusError(f"[V4-004] node {node_id} not in run {run_id}")
        self._edit(run_id, apply)

    def mark_node_done(
        self, run_id: str, node_id: str, output_ref: Dict[str, Any],
        provider_req_id: Optional[str] = None,
        provider_name: Optional[str] = None,
        cost_cents: int = 0,
        cost_class: str = "FREE_LOCAL",
    ) -> None:
        def apply(rec: WorkPathRunRecord) -> None:
            for node in rec.nodes:
                if node.node_id != node_id:
                    continue
                if cost_cents < 0:
                    raise RunStatusError(f"[V4-006] negative node charge: {cost_cents}")
                if node.status == RunStatus.COMPLETED:
                    if (node.output_ref == output_ref
                            and node.provider_req_id == provider_req_id
                            and node.provider_name == provider_name
                            and node.cost_cents == cost_cents
                            and node.cost_class == cost_class):
                        return
                    raise RunStatusError(f"[V4-007] conflicting completion: {node_id}")
                if node.status != RunStatus.RUNNING:
                    raise RunStatusError(
                        f"[V4-011] node must be RUNNING before completion: {node_id}"
                    )
                node.status = RunStatus.COMPLETED
                node.output_ref = copy.deepcopy(output_ref)
                node.provider_req_id = provider_req_id
                node.provider_name = provider_name
                node.cost_cents = cost_cents
                node.cost_class = cost_class
                node.finished_at = datetime.now(timezone.utc).isoformat()
                rec.budget_spent_cents += cost_cents
                rec.updated_at = node.finished_at
                return
            raise RunStatusError(f"[V4-004] node {node_id} not in run {run_id}")
        self._edit(run_id, apply)

    def mark_node_failed(
        self, run_id: str, node_id: str, error_code: str, error_message: str,
    ) -> None:
        def apply(rec: WorkPathRunRecord) -> None:
            for node in rec.nodes:
                if node.node_id == node_id:
                    if node.status == RunStatus.COMPLETED:
                        raise RunStatusError(f"[V4-008] completed node cannot fail: {node_id}")
                    node.status = RunStatus.FAILED
                    node.error_code = error_code
                    node.error_message = error_message
                    node.finished_at = datetime.now(timezone.utc).isoformat()
                    rec.updated_at = node.finished_at
                    return
            raise RunStatusError(f"[V4-004] node {node_id} not in run {run_id}")
        self._edit(run_id, apply)

    def cancel(self, run_id: str) -> bool:
        if self.get_run(run_id) is None:
            return False
        def apply(rec: WorkPathRunRecord) -> bool:
            if rec.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED):
                return False
            rec.status = RunStatus.CANCELED
            rec.updated_at = datetime.now(timezone.utc).isoformat()
            return True
        return self._edit(run_id, apply)

    def reset(self) -> None:
        """测试用 — 清空"""
        with self._mtx:
            self._runs.clear()
        self.idempotency.clear()
