"""Signed JWT must not keep access after the SaaS tenant or user is disabled."""
import sqlite3
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.v4 import router
from api.v4.auth import mint_jwt


def test_v4_requires_current_active_user_and_tenant(tmp_path, monkeypatch):
    database = tmp_path / "test_identity.sqlite"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE saas_users (user_id TEXT, tenant_id TEXT)")
        db.execute("CREATE TABLE saas_tenants (tenant_id TEXT, active INTEGER)")
        db.execute("INSERT INTO saas_users VALUES('u1','t1')")
        db.execute("INSERT INTO saas_tenants VALUES('t1',1)")

    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.delenv("CLOUDTECH_ALLOW_INSECURE_DEV_AUTH", raising=False)
    monkeypatch.setenv("V4_JWT_SECRET", "long-test-signing-secret-" * 3)
    monkeypatch.setenv("CLOUDTECH_SAAS_DB_PATH", str(database))

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    token = mint_jwt("t1", "u1")
    auth = {"Authorization": "Bearer " + token}

    accepted = client.get("/v4/workpaths/runs?tenant_id=t1", headers=auth)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["items"] == []
    assert client.get("/v4/workpaths/runs?tenant_id=t2", headers=auth).status_code == 401

    # Revoking the enterprise takes effect with the next V4 request.
    with sqlite3.connect(database) as db:
        db.execute("UPDATE saas_tenants SET active=0 WHERE tenant_id='t1'")
    assert client.get("/v4/workpaths/runs?tenant_id=t1", headers=auth).status_code == 403

    with sqlite3.connect(database) as db:
        db.execute("UPDATE saas_tenants SET active=1 WHERE tenant_id='t1'")
        db.execute("DELETE FROM saas_users WHERE user_id='u1'")
    assert client.get("/v4/workpaths/runs?tenant_id=t1", headers=auth).status_code == 403

    database.unlink()
    assert client.get("/v4/workpaths/runs?tenant_id=t1", headers=auth).status_code == 503


def test_v4_unsigned_or_bad_token_never_queries_membership(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("V4_JWT_SECRET", "long-test-signing-secret-" * 3)
    monkeypatch.setenv("CLOUDTECH_SAAS_DB_PATH", str(tmp_path / "absent.db"))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/v4/workpaths/runs?tenant_id=t1",
                          headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
    assert not (tmp_path / "absent.db").exists()
