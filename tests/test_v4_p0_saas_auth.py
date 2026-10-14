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
