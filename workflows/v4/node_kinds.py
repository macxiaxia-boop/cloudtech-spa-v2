"""V4 — 7 类 node_kind
TRANSFORM 解析/文字 | FETCH_PUBLIC 有授权数据获取 | MODEL_REASON 现有分析模型
MEDIA_GENERATE 单独供应商预算保护 | HUMAN_REVIEW 人工 | EXPORT | PUBLISH_WITH_AUTH
节点间只传 asset_ids/result_ids 等 typed refs, 不复制巨大内容/不泄露密钥
"""
from enum import Enum


class NodeKind(str, Enum):
    TRANSFORM = "TRANSFORM"
    FETCH_PUBLIC = "FETCH_PUBLIC"
    MODEL_REASON = "MODEL_REASON"
    MEDIA_GENERATE = "MEDIA_GENERATE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    EXPORT = "EXPORT"
    PUBLISH_WITH_AUTH = "PUBLISH_WITH_AUTH"


# 节点类别 → 默认 cost_class
NODE_KIND_COST_CLASS = {
    NodeKind.TRANSFORM: "FREE_LOCAL",
    NodeKind.FETCH_PUBLIC: "METERED_NONMEDIA",
    NodeKind.MODEL_REASON: "METERED_NONMEDIA",
    NodeKind.MEDIA_GENERATE: "METERED_MEDIA",
    NodeKind.HUMAN_REVIEW: "FREE_LOCAL",
    NodeKind.EXPORT: "FREE_LOCAL",
    NodeKind.PUBLISH_WITH_AUTH: "EXTERNAL_WRITE",
}

# 节点类别 → 默认幂等保证级别
NODE_KIND_IDEMPOTENT = {
    NodeKind.TRANSFORM: True,
    NodeKind.FETCH_PUBLIC: True,
    NodeKind.MODEL_REASON: True,
    NodeKind.MEDIA_GENERATE: False,  # 必须 idempotency_key
    NodeKind.HUMAN_REVIEW: False,
    NodeKind.EXPORT: False,
    NodeKind.PUBLISH_WITH_AUTH: False,
}

NODE_KINDS = [k.value for k in NodeKind]
