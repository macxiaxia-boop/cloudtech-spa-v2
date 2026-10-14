"""P8: actual CloudTech V4 operation registry contracts, not mock-as-real tests."""
from __future__ import annotations

from workflows.v4.registry import OperationRegistry


def test_homepage_parse_dict_does_not_crash_or_claim_real_capture():
    result = OperationRegistry().dispatch(
        "platform.homepage_parse",
        {"url": "https://www.douyin.com/user/authorized-placeholder", "limit": 4},
    )
    assert result["ok"] is False
    assert result["mock"] is True
    assert result["total"] == 4
    assert len(result["items"]) == 4
    assert result["status"] == "MOCK_HOMEPAGE_NOT_VERIFIED"
    assert result["rights_status"] == "unknown_need_user_confirm"


def test_permission_check_reads_actual_dict_fields_and_not_fake_authorization():
    result = OperationRegistry().dispatch(
        "platform.permission_check", {"url": "https://www.douyin.com/user/id"}
    )
    assert result["ok"] is False
    assert result["mock"] is True
    assert result["source_platform"] == "douyin"
    assert result["allowed_hint"] is True
    assert result["permission_verified"] is False


def test_blacklisted_platform_stays_blocked():
    result = OperationRegistry().dispatch(
        "platform.permission_check",
        {"url": "https://www.douyin.com/private/user"},
    )
    assert result["ok"] is False
    assert result["allowed_hint"] is False


def test_unknown_operation_cannot_return_success_shape():
    result = OperationRegistry().dispatch(
        "platform.this_tool_does_not_exist", {"test": "input"}
    )
    assert result["ok"] is False
    assert result["status"] == "UNREGISTERED_OPERATION"
    assert result["mock"] is True


def test_mock_zip_export_is_not_a_real_file():
    result = OperationRegistry().dispatch("export.zip", {"artifact": "a"})
    assert result["ok"] is False
    assert result["mock"] is True
    assert result["package"] == "mock-zip"
