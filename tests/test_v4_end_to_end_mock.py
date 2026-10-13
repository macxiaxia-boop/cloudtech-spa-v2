"""V4 — 端到端 mock 集成测试
完整链路: 用户输入 → resolve → create_run → alias bind → resolve → new_version
全部 in-process mock, 0 真实调用
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api.v4 import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_e2e_blogger_workflow():
    """完整博主研究工作流 mock"""
    # 1. 用户输入 utterance
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "研究博主 https://example.com/u1 的最近 30 条视频, 给装修公司写 10 条原创",
        "project_id": "P_decoration_001",
        "input_refs": [
            {"role": "homepage_url", "value": "https://example.com/u1"},
            {"role": "target_industry", "value": "decoration"},
            {"role": "audience", "value": "准备装修的小家庭"}
        ]
    })
    assert r.status_code == 200
    resolved = r.json()
    assert resolved["matched_path_id"] == "WP-BLOGGER-RESEARCH"
    assert resolved["missing_roles"] == []
    print(f"[OK] e2e_blogger step 1: resolve → {resolved['matched_path_id']}")

    # 2. 创建 run (幂等)
    body = {
        "path_id": "WP-BLOGGER-RESEARCH",
        "revision": 1,
        "input_bindings": {"homepage_url": "https://example.com/u1", "target_industry": "decoration"},
        "idempotency_key": "blogger_e2e_001",
        "project_id": "P_decoration_001",
        "conversation_id": "C_blogger_001",
        "budget_cap_cents": 5000
    }
    r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    print(f"[OK] e2e_blogger step 2: create_run → {run_id}")

    # 3. 上传图 1 (户型), bind alias
    r = client.post("/v4/assets/bind", json={
        "tenant_id": "t1",
        "project_id": "P_decoration_001",
        "conversation_id": "C_blogger_001",
        "alias": "图1",
        "role": "floorplan",
        "asset_id": "asset_floorplan_v1",
        "version_id": "v1",
        "message_id": "msg_1"
    })
    assert r.status_code == 200
    print("[OK] e2e_blogger step 3: bind_alias 图1")

    # 4. 解析 alias
    r = client.post("/v4/assets/resolve-alias?tenant_id=t1", json={
        "conversation_id": "C_blogger_001",
        "alias": "图1"
    })
    assert r.json()["asset_id"] == "asset_floorplan_v1"
    print("[OK] e2e_blogger step 4: resolve_alias 图1 → asset_floorplan_v1")

    # 5. 上传新版本 (用户修改户型)
    r = client.post("/v4/assets/asset_floorplan_v1/versions", json={
        "tenant_id": "t1",
        "project_id": "P_decoration_001",
        "conversation_id": "C_blogger_001",
        "alias": "图1",
        "new_asset_id": "asset_floorplan_v1",
        "new_version_id": "v2",
        "parent_version_id": "v1",
        "edit_spec": {"annotation": "改动了厨房"},
        "message_id": "msg_2"
    })
    assert r.status_code == 200
    print("[OK] e2e_blogger step 5: new_version v2")

    # 6. 同 key 第二次创建应返回同 run_id (幂等)
    r2 = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    assert r2.json()["run_id"] == run_id
    assert r2.json().get("idempotent_hit") is True
    print("[OK] e2e_blogger step 6: idempotent_hit")

    # 7. export (此时 run 未 COMPLETED, 应 ready=False)
    r = client.get(f"/v4/workpaths/runs/{run_id}/export")
    data = r.json()
    assert data["ready"] is False
    print(f"[OK] e2e_blogger step 7: export not ready → status={data['status']}")


def test_e2e_renovation_full_workflow():
    """装修多图 → 全屋效果图 → 局部替换"""
    # 1. Resolve
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "给我家做装修效果图, 图 6 沙发换掉",
        "input_refs": [
            {"role": "floorplan_image", "value": "asset_fp"},
            {"role": "style_reference", "value": "asset_style"},
            {"role": "furniture_refs", "value": "asset_f1"},
        ]
    })
    assert r.json()["matched_path_id"] == "WP-RENOVATION-FULL"
    print(f"[OK] e2e_renovation step 1: resolve")

    # 2. Create run with budget cap
    body = {
        "path_id": "WP-RENOVATION-FULL",
        "revision": 1,
        "input_bindings": {
            "floorplan_image": "asset_fp",
            "style_reference": "asset_style",
            "furniture_refs": ["asset_f1", "asset_f2"]
        },
        "budget_cap_cents": 10000,
        "idempotency_key": "renovation_e2e_001",
        "conversation_id": "C_renovation_001"
    }
    r = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    print(f"[OK] e2e_renovation step 2: create_run → {run_id}")

    # 3. Bind 图 1 (floorplan), 图 2 (style), 图 6 (sofa)
    for alias, role, asset in [
        ("图1", "floorplan", "asset_fp"),
        ("图2", "style", "asset_style"),
        ("图6", "sofa", "asset_sofa"),
    ]:
        r = client.post("/v4/assets/bind", json={
            "tenant_id": "t1", "conversation_id": "C_renovation_001",
            "alias": alias, "role": role, "asset_id": asset, "version_id": "v1", "message_id": "msg_1"
        })
        assert r.status_code == 200
    print("[OK] e2e_renovation step 3: bind 图1/图2/图6")

    # 4. 用户说"图 6 沙发换为新上传图" — 创建新版本
    r = client.post("/v4/assets/asset_sofa/versions", json={
        "tenant_id": "t1",
        "conversation_id": "C_renovation_001",
        "alias": "图6",
        "new_asset_id": "asset_sofa_new",
        "new_version_id": "v2",
        "parent_version_id": "v1",
        "edit_spec": {"inpaint_mask": "mask_url_x", "source_refs": ["asset_sofa_new"]},
        "message_id": "msg_2"
    })
    assert r.status_code == 200
    new_ver = r.json()["version_id"]
    assert new_ver == "v2"
    print(f"[OK] e2e_renovation step 4: 图6 沙发换版 → {new_ver}")

    # 5. 历史确定: 用 at_message_id=msg_1 应取 v1, 当前应取 v2
    r_now = client.post("/v4/assets/resolve-alias?tenant_id=t1", json={
        "conversation_id": "C_renovation_001", "alias": "图6"
    })
    assert r_now.json()["version_id"] == "v2"
    r_hist = client.post("/v4/assets/resolve-alias?tenant_id=t1", json={
        "conversation_id": "C_renovation_001", "alias": "图6", "at_message_id": "msg_1"
    })
    assert r_hist.json()["version_id"] == "v1"
    print("[OK] e2e_renovation step 5: 当前 v2, 历史 msg_1→v1")


def test_e2e_idempotency_under_failure():
    """失败重试不双扣费"""
    body = {
        "path_id": "WP-GROWTH-VIDEO",
        "revision": 1,
        "input_bindings": {"first_frame": "asset_f", "last_frame": "asset_l", "duration_sec": 15},
        "idempotency_key": "growth_video_e2e_001"
    }
    r1 = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    r2 = client.post("/v4/workpaths/runs?tenant_id=t1", json=body)
    assert r1.json()["run_id"] == r2.json()["run_id"]
    # 模拟失败: 调用 resume (no_repeat_billing=true)
    run_id = r1.json()["run_id"]
    r = client.post(f"/v4/workpaths/runs/{run_id}/resume", json={"failed_nodes_only": True})
    assert r.json()["no_repeat_billing"] is True
    print(f"[OK] e2e_idempotency_under_failure → {run_id} (no double billing)")


if __name__ == "__main__":
    test_e2e_blogger_workflow()
    test_e2e_renovation_full_workflow()
    test_e2e_idempotency_under_failure()
    print("\n=== ALL E2E MOCK TESTS PASSED ===")
