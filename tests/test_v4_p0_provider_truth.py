"""Provider truthfulness and paid-call authorization; no external calls."""
from src.cloudtech.live_migration import provider_router as router
from src.cloudtech.live_migration.minimax_provider import chat_minimax


def test_empty_environment_never_fakes_a_model_success(monkeypatch):
    for key in (
        "CLOUDTECH_ENV", "CLOUDTECH_RC2_USE_FAKE",
        "CLOUDTECH_RC2_USE_MINIMAX", "DEEPSEEK_API_KEY",
        "CLOUDTECH_ALLOW_REAL_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)
    assert router.detect_provider_mode() is router.ProviderMode.UNAVAILABLE
    response = router.chat([{"role": "user", "content": "sensitive-user-input"}])
    assert response.mode == "invalid"
    assert response.provider == "unavailable"
    assert response.cost_usd == 0.0
    assert response.metadata["model_call_executed"] is False
    assert "sensitive-user-input" not in response.content


def test_fake_flag_without_test_environment_is_not_an_inference_provider(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("CLOUDTECH_RC2_USE_FAKE", "1")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDTECH_ALLOW_REAL_PROVIDER", raising=False)
    assert router.detect_provider_mode() is router.ProviderMode.UNAVAILABLE


def test_api_key_alone_does_not_authorize_real_cost(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "do-not-call-this-key")
    monkeypatch.delenv("CLOUDTECH_ALLOW_REAL_PROVIDER", raising=False)
    assert router.detect_provider_mode() is router.ProviderMode.UNAVAILABLE
    assert router.chat([{"role": "user", "content": "ping"}]).mode == "invalid"


def test_explicit_real_provider_route_is_available_but_not_called(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "dummy")
    monkeypatch.setenv("CLOUDTECH_ALLOW_REAL_PROVIDER", "1")
    assert router.detect_provider_mode() is router.ProviderMode.REAL_DEEPSEEK


def test_minimax_legacy_shim_cannot_be_mistaken_for_inference():
    result = chat_minimax([{"role": "user", "content": "secret to hide"}])
    assert result.mode == "invalid"
    assert result.provider == "unavailable"
    assert result.metadata["model_call_executed"] is False
    assert result.cost_usd == 0
    assert "secret to hide" not in result.content


def test_minimax_forced_hook_does_not_return_fake_success():
    result = router._chat_minimax([{"role": "user", "content": "secret"}],
                                   "minimax-m3", 100)
    assert result.mode == "invalid"
    assert result.metadata["model_call_executed"] is False
