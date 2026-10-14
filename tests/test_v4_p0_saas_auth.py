"""SaaS v8 security regression; isolated SQLite only, zero external side effects."""
import hashlib
import importlib.util
from pathlib import Path
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def saas(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "data-layer" / "v_saas_v8.py"
    spec = importlib.util.spec_from_file_location("test_only_v_saas_v8", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.DB = str(tmp_path / "test_cloudtech.db")
    monkeypatch.setenv("CLOUDTECH_SAAS_JWT_SECRET", "0123456789abcdef" * 4)
    module._ensure_db()
    with sqlite3.connect(module.DB) as conn:
        conn.execute("""CREATE TABLE email_queue (
            to_email TEXT, template TEXT, subject TEXT, body_html TEXT,
            variables TEXT, status TEXT, attempts INTEGER,
            created_at TEXT, sent_at TEXT
        )""")
    app = FastAPI()
    app.include_router(module.router)
    return module, TestClient(app)


def test_missing_jwt_secret_fails_before_account_mutation(saas, monkeypatch):
    module, client = saas
    monkeypatch.delenv("CLOUDTECH_SAAS_JWT_SECRET", raising=False)
    r = client.post("/api/saas/v1/register", json={
        "email": "user@example.com", "password": "strongpass", "tenant_name": "Company"
    })
    assert r.status_code == 503, r.text
    with sqlite3.connect(module.DB) as conn:
        assert conn.execute("SELECT COUNT(*) FROM saas_users").fetchone()[0] == 0


def test_registration_hash_and_email_queue_are_honest(saas):
    module, client = saas
    r = client.post("/api/saas/v1/register", json={
        "email": "user@example.com", "password": "strongpass",
        "name": "<svg onload=alert(1)>", "tenant_name": "Company",
    })
    assert r.status_code == 200, r.text
    result = r.json()
    assert result["welcome_email_sent"] is False
    assert result["welcome_email_queued"] is True
    assert result["token"].count(".") == 2
    with sqlite3.connect(module.DB) as conn:
        pwd_hash = conn.execute(
            "SELECT password_hash FROM saas_users WHERE email=?", ("user@example.com",)
        ).fetchone()[0]
        assert pwd_hash.startswith("pbkdf2:sha256:260000$")
        email = conn.execute("SELECT status,attempts,sent_at,body_html FROM email_queue").fetchone()
        assert email[0] == "queued" and email[1] == 0 and email[2] is None
        assert "<svg onload=" not in email[3]

    logged_in = client.post("/api/saas/v1/login", json={
        "email": "user@example.com", "password": "strongpass",
    })
    assert logged_in.status_code == 200, logged_in.text


def test_legacy_sha256_hash_is_upgraded_after_successful_login(saas):
    module, client = saas
    pwd = "legacy-password"
    salt = "legacy-salt"
    legacy = hashlib.sha256((salt + pwd).encode()).hexdigest()
    with sqlite3.connect(module.DB) as conn:
        conn.execute("""INSERT INTO saas_users(
          user_id,email,password_hash,salt,tenant_id,industry,plan,created_at)
          VALUES(?,?,?,?,?,?,?,?)""",
          ("legacy-u", "legacy@example.com", legacy, salt,
           "tenant-legacy", "decoration", "basic", "2026-01-01"))
    bad = client.post("/api/saas/v1/login", json={
        "email": "legacy@example.com", "password": "wrong"
    })
    assert bad.status_code == 401
    with sqlite3.connect(module.DB) as conn:
        assert conn.execute("SELECT password_hash FROM saas_users").fetchone()[0] == legacy
    ok = client.post("/api/saas/v1/login", json={
        "email": "legacy@example.com", "password": pwd,
    })
    assert ok.status_code == 200, ok.text
    with sqlite3.connect(module.DB) as conn:
        upgraded = conn.execute("SELECT password_hash FROM saas_users").fetchone()[0]
        assert upgraded.startswith("pbkdf2:sha256:260000$")
        assert upgraded != legacy


def test_bad_jwt_secret_is_not_accepted_even_if_present(saas, monkeypatch):
    module, client = saas
    monkeypatch.setenv("CLOUDTECH_SAAS_JWT_SECRET", "short")
    with pytest.raises(Exception) as exc:
        module._mint_jwt("user", "tenant")
    assert "503" in str(exc.value)


def test_signed_saas_session_is_looked_up_in_db(saas):
    module, client = saas
    registered = client.post("/api/saas/v1/register", json={
        "email": "verified@example.com", "password": "strong-pass-123",
        "tenant_name": "真实工作空间",
    })
    assert registered.status_code == 200, registered.text
    auth = {"Authorization": "Bearer " + registered.json()["token"]}
    response = client.get("/api/saas/v1/me", headers=auth)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["verified"] is True
    assert data["tenant_id"] == registered.json()["tenant_id"]
    assert data["workspace_name"] == "真实工作空间"
    assert data["role"] == "member"
    assert client.get("/api/saas/v1/me").status_code == 401
    assert client.get("/api/saas/v1/me", headers={
        "Authorization": auth["Authorization"][:-3] + "abc",
    }).status_code == 401


def test_signed_saas_jwt_can_be_verified_by_existing_v4_tenant_middleware(saas, monkeypatch):
    module, client = saas
    from api.v4.auth import _verify_jwt, _get_jwt_secret
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    token = module._mint_jwt("user-123", "tenant-123")
    assert _get_jwt_secret() == "0123456789abcdef" * 4
    claims = _verify_jwt(token, _get_jwt_secret(), "tenant-123")
    assert claims is not None
    assert claims["tenant_id"] == "tenant-123"
    assert claims["user_id"] == "user-123"
    assert _verify_jwt(token, _get_jwt_secret(), "other-tenant") is None


def test_saas_session_denied_after_tenant_disabled(saas):
    module, client = saas
    created = client.post("/api/saas/v1/register", json={
        "email": "disabled@example.com", "password": "strongpass",
        "tenant_name": "Disabled",
    })
    assert created.status_code == 200
    with sqlite3.connect(module.DB) as conn:
        conn.execute("UPDATE saas_tenants SET active=0 WHERE tenant_id=?",
                     (created.json()["tenant_id"],))
    response = client.get("/api/saas/v1/me", headers={
        "Authorization": "Bearer " + created.json()["token"],
    })
    assert response.status_code == 403
