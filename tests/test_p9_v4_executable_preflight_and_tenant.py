"""P9: verified behavior for six existing V4 paths and tenant isolation.

No provider calls or production account operations.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v4 import router
from workflows.v4.capability_preflight import inspect_all_paths, inspect_path
from workflows.v4.orchestrator import RunStatusError, V4Orchestrator

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _body(key: str, *, topic: str = "装修"):
    return {
        "path_id": "WP-VIDEO-TRANSCRIBE",
        "revision": 1,
        "input_bindings": {"video_source": "test-owned-video", "topic": topic},
        "idempotency_key": key,
    }


def test_six_real_paths_have_readonly_source_status_and_no_fake_success():
    all_paths = inspect_all_paths()
    assert all_paths["total_paths"] == 6
    assert all_paths["total_nodes"] >= 45
    assert all_paths["execution_ready_paths"] == 0
    for path in all_paths["paths"]:
        assert path["nodes"]
        assert path["checks"]["graph_valid"] is True
        assert path["total_nodes"] == len(path["nodes"])
        assert path["checks"]["mock_only"] + path["checks"]["adapter_unmapped"] > 0


def test_homepage_path_has_real_local_ops_but_mock_external_ones():
    path = inspect_path("WP-BLOGGER-RESEARCH")
    lookup = {n["operation"]: n for n in path["nodes"]}
    assert lookup["url.normalize"]["capability"] == "LOCAL_IMPLEMENTED"
    assert lookup["platform.homepage_parse"]["capability"] == "MOCK_ONLY"
    assert lookup["transcript.extract"]["needs_provider_proof"] is True
    assert path["execution_ready"] is False


def test_preflight_http_returns_proof_not_optimistic_ready():
    r = client.get("/v4/workpaths/WP-BLOGGER-RESEARCH/preflight")
    assert r.status_code == 200
    assert r.json()["execution_ready"] is False
    assert r.json()["level"] == "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION"
    idx = client.get("/v4/workpaths/capabilities")
    assert idx.status_code == 200
    assert idx.json()["total_paths"] == 6
    bad = client.get("/v4/workpaths/WP-NONEXISTENT/preflight")
    assert bad.status_code == 404


def test_two_tenants_same_key_get_different_run_ids_and_no_cross_tenant_read(monkeypatch):
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    x = client.post("/v4/workpaths/runs?tenant_id=p9_tenant_A", json=_body("p9-shared-key"))
    y = client.post("/v4/workpaths/runs?tenant_id=p9_tenant_B", json=_body("p9-shared-key"))
    assert x.status_code == y.status_code == 200
    assert x.json()["run_id"] != y.json()["run_id"]
    aid = x.json()["run_id"]
    assert client.get(f"/v4/workpaths/runs/{aid}?tenant_id=p9_tenant_A").status_code == 200
    assert client.get(f"/v4/workpaths/runs/{aid}?tenant_id=p9_tenant_B").status_code == 404
    assert client.get(f"/v4/workpaths/runs/{aid}").status_code == 422


def test_same_tenant_key_may_not_be_reused_for_different_payload(monkeypatch):
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    url = "/v4/workpaths/runs?tenant_id=p9_tenant_C"
    first = client.post(url, json=_body("p9-conflict", topic="A"))
    second = client.post(url, json=_body("p9-conflict", topic="B"))
    assert first.status_code == 200
    assert second.status_code == 409
    retried = client.post(url, json=_body("p9-conflict", topic="A"))
    assert retried.status_code == 200
    assert retried.json()["run_id"] == first.json()["run_id"]
    assert retried.json()["idempotent_hit"] is True
    assert retried.json()["execution_ready"] is False


def test_cross_tenant_resume_approve_and_export_refused(monkeypatch):
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    response = client.post(
        "/v4/workpaths/runs?tenant_id=p9_owner",
        json=_body("p9-ownership"),
    )
    assert response.status_code == 200
    rid = response.json()["run_id"]
    assert client.post(
        f"/v4/workpaths/runs/{rid}/approve?tenant_id=p9_attacker",
        json={"checkpoint_id": "fake"},
    ).status_code == 404
    assert client.post(
        f"/v4/workpaths/runs/{rid}/resume?tenant_id=p9_attacker",
        json={"failed_nodes_only": True},
    ).status_code == 404
    assert client.get(
        f"/v4/workpaths/runs/{rid}/export?tenant_id=p9_attacker"
    ).status_code == 404

    # Owner may view resume preview, but it does not pretend execution.
    allowed = client.post(
        f"/v4/workpaths/runs/{rid}/resume?tenant_id=p9_owner",
        json={"failed_nodes_only": True},
    )
    assert allowed.status_code == 200
    assert allowed.json()["scheduled"] is False
    assert allowed.json()["no_repeat_billing"] is False


def test_same_key_concurrent_submit_creates_single_run():
    o = V4Orchestrator()
    def submit(_):
        return o.create_run(
            path_id="WP-BLOGGER-RESEARCH",
            path_revision=1,
            tenant_id="atomic-tenant",
            input_bindings={"homepage_url": "https://example.com/user"},
            idempotency_key="same-key",
        ).run_id

    with ThreadPoolExecutor(max_workers=8) as pool:
        runs = list(pool.map(submit, range(24)))
    assert len(set(runs)) == 1
    with pytest.raises(RunStatusError, match="different run parameters"):
        o.create_run(
            path_id="WP-BLOGGER-RESEARCH",
            path_revision=1,
            tenant_id="atomic-tenant",
            input_bindings={"homepage_url": "https://example.com/DIFFERENT"},
            idempotency_key="same-key",
        )


def test_production_requires_real_secret_and_authenticated_tenant(monkeypatch):
    from api.v4.auth import mint_jwt

    monkeypatch.setenv("V4_ENV", "production")
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    body = _body("production-auth-test")
    url = "/v4/workpaths/runs?tenant_id=prod-A"
    missing = client.post(url, json=body)
    assert missing.status_code == 401
    monkeypatch.setenv("V4_JWT_SECRET", "short-secret")
    short = client.post(url, json=body)
    assert short.status_code == 401

    monkeypatch.setenv("V4_JWT_SECRET", "p9-test-only-secret-with-32-plus-bytes-123456")
    absent_token = client.post(url, json=body)
    assert absent_token.status_code == 401
    real_token = mint_jwt("prod-A", user_id="tester")
    authorized = client.post(
        url, json=body, headers={"Authorization": f"Bearer {real_token}"},
    )
    assert authorized.status_code == 200
    rid = authorized.json()["run_id"]
    forged_tenant = client.get(
        f"/v4/workpaths/runs/{rid}?tenant_id=prod-B",
        headers={"Authorization": f"Bearer {real_token}"},
    )
    assert forged_tenant.status_code == 401
    own = client.get(
        f"/v4/workpaths/runs/{rid}?tenant_id=prod-A",
        headers={"Authorization": f"Bearer {real_token}"},
    )
    assert own.status_code == 200
