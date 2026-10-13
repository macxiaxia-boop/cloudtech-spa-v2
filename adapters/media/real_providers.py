"""V4 — 真实 provider HTTP client 实现
⚠️ 红线 #60 #22 L4: 本文件写真实 HTTP client, 但默认 NEVER 调
需 user 拍 (DATABASE_URL + provider key) + 调用方显式 enable_real_providers=True
"""
from __future__ import annotations
import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .types import MediaRequest, MediaResponse
from .real_http_clients import ProviderHttpClient, HttpClientConfig, HttpClientError


def _env_or_die(env_var: str) -> str:
    """env var 必须存在, 不存在 raise"""
    v = os.environ.get(env_var)
    if not v:
        raise HttpClientError(f"[HC-ENV] env var {env_var} 未设置; 真实 provider 调用需 user 拍 L4")
    return v


@dataclass
class DoubaoSeedreamHttpClient(ProviderHttpClient):
    """豆包 Seedream 真实 HTTP client
    endpoint: https://ark.cn-beijing.volces.com/api/v3/images/generations
    auth: DOUBAO_API_KEY (mcp_credentials.env)
    model: doubao-seedream-3-0-t2i-250415 (或更新)
    """
    config: HttpClientConfig = None  # type: ignore

    def __post_init__(self):
        if self.config is None:
            self.config = HttpClientConfig(
                base_url="https://ark.cn-beijing.volces.com/api/v3/images/generations",
                auth_header="Authorization",
                auth_prefix="Bearer ",
                timeout_sec=120,
                max_retries=2,
            )

    def _call(self, req: MediaRequest, auth_token: str) -> MediaResponse:
        self._check_ready()
        prompt = req.inputs.get("prompt", "")
        size = req.inputs.get("size", "1024x1024")
        # 真实 request payload (按火山方舟 API 文档)
        body = {
            "model": "doubao-seedream-3-0-t2i-250415",
            "prompt": prompt,
            "size": size,
            "response_format": "url",
            "n": 1,
        }
        headers = self._build_headers(auth_token)
        # ⚠️ 真实调用: 必须由 user 拍 L4 + enable_real_providers=True
        if not req.inputs.get("__enable_real", False):
            # 返回 mock, 标 mock=True
            return MediaResponse(
                request_id="mock_" + uuid.uuid4().hex[:12],
                provider="doubao_seedream",
                operation=req.operation,
                output_assets=[{"url": f"mock://doubao_seedream/{uuid.uuid4().hex[:8]}.png", "mime": "image/png", "sha256": hashlib.sha256(prompt.encode()).hexdigest(), "mock": True}],
                actual_cost_cents=20,
                duration_ms=10,
                mock=True,
                provider_metadata={"endpoint": self.config.base_url, "model": body["model"]},
            )
        # 真实模式 — 必须 enable_real
        try:
            import httpx
        except ImportError:
            raise HttpClientError("[HC-DEPS] httpx 未安装, pip install httpx")
        t0 = time.time()
        r = httpx.post(
            self.config.base_url,
            headers=headers,
            json=body,
            timeout=self.config.timeout_sec,
        )
        duration = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            raise HttpClientError(f"[HC-REAL] doubao_seedream HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        url = data.get("data", [{}])[0].get("url", "")
        return MediaResponse(
            request_id=data.get("id", "doubao_" + uuid.uuid4().hex[:8]),
            provider="doubao_seedream",
            operation=req.operation,
            output_assets=[{"url": url, "mime": "image/png", "mock": False}],
            actual_cost_cents=20,
            duration_ms=duration,
            mock=False,
            provider_metadata={"endpoint": self.config.base_url, "model": body["model"], "raw": data},
        )


@dataclass
class JimengHttpClient(ProviderHttpClient):
    """即梦真实 HTTP client
    endpoint: https://visual.volcengineapi.com (待 L4 拍 — 即梦有 AK/SK 签名, 不是 Bearer)
    auth: JIMENG_ACCESS_KEY + JIMENG_SECRET_KEY (mcp_credentials.env)
    注意: 即梦走 AWS-style 签名 (v4), Bearer 不工作, 需自行计算 Signature
    """
    config: HttpClientConfig = None  # type: ignore

    def __post_init__(self):
        if self.config is None:
            self.config = HttpClientConfig(
                base_url="https://visual.volcengineapi.com",
                auth_header="Authorization",  # volces 实际用 AWS-style 签名
                auth_prefix="HMAC-SHA256 ",
                timeout_sec=120,
            )

    def _call(self, req: MediaRequest, auth_token: str) -> MediaResponse:
        self._check_ready()
        prompt = req.inputs.get("prompt", "")
        if not req.inputs.get("__enable_real", False):
            return MediaResponse(
                request_id="mock_" + uuid.uuid4().hex[:12],
                provider="jimeng",
                operation=req.operation,
                output_assets=[{"url": f"mock://jimeng/{uuid.uuid4().hex[:8]}.png", "mime": "image/png", "mock": True}],
                actual_cost_cents=30,
                duration_ms=10,
                mock=True,
                provider_metadata={"endpoint": self.config.base_url, "note": "需 AWS-style 签名, 待 user 拍 L4"},
            )
        # 真实模式 — 需 user 拍 L4 + 实现 volces 签名
        raise HttpClientError("[HC-REAL] jimeng 真实调用需 AWS-style v4 签名 + L4 user 拍 (JIMENG_ACCESS_KEY/SECRET)")


@dataclass
class YihookHttpClient(ProviderHttpClient):
    """Yihook 真实 HTTP client
    endpoint: https://app.yihook.cn/api/mcp (workbuddy MCP, streamable-http)
    auth: workbuddy-connector-plugins-official 已 live
    """
    config: HttpClientConfig = None  # type: ignore

    def __post_init__(self):
        if self.config is None:
            self.config = HttpClientConfig(
                base_url="https://app.yihook.cn/api/mcp",
                auth_header="Authorization",
                auth_prefix="Bearer ",
                timeout_sec=120,
            )

    def _call(self, req: MediaRequest, auth_token: str) -> MediaResponse:
        self._check_ready()
        prompt = req.inputs.get("prompt", "")
        if not req.inputs.get("__enable_real", False):
            return MediaResponse(
                request_id="mock_" + uuid.uuid4().hex[:12],
                provider="yihook",
                operation=req.operation,
                output_assets=[{"url": f"mock://yihook/{uuid.uuid4().hex[:8]}.png", "mime": "image/png", "mock": True}],
                actual_cost_cents=15,
                duration_ms=10,
                mock=True,
                provider_metadata={"endpoint": self.config.base_url, "model": "gpt-image-2"},
            )
        # 真实模式 — JSON-RPC over streamable-http
        try:
            import httpx
        except ImportError:
            raise HttpClientError("[HC-DEPS] httpx 未安装")
        t0 = time.time()
        body = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex[:8],
            "method": "image.generate",
            "params": {"prompt": prompt, "model": "gpt-image-2"},
        }
        r = httpx.post(
            self.config.base_url,
            headers={**self._build_headers(auth_token), "Content-Type": "application/json"},
            json=body,
            timeout=self.config.timeout_sec,
        )
        duration = int((time.time() - t0) * 1000)
        if r.status_code != 200:
            raise HttpClientError(f"[HC-REAL] yihook HTTP {r.status_code}")
        data = r.json()
        return MediaResponse(
            request_id=data.get("id", "yihook_" + uuid.uuid4().hex[:8]),
            provider="yihook",
            operation=req.operation,
            output_assets=[{"url": data.get("result", {}).get("url", ""), "mime": "image/png", "mock": False}],
            actual_cost_cents=15,
            duration_ms=duration,
            mock=False,
            provider_metadata={"endpoint": self.config.base_url},
        )


