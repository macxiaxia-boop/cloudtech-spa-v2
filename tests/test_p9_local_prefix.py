"""P9: actual read-only local execution for first already-implemented V4 node."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.v4 import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _create(key: str, homepage_url: str) -> str:
    result = client.post(
        "/v4/workpaths/runs?tenant_id=p9-local-owner",
        json={
            "path_id": "WP-BLOGGER-RESEARCH",
            "revision": 1,
            "input_bindings": {
                "homepage_url": homepage_url,
                "target_industry": "装修",
            },
            "idempotency_key": key,
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["execution_ready"] is False
    return result.json()["run_id"]


def test_local_prefix_runs_real_url_step_then_stops_at_mock_permission():
    rid = _create("safe-001", "https://example.com/creator?cursor=10")
    first = client.post(
        f"/v4/workpaths/runs/{rid}/execute-local?tenant_id=p9-local-owner"
    )
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["executed_nodes"] == ["url_normalize"]
    assert result["blocked_at"]["operation"] == "platform.permission_check"
    assert result["blocked_at"]["reason"] == "MOCK_ONLY"
    assert result["status"] == "PARTIAL"
    assert result["external_calls"] == 0
    assert result["charged_cents"] == 0
    assert result["execution_ready"] is False

    stored = client.get(
        f"/v4/workpaths/runs/{rid}?tenant_id=p9-local-owner"
    ).json()
    assert len(stored["nodes"]) == 1
    assert stored["nodes"][0]["status"] == "COMPLETED"
    normalized = stored["nodes"][0]["output_ref"]["local_result"]["normalized"]
    assert normalized == "https://example.com/creator?cursor=10"

    repeated = client.post(
        f"/v4/workpaths/runs/{rid}/execute-local?tenant_id=p9-local-owner"
    )
    assert repeated.status_code == 200
    assert repeated.json()["executed_nodes"] == []
    assert len(client.get(
        f"/v4/workpaths/runs/{rid}?tenant_id=p9-local-owner"
    ).json()["nodes"]) == 1


def test_untrusted_url_scheme_is_not_marked_completed():
    rid = _create("unsafe-001", "file:///etc/passwd")
    result = client.post(
        f"/v4/workpaths/runs/{rid}/execute-local?tenant_id=p9-local-owner"
    )
    assert result.status_code == 200
    assert result.json()["executed_nodes"] == []
    assert result.json()["blocked_at"]["reason"] == "UNVERIFIED_OPERATION_RESULT"
    stored = client.get(
        f"/v4/workpaths/runs/{rid}?tenant_id=p9-local-owner"
    ).json()
    assert stored["nodes"] == []


def test_other_tenant_cannot_run_local_actions():
    rid = _create("tenant-001", "https://example.com/creator")
    response = client.post(
        f"/v4/workpaths/runs/{rid}/execute-local?tenant_id=p9-local-attacker"
    )
    assert response.status_code == 404
