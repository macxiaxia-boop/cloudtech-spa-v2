"""V4 media_gate 测试 — 服务端白名单"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workflows.v4 import MediaGate, MediaGateError


def test_allowed_image_generate():
    MediaGate.check("image.generate", "METERED_MEDIA")
    print("[OK] image.generate allowed")


def test_allowed_video_generate():
    MediaGate.check("video.generate", "METERED_MEDIA")
    print("[OK] video.generate allowed")


def test_denied_chat():
    try:
        MediaGate.check("chat", "METERED_MEDIA")
        assert False, "chat 必须被拒"
    except MediaGateError as e:
        print(f"[OK] chat denied → {e}")


def test_denied_qa():
    try:
        MediaGate.check("qa", "METERED_MEDIA")
        assert False
    except MediaGateError:
        print("[OK] qa denied")


def test_denied_transcribe():
    try:
        MediaGate.check("transcribe", "METERED_MEDIA")
        assert False
    except MediaGateError:
        print("[OK] transcribe denied (即使 METERED_MEDIA)")


def test_unknown_media_op_rejected():
    """白名单外 media op 必须被拒"""
    try:
        MediaGate.check("image.something_unusual", "METERED_MEDIA")
        assert False, "白名单外必须 deny"
    except MediaGateError as e:
        print(f"[OK] unknown_media_op denied → {e}")


def test_free_local_bypass():
    """FREE_LOCAL 不受 7 类媒体白名单约束 (但黑名单仍生效)"""
    MediaGate.check("vision.analyze", "FREE_LOCAL")  # 非黑名单, 非白名单 media, FREE_LOCAL 通过
    print("[OK] FREE_LOCAL bypass (vision.analyze)")


def test_list_allowed():
    allowed = MediaGate.list_allowed()
    assert "image.generate" in allowed
    assert "video.generate" in allowed
    print(f"[OK] allowed count = {len(allowed)}")


if __name__ == "__main__":
    test_allowed_image_generate()
    test_allowed_video_generate()
    test_denied_chat()
    test_denied_qa()
    test_denied_transcribe()
    test_unknown_media_op_rejected()
    test_free_local_bypass()
    test_list_allowed()
    print("\n=== ALL MEDIA_GATE TESTS PASSED ===")
