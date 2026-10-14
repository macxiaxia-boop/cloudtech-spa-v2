"""Negative safety tests: mock media and mock ASR must NEVER pass as production results."""
import pytest
from adapters.media.provider_registry import ProviderRegistry
from adapters.media.types import MediaRequest, ProviderError
from adapters.media.media_adapter import MediaAdapter
from adapters.transcribe.asr_engine import transcribe
from workflows.v4 import BudgetGate, IdempotencyStore

def _image_req():
    return MediaRequest(
        operation="image.generate", inputs={"prompt": "local test"},
        tenant_id="tenant1", idempotency_key="mock_guard_idem",
        estimated_cost_cents=100, cost_class="METERED_MEDIA",
    )

def test_mock_image_rejected_in_production_even_with_flag(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_MEDIA", "1")
    with pytest.raises(ProviderError, match="MEDIA-MOCK-403"):
        ProviderRegistry().dispatch(_image_req())

def test_mock_image_rejected_when_runtime_unspecified(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_ENV", raising=False)
    monkeypatch.delenv("CLOUDTECH_ALLOW_MOCK_MEDIA", raising=False)
    with pytest.raises(ProviderError, match="MEDIA-MOCK-403"):
        ProviderRegistry().dispatch(_image_req())

def test_media_failure_releases_budget_without_receipt(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.delenv("CLOUDTECH_ALLOW_MOCK_MEDIA", raising=False)
    budget = BudgetGate()
    adapter = MediaAdapter(ProviderRegistry(), budget, IdempotencyStore())
    with pytest.raises(ProviderError, match="MEDIA-MOCK-403"):
        adapter.request(_image_req())
    assert budget.get_spent("tenant1") == 0

def test_mock_asr_rejected_in_production_even_with_flag(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_ASR", "1")
    with pytest.raises(RuntimeError, match="ASR-MOCK-403"):
        transcribe("/tmp/nonexistent-recording.mp3")

def test_mock_asr_rejected_when_runtime_unspecified(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_ENV", raising=False)
    monkeypatch.delenv("CLOUDTECH_ALLOW_MOCK_ASR", raising=False)
    with pytest.raises(RuntimeError, match="ASR-MOCK-403"):
        transcribe("/tmp/nonexistent-recording.mp3")

def test_explicit_isolated_test_mode_still_supports_mocks(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "test")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_MEDIA", "1")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_ASR", "1")
    image = ProviderRegistry().dispatch(_image_req())
    transcript = transcribe("synthetic-test")
    assert image.mock is True
    assert image.output_assets[0]["mock"] is True
    assert transcript["mock"] is True

def test_mock_homepage_catalog_rejected_in_production(monkeypatch):
    from adapters.platform.homepage_parser import parse_homepage
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_PLATFORM", "1")
    with pytest.raises(RuntimeError, match="PLATFORM-MOCK-403"):
        parse_homepage("https://www.douyin.com/user/abc")

def test_tikhub_fake_provider_rejected_in_production(monkeypatch):
    from adapters.platform.tikhub_connector import TikHubConnector
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_PLATFORM", "1")
    with pytest.raises(PermissionError, match="TIK-MOCK-403"):
        TikHubConnector().douyin_homepage("https://www.douyin.com/user/abc")

def test_tikhub_real_provider_needs_explicit_authorization(monkeypatch):
    from adapters.platform.tikhub_connector import TikHubConnector
    monkeypatch.delenv("CLOUDTECH_ALLOW_REAL_PLATFORM", raising=False)
    monkeypatch.delenv("TIKHUB_TOKEN", raising=False)
    with pytest.raises(PermissionError, match="TIK-LIVE-403"):
        TikHubConnector(enable_real=True).douyin_homepage("https://www.douyin.com/user/abc")
