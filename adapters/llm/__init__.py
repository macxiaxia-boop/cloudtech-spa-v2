"""CloudTech V4 LLM interface: real provider bridge + explicitly isolated test mock.

This module never connects to the Claude Code session implicitly, never
charges without explicit real-provider opt-in, and never promotes mock text
to an actual model inference result.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    system: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    mock: bool
    provider: str
    request_id: str = ""


class LLMProviderUnavailable(RuntimeError):
    pass


class CloudTechLLMProvider:
    """Real, explicitly authorized model provider backed by existing CloudTech router."""
    name = "cloudtech-router"

    def is_available(self) -> bool:
        from src.cloudtech.live_migration.provider_router import (
            ProviderMode, detect_provider_mode,
        )
        return detect_provider_mode() == ProviderMode.REAL_DEEPSEEK

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise LLMProviderUnavailable("[MODEL_NOT_CONNECTED] No authorized real LLM")
        from src.cloudtech.live_migration.provider_router import chat
        response = chat(
            [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ]
        )
        if response.mode != "success" or response.provider != "deepseek":
            raise LLMProviderUnavailable(
                "[MODEL_FAILED] Upstream provider did not return an accepted inference"
            )
        return LLMResponse(
            text=response.content, mock=False, provider=response.provider,
            request_id=response.request_id,
        )


class MockLLMProvider:
    """Test-only contract stub. It is not a production model backend."""
    name = "explicit-test-mock"

    def is_available(self) -> bool:
        return (
            os.environ.get("CLOUDTECH_ENV", "").lower() in {"test", "development"}
            and os.environ.get("CLOUDTECH_ALLOW_MOCK_LLM") == "1"
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.is_available():
            raise LLMProviderUnavailable("[LLM-MOCK-403] Synthetic LLM disabled")
        return LLMResponse(
            text="[MOCK STRUCTURE] source script structure sample",
            mock=True, provider=self.name, request_id="mock-test-only",
        )
