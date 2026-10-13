"""V4 — 幂等键管理
防止同一收费操作被双扣费 — 服务端强制
key  = tenant_id/project_id/workpath_id/run_id/node_id/input_hash
首次见到 key → 创建新 run
后续见到 key → 返回原 run_id, 不重新触发 provider
"""
from __future__ import annotations
import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class IdempotencyHit:
    key: str
    run_id: Optional[str]
    node_id: Optional[str] = None
    provider_req_id: Optional[str] = None


class IdempotencyStore:
    def __init__(self) -> None:
        self._store: Dict[str, IdempotencyHit] = {}
        self._mtx = threading.Lock()

    def compute_key(
        self,
        tenant_id: str,
        project_id: Optional[str],
        path_id: str,
        node_id: str,
        payload: Dict[str, Any],
    ) -> str:
        """幂等键: tenant_id|project_id|path_id|node_id|sha256(payload)"""
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{tenant_id}|{project_id or '_'}|{path_id}|{node_id}|{h}"

    def check(self, key: str) -> Optional[IdempotencyHit]:
        with self._mtx:
            return self._store.get(key)

    def bind(self, key: str, run_id: str, node_id: Optional[str] = None) -> None:
        with self._mtx:
            hit = self._store.get(key)
            if hit is None:
                hit = IdempotencyHit(key=key, run_id=run_id, node_id=node_id)
                self._store[key] = hit
            else:
                hit.run_id = run_id
                if node_id:
                    hit.node_id = node_id

    def set_provider_req_id(self, key: str, provider_req_id: str) -> None:
        with self._mtx:
            hit = self._store.get(key)
            if hit:
                hit.provider_req_id = provider_id = provider_req_id

    def clear(self) -> None:
        with self._mtx:
            self._store.clear()
