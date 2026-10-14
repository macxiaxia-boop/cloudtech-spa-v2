"""Actual V4 HTTP endpoints can read durable task records after process reload.

No real workers, providers, payments, or production migrations occur.
"""
import importlib
from fastapi import FastAPI
from fastapi.testclient import TestClient
from workflows.v4 import IdempotencyStore, V4Orchestrator
from workflows.v4.sqlite_run_store import SQLiteRunStore


def test_v4_http_persistent_create_replay_read_and_tenant_isolation(
    tmp_path, monkeypatch,
):
    api = importlib.import_module("api.v4")
    db_path = tmp_path / "v4.sqlite3"
    monkeypatch.setattr(
        api, "_orchestrator",
        V4Orchestrator(IdempotencyStore(), run_store=SQLiteRunStore(db_path)),
    )
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    payload = {
        "path_id": "WP-VIDEO-TRANSCRIBE",
        "revision": 1,
        "input_bindings": {"video_source": "https://example.org/clip"},
        "idempotency_key": "client-retry-001",
    }
    r = client.post("/v4/workpaths/runs?tenant_id=owner_one", json=payload)
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["storage"] == "SQLITE_LOCAL_DURABLE"
    assert created["status"] == "READY"
    assert created["execution_started"] is False
    run_id = created["run_id"]

    # Emulate restarting V4 in a new process without reopening the same
    # orchestrator object. The authoritative record must be in SQLite.
    monkeypatch.setattr(
        api, "_orchestrator",
        V4Orchestrator(IdempotencyStore(), run_store=SQLiteRunStore(db_path)),
    )
    replay = client.post("/v4/workpaths/runs?tenant_id=owner_one", json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["run_id"] == run_id
    assert replay.json()["idempotent_hit"] is True

    fetched = client.get(f"/v4/workpaths/runs/{run_id}?tenant_id=owner_one")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "READY"
    other = client.get(f"/v4/workpaths/runs/{run_id}?tenant_id=other_org")
    assert other.status_code == 404

    listed = client.get("/v4/workpaths/runs?tenant_id=owner_one")
    assert listed.status_code == 200, listed.text
    assert listed.json()["storage"] == "SQLITE_LOCAL_DURABLE"
    assert [item["run_id"] for item in listed.json()["items"]] == [run_id]
    assert client.get("/v4/workpaths/runs?tenant_id=other_org").json()["items"] == []

    changed = dict(payload)
    changed["input_bindings"] = {"video_source": "https://another.org/video"}
    conflict = client.post("/v4/workpaths/runs?tenant_id=owner_one", json=changed)
    assert conflict.status_code == 409

    resume = client.post(
        f"/v4/workpaths/runs/{run_id}/resume?tenant_id=owner_one",
        json={"failed_nodes_only": True},
    )
    assert resume.status_code == 501  # No falsely claimed Worker recovery



def test_concurrent_http_same_key_creates_only_one_ready_run(tmp_path, monkeypatch):
    import importlib
    from concurrent.futures import ThreadPoolExecutor
    api = importlib.import_module("api.v4")
    db = tmp_path / "concurrent-http.sqlite"
    monkeypatch.setattr(api, "_orchestrator", V4Orchestrator(
        IdempotencyStore(), run_store=SQLiteRunStore(db),
    ))
    app = FastAPI()
    app.include_router(api.router)
    payload = {
        "path_id": "WP-VIDEO-TRANSCRIBE",
        "revision": 1,
        "input_bindings": {"video_source": "https://example.org/a"},
        "idempotency_key": "same-http-request",
    }
    def create(_):
        with TestClient(app) as client:
            response = client.post("/v4/workpaths/runs?tenant_id=owner", json=payload)
            return response.status_code, response.json()
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(create, range(24)))
    assert all(status == 200 for status, _ in results), results
    assert len({body["run_id"] for _, body in results}) == 1
    verify = V4Orchestrator(IdempotencyStore(), run_store=SQLiteRunStore(db))
    runs = verify.list_runs(tenant_id="owner")
    assert len(runs) == 1
    assert runs[0].status.value == "READY"
