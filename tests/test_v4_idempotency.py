"""V4 idempotency + asset_resolver 测试"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workflows.v4 import IdempotencyStore, AssetResolver, AssetBindingError


def test_idempotency_compute_key():
    store = IdempotencyStore()
    k1 = store.compute_key("t1", "p1", "WP-X", "n1", {"a": 1, "b": 2})
    k2 = store.compute_key("t1", "p1", "WP-X", "n1", {"b": 2, "a": 1})
    assert k1 == k2, "同 payload 同 key (顺序无关)"
    k3 = store.compute_key("t1", "p1", "WP-X", "n1", {"a": 1, "b": 3})
    assert k1 != k3
    print("[OK] idempotency_compute_key deterministic + payload-sensitive")


def test_idempotency_bind_hit():
    store = IdempotencyStore()
    store.bind("k1", "run_001", "n1")
    hit = store.check("k1")
    assert hit and hit.run_id == "run_001"
    print("[OK] idempotency_bind_hit")


def test_alias_bind_and_resolve():
    resolver = AssetResolver()
    b = resolver.bind("t1", "p1", "c1", "图1", "floorplan", "asset_a", "v1", "msg_1")
    resolved = resolver.resolve("t1", "c1", "图1")
    assert resolved.asset_id == "asset_a"
    assert resolved.version_id == "v1"
    print(f"[OK] alias bind+resolve → {resolved.asset_id}/{resolved.version_id}")


def test_alias_resolve_at_message_id():
    resolver = AssetResolver()
    resolver.bind("t1", None, "c1", "图1", "image", "a1", "v1", "msg_1")
    resolver.bind("t1", None, "c1", "图1", "image", "a1", "v2", "msg_2")
    resolver.bind("t1", None, "c1", "图1", "image", "a1", "v3", "msg_3")
    hist = resolver.resolve("t1", "c1", "图1", at_message_id="msg_1")
    assert hist.version_id == "v1"
    print(f"[OK] alias_resolve_at_message_id → v1={hist.version_id}")


def test_alias_new_version_with_parent():
    resolver = AssetResolver()
    resolver.bind("t1", None, "c1", "图6", "sofa", "asset_sofa", "v1", "msg_1")
    b = resolver.new_version("t1", None, "c1", "图6", "asset_sofa", "v2", parent_version_id="v1")
    assert b.version_id == "v2"
    print("[OK] new_version with matching parent")


def test_alias_new_version_wrong_parent_rejected():
    resolver = AssetResolver()
    resolver.bind("t1", None, "c1", "图6", "sofa", "asset_sofa", "v1", "msg_1")
    try:
        resolver.new_version("t1", None, "c1", "图6", "asset_sofa", "v2", parent_version_id="v99")
        assert False, "应拒绝错误 parent_version_id"
    except AssetBindingError as e:
        print(f"[OK] wrong_parent_rejected → {e}")


def test_alias_unbound_resolve_404():
    resolver = AssetResolver()
    try:
        resolver.resolve("t1", "c1", "图99")
        assert False
    except AssetBindingError as e:
        print(f"[OK] unbound_resolve → {e}")


if __name__ == "__main__":
    test_idempotency_compute_key()
    test_idempotency_bind_hit()
    test_alias_bind_and_resolve()
    test_alias_resolve_at_message_id()
    test_alias_new_version_with_parent()
    test_alias_new_version_wrong_parent_rejected()
    test_alias_unbound_resolve_404()
    print("\n=== ALL IDEMPOTENCY + ASSET_RESOLVER TESTS PASSED ===")
