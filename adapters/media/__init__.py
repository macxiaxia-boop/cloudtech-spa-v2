"""adapters.media — 媒体生成适配层 (mock-only)
所有 provider 均为 stub，绝不调真实 API。
"""
from .types import MediaRequest, MediaResponse, ProviderError
from .media_adapter import MediaAdapter
from .provider_registry import ProviderRegistry

__all__ = [
    "MediaRequest",
    "MediaResponse",
    "ProviderError",
    "MediaAdapter",
    "ProviderRegistry",
]
