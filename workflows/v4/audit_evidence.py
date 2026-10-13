"""V4 — Audit Evidence 写入辅助
按 V4 spec §08: provenance + decision + provider_response + rollback 全部需可追溯
对应 pg_v4_migration.sql audit_evidence 表 (id/run_id/node_id/evidence_kind/payload_json/evidence_hash)
⚠️ 默认 in-memory (开发) — 真实持久化需 L4 user 拍 DATABASE_URL
"""
from __future__ import annotations
import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class EvidenceRecord:
    id: str
    run_id: str
    node_id: Optional[str]
    evidence_kind: str  # input/output/decision/provider_response/rollback
    payload: Dict[str, Any]
    evidence_hash: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


class AuditEvidenceWriter:
    """线程安全 evidence writer; 支持注入持久化回调"""

    _instance: Optional["AuditEvidenceWriter"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._records: List[EvidenceRecord] = []
        self._mtx = threading.Lock()
        self._persistence: Optional[Callable[[EvidenceRecord], None]] = None

    @classmethod
    def instance(cls) -> "AuditEvidenceWriter":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = AuditEvidenceWriter()
        return cls._instance

    def bind_persistence(self, fn: Callable[[EvidenceRecord], None]) -> None:
        """注入真实持久化 (e.g. 写 Postgres audit_evidence 表)"""
        self._persistence = fn

    def write(
        self,
        run_id: str,
        node_id: Optional[str],
        evidence_kind: str,
        payload: Dict[str, Any],
    ) -> EvidenceRecord:
        """写一条 evidence; 自动算 evidence_hash (sha256 of payload)"""
        if evidence_kind not in {"input", "output", "decision", "provider_response", "rollback", "auth"}:
            raise ValueError(f"[AE-001] 非法 evidence_kind: {evidence_kind}")
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        ev_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        rec = EvidenceRecord(
            id="ev_" + ev_hash[:12],
            run_id=run_id,
            node_id=node_id,
            evidence_kind=evidence_kind,
            payload=payload,
            evidence_hash=ev_hash,
        )
        with self._mtx:
            self._records.append(rec)
        if self._persistence:
            try:
                self._persistence(rec)
            except Exception:
                pass  # 持久化失败不应阻塞流程 (但应记录)
        return rec

    def list_for_run(self, run_id: str) -> List[EvidenceRecord]:
        with self._mtx:
            return [r for r in self._records if r.run_id == run_id]

    def list_all(self) -> List[EvidenceRecord]:
        with self._mtx:
            return list(self._records)

    def reset(self) -> None:
        with self._mtx:
            self._records.clear()


# 集成到 orchestrator 的 hooks:
def on_node_input(run_id: str, node_id: str, inputs: Dict[str, Any]) -> None:
    AuditEvidenceWriter.instance().write(run_id, node_id, "input", {"inputs": inputs})


def on_node_output(run_id: str, node_id: str, output_ref: Dict[str, Any], cost_cents: int = 0, cost_class: str = "FREE_LOCAL") -> None:
    AuditEvidenceWriter.instance().write(
        run_id, node_id, "output",
        {"output_ref": output_ref, "cost_cents": cost_cents, "cost_class": cost_class},
    )


def on_provider_response(run_id: str, node_id: str, provider: str, request_id: str, response: Dict[str, Any]) -> None:
    AuditEvidenceWriter.instance().write(
        run_id, node_id, "provider_response",
        {"provider": provider, "request_id": request_id, "response": response},
    )


def on_auth(run_id: str, tenant_id: str, user_id: Optional[str], verdict: str) -> None:
    AuditEvidenceWriter.instance().write(
        run_id, None, "auth",
        {"tenant_id": tenant_id, "user_id": user_id, "verdict": verdict},
    )


def on_rollback(run_id: str, node_id: str, reason: str) -> None:
    AuditEvidenceWriter.instance().write(
        run_id, node_id, "rollback",
        {"reason": reason},
    )


def on_decision(run_id: str, node_id: str, decision: str, rationale: str) -> None:
    AuditEvidenceWriter.instance().write(
        run_id, node_id, "decision",
        {"decision": decision, "rationale": rationale},
    )
