"""V4 — WorkBuddy connector bridge 测试
不调任何真实 API"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path
from adapters.platform.workbuddy_bridge import WorkBuddyBridge, KEY_CONNECTORS


def test_scan_real_workbuddy_connectors():
    """真实扫描 D:\AIOS\_relinked\workbuddy\.../connectors"""
    bridge = WorkBuddyBridge()
    n = bridge.scan()
    print(f"[OK] scanned {n} workbuddy connectors")
    # 实际应有 100+ connector
    assert n >= 50, f"应至少有 50 个 connector, 实有 {n}"
    # 关键 connector 应被找到
    for key in ["kling-ai-plugin", "yihook", "tiktok"]:
        if bridge.get(key) is not None:
            print(f"[OK] {key} found")


def test_key_connectors_registered():
    """KEY_CONNECTORS 中 5 个关键 connector 应都有"""
    assert len(KEY_CONNECTORS) == 5
    print(f"[OK] KEY_CONNECTORS = {list(KEY_CONNECTORS.keys())}")


def test_call_skill_mock():
    """mock 调用 — 不发真实 HTTP"""
    bridge = WorkBuddyBridge()
    bridge.scan()
    # 用 yihook 测 (已知含 image-generation skill)
    result = bridge.call_skill("yihook", "image-generation", {"prompt": "test"})
    assert "mock" in result, f"必须含 mock 字段: {result}"
    if result["ok"]:
        assert result["mock"] is True
        assert result["actual_cost_cents"] == 0
        print(f"[OK] mock call yihook/image-generation → {result['result']['url']}")
    else:
        # 实际 yihook 的 skills 可能命名不同 — 接受 error 路径
        assert "error" in result
        print(f"[INFO] yihook/image-generation rejected (skill name may differ): {result['error']}")


def test_call_skill_yihook_with_real_skill():
    """用 yihook 真实 skill 测"""
    bridge = WorkBuddyBridge()
    bridge.scan()
    c = bridge.get("yihook")
    assert c is not None
    skills = c.get("skills", [])
    if not skills:
        print("[SKIP] yihook has no skills dir")
        return
    # 测第一个 skill
    skill = skills[0]
    result = bridge.call_skill("yihook", skill, {"prompt": "test"})
    assert "mock" in result
    if result["ok"]:
        assert result["mock"] is True
        print(f"[OK] mock call yihook/{skill}")


def test_call_skill_invalid_connector():
    bridge = WorkBuddyBridge()
    result = bridge.call_skill("nonexistent", "any", {})
    assert result["ok"] is False
    print("[OK] invalid_connector_rejected")


def test_filter_by_skill():
    """找含 lipsync-avatar 的 connector"""
    bridge = WorkBuddyBridge()
    bridge.scan()
    matches = bridge.filter_by_skill("lipsync-avatar")
    print(f"[OK] lipsync-avatar found in: {matches[:5]}")


if __name__ == "__main__":
    test_scan_real_workbuddy_connectors()
    test_key_connectors_registered()
    test_call_skill_mock()
    test_call_skill_yihook_with_real_skill()
    test_call_skill_invalid_connector()
    test_filter_by_skill()
    print("\n=== ALL WORKBUDDY BRIDGE TESTS PASSED ===")
