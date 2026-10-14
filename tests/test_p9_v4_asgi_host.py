"""Verify the original V4 router can run as a loopback ASGI application."""
from fastapi.testclient import TestClient
from api.v4.asgi import app


def test_asgi_entry_exposes_real_capability_index():
    with TestClient(app) as client:
        response = client.get("/v4/workpaths/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["total_paths"] == 6
    assert data["execution_ready_paths"] == 0
    assert data["total_nodes"] >= 45


def test_asgi_entry_rejects_unknown_workpath():
    with TestClient(app) as client:
        response = client.get("/v4/workpaths/unknown/preflight")
    assert response.status_code == 404
