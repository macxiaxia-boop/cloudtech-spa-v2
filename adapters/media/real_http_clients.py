"""V4 — 真实 HTTP client 接口骨架 (仅契约, 不触发真实请求)
按红线 #60 #22: 真实 provider 调用必须经 L4 user 拍板 + budget reserve.
本文件定义 4 provider 的 HTTP 接口契约, 供后续替换 mock.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .types import MediaRequest, MediaResponse


@dataclass
class HttpClientConfig:
    base_url: str
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "
    timeout_sec: int = 120
    max_retries: int = 2
    rate_limit_per_min: int = 60


class HttpClientError(Exception):
    pass


class ProviderHttpClient:
    """真实 HTTP client 接口契约 — 子类必须实现 _call()
    任何实现必须:
      1. 不在 init 阶段发请求
      2. _call 必须先过 auth + budget check
      3. 返回 MediaResponse.mock = False
    """

    config: HttpClientConfig

    def _check_ready(self) -> None:
        """子类实现: 验证 config 完整 (URL/timeout)"""
        if not self.config.base_url:
            raise HttpClientError("[HC-001] base_url 缺失")

    def _build_headers(self, auth_token: str) -> Dict[str, str]:
        return {
            self.config.auth_header: self.config.auth_prefix + auth_token,
            "Content-Type": "application/json",
            "User-Agent": "CloudTech-V4/1.0",
        }

    def _call(self, req: MediaRequest, auth_token: str) -> MediaResponse:
        """子类实现: 真实 HTTP 调用"""
        raise NotImplementedError("ProviderHttpClient 是接口契约, 子类必须实现 _call()")


# === 4 个 provider 接口契约 ===

class JimengHttpClient(ProviderHttpClient):
    """即梦 — image.generate/edit/inpaint
    真实 endpoint: https://visual.volcengineapi.com (待 L4 拍板)
    """
    pass


class YihookHttpClient(ProviderHttpClient):
    """Yihook — image.generate (gpt-image-2)
    真实 endpoint: https://api.yihook.cn/v1/images/generations (待 L4 拍板)
    """
    pass


class KlingHttpClient(ProviderHttpClient):
    """可灵 — video.generate/extend/image_to_video
    真实 endpoint: https://api.klingai.com (待 L4 拍板)
    """
    pass


class DoubaoSeedreamHttpClient(ProviderHttpClient):
    """豆包 Seedream — image.generate
    真实 endpoint: https://ark.cn-beijing.volces.com/api/v3/images/generations
    (DOUBAO_API_KEY 已在 mcp_credentials.env 实证)
    """
    pass


# === Provider 能力矩阵 (8 类 op × 4 provider) ===

PROVIDER_CAPABILITY_MATRIX: Dict[str, List[str]] = {
    "image.generate": ["jimeng", "yihook", "doubao_seedream"],
    "image.edit": ["jimeng"],
    "image.inpaint": ["jimeng", "yihook"],
    "image.reference_fusion": ["jimeng"],
    "image.crop_or_outpaint": [],  # local, no provider
    "video.generate": ["kling"],
    "video.extend": ["kling"],
    "video.image_to_video": ["kling"],
    "video.stitch_ffmpeg": [],  # local, no provider
    "doubao.tts": ["doubao_seedream"],  # via tts endpoint, not in media_gate
}


def get_providers_for_op(operation: str) -> List[str]:
    return PROVIDER_CAPABILITY_MATRIX.get(operation, [])


def get_client_class(provider_name: str) -> Optional[type]:
    return {
        "jimeng": JimengHttpClient,
        "yihook": YihookHttpClient,
        "kling": KlingHttpClient,
        "doubao_seedream": DoubaoSeedreamHttpClient,
    }.get(provider_name)
