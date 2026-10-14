"""P0 security regressions for CloudTech's EXISTING V4 API.

These tests do not call remote providers, pay money, or modify production data.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.v4 import router
from workflows.v4 import V4Orchestrator, BudgetGate, CostClass, BudgetError

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def _run(tenant="tenant_a", key=None, video="a"):
    body = {"path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1,
            "input_bindings": {"video_source": video}}
    if key:
        body["idempotency_key"] = key
    return client.post(f"/v4/workpaths/runs?tenant_id={tenant}", json=body)

def test_cross_tenant_read_and_export_denied():
    run = _run()
    assert run.status_code == 200, run.text
    ident = run.json()["run_id"]
    for url in (f"/v4/workpaths/runs/{ident}",
                f"/v4/workpaths/runs/{ident}/export"):
        assert client.get(url + "?tenant_id=tenant_b").status_code == 404
        assert client.get(url).status_code == 422
        assert client.get(url + "?tenant_id=tenant_a").status_code == 200

def test_cross_tenant_approve_and_resume_denied():
    run = _run()
    assert run.status_code == 200
    ident = run.json()["run_id"]
    approve = client.post(f"/v4/workpaths/runs/{ident}/approve?tenant_id=tenant_b",
                          json={"checkpoint_id": "x"})
    resume = client.post(f"/v4/workpaths/runs/{ident}/resume?tenant_id=tenant_b",
                         json={"failed_nodes_only": True})
    assert approve.status_code == 404
    assert resume.status_code == 404
    honest = client.post(f"/v4/workpaths/runs/{ident}/resume?tenant_id=tenant_a",
                         json={"failed_nodes_only": True})
    assert honest.status_code == 501  # No worker requeue yet

def test_alias_bind_cannot_choose_other_tenant():
    body = {"tenant_id": "tenant_a", "conversation_id": "c",
            "alias": "img", "role": "image", "asset_id": "x", "version_id": "v1"}
    assert client.post("/v4/assets/bind?tenant_id=tenant_b", json=body).status_code == 403
    assert client.post("/v4/assets/bind", json=body).status_code == 422
    assert client.post("/v4/assets/bind?tenant_id=tenant_a", json=body).status_code == 200

def test_scoped_idempotency_and_payload_conflicts():
    a = _run("tenant_a", "nonce-one", "a")
    again = _run("tenant_a", "nonce-one", "a")
    b = _run("tenant_b", "nonce-one", "a")
    conflict = _run("tenant_a", "nonce-one", "different")
    assert a.status_code == again.status_code == b.status_code == 200
    assert a.json()["run_id"] == again.json()["run_id"]
    assert a.json()["run_id"] != b.json()["run_id"]
    assert conflict.status_code == 409

def test_multiple_reference_inputs_not_collapsed():
    r = client.post("/v4/workpaths/resolve", json={
        "utterance": "生成全屋装修效果图",
        "input_refs": [
            {"role": "floorplan_image", "value": "f1"},
            {"role": "style_reference", "value": "s1"},
            {"role": "furniture_refs", "value": "chair"},
            {"role": "furniture_refs", "value": "table"}]})
    assert r.status_code == 200, r.text
    assert r.json()["matched_path_id"] == "WP-RENOVATION-FULL"

def test_missing_or_excess_assets_rejected_at_create():
    for furniture in (["x"] * 11, []):
        bindings = {"floorplan_image": "f1", "style_reference": "s1",
                    "furniture_refs": furniture}
        r = client.post("/v4/workpaths/runs?tenant_id=tenant_a",
                        json={"path_id": "WP-RENOVATION-FULL", "input_bindings": bindings})
        if len(furniture) > 10:
            assert r.status_code == 422, r.text
        else:
            assert r.status_code == 200, r.text
    empty = client.post("/v4/workpaths/runs?tenant_id=tenant_a",
        json={"path_id": "WP-RENOVATION-FULL", "input_bindings": {}})
    assert empty.status_code == 422

def test_pending_budget_is_included_in_cap():
    gate = BudgetGate()
    reserved = gate.reserve("tenant_a", "r1", None, CostClass.METERED_MEDIA, 90, 100)
    try:
        gate.reserve("tenant_a", "r2", None, CostClass.METERED_MEDIA, 20, 100)
        assert False, "must enforce aggregate pending reservations"
    except BudgetError:
        pass
    gate.release(reserved.reservation_id)
    assert gate.reserve("tenant_a", "r3", None, CostClass.METERED_MEDIA, 20, 100)

def test_settle_must_not_silently_clamp_cost():
    gate = BudgetGate()
    reserved = gate.reserve("tenant_a", "r1", None, CostClass.METERED_MEDIA, 10, 100)
    try:
        gate.settle(reserved.reservation_id, 100)
        assert False, "must not hide upstream provider cost"
    except BudgetError:
        pass

def test_production_without_signing_secret_fails_closed(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    r = _run("tenant_prod")
    assert r.status_code == 503

def test_short_jwt_secret_denied_outside_explicit_dev(monkeypatch):
    """A valid HMAC is not sufficient when the signing key is trivially short."""
    from api.v4.auth import mint_jwt
    monkeypatch.setenv("V4_JWT_SECRET", "guessable")
    monkeypatch.delenv("CLOUDTECH_SAAS_JWT_SECRET", raising=False)
    monkeypatch.setenv("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", "1")
    token = mint_jwt("tenant_secure", user_id="user_1")
    for deployment in ("production", "staging", ""):
        monkeypatch.setenv("CLOUDTECH_ENV", deployment)
        response = client.get(
            "/v4/workpaths/runs?tenant_id=tenant_secure",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503, (deployment, response.text)
        assert "AUTH-010" in response.text


def test_short_secret_opt_in_is_test_only(monkeypatch):
    """Historical isolated V4 tests may explicitly opt in; no prod bypass."""
    from api.v4.auth import mint_jwt
    monkeypatch.setenv("CLOUDTECH_ENV", "test")
    monkeypatch.setenv("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", "1")
    monkeypatch.setenv("V4_JWT_SECRET", "guessable")
    monkeypatch.delenv("CLOUDTECH_SAAS_JWT_SECRET", raising=False)
    token = mint_jwt("tenant_test", user_id="user_1")
    response = client.get(
        "/v4/workpaths/runs?tenant_id=tenant_test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text


def test_unspecified_runtime_auth_is_fail_closed(monkeypatch):
    monkeypatch.delenv("CLOUDTECH_ENV", raising=False)
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", raising=False)
    r = _run("tenant_unconfigured")
    assert r.status_code == 503

def test_dev_mode_requires_explicit_insecure_opt_in(monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "development")
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    monkeypatch.delenv("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", raising=False)
    assert _run("tenant_dev").status_code == 503

def test_run_listing_returns_only_owned_records_without_fake_worker():
    own = _run("tenant_list_a", video="my-source")
    other = _run("tenant_list_b", video="other-source")
    assert own.status_code == other.status_code == 200
    r = client.get("/v4/workpaths/runs?tenant_id=tenant_list_a")
    assert r.status_code == 200, r.text
    body = r.json()
    own_id = own.json()["run_id"]
    other_id = other.json()["run_id"]
    assert own_id in [item["run_id"] for item in body["items"]]
    assert other_id not in [item["run_id"] for item in body["items"]]
    assert all(item["tenant_id"] == "tenant_list_a" for item in body["items"])
    assert body["worker_connected"] is False
    assert body["production_ready"] is False
    assert body["storage"] == "VOLATILE_MEMORY"

def test_run_listing_cannot_be_read_without_auth_context():
    assert client.get("/v4/workpaths/runs").status_code == 422

def test_run_status_cannot_pretend_worker_started():
    r = _run("tenant_state", video="video-alpha")
    assert r.status_code == 200
    assert r.json()["execution_started"] is False
    assert r.json()["worker_connected"] is False
