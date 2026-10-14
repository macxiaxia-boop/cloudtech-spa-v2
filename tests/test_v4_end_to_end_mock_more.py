"""V4 — 4 个剩余旗舰路径 E2E mock 测试
补漏: WP-VIDEO-TRANSCRIBE / WP-ARTICLE-REWRITE / WP-GROWTH-VIDEO / WP-PRODUCT-MARKETING
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from fastapi import FastAPI
from api.v4 import router
from api.v4.auth import mint_jwt

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _post(path, body):
    """带 dev-mode auth"""
    if "V4_JWT_SECRET" in os.environ:
        del os.environ["V4_JWT_SECRET"]
    return client.post(path, json=body)


def test_e2e_video_transcribe():
    """WP-VIDEO-TRANSCRIBE: 用户上传视频 → ASR → 结构拆解 → 原创脚本 → QC"""
    # 1. Resolve
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "提取这个视频的逐字稿, 然后仿写",
        "input_refs": [{"role": "video_source", "value": "asset_video_001"}]
    })
    assert r.json()["matched_path_id"] == "WP-VIDEO-TRANSCRIBE"
    print("[OK] video_transcribe step 1: resolve")

    # 2. Create run
    body = {
        "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1,
        "input_bindings": {"video_source": "asset_video_001"},
        "idempotency_key": "video_e2e_001",
        "conversation_id": "C_video_001",
    }
    r = _post("/v4/workpaths/runs?tenant_id=t1", body)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    print(f"[OK] video_transcribe step 2: create_run → {run_id}")

    # 3. Alias bind (源视频作为图 1)
    r = _post("/v4/assets/bind?tenant_id=t1", {
        "tenant_id": "t1", "conversation_id": "C_video_001",
        "alias": "源视频", "role": "video_source",
        "asset_id": "asset_video_001", "version_id": "v1",
        "message_id": "msg_1",
    })
    assert r.status_code == 200

    # 4. Resolve alias
    r = _post("/v4/assets/resolve-alias?tenant_id=t1", {
        "conversation_id": "C_video_001", "alias": "源视频"
    })
    assert r.json()["asset_id"] == "asset_video_001"
    print("[OK] video_transcribe step 3-4: bind + resolve")

    # 5. Idempotent re-run
    r2 = _post("/v4/workpaths/runs?tenant_id=t1", body)
    assert r2.json()["run_id"] == run_id
    assert r2.json().get("idempotent_hit") is True
    print("[OK] video_transcribe step 5: idempotent")


def test_e2e_article_rewrite():
    """WP-ARTICLE-REWRITE: 图文 URL → 原文 + 配图 → 二创"""
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "把这篇图文改写成平台笔记",
        "input_refs": [{"role": "article_url", "value": "https://example.com/a1"}]
    })
    assert r.json()["matched_path_id"] == "WP-ARTICLE-REWRITE"
    print("[OK] article_rewrite step 1: resolve")

    body = {
        "path_id": "WP-ARTICLE-REWRITE", "revision": 1,
        "input_bindings": {"article_url": "https://example.com/a1"},
        "idempotency_key": "article_e2e_001",
        "conversation_id": "C_article_001",
        "budget_cap_cents": 2000,
    }
    r = _post("/v4/workpaths/runs?tenant_id=t1", body)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    print(f"[OK] article_rewrite step 2: create_run → {run_id}")

    # Bind source article as alias
    r = _post("/v4/assets/bind?tenant_id=t1", {
        "tenant_id": "t1", "conversation_id": "C_article_001",
        "alias": "源图文", "role": "article_source",
        "asset_id": "asset_article_001", "version_id": "v1",
        "message_id": "msg_1",
    })
    assert r.status_code == 200
    print("[OK] article_rewrite step 3: bind source")


def test_e2e_growth_video():
    """WP-GROWTH-VIDEO: 首尾帧 → 15 秒视频"""
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "给我生成毛坯到完工的生长视频 15 秒",
        "input_refs": [
            {"role": "first_frame", "value": "asset_first"},
            {"role": "last", "value": "asset_last"},
            {"role": "duration_sec", "value": 15},
        ]
    })
    assert r.json()["matched_path_id"] == "WP-GROWTH-VIDEO"
    print("[OK] growth_video step 1: resolve")

    body = {
        "path_id": "WP-GROWTH-VIDEO", "revision": 1,
        "input_bindings": {
            "first_frame": "asset_first",
            "frame": "asset_last",
            "duration_sec": 15,
        },
        "idempotency_key": "growth_video_e2e_002",
        "conversation_id": "C_growth_001",
        "budget_cap_cents": 5000,
    }
    r = _post("/v4/workpaths/runs?tenant_id=t1", body)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    print(f"[OK] growth_video step 2: create_run → {run_id}")

    # Bind 首帧/尾帧
    for alias, asset in [("首帧", "asset_first"), ("尾帧", "asset_last")]:
        r = _post("/v4/assets/bind?tenant_id=t1", {
            "tenant_id": "t1", "conversation_id": "C_growth_001",
            "alias": alias, "role": "frame",
            "asset_id": asset, "version_id": "v1", "message_id": "msg_1",
        })
        assert r.status_code == 200
    print("[OK] growth_video step 3: bind 首帧/尾帧")


def test_e2e_product_marketing():
    """WP-PRODUCT-MARKETING: 商品源图 → 图文营销全套"""
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "把这商品图做成多渠道营销全套",
        "input_refs": [
            {"role": "product_image", "value": "asset_product"},
            {"role": "selling_points", "value": "高性价比"},
        ]
    })
    assert r.json()["matched_path_id"] == "WP-PRODUCT-MARKETING"
    print("[OK] product_marketing step 1: resolve")

    body = {
        "path_id": "WP-PRODUCT-MARKETING", "revision": 1,
        "input_bindings": {"product_image": "asset_product", "selling_points": "高性价比"},
        "idempotency_key": "product_e2e_001",
        "conversation_id": "C_product_001",
        "budget_cap_cents": 8000,
    }
    r = _post("/v4/workpaths/runs?tenant_id=t1", body)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    print(f"[OK] product_marketing step 2: create_run → {run_id}")

    # Bind product image
    r = _post("/v4/assets/bind?tenant_id=t1", {
        "tenant_id": "t1", "conversation_id": "C_product_001",
        "alias": "图1", "role": "product_image",
        "asset_id": "asset_product", "version_id": "v1", "message_id": "msg_1",
    })
    assert r.status_code == 200
    print("[OK] product_marketing step 3: bind product")


def test_e2e_all_six_paths_resolvable():
    """6 旗舰路径都能被 resolve + create_run"""
    # 用具体 utterances 触发关键词匹配
    paths_utterances_inputs = [
        ("WP-BLOGGER-RESEARCH", "研究博主主页", {"homepage_url": "x", "target_industry": "decoration"}),
        ("WP-VIDEO-TRANSCRIBE", "提取视频逐字稿", {"video_source": "x"}),
        ("WP-ARTICLE-REWRITE", "改写图文笔记", {"article_url": "x"}),
        ("WP-RENOVATION-FULL", "装修全屋效果图", {"floorplan_image": "x", "style_reference": "y"}),
        ("WP-GROWTH-VIDEO", "毛坯生长视频", {"first_frame": "x", "frame": "y"}),
        ("WP-PRODUCT-MARKETING", "商品营销全套", {"product_image": "x"}),
    ]
    for path_id, utterance, inputs in paths_utterances_inputs:
        r = client.post("/v4/workpaths/resolve", json={
            "utterance": utterance,
            "input_refs": [{"role": k, "value": v} for k, v in inputs.items()]
        })
        assert r.json()["matched_path_id"] == path_id, f"{path_id} resolve failed: got {r.json()['matched_path_id']}, utterance={utterance!r}"
        body = {"path_id": path_id, "revision": 1, "input_bindings": inputs}
        r2 = _post(f"/v4/workpaths/runs?tenant_id=t_e2e_all", body)
        assert r2.status_code == 200, f"{path_id} create_run failed: {r2.status_code}"
    print(f"[OK] all 6 flagship paths resolvable + runnable")


if __name__ == "__main__":
    test_e2e_video_transcribe()
    test_e2e_article_rewrite()
    test_e2e_growth_video()
    test_e2e_product_marketing()
    test_e2e_all_six_paths_resolvable()
    print("\n=== ALL 4 ADDITIONAL E2E PATH TESTS PASSED ===")
