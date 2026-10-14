"""P12: inspect existing V4 DAGs and mount their actual ASGI endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from api.v4.asgi import app
from workflows.v4.capability_preflight import inspect_all_paths, inspect_path


def test_eight_defined_paths_are_visible_without_fake_production_success():
    data = inspect_all_paths()
    assert data["total_paths"] == 8
    assert data["execution_ready_paths"] == 0
    assert data["total_nodes"] >= 45
    assert all(p["level"] == "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION"
               for p in data["paths"])
    assert all(p["business_validated"] is False for p in data["paths"])


def test_two_user_supplied_local_paths_have_narrow_contracts():
    article = inspect_path("WP-LOCAL-ARTICLE-EXTRACT")
    subtitle = inspect_path("WP-LOCAL-SUBTITLE-EXPORT")
    assert article["local_sync_supported"] is True
    assert subtitle["local_worker_supported"] is True
    assert article["requires_provider_auth"] is False
    assert subtitle["requires_provider_auth"] is False
    assert article["execution_ready"] is False
    assert subtitle["execution_ready"] is False
    blogger = inspect_path("WP-BLOGGER-RESEARCH")
    assert blogger["requires_provider_auth"] is True
    assert blogger["execution_ready"] is False


def test_actual_asgi_host_serves_source_preflight_and_rejects_unknown():
    with TestClient(app) as client:
        index = client.get("/v4/workpaths/capabilities")
        assert index.status_code == 200
        assert index.json()["total_paths"] == 8
        route = client.get("/v4/workpaths/WP-LOCAL-ARTICLE-EXTRACT/preflight")
        assert route.status_code == 200
        assert route.json()["local_sync_supported"] is True
        unknown = client.get("/v4/workpaths/WP-DOES-NOT-EXIST/preflight")
        assert unknown.status_code == 404
