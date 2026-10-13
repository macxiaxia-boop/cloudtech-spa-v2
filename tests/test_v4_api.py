"""V4 API integration smoke — 不发真实请求"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.v4 import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_health():
    r = client.get("/v4/health")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["paths_registered"] == 6
    print(f"[OK] health → {data}")


def test_resolve_blogger():
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "研究这个博主最近的视频",
        "input_refs": [
            {"role": "homepage_url", "value": "https://example.com/u1"},
            {"role": "target_industry", "value": "decoration"},
        ]
    })
    assert r.status_code == 200
    data = r.json()
    assert data["matched_path_id"] == "WP-BLOGGER-RESEARCH"
    print(f"[OK] resolve_blogger → matched={data['matched_path_id']}, missing={data['missing_roles']}")


def test_resolve_video():
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "提取这个视频的逐字稿",
        "input_refs": [{"role": "video_source", "value": "https://example.com/v1"}]
    })
    data = r.json()
    assert data["matched_path_id"] == "WP-VIDEO-TRANSCRIBE"
    print(f"[OK] resolve_video → {data['matched_path_id']}")


def test_resolve_renovation():
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "给我家做装修效果图",
        "input_refs": [
            {"role": "floorplan_image", "value": "asset_x"},
            {"role": "style_reference", "value": "asset_y"},
        ]
    })
    data = r.json()
    assert data["matched_path_id"] == "WP-RENOVATION-FULL"
    print(f"[OK] resolve_renovation → {data['matched_path_id']}")


def test_create_run_with_idempotency():
    body = {
        "path_id": "WP-VIDEO-TRANSCRIBE",
        "revision": 1,
        "input_bindings": {"video_source": "asset_v1"},
        "idempotency_key": "idem_test_001"
    }
    r1 = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    assert r1.status_code == 200
    run_id_1 = r1.json()["run_id"]
    # 同 key 第二次应返回同一 run_id (idempotency_hit)
    r2 = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    assert r2.status_code == 200
    run_id_2 = r2.json()["run_id"]
    assert run_id_1 == run_id_2, "幂等键必须返回同一 run_id"
    print(f"[OK] create_run_idempotent → {run_id_1}")


def test_create_run_unknown_path():
    r = client.post("/v4/workpaths/runs?tenant_id=t1", json={
        "path_id": "WP-NONEXISTENT",
        "revision": 1,
        "input_bindings": {}
    })
    assert r.status_code == 404
    print(f"[OK] unknown_path_404")


def test_create_run_revision_mismatch():
    r = client.post("/v4/workpaths/runs?tenant_id=t1", json={
        "path_id": "WP-VIDEO-TRANSCRIBE",
        "revision": 99,  # 当前 revision=1
        "input_bindings": {}
    })
    assert r.status_code == 409
    print(f"[OK] revision_mismatch_409")


def test_alias_bind_and_resolve():
    r = client.post("/v4/assets/bind", json={
        "tenant_id": "t1",
        "conversation_id": "c1",
        "alias": "图1",
        "role": "floorplan",
        "asset_id": "asset_a",
        "version_id": "v1",
        "message_id": "msg_1"
    })
    assert r.status_code == 200
    binding_id = r.json()["binding_id"]
    # 解析
    r2 = client.post("/v4/assets/resolve-alias?tenant_id=t1", json={
        "conversation_id": "c1",
        "alias": "图1"
    })
    assert r2.status_code == 200
    data = r2.json()
    assert data["asset_id"] == "asset_a"
    assert data["version_id"] == "v1"
    print(f"[OK] alias bind+resolve → {data['asset_id']}/{data['version_id']}")


def test_alias_resolve_404():
    r = client.post("/v4/assets/resolve-alias?tenant_id=t1", json={
        "conversation_id": "c1",
        "alias": "图99"
    })
    assert r.status_code == 404
    print(f"[OK] alias_resolve_404")


def test_new_version_sofa_replace():
    """图 6 沙发替换 — parent_version_id 必须匹配"""
    client.post("/v4/assets/bind", json={
        "tenant_id": "t1",
        "conversation_id": "c2",
        "alias": "图6",
        "role": "sofa",
        "asset_id": "asset_sofa",
        "version_id": "v1",
        "message_id": "msg_1"
    })
    r = client.post("/v4/assets/asset_sofa/versions", json={
        "tenant_id": "t1",
        "conversation_id": "c2",
        "alias": "图6",
        "new_asset_id": "asset_sofa",
        "new_version_id": "v2",
        "parent_version_id": "v1",
        "edit_spec": {"inpaint_mask": "mask_url_x"}
    })
    assert r.status_code == 200
    data = r.json()
    assert data["version_id"] == "v2"
    print(f"[OK] new_version_sofa_replace → {data['version_id']}")


def test_new_version_wrong_parent():
    client.post("/v4/assets/bind", json={
        "tenant_id": "t1",
        "conversation_id": "c3",
        "alias": "图6",
        "role": "sofa",
        "asset_id": "asset_sofa",
        "version_id": "v1",
        "message_id": "msg_1"
    })
    r = client.post("/v4/assets/asset_sofa/versions", json={
        "tenant_id": "t1",
        "conversation_id": "c3",
        "alias": "图6",
        "new_asset_id": "asset_sofa",
        "new_version_id": "v2",
        "parent_version_id": "v99"  # wrong
    })
    assert r.status_code == 400
    print(f"[OK] new_version_wrong_parent_400")


def test_resume_run():
    """断点续跑 — 不重收费"""
    body = {
        "path_id": "WP-ARTICLE-REWRITE",
        "revision": 1,
        "input_bindings": {"article_url": "https://example.com/a1"}
    }
    r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    run_id = r.json()["run_id"]
    r2 = client.post(f"/v4/workpaths/runs/{run_id}/resume", json={"failed_nodes_only": True})
    assert r2.status_code == 200
    data = r2.json()
    assert data["no_repeat_billing"] is True
    print(f"[OK] resume_run → no_repeat_billing={data['no_repeat_billing']}")


def test_export_run_not_ready():
    r = client.post("/v4/workpaths/runs?tenant_id=t1", json={
        "path_id": "WP-ARTICLE-REWRITE", "revision": 1, "input_bindings": {}
    })
    run_id = r.json()["run_id"]
    r2 = client.get(f"/v4/workpaths/runs/{run_id}/export")
    data = r2.json()
    assert data["ready"] is False
    print(f"[OK] export_run_not_ready → status={data['status']}")


if __name__ == "__main__":
    test_health()
    test_resolve_blogger()
    test_resolve_video()
    test_resolve_renovation()
    test_create_run_with_idempotency()
    test_create_run_unknown_path()
    test_create_run_revision_mismatch()
    test_alias_bind_and_resolve()
    test_alias_resolve_404()
    test_new_version_sofa_replace()
    test_new_version_wrong_parent()
    test_resume_run()
    test_export_run_not_ready()
    print("\n=== ALL API INTEGRATION TESTS PASSED ===")
