"""V4 — 服务端媒体门禁
allow: image.generate/image.edit/image.inpaint/image.reference_fusion/video.generate/video.extend/video.image_to_video
deny: chat/qa/plan/analyze/transcribe/research/code/extract/download/scrape/route/publish/generic_completion/embedding
V4 spec §09 红线: 靠提示词不能阻止通用媒体中转站误收费; 必须服务端严格白名单
"""
from __future__ import annotations
from typing import FrozenSet


# 媒体生成白名单 — 仅这 7 类可调真实 provider
ALLOWED_MEDIA_OPERATIONS: FrozenSet[str] = frozenset({
    "image.generate",
    "image.edit",
    "image.inpaint",
    "image.reference_fusion",
    "video.generate",
    "video.extend",
    "video.image_to_video",
})

# 黑名单 — 即使在 prompt 中提到也必须拒绝
DENIED_OPERATIONS: FrozenSet[str] = frozenset({
    "chat",
    "qa",
    "plan",
    "analyze",
    "transcribe",
    "research",
    "code",
    "extract",
    "download",
    "scrape",
    "route",
    "publish",
    "generic_completion",
    "embedding",
    "summarize",
    "translate",
})


class MediaGateError(Exception):
    pass


class MediaGate:
    """服务端白名单 — 不依赖 prompt 工程"""

    @staticmethod
    def check(operation: str, cost_class: str = "METERED_MEDIA") -> None:
        """检查 operation 是否允许; 不允许直接 raise MediaGateError
        规则:
          1. 任何黑名单 op 全局拒绝 (包括 FREE_LOCAL)
          2. METERED_MEDIA 必须是 7 类白名单之一
          3. 其他 cost_class 不受白名单约束 (但黑名单仍生效)
        """
        if not isinstance(operation, str) or not operation.strip():
            raise MediaGateError("[MG-001] operation 必须非空字符串")
        op = operation.strip().lower()
        if op in DENIED_OPERATIONS:
            raise MediaGateError(f"[MG-002] operation '{operation}' 在黑名单 (Deny-default)")
        if cost_class == "METERED_MEDIA" and op not in ALLOWED_MEDIA_OPERATIONS:
            raise MediaGateError(
                f"[MG-003] METERED_MEDIA operation '{operation}' 不在白名单 "
                f"(允许: {sorted(ALLOWED_MEDIA_OPERATIONS)})"
            )
        # FREE_LOCAL/METERED_NONMEDIA/EXTERNAL_WRITE 仅受黑名单约束, 白名单 bypass

    @staticmethod
    def list_allowed() -> FrozenSet[str]:
        return ALLOWED_MEDIA_OPERATIONS

    @staticmethod
    def list_denied() -> FrozenSet[str]:
        return DENIED_OPERATIONS
