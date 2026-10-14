"""Provider 注册表 + 4 个 mock stub provider"""
from __future__ import annotations
import base64
import os
import io
import uuid
from typing import Dict, List, Any

from PIL import Image

from .types import MediaRequest, MediaResponse, ProviderError


def _require_explicit_mock_media() -> None:
    """Never return fabricated assets in a real deployment by accident."""
    is_isolated = os.environ.get("CLOUDTECH_ENV", "").lower() in {"test", "development"}
    allowed = os.environ.get("CLOUDTECH_ALLOW_MOCK_MEDIA") == "1"
    if not (is_isolated and allowed):
        raise ProviderError(
            "[MEDIA-MOCK-403] No real provider is wired; enable explicit mock media only in isolated tests"
        )


# ── shared mock helpers ──────────────────────────────────────────────────────

def _mock_img_asset() -> Dict[str, Any]:
    """生成 1×1 white PNG + metadata (mock, 不写文件)"""
    img = Image.new("RGB", (1, 1), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {
        "url": f"mock://asset/{uuid.uuid4().hex[:12]}",
        "mime": "image/png",
        "sha256": "mock_sha256_placeholder",
        "base64_data": b64,
        "mock": True,
    }


def _mock_video_asset(duration_sec: int = 5) -> Dict[str, Any]:
    return {
        "url": f"mock://asset/{uuid.uuid4().hex[:12]}",
        "mime": "video/mp4",
        "sha256": "mock_sha256_placeholder",
        "duration_sec": duration_sec,
        "mock": True,
    }


# ── base class ───────────────────────────────────────────────────────────────

class BaseProvider:
    name: str = "base"
    endpoint_env: str = ""      # 占位，不读取
    auth_env: str = ""           # 占位，不读取
    capabilities: List[str] = []

    def dispatch(self, req: MediaRequest) -> MediaResponse:
        raise ProviderError(f"[{self.name}] dispatch 未实现")


# ── 即梦 ─────────────────────────────────────────────────────────────────────

class JimengProvider(BaseProvider):
    """即梦: image.generate / image.edit / image.inpaint"""
    name = "jimeng"
    endpoint_env = "JIMENG_API_BASE"      # 不读取
    auth_env = "JIMENG_API_KEY"          # 不读取
    capabilities = ["image.generate", "image.edit", "image.inpaint"]

    def dispatch(self, req: MediaRequest) -> MediaResponse:
        _require_explicit_mock_media()
        if req.operation not in self.capabilities:
            raise ProviderError(f"[{self.name}] 不支持 operation={req.operation}")
        import time; t0 = time.monotonic()
        return MediaResponse(
            request_id=f"mock_{uuid.uuid4().hex[:16]}",
            provider=self.name,
            operation=req.operation,
            output_assets=[_mock_img_asset()],
            actual_cost_cents=30,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )


# ── Yihook ───────────────────────────────────────────────────────────────────

class YihookProvider(BaseProvider):
    """Yihook: image.generate (gpt-image-2)"""
    name = "yihook"
    endpoint_env = "YIHOOK_API_BASE"     # 不读取
    auth_env = "YIHOOK_API_KEY"          # 不读取
    capabilities = ["image.generate"]

    def dispatch(self, req: MediaRequest) -> MediaResponse:
        _require_explicit_mock_media()
        if req.operation not in self.capabilities:
            raise ProviderError(f"[{self.name}] 不支持 operation={req.operation}")
        import time; t0 = time.monotonic()
        return MediaResponse(
            request_id=f"mock_{uuid.uuid4().hex[:16]}",
            provider=self.name,
            operation=req.operation,
            output_assets=[_mock_img_asset()],
            actual_cost_cents=20,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )


# ── 可灵 ─────────────────────────────────────────────────────────────────────

class KlingProvider(BaseProvider):
    """可灵: video.generate / video.extend / video.image_to_video"""
    name = "kling"
    endpoint_env = "KLING_API_BASE"       # 不读取
    auth_env = "KLING_API_KEY"           # 不读取
    capabilities = ["video.generate", "video.extend", "video.image_to_video"]

    def dispatch(self, req: MediaRequest) -> MediaResponse:
        _require_explicit_mock_media()
        if req.operation not in self.capabilities:
            raise ProviderError(f"[{self.name}] 不支持 operation={req.operation}")
        duration = req.inputs.get("duration_sec", 5)
        if not (1 <= duration <= 60):
            raise ProviderError(f"[{self.name}] duration_sec={duration} 超出 [1,60]")
        import time; t0 = time.monotonic()
        return MediaResponse(
            request_id=f"mock_{uuid.uuid4().hex[:16]}",
            provider=self.name,
            operation=req.operation,
            output_assets=[_mock_video_asset(duration)],
            actual_cost_cents=150,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )


# ── 豆包 Seedream ────────────────────────────────────────────────────────────

class DoubaoSeedreamProvider(BaseProvider):
    """豆包 Seedream: image.generate"""
    name = "doubao_seedream"
    endpoint_env = "DOUBAO_SEEDREAM_API_BASE"   # 不读取
    auth_env = "DOUBAO_SEEDREAM_API_KEY"       # 不读取
    capabilities = ["image.generate"]

    def dispatch(self, req: MediaRequest) -> MediaResponse:
        _require_explicit_mock_media()
        if req.operation not in self.capabilities:
            raise ProviderError(f"[{self.name}] 不支持 operation={req.operation}")
        import time; t0 = time.monotonic()
        return MediaResponse(
            request_id=f"mock_{uuid.uuid4().hex[:16]}",
            provider=self.name,
            operation=req.operation,
            output_assets=[_mock_img_asset()],
            actual_cost_cents=25,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )


# ── registry ─────────────────────────────────────────────────────────────────

class ProviderRegistry:
    """operation → provider 路由"""

    def __init__(self) -> None:
        self._providers: Dict[str, BaseProvider] = {}
        for p in [JimengProvider(), YihookProvider(),
                  KlingProvider(), DoubaoSeedreamProvider()]:
            for cap in p.capabilities:
                self._providers[cap] = p

    def dispatch(self, req: MediaRequest) -> MediaResponse:
        provider = self._providers.get(req.operation)
        if provider is None:
            raise ProviderError(f"[Registry] 无 provider 支持 operation={req.operation}")
        return provider.dispatch(req)

    def list_operations(self) -> List[str]:
        return sorted(self._providers.keys())
