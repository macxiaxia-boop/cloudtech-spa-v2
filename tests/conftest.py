"""Explicitly opt into the legacy mock V4 auth ONLY inside V4/adapter tests.

Production (and an unspecified runtime environment) never get this bypass.
"""
from pathlib import Path
import pytest

@pytest.fixture(autouse=True)
def _v4_isolated_dev_auth(monkeypatch, request):
    test_name = Path(str(request.node.fspath)).name
    if test_name.startswith(("test_v4_", "test_adapters_")):
        monkeypatch.setenv("CLOUDTECH_ENV", "test")
        monkeypatch.setenv("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", "1")
        monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_MEDIA", "1")
        monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_ASR", "1")
        monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_PLATFORM", "1")
        monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_ARTICLE", "1")
        monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_LLM", "1")
