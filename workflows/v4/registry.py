"""V4 — Operation Registry
从 data/skill_orchestrator/<name>/SKILL.md 加载 + 适配器包装
不做第二套抓取器/图像工具 — 复用已有 skill 目录
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .media_gate import MediaGate


@dataclass
class OperationDefinition:
    op_id: str
    provider: str
    kind: str  # TRANSFORM/FETCH_PUBLIC/MODEL_REASON/MEDIA_GENERATE/HUMAN_REVIEW/EXPORT/PUBLISH_WITH_AUTH
    side_effect: bool
    required_inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    auth_scope: str = "user"
    price_policy: str = "FREE_LOCAL"
    rate_limit: Optional[str] = None
    idempotency: bool = True
    health_probe: Optional[str] = None
    fallback_op: Optional[str] = None
    privacy_class: str = "public"
    confidence: float = 1.0
    skill_md_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "op_id": self.op() if False else self.op_id,
            "provider": self.provider,
            "kind": self.kind,
            "side_effect": self.side_effect,
            "required_inputs": self.required_inputs,
            "outputs": self.outputs,
            "auth_scope": self.auth_scope,
            "price_policy": self.price_policy,
            "rate_limit": self.rate_limit,
            "idempotency": self.idempotency,
            "health_probe": self.health_probe,
            "fallback_op": self.fallback_op,
            "privacy_class": self.privacy_class,
            "confidence": self.confidence,
            "skill_md_path": self.skill_md_path,
        }


class OperationRegistry:
    """从 skill_orchestrator 目录加载所有 SKILL.md → OperationDefinition"""

    # 默认 OP→kind 映射 (基于名称启发)
    DEFAULT_KIND_BY_OP_PREFIX = {
        "image.": "MEDIA_GENERATE",
        "video.": "MEDIA_GENERATE",
        "transcript.": "TRANSFORM",
        "asr.": "TRANSFORM",
        "extract.": "FETCH_PUBLIC",
        "fetch.": "FETCH_PUBLIC",
        "scrape.": "FETCH_PUBLIC",
        "tts.": "MEDIA_GENERATE",
        "doubao.tts": "MEDIA_GENERATE",
        "content.": "MODEL_REASON",
        "content.similarity": "MODEL_REASON",
        "content.original_script": "MODEL_REASON",
        "export.": "EXPORT",
        "publish.": "PUBLISH_WITH_AUTH",
    }

    def __init__(self, skill_root: Optional[Path] = None) -> None:
        self._ops: Dict[str, OperationDefinition] = {}
        self._skill_root = skill_root
        if skill_root is not None:
            self.load_from_skills(skill_root)

    def load_from_skills(self, root: Path) -> int:
        """扫描 root 下所有 SKILL.md; 解析为 OperationDefinition"""
        if not root.exists():
            return 0
        loaded = 0
        for skill_md in root.rglob("SKILL.md"):
            try:
                text = skill_md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            op_id = self._infer_op_id(skill_md.parent.name)
            kind = self._infer_kind(op_id)
            price = self._infer_price(op_id, text)
            # 服务端校验: MEDIA_GENERATE 必须经 MediaGate
            if kind == "MEDIA_GENERATE":
                try:
                    MediaGate.check(op_id, price)
                except Exception:
                    continue  # 黑名单/白名单拒绝的 op 不载入
            op = OperationDefinition(
                op_id=op_id,
                provider=self._infer_provider(text),
                kind=kind,
                side_effect=kind in {"MEDIA_GENERATE", "PUBLISH_WITH_AUTH"},
                required_inputs=self._parse_inputs(text),
                outputs=self._parse_outputs(text),
                auth_scope="tenant" if kind == "MEDIA_GENERATE" else "user",
                price_policy=price,
                idempotency=kind not in {"MEDIA_GENERATE", "PUBLISH_WITH_AUTH"},
                privacy_class=self._infer_privacy(text),
                confidence=0.9,
                skill_md_path=str(skill_md),
            )
            self._ops[op_id] = op
            loaded += 1
        return loaded

    def register(self, op: OperationDefinition) -> None:
        self._ops[op.op_id] = op

    def get(self, op_id: str) -> Optional[OperationDefinition]:
        return self._ops.get(op_id)

    def list_by_kind(self, kind: str) -> List[OperationDefinition]:
        return [o for o in self._ops.values() if o.kind == kind]

    def list_all(self) -> List[OperationDefinition]:
        return list(self._ops.values())

    def count(self) -> int:
        return len(self._ops)

    # --- 内部启发式 ---

    def _infer_op_id(self, name: str) -> str:
        n = name.strip().lower()
        if n.startswith("content.") or n.startswith("transcript.") or n.startswith("export."):
            return n
        if "." in n:
            return n
        return n.replace("-", ".")

    def _infer_kind(self, op_id: str) -> str:
        for prefix, kind in self.DEFAULT_KIND_BY_OP_PREFIX.items():
            if op_id.startswith(prefix):
                return kind
        return "TRANSFORM"

    def _infer_price(self, op_id: str, text: str) -> str:
        m = re.search(r"price_policy\s*[:=]\s*(\w+)", text, re.IGNORECASE)
        if m:
            v = m.group(1).upper()
            if v in {"FREE_LOCAL", "METERED_NONMEDIA", "METERED_MEDIA", "EXTERNAL_WRITE"}:
                return v
        if op_id.startswith(("image.", "video.", "tts.", "doubao.tts")):
            return "METERED_MEDIA"
        if op_id.startswith(("extract.", "fetch.", "scrape.", "publish.")):
            return "EXTERNAL_WRITE"
        return "FREE_LOCAL"

    def _infer_provider(self, text: str) -> str:
        m = re.search(r"provider\s*[:=]\s*(\S+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip("'\"")
        return "unknown"

    def _infer_privacy(self, text: str) -> str:
        if "personal" in text.lower() or "private" in text.lower():
            return "private"
        return "public"

    def _parse_inputs(self, text: str) -> List[str]:
        m = re.search(r"##\s*Inputs?\s*\n(.*?)(?=\n##|\Z)", text, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        block = m.group(1)
        return [line.strip("-* ").split()[0] for line in block.splitlines() if line.strip().startswith(("-", "*"))][:10]

    def _parse_outputs(self, text: str) -> List[str]:
        m = re.search(r"##\s*Outputs?\s*\n(.*?)(?=\n##|\Z)", text, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        block = m.group(1)
        return [line.strip("-* ").split()[0] for line in block.splitlines() if line.strip().startswith(("-", "*"))][:10]
