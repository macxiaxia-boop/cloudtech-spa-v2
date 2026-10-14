"""Gated LLM provider bridge tests: never use a paid network call."""
import pytest
from adapters.llm import (
    CloudTechLLMProvider, MockLLMProvider, LLMRequest, LLMProviderUnavailable,
)

def test_real_provider_unavailable_without_configuration(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDTECH_ALLOW_REAL_PROVIDER", raising=False)
    provider = CloudTechLLMProvider()
    assert provider.is_available() is False
    with pytest.raises(LLMProviderUnavailable, match="MODEL_NOT_CONNECTED"):
        provider.generate(LLMRequest(prompt="sensitive test prompt"))

def test_mock_provider_is_explicit_and_marks_mock():
    provider = MockLLMProvider()
    assert provider.is_available()
    response = provider.generate(LLMRequest(prompt="structure"))
    assert response.mock is True
    assert response.provider == "explicit-test-mock"

def test_mock_provider_prohibited_in_production(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_LLM", "1")
    provider = MockLLMProvider()
    assert not provider.is_available()
    with pytest.raises(LLMProviderUnavailable, match="LLM-MOCK-403"):
        provider.generate(LLMRequest(prompt="do not echo a production prompt"))

def test_real_provider_requires_explicit_spend_authorization(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "never-send-dummy")
    monkeypatch.delenv("CLOUDTECH_ALLOW_REAL_PROVIDER", raising=False)
    assert CloudTechLLMProvider().is_available() is False
