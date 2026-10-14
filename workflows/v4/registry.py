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

    # ------------------------------------------------------------------
    # 执行层 dispatch:op_id → adapter → result
    # ------------------------------------------------------------------
    def dispatch(self, op_id: str, inputs: Dict, llm_provider=None) -> Dict:
        """将 op_id 路由到具体 adapter/函数,返回 dict

        内置路由:
          url.normalize          → 简单 URL 标准化
          platform.*             → adapters.platform.*
          transcript.*           → adapters.transcribe.*
          content.*              → adapters.content.* (LLM 注入)
          doubao.tts             → adapters.tts.*
          ocr.*                  → adapters.ocr.*
          search.*               → adapters.search.*
          metrics.*              → adapters.metrics.*
          meeting.*              → adapters.meeting.*
          video.assembly         → adapters.ffmpeg_video.*
          export.zip             → 打包 export(简化)
          其他                   → stub
        """
        from dataclasses import asdict, is_dataclass
        def _to_dict(obj):
            if obj is None:
                return {}
            if isinstance(obj, dict):
                return obj
            if is_dataclass(obj):
                return asdict(obj)
            if isinstance(obj, (list, tuple)):
                return [_to_dict(x) for x in obj]
            return obj

        # Load only the adapter needed by this op. Otherwise an optional
        # missing plugin would break unrelated core operations before dispatch.
        try:
            if op_id == "url.normalize":
                from urllib.parse import urlparse
                u = inputs.get("url", "")
                p = urlparse(u)
                return {"normalized": f"{p.scheme}://{p.netloc}{p.path}", "host": p.netloc, "path": p.path}

            if op_id == "platform.permission_check":
                from adapters import platform as Aplat
                r = Aplat.permission_gate.check(inputs["url"])
                if not isinstance(r, dict):
                    return {"ok": False, "status": "INVALID_PERMISSION_CONTRACT", "mock": True}
                # The existing gate currently implements mock policy only;
                # allowed=True is NOT proof of account authorization.
                return {
                    "ok": False,
                    "status": "MOCK_PERMISSION_NOT_AUTHORIZED",
                    "allowed_hint": bool(r.get("allowed", False)),
                    "reason": r.get("reason", "UNKNOWN"),
                    "source_platform": r.get("source_platform", "unknown"),
                    "mock": True,
                    "permission_verified": False,
                }

            if op_id == "platform.homepage_parse":
                from adapters import platform as Aplat
                parsed = Aplat.homepage_parser.parse_homepage(
                    inputs["url"], limit=inputs.get("limit", 30)
                )
                if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list):
                    return {"ok": False, "status": "INVALID_HOMEPAGE_CONTRACT", "mock": True}
                items = parsed["items"][:30]
                # Existing parser creates MOCK works, not real platform data.
                return {
                    "ok": False,
                    "status": "MOCK_HOMEPAGE_NOT_VERIFIED",
                    "total": len(items),
                    "items": _to_dict(items),
                    "source_platform": parsed.get("source_platform"),
                    "source_author": parsed.get("source_author"),
                    "rights_status": "unknown_need_user_confirm",
                    "mock": True,
                }

            if op_id == "content.dedupe":
                items = inputs.get("items", [])
                seen, out = set(), []
                for x in items:
                    if isinstance(x, dict):
                        k = x.get("url") or x.get("id") or str(x)
                    else:
                        k = str(x)
                    if k not in seen:
                        seen.add(k); out.append(x)
                return {"deduped": len(out), "items": out}

            if op_id == "transcript.extract":
                from adapters import transcribe as Atrans
                audio = inputs.get("audio_path") or inputs.get("video_path")
                if not audio:
                    return {"text": "", "segments": []}
                return _to_dict(Atrans.asr_engine.transcribe(audio))

            if op_id == "video.frame_extract":
                from adapters import transcribe as Atrans
                return {"frames": _to_dict(Atrans.frame_extractor.extract(inputs["video_path"], n=8))}

            if op_id == "content.structure.analyze":
                from adapters import content as Acont
                return _to_dict(Acont.structure_analyzer.analyze(
                    inputs.get("segments", []),
                    inputs.get("transcript", ""),
                    provider=llm_provider,
                ))

            if op_id == "content.original_script.generate":
                from adapters import content as Acont
                return _to_dict(Acont.original_script_generator.generate(
                    inputs.get("structure", {}),
                    inputs.get("audience", ""),
                    inputs.get("industry", ""),
                    inputs.get("transcript", ""),
                    provider=llm_provider,
                ))

            if op_id == "content.storyboard.generate":
                from adapters import content as Acont
                result = Acont.director.direct(
                    inputs.get("goal", ""),
                    inputs.get("audience", ""),
                    inputs.get("industry", ""),
                    inputs.get("transcript"),
                    provider=llm_provider,
                )
                return {"storyboard": _to_dict(result)}

            if op_id == "content.similarity.review":
                from adapters import content as Acont
                r = Acont.similarity_qc.review(
                    inputs.get("original", ""),
                    inputs.get("derivative", ""),
                    inputs.get("structure", {}),
                )
                return _to_dict(r)

            if op_id == "doubao.tts":
                from adapters.tts import MockTTSEngine
                from adapters.tts import TTSRequest
                return _to_dict(MockTTSEngine().synthesize(TTSRequest(text=inputs.get("text", ""))))

            if op_id == "ocr.recognize":
                from adapters.ocr import MockOCREngine
                return _to_dict(MockOCREngine().recognize(inputs.get("image_path", "")))

            if op_id == "search.authors":
                from adapters.search import MockSearchEngine
                return _to_dict(MockSearchEngine().search_authors(
                    inputs.get("keywords", []), platform=inputs.get("platform", "douyin")))

            if op_id == "metrics.fetch":
                from adapters.metrics import MockMetricsStore
                return _to_dict(MockMetricsStore().fetch_videos(inputs.get("author_id", "")))

            if op_id == "meeting.process":
                from adapters.meeting import MockMeetingProcessor
                from adapters.meeting import MeetingRequest
                return _to_dict(MockMeetingProcessor().process(
                    MeetingRequest(audio_path=inputs.get("audio_path", ""))))

            if op_id == "video.assembly":
                from adapters.ffmpeg_video import FFmpegEngine
                from adapters.ffmpeg_video import AssemblyRequest
                return _to_dict(FFmpegEngine().assemble(
                    AssemblyRequest(segments=inputs.get("segments", []),
                                   output_path=inputs.get("output_path", "/tmp/out.mp4"))))

            if op_id == "export.zip":
                return {
                    "ok": False, "status": "MOCK_EXPORT_NOT_AN_ARTIFACT",
                    "package": "mock-zip", "files": list(inputs.keys()), "mock": True,
                }

            return {
                "ok": False, "op": op_id, "status": "UNREGISTERED_OPERATION",
                "error": "operation has no verified adapter; fail closed",
                "mock": True,
            }

        except Exception as e:
            return {"op": op_id, "status": "error", "error": str(e)[:300]}

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
