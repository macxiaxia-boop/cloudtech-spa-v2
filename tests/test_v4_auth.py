"""V4 — Auth middleware + audit evidence 测试"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends
from api.v4 import router
from api.v4.auth import auth_required, AuthContext, mint_jwt
from workflows.v4.audit_evidence import AuditEvidenceWriter, on_node_input, on_node_output


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_dev_mode_tenant_only():
    """开发模式 (无 V4_JWT_SECRET): tenant_id 即可"""
    if "V4_JWT_SECRET" in os.environ:
        del os.environ["V4_JWT_SECRET"]
    r = client.post("/v4/workpaths/runs?tenant_id=t_test_001", json={
        "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1, "input_bindings": {"video_source": "asset_demo"}
    })
    assert r.status_code == 200
    print("[OK] dev_mode tenant only")


def test_dev_mode_tenant_id_required():
    if "V4_JWT_SECRET" in os.environ:
        del os.environ["V4_JWT_SECRET"]
    r = client.post("/v4/workpaths/runs", json={
        "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1, "input_bindings": {"video_source": "asset_demo"}
    })
    assert r.status_code == 422  # FastAPI validation
    print("[OK] dev_mode missing tenant_id → 422")


def test_dev_mode_tenant_id_too_long():
    if "V4_JWT_SECRET" in os.environ:
        del os.environ["V4_JWT_SECRET"]
    r = client.post(f"/v4/workpaths/runs?tenant_id={'x'*100}", json={
        "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1, "input_bindings": {"video_source": "asset_demo"}
    })
    assert r.status_code == 401
    print("[OK] tenant_id_too_long → 401")


def test_dev_mode_invalid_tenant_chars():
    if "V4_JWT_SECRET" in os.environ:
        del os.environ["V4_JWT_SECRET"]
    r = client.post("/v4/workpaths/runs?tenant_id=t!@#", json={
        "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1, "input_bindings": {"video_source": "asset_demo"}
    })
    assert r.status_code == 401
    print("[OK] invalid_tenant_chars → 401")


def test_prod_mode_missing_jwt():
    """生产模式 (V4_JWT_SECRET 设): 必须 JWT"""
    os.environ["V4_JWT_SECRET"] = "test_secret_xxx"
    r = client.post("/v4/workpaths/runs?tenant_id=t_test_001", json={
        "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1, "input_bindings": {"video_source": "asset_demo"}
    })
    assert r.status_code == 401
    print(f"[OK] prod_mode missing JWT → 401")
    del os.environ["V4_JWT_SECRET"]


def test_prod_mode_valid_jwt():
    """生产模式 + 合法 JWT"""
    os.environ["V4_JWT_SECRET"] = "test_secret_xxx"
    token = mint_jwt("t_test_001", user_id="u_1", permissions=["v4:run"])
    r = client.post(
        "/v4/workpaths/runs?tenant_id=t_test_001",
        json={"path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1, "input_bindings": {"video_source": "asset_demo"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    print("[OK] prod_mode valid JWT → 200")
    del os.environ["V4_JWT_SECRET"]


def test_prod_mode_jwt_wrong_tenant():
    """生产模式 + JWT tenant 与 query tenant 不匹配"""
    os.environ["V4_JWT_SECRET"] = "test_secret_xxx"
    token = mint_jwt("t_other_tenant", user_id="u_1")
    r = client.post(
        "/v4/workpaths/runs?tenant_id=t_test_001",
        json={"path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1, "input_bindings": {"video_source": "asset_demo"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401
    print("[OK] prod_mode tenant mismatch → 401")
    del os.environ["V4_JWT_SECRET"]


# === Audit Evidence Writer ===

def test_audit_evidence_write():
    AuditEvidenceWriter.instance().reset()
    rec = AuditEvidenceWriter.instance().write(
        run_id="r1", node_id="n1",
        evidence_kind="input", payload={"x": 1},
    )
    assert rec.id.startswith("ev_")
    assert len(rec.evidence_hash) == 64
    print(f"[OK] audit write → hash={rec.evidence_hash[:8]}")


def test_audit_evidence_invalid_kind():
    try:
        AuditEvidenceWriter.instance().write("r1", "n1", "BAD_KIND", {})
        assert False
    except ValueError as e:
        print(f"[OK] invalid_kind rejected → {e}")


def test_audit_evidence_query_by_run():
    AuditEvidenceWriter.instance().reset()
    AuditEvidenceWriter.instance().write("r1", "n1", "input", {"a": 1})
    AuditEvidenceWriter.instance().write("r1", "n1", "output", {"b": 2})
    AuditEvidenceWriter.instance().write("r2", "n1", "input", {"c": 3})
    r1_records = AuditEvidenceWriter.instance().list_for_run("r1")
    assert len(r1_records) == 2
    print(f"[OK] query by run → r1 has {len(r1_records)} records")


def test_audit_hooks_on_node_io():
    AuditEvidenceWriter.instance().reset()
    on_node_input("r3", "n1", {"prompt": "test"})
    on_node_output("r3", "n1", {"url": "x"}, cost_cents=100, cost_class="METERED_MEDIA")
    records = AuditEvidenceWriter.instance().list_for_run("r3")
    assert len(records) == 2
    kinds = [r.evidence_kind for r in records]
    assert "input" in kinds
    assert "output" in kinds
    print(f"[OK] hooks → input/output kinds recorded")


if __name__ == "__main__":
    test_dev_mode_tenant_only()
    test_dev_mode_tenant_id_required()
    test_dev_mode_tenant_id_too_long()
    test_dev_mode_invalid_tenant_chars()
    test_prod_mode_missing_jwt()
    test_prod_mode_valid_jwt()
    test_prod_mode_jwt_wrong_tenant()
    test_audit_evidence_write()
    test_audit_evidence_invalid_kind()
    test_audit_evidence_query_by_run()
    test_audit_evidence_query_by_run()
    test_audit_hooks_on_node_io()
    print("\n=== ALL AUTH + AUDIT TESTS PASSED ===")
