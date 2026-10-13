"""V4 — 资产别名解析
图 1/图 6 = alias → asset_id+version_id (必须)
新上传素材默认仅为新增 source, 不覆盖历史图 6
alias 模糊 → fail closed (仅问一个必要问题)
"""
from __future__ import annotations
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


class AssetBindingError(Exception):
    pass


@dataclass
class AssetBinding:
    binding_id: str
    tenant_id: str
    project_id: Optional[str]
    conversation_id: str
    alias: str
    role: str
    asset_id: str
    version_id: str
    message_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AliasSnapshot:
    snapshot_id: str
    conversation_id: str
    message_id: str
    alias: str
    asset_id: str
    version_id: str
    snapshot_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AssetResolver:
    """线程安全别名解析器"""

    _instance: Optional["AssetResolver"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # conversation_id+alias → AssetBinding (当前)
        self._current: Dict[str, AssetBinding] = {}
        # conversation_id+message_id+alias → AliasSnapshot (历史)
        self._snapshots: Dict[str, AliasSnapshot] = {}
        self._mtx = threading.Lock()

    @classmethod
    def instance(cls) -> "AssetResolver":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = AssetResolver()
        return cls._instance

    def bind(
        self,
        tenant_id: str,
        project_id: Optional[str],
        conversation_id: str,
        alias: str,
        role: str,
        asset_id: str,
        version_id: str,
        message_id: Optional[str] = None,
    ) -> AssetBinding:
        """绑定 alias → asset_version (会话级)"""
        key = self._key(tenant_id, conversation_id, alias)
        with self._mtx:
            binding = AssetBinding(
                binding_id="ab_" + secrets.token_hex(6),
                tenant_id=tenant_id,
                project_id=project_id,
                conversation_id=conversation_id,
                alias=alias,
                role=role,
                asset_id=asset_id,
                version_id=version_id,
                message_id=message_id,
            )
            self._current[key] = binding
            if message_id:
                snap_key = f"{tenant_id}|{conversation_id}|{message_id}|{alias}"
                snap = AliasSnapshot(
                    snapshot_id="as_" + secrets.token_hex(6),
                    conversation_id=conversation_id,
                    message_id=message_id,
                    alias=alias,
                    asset_id=asset_id,
                    version_id=version_id,
                )
                self._snapshots[snap_key] = snap
        return binding

    def resolve(
        self,
        tenant_id: str,
        conversation_id: str,
        alias: str,
        at_message_id: Optional[str] = None,
    ) -> AssetBinding:
        """解析 alias → AssetBinding
        at_message_id 指定 → 取该时刻的 snapshot (历史确定)
        at_message_id 缺省 → 取当前 binding
        """
        with self._mtx:
            if at_message_id:
                snap_key = f"{tenant_id}|{conversation_id}|{at_message_id}|{alias}"
                snap = self._snapshots.get(snap_key)
                if snap is None:
                    raise AssetBindingError(
                        f"[AR-001] 历史 alias '{alias}' 不存在 (message_id={at_message_id})"
                    )
                return AssetBinding(
                    binding_id="ab_resolved",
                    tenant_id=tenant_id,
                    project_id=None,
                    conversation_id=conversation_id,
                    alias=alias,
                    role="resolved",
                    asset_id=snap.asset_id,
                    version_id=snap.version_id,
                    message_id=at_message_id,
                )
            key = self._key(tenant_id, conversation_id, alias)
            binding = self._current.get(key)
            if binding is None:
                raise AssetBindingError(
                    f"[AR-002] alias '{alias}' 在当前会话未绑定 (conversation={conversation_id})"
                )
            return binding

    def resolve_or_none(
        self,
        tenant_id: str,
        conversation_id: str,
        alias: str,
        at_message_id: Optional[str] = None,
    ) -> Optional[AssetBinding]:
        try:
            return self.resolve(tenant_id, conversation_id, alias, at_message_id)
        except AssetBindingError:
            return None

    def list_aliases(
        self,
        tenant_id: str,
        conversation_id: str,
    ) -> List[AssetBinding]:
        with self._mtx:
            out = []
            for k, b in self._current.items():
                if b.tenant_id == tenant_id and b.conversation_id == conversation_id:
                    out.append(b)
            return out

    def new_version(
        self,
        tenant_id: str,
        project_id: Optional[str],
        conversation_id: str,
        alias: str,
        new_asset_id: str,
        new_version_id: str,
        parent_version_id: Optional[str] = None,
        edit_spec: Optional[Dict] = None,
        source_refs: Optional[List[str]] = None,
        message_id: Optional[str] = None,
    ) -> AssetBinding:
        """同一 alias 创建新版本 (例如沙发替换)
        parent_version_id 校验: 必须来自同一 alias 的历史 binding
        """
        if parent_version_id is not None:
            current = self.resolve_or_none(tenant_id, conversation_id, alias)
            if current is None or current.version_id != parent_version_id:
                raise AssetBindingError(
                    f"[AR-003] parent_version_id={parent_version_id} 不匹配当前 alias={alias}"
                )
        return self.bind(
            tenant_id=tenant_id,
            project_id=project_id,
            conversation_id=conversation_id,
            alias=alias,
            role=self._current.get(self._key(tenant_id, conversation_id, alias), AssetBinding(
                binding_id="x", tenant_id=tenant_id, project_id=project_id,
                conversation_id=conversation_id, alias=alias, role="unknown",
                asset_id="", version_id=""
            )).role or "edited",
            asset_id=new_asset_id,
            version_id=new_version_id,
            message_id=message_id,
        )

    def reset(self) -> None:
        with self._mtx:
            self._current.clear()
            self._snapshots.clear()

    @staticmethod
    def _key(tenant_id: str, conversation_id: str, alias: str) -> str:
        return f"{tenant_id}|{conversation_id}|{alias}"
