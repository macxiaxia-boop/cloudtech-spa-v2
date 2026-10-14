"""One REAL CloudTech business journey: HTML -> run -> local node -> persisted result.

No fake LLM, no paid model, no external webpage fetch, no production migration.
"""
import hashlib
import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workflows.v4 import IdempotencyStore, V4Orchestrator
from workflows.v4.sqlite_run_store import SQLiteRunStore


def test_real_html_extraction_workpath_closes_and_survives_restart(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    sqlite_path = tmp_path / "article-run.sqlite3"
    def fresh():
        return V4Orchestrator(IdempotencyStore(), run_store=SQLiteRunStore(sqlite_path))
    monkeypatch.setattr(api, "_orchestrator", fresh())
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)

    source_html = (
        "<html><head><title>真实用户素材</title></head>"
        "<body><h1>标题</h1><article><p>原创说明第一段。</p>"
        "<img src='https://example.org/p.png'>"
        "<p>真实素材第二段。</p></article></body></html>"
    )
    req = {
        "path_id": "WP-LOCAL-ARTICLE-EXTRACT",
        "revision": 1,
        "input_bindings": {
            "html": source_html,
            "source_url": "https://example.org/source",
        },
        "idempotency_key": "local-article-1",
    }
    created = client.post("/v4/workpaths/runs?tenant_id=tenant-a", json=req)
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "READY"
    assert created.json()["storage"] == "SQLITE_LOCAL_DURABLE"
    run_id = created.json()["run_id"]

    forbidden = client.post(f"/v4/workpaths/runs/{run_id}/execute-local?tenant_id=tenant-b")
    assert forbidden.status_code == 404

    executed = client.post(f"/v4/workpaths/runs/{run_id}/execute-local?tenant_id=tenant-a")
    assert executed.status_code == 200, executed.text
    result = executed.json()
    assert result["status"] == "COMPLETED"
    assert result["cost_cents"] == 0
    assert result["provider_called"] is False
    assert result["worker_type"] == "SYNCHRONOUS_LOCAL_ONLY"
    assert len(result["nodes"]) == 1
    node = result["nodes"][0]
    assert node["status"] == "COMPLETED"
    assert node["cost_cents"] == 0
    assert "真实素材第二段" in node["output_ref"]["text"]
    assert node["output_ref"]["content_sha256"] == hashlib.sha256(source_html.encode()).hexdigest()

    # Explicitly reconnect a new orchestrator to prove the result was saved.
    monkeypatch.setattr(api, "_orchestrator", fresh())
    stored = client.get(f"/v4/workpaths/runs/{run_id}?tenant_id=tenant-a")
    assert stored.status_code == 200, stored.text
    assert stored.json()["status"] == "COMPLETED"
    assert stored.json()["nodes"][0]["output_ref"] == node["output_ref"]

    export = client.get(f"/v4/workpaths/runs/{run_id}/export?tenant_id=tenant-a")
    assert export.status_code == 200
    assert export.json()["ready"] is True
    assert export.json()["manifest"]["budget_spent_cents"] == 0

    replay = client.post(f"/v4/workpaths/runs/{run_id}/execute-local?tenant_id=tenant-a")
    assert replay.status_code == 200
    assert replay.json()["idempotent_hit"] is True
    assert replay.json()["nodes"] == result["nodes"]
    journal = SQLiteRunStore(sqlite_path)
    assert journal.receipt_count(run_id) == 1


