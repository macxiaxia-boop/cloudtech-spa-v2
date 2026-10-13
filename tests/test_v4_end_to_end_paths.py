"""tests/test_v4_end_to_end_paths.py — Phase 5 e2e 6 旗舰路径 mock 端到端

参照 test_v4_end_to_end_mock.py 模式(FastAPI test client)
每条路径从 resolve → create_run → assets/bind 完整链路
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.v4 import router
from workflows.v4.paths import list_paths

app = FastAPI()
app.include_router(router)
client = TestClient(app)


# ============================================================
# WorkPath 注册检查
# ============================================================

class TestFlagshipPathsRegistered:
    def test_six_paths_registered(self):
        paths = list_paths()
        assert len(paths) == 6, f"expected 6 flagship paths, got {len(paths)}"

    def test_paths_have_required_fields(self):
        paths = list_paths()
        for p in paths:
            assert p["id"].startswith("WP-")
            assert p["title"]
            assert len(p["steps"]) >= 3, f"{p['id']} has only {len(p['steps'])} steps"
            assert p["planner"]
            assert len(p["inputs"]) >= 1
            assert p["exported_artifacts"]
            assert p["recovery"]
            assert p["evidence"]


# ============================================================
# E2E: 6 旗舰路径(API 模式)
# ============================================================

class TestPathE2E_Blogger:
    def test_resolve_create_bind_idempotent(self):
        # 1. resolve
        r = client.post("/v4/workpaths/resolve", json={
            "utterance": "研究博主",
            "project_id": "P_e2e_blogger",
            "input_refs": [
                {"role": "homepage_url", "value": "https://example.com/u1"},
                {"role": "target_industry", "value": "装修"},
            ],
        })
        assert r.status_code == 200
        assert r.json()["matched_path_id"] == "WP-BLOGGER-RESEARCH"

        # 2. create_run
        body = {
            "path_id": "WP-BLOGGER-RESEARCH",
            "revision": 1,
            "input_bindings": {"homepage_url": "https://example.com/u1", "target_industry": "装修"},
            "idempotency_key": "e2e_blogger_001",
            "project_id": "P_e2e_blogger",
        }
        r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
        assert r.status_code == 200
        run_id = r.json()["run_id"]

        # 3. 同 key 重试 → 同 run_id
        r2 = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
        assert r2.json()["run_id"] == run_id
        assert r2.json().get("idempotent_hit") is True

        # 4. export (未完成, ready=False)
        r3 = client.get(f"/v4/workpaths/runs/{run_id}/export")
        assert r3.json()["ready"] is False


class TestPathE2E_VideoTranscribe:
    def test_video_path_lifecycle(self):
        r = client.post("/v4/workpaths/resolve", json={
            "utterance": "提取视频口播",
            "input_refs": [
                {"role": "video_source", "value": "asset_v"},
            ],
        })
        assert r.json()["matched_path_id"] == "WP-VIDEO-TRANSCRIBE"

        body = {
            "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1,
            "input_bindings": {"video_source": "asset_v_test"},
            "idempotency_key": "e2e_video_001",
        }
        r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
        assert r.status_code == 200
        assert r.json()["run_id"]


class TestPathE2E_ArticleRewrite:
    def test_article_path_lifecycle(self):
        r = client.post("/v4/workpaths/resolve", json={
            "utterance": "改写图文",
            "input_refs": [{"role": "article_url", "value": "asset_a"}],
        })
        assert r.json()["matched_path_id"] == "WP-ARTICLE-REWRITE"

        body = {
            "path_id": "WP-ARTICLE-REWRITE", "revision": 1,
            "input_bindings": {"article_url": "asset_a_test"},
            "idempotency_key": "e2e_article_001",
        }
        r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
        assert r.status_code == 200
        assert r.json()["run_id"]


class TestPathE2E_RenovationFull:
    def test_renovation_path_with_budget(self):
        r = client.post("/v4/workpaths/resolve", json={
            "utterance": "装修效果图",
            "input_refs": [
                {"role": "floorplan_image", "value": "asset_fp"},
                {"role": "style_reference", "value": "asset_st"},
            ],
        })
        assert r.json()["matched_path_id"] == "WP-RENOVATION-FULL"

        body = {
            "path_id": "WP-RENOVATION-FULL", "revision": 1,
            "input_bindings": {
                "floorplan_image": "asset_fp",
                "style_reference": "asset_st",
                "furniture_refs": ["asset_f1"],
            },
            "budget_cap_cents": 100000,
            "idempotency_key": "e2e_reno_001",
        }
        r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
        assert r.status_code == 200
        run_id = r.json()["run_id"]

        # Bind 3 assets
        for alias, asset in [("图1", "asset_fp"), ("图2", "asset_st"), ("图6", "asset_sofa")]:
            rb = client.post("/v4/assets/bind?tenant_id=t1", json={
                "tenant_id": "t1",
                "project_id": "P_e2e_reno",
                "conversation_id": "C_e2e_reno",
                "alias": alias,
                "role": {"图1": "floorplan", "图2": "style", "图6": "sofa"}[alias],
                "asset_id": asset, "version_id": "v1", "message_id": "msg_1",
            })
            assert rb.status_code == 200


class TestPathE2E_GrowthVideo:
    def test_growth_video_path(self):
        r = client.post("/v4/workpaths/resolve", json={
            "utterance": "生长视频",
            "input_refs": [
                {"role": "first_frame", "value": "asset_f"},
                {"role": "last_frame", "value": "asset_l"},
            ],
        })
        assert r.json()["matched_path_id"] == "WP-GROWTH-VIDEO"

        body = {
            "path_id": "WP-GROWTH-VIDEO", "revision": 1,
            "input_bindings": {
                "first_frame": "asset_f", "last_frame": "asset_l",
                "target_duration": 15.0,
            },
            "budget_cap_cents": 50000,
            "idempotency_key": "e2e_growth_001",
        }
        r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
        assert r.status_code == 200


class TestPathE2E_ProductMarketing:
    def test_product_marketing_path(self):
        r = client.post("/v4/workpaths/resolve", json={
            "utterance": "商品营销全套",
            "input_refs": [
                {"role": "product_image", "value": "asset_p"},
                {"role": "brand_spec", "value": "风格:简约"},
            ],
        })
        assert r.json()["matched_path_id"] == "WP-PRODUCT-MARKETING"

        body = {
            "path_id": "WP-PRODUCT-MARKETING", "revision": 1,
            "input_bindings": {
                "product_image": "asset_p",
                "brand_spec": "风格:简约",
                "channels": ["douyin", "xiaohongshu"],
            },
            "budget_cap_cents": 30000,
            "idempotency_key": "e2e_pm_001",
        }
        r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
        assert r.status_code == 200


# ============================================================
# Operations Registry + 真实 dispatch(adapter 真跑)
# ============================================================

class TestRegistryRealDispatch:
    """registry.dispatch() 真调用 adapter,不走 orchestrator"""

    def test_dispatch_url_normalize(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("url.normalize", {"url": "https://example.com/path?q=1"})
        assert out["host"] == "example.com"

    def test_dispatch_dedupe(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        items = [{"id": 1}, {"id": 2}, {"id": 1}, {"id": 3}]
        out = r.dispatch("content.dedupe", {"items": items})
        assert out["deduped"] == 3

    def test_dispatch_export_zip(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("export.zip", {"topic_cards": 10, "scripts": 5})
        assert out["mock"] is True
        assert "topic_cards" in out["files"]

    def test_dispatch_unknown_returns_stub(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("unknown.op.id", {})
        assert out["status"] == "stub"

    def test_dispatch_with_llm_provider_runs_adapter(self):
        from workflows.v4.registry import OperationRegistry
        from adapters.llm import MockLLMProvider
        r = OperationRegistry()
        out = r.dispatch(
            "content.structure.analyze",
            {"segments": [], "transcript": "你知道吗?这是钩子关注我"},
            llm_provider=MockLLMProvider(),
        )
        assert out["structure_template"] == "llm-derived"
        assert out["mock"] is True  # mock provider marks mock=True

    def test_dispatch_ocr_only(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("ocr.recognize", {"image_path": "/tmp/invoice_001.pdf"})
        assert "full_text" in out

    def test_dispatch_search_only(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("search.authors", {"keywords": ["装修"], "platform": "douyin"})
        assert out["total"] > 0

    def test_dispatch_metrics_only(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("metrics.fetch", {"author_id": "mock_001"})
        assert out["total_videos"] > 0

    def test_dispatch_tts_only(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("doubao.tts", {"text": "你好世界"})
        assert out["mock"] is True
        assert out["duration_sec"] > 0

    def test_dispatch_meeting_only(self):
        from workflows.v4.registry import OperationRegistry
        r = OperationRegistry()
        out = r.dispatch("meeting.process", {"audio_path": "/tmp/mtg.mp3"})
        assert "summary" in out
        assert len(out["action_items"]) > 0