"""True policy/connectivity boundary for V4 platform dispatcher.

These tests are intentionally provider-free. They do not claim that a public
URL, a domain allowlist, or a local fixture establishes platform access.
"""
from workflows.v4.registry import OperationRegistry


def test_whitelisted_url_is_not_connected_authorization():
    result = OperationRegistry().dispatch("platform.permission_check", {
        "url": "https://www.douyin.com/user/owned_by_someone"
    })
    assert result["url_policy_passed"] is True
    assert result["status"] == "blocked"
    assert result["error_code"] == "PLATFORM_CONNECTOR_NOT_CONNECTED"
    assert result["authenticated"] is False
    assert result["provider_connected"] is False
    assert result["mock"] is False


def test_unknown_host_fails_closed():
    result = OperationRegistry().dispatch("platform.permission_check", {
        "url": "https://douyin.com.attacker.invalid/user/abc"
    })
    assert result["status"] == "blocked"
    assert result["url_policy_passed"] is False
    assert result["error_code"] == "PLATFORM_URL_POLICY_DENIED"


def test_missing_url_fails_closed():
    registry = OperationRegistry()
    for op in ("platform.permission_check", "platform.homepage_parse"):
        result = registry.dispatch(op, {})
        assert result["status"] == "blocked"
        assert result["error_code"] == "URL_REQUIRED"


def test_homepage_cannot_invent_items_without_provider(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_ALLOW_MOCK_PLATFORM", raising=False)
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    result = OperationRegistry().dispatch("platform.homepage_parse", {
        "url": "https://www.douyin.com/user/abc"
    })
    assert result["status"] == "blocked"
    assert result["error_code"] == "PLATFORM_CONNECTOR_NOT_CONNECTED"
    assert result["mock"] is False
    assert "items" not in result
    assert "total" not in result


def test_explicit_mock_is_typed_and_conspicuously_marked(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "test")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_PLATFORM", "1")
    result = OperationRegistry().dispatch("platform.homepage_parse", {
        "url": "https://www.douyin.com/user/abc", "limit": 2
    })
    assert result["status"] == "mock_only"
    assert result["mock"] is True
    assert result["retrieved_policy"] == "mock"
    assert result["total"] == 2
    assert len(result["items"]) == 2
    assert all(item["rights_status"] == "unknown_need_user_confirm" for item in result["items"])
    assert all(item["title"].startswith("[MOCK]") for item in result["items"])


def test_mock_mode_does_not_override_platform_policy(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "test")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_PLATFORM", "1")
    result = OperationRegistry().dispatch("platform.homepage_parse", {
        "url": "https://www.douyin.com/private/user/abc"
    })
    assert result["status"] == "blocked"
    assert result["error_code"] == "PLATFORM_URL_POLICY_DENIED"
    assert result["mock"] is False