def test_local_executor_denies_complex_flagship_and_missing_html(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    monkeypatch.setattr(api, "_orchestrator", V4Orchestrator(
        IdempotencyStore(), run_store=SQLiteRunStore(tmp_path / "blocked.sqlite")
    ))
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    created = client.post("/v4/workpaths/runs?tenant_id=tenant-a", json={
        "path_id": "WP-VIDEO-TRANSCRIBE", "revision": 1,
        "input_bindings": {"video_source": "https://example.org/video"},
    })
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    denied = client.post(f"/v4/workpaths/runs/{run_id}/execute-local?tenant_id=tenant-a")
    assert denied.status_code == 422
    assert client.get(f"/v4/workpaths/runs/{run_id}?tenant_id=tenant-a").json()["status"] == "READY"

    invalid = client.post("/v4/workpaths/runs?tenant_id=tenant-a", json={
        "path_id": "WP-LOCAL-ARTICLE-EXTRACT", "revision": 1,
        "input_bindings": {},
    })
    assert invalid.status_code == 422



def test_local_crash_reconciliation_uses_receipt_without_reexecution(tmp_path, monkeypatch):
    from workflows.v4 import RunStatus
    from workflows.v4.orchestrator import NodeRunRecord
    from workflows.v4.node_kinds import NodeKind
    from adapters.article.article_parser import parse_html

    api = importlib.import_module("api.v4")
    db_path = tmp_path / "recover.sqlite"
    def new_orchestrator():
        return V4Orchestrator(IdempotencyStore(), run_store=SQLiteRunStore(db_path))
    orch = new_orchestrator()
    monkeypatch.setattr(api, "_orchestrator", orch)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    html = "<html><title>单机恢复</title><body><p>原始内容</p></body></html>"
    created = client.post("/v4/workpaths/runs?tenant_id=tenant_r", json={
        "path_id": "WP-LOCAL-ARTICLE-EXTRACT", "revision": 1,
        "input_bindings": {"html": html}, "idempotency_key": "recover-1",
    })
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]
    orch.transition(run_id, RunStatus.RUNNING)
    node = NodeRunRecord(
        node_id="html_parse", node_kind=NodeKind.TRANSFORM,
        operation="article.html_parse", requires={}, produces={},
        input_hash=hashlib.sha256(html.encode()).hexdigest(),
    )
    orch.add_node(run_id, node)
    orch.mark_node_running(run_id, "html_parse")
    orch.mark_node_done(
        run_id, "html_parse", parse_html(html),
        provider_name="local_html_parser", cost_cents=0,
    )
    assert orch.get_run(run_id).status is RunStatus.RUNNING
    assert SQLiteRunStore(db_path).receipt_count(run_id) == 1

    monkeypatch.setattr(api, "_orchestrator", new_orchestrator())
    denied = client.post(f"/v4/workpaths/runs/{run_id}/reconcile-local?tenant_id=other")
    assert denied.status_code == 404
    response = client.post(f"/v4/workpaths/runs/{run_id}/reconcile-local?tenant_id=tenant_r")
    assert response.status_code == 200, response.text
    assert response.json()["reconciled"] is True
    assert response.json()["provider_recalled"] is False
    assert response.json()["new_charge_cents"] == 0
    assert client.get(f"/v4/workpaths/runs/{run_id}?tenant_id=tenant_r").json()["status"] == "COMPLETED"
    assert SQLiteRunStore(db_path).receipt_count(run_id) == 1
    replay = client.post(f"/v4/workpaths/runs/{run_id}/reconcile-local?tenant_id=tenant_r")
    assert replay.status_code == 200
    assert replay.json()["reconciled"] is False


def test_local_reconcile_refuses_incomplete_uncertain_execution(tmp_path, monkeypatch):
    api = importlib.import_module("api.v4")
    orch = V4Orchestrator(
        IdempotencyStore(), run_store=SQLiteRunStore(tmp_path / "incomplete.sqlite")
    )
    monkeypatch.setattr(api, "_orchestrator", orch)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    created = client.post("/v4/workpaths/runs?tenant_id=tenant_r", json={
        "path_id": "WP-LOCAL-ARTICLE-EXTRACT", "revision": 1,
        "input_bindings": {"html": "<p>未完成</p>"},
    })
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    from workflows.v4 import RunStatus
    orch.transition(run_id, RunStatus.RUNNING)
    result = client.post(f"/v4/workpaths/runs/{run_id}/reconcile-local?tenant_id=tenant_r")
    assert result.status_code == 409
    assert orch.get_run(run_id).status is RunStatus.RUNNING