@dataclass
class KlingHttpClient(ProviderHttpClient):
    """可灵真实 HTTP client
    endpoint: https://api.klingai.com (待 L4 拍 — JWT 认证)
    auth: KLING_ACCESS_KEY + KLING_SECRET_KEY → JWT (HS256)
    """
    config: HttpClientConfig = None  # type: ignore

    def __post_init__(self):
        if self.config is None:
            self.config = HttpClientConfig(
                base_url="https://api.klingai.com",
                auth_header="Authorization",
                auth_prefix="Bearer ",
                timeout_sec=300,  # 视频生成较慢
            )

    def _call(self, req: MediaRequest, auth_token: str) -> MediaResponse:
        self._check_ready()
        prompt = req.inputs.get("prompt", "")
        duration_sec = req.inputs.get("duration_sec", 5)
        if not req.inputs.get("__enable_real", False):
            return MediaResponse(
                request_id="mock_" + uuid.uuid4().hex[:12],
                provider="kling",
                operation=req.operation,
                output_assets=[{"url": f"mock://kling/{uuid.uuid4().hex[:8]}.mp4", "mime": "video/mp4", "duration_sec": duration_sec, "mock": True}],
                actual_cost_cents=duration_sec * 50,  # 假设 0.5 元/秒
                duration_ms=10,
                mock=True,
                provider_metadata={"endpoint": self.config.base_url, "note": "需 JWT 认证 + L4 拍"},
            )
        # 真实模式 — JWT 认证 + 异步轮询
        raise HttpClientError("[HC-REAL] kling 真实调用需 JWT (PyJWT) + L4 user 拍")


def get_real_client(provider: str) -> ProviderHttpClient:
    factory = {
        "doubao_seedream": DoubaoSeedreamHttpClient,
        "jimeng": JimengHttpClient,
        "yihook": YihookHttpClient,
        "kling": KlingHttpClient,
    }
    if provider not in factory:
        raise HttpClientError(f"[HC-PROV] 未知 provider {provider}")
    return factory[provider]()
