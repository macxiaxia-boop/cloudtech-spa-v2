"""媒体请求/响应数据类型"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class MediaRequest:
    """媒体生成请求"""
    operation: str           # image.generate / image.edit / video.generate 等
    inputs: Dict[str, Any]  # prompt, ref_urls, mask_url, duration_sec, …
    tenant_id: str
    idempotency_key: str
    estimated_cost_cents: int
    cost_class: str = "METERED_MEDIA"


@dataclass
class MediaResponse:
    """媒体生成响应 (mock)"""
    request_id: str                          # mock_<uuid>
    provider: str
    operation: str
    output_assets: List[Dict[str, Any]]      # [{url, mime, sha256, mock}]
    actual_cost_cents: int
    duration_ms: int
    mock: bool = True
    provider_metadata: Dict[str, Any] = field(default_factory=dict)


class ProviderError(Exception):
    """Provider 异常 — mock 场景下也显式 raise"""
    pass
