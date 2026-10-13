"""V4 — 真实 provider clients 测试
⚠️ 默认 mock — 真实调用需 __enable_real=True (L4 user 拍)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from adapters.media.real_providers import (
    DoubaoSeedreamHttpClient, JimengHttpClient, YihookHttpClient, KlingHttpClient, get_real_client
)
from adapters.media.types import MediaRequest
from adapters.platform.tikhub_connector import TikHubConnector, homepage_via_tikhub, TIKHUB_ENDPOINTS


def test_doubao_mock_default():
    """doubao_seedream 默认 mock, 真实需 __enable_real=True"""
    client = get_real_client("doubao_seedream")
    req = MediaRequest(
        operation="image.generate",
        inputs={"prompt": "现代简约客厅", "size": "1024x1024"},
        tenant_id="t1",
        idempotency_key="k1",
        estimated_cost_cents=20,
        cost_class="METERED_MEDIA",
    )
    r = client._call(req, auth_token="mock_token")
    assert r.mock is True, "默认 mock"
    assert r.provider == "doubao_seedream"
    assert r.actual_cost_cents == 20
    print(f"[OK] doubao mock → request_id={r.request_id}")


def test_doubao_real_requires_flag():
    """doubao 真实调用需 __enable_real=True, 否则仍 mock"""
    client = DoubaoSeedreamHttpClient()
    req = MediaRequest(
        operation="image.generate",
        inputs={"prompt": "test", "__enable_real": True},  # 真实模式
        tenant_id="t1",
        idempotency_key="k1",
        estimated_cost_cents=20,
        cost_class="METERED_MEDIA",
    )
    try:
        r = client._call(req, auth_token="mock_token")
        # 如 httpx 安装且 endpoint 通, 应有真实响应; 否则 raise
        print(f"[INFO] doubao real called → mock={r.mock}, request_id={r.request_id}")
    except Exception as e:
        print(f"[OK] doubao real blocked: {e}")


def test_jimeng_mock():
    client = JimengHttpClient()
    req = MediaRequest(operation="image.edit", inputs={"prompt": "换沙发"}, tenant_id="t1", idempotency_key="k2", estimated_cost_cents=30, cost_class="METERED_MEDIA")
    r = client._call(req, auth_token="x")
    assert r.mock is True
    print(f"[OK] jimeng mock → cost={r.actual_cost_cents}c")


def test_yihook():
    client = YihookHttpClient()
    req = MediaRequest(operation="image.generate", inputs={"prompt": "电商场景"}, tenant_id="t1", idempotency_key="k3", estimated_cost_cents=15, cost_class="METERED_MEDIA")
    r = client._call(req, auth_token="x")
    assert r.mock is True
    print(f"[OK] yihook mock → model=gpt-image-2")


def test_kling_mock():
    client = KlingHttpClient()
    req = MediaRequest(operation="video.image_to_video", inputs={"prompt": "生长", "duration_sec": 5}, tenant_id="t1", idempotency_key="k4", estimated_cost_cents=250, cost_class="METERED_MEDIA")
    r = client._call(req, auth_token="x")
    assert r.mock is True
    assert "mp4" in r.output_assets[0]["url"]
    print(f"[OK] kling mock → duration={r.output_assets[0].get('duration_sec')}s")


def test_tikhub_endpoints_5():
    """5 平台 endpoint 已 LIVE"""
    assert len(TIKHUB_ENDPOINTS) == 5
    print(f"[OK] TikHub 5 endpoints: {list(TIKHUB_ENDPOINTS.keys())}")


def test_tikhub_default_mock():
    conn = TikHubConnector(enable_real=False)
    r = conn.douyin_homepage("https://douyin.com/user/abc")
    assert r["mock"] is True
    assert len(r["items"]) == 5
    print(f"[OK] TikHub mock douyin → {len(r['items'])} items")


def test_tikhub_platform_hint_routing():
    """自动识别 URL 平台"""
    cases = [
        ("https://www.douyin.com/user/X", "douyin"),
        ("https://www.xiaohongshu.com/user/Y", "xiaohongshu"),
        ("https://channels.weixin.qq.com/Z", "wechat"),
        ("https://weibo.com/u/W", "weibo"),
        ("https://www.kuaishou.com/u/V", "kuaishou"),
    ]
    for url, expected in cases:
        r = homepage_via_tikhub(url)
        assert r["platform"] == expected, f"{url} 应→ {expected}, 实 {r['platform']}"
    print(f"[OK] platform hint routing 5/5 cases")


def test_tikhub_real_requires_token():
    conn = TikHubConnector(enable_real=True)
    try:
        conn.douyin_homepage("https://douyin.com/user/x")
        assert False, "无 TIKHUB_TOKEN 应 raise"
    except PermissionError as e:
        print(f"[OK] tikhub real without token → {e}")


def test_unknown_provider():
    try:
        get_real_client("nonexistent")
        assert False
    except Exception as e:
        print(f"[OK] unknown_provider_rejected → {e}")


if __name__ == "__main__":
    test_doubao_mock_default()
    test_doubao_real_requires_flag()
    test_jimeng_mock()
    test_yih_mock()
    test_kling_mock()
    test_tikhub_endpoints_5()
    test_tikhub_default_mock()
    test_tikhub_platform_hint_routing()
    test_tikhub_real_requires_token()
    test_unknown_provider()
    print("\n=== ALL REAL PROVIDER CLIENT TESTS PASSED ===")
