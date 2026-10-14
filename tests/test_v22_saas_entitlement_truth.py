"""Real isolated FastAPI+SQLite SaaS register, login and entitlement contract.

No real customer data, email sending, paid provider or production database.
Tests the actual legacy v_saas_v8 router, not a copied fake service.
"""
import importlib.util
import sqlite3
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "data-layer/v_saas_v8.py"


def _app(monkeypatch, database):
    monkeypatch.setenv("CLOUDTECH_SAAS_DB_PATH", str(database))
    monkeypatch.setenv("CLOUDTECH_SAAS_JWT_SECRET", "test-only-tenant-signing-secret-2026-at-least-32-bytes")
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    module_name = "isolated_real_saas_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(module_name, SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app)


def _register(client, email="real-owner@example.test"):
    return client.post("/api/saas/v1/register", json={
        "email": email, "password": "a-secure-unique-test-password-2026",
        "tenant_name": "示例企业（离线隔离）", "industry": "decoration",
        "sku_id": "dec_basic",
    })


def test_real_register_without_subscription_table_does_not_invent_trial(tmp_path, monkeypatch):
    db = tmp_path / "isolated-saas.sqlite"
    client = _app(monkeypatch, db)
    with client:
        trial_info = client.get("/api/saas/v1/info")
        assert trial_info.status_code == 200
        assert trial_info.json()["trial"]["auto_grant"] is False
        assert trial_info.json()["trial"]["requires_verified_subscription"] is True
        registration = _register(client)
        assert registration.status_code == 200, registration.text
        data = registration.json()
        assert data["status"] == "ok"
        assert data["plan"] == "basic"
        assert data["trial_days"] == 0
        assert data["trial_end_at"] is None
        assert data["token"].count(".") == 2
        assert client.get("/api/saas/v1/me").status_code == 401
        verified = client.get("/api/saas/v1/me", headers={
            "Authorization": "Bearer " + data["token"]
        })
        assert verified.status_code == 200, verified.text
        assert verified.json()["verified"] is True
        assert verified.json()["tenant_id"] == data["tenant_id"]
        assert verified.json()["email"] == "real-owner@example.test"
        wrong_password = client.post("/api/saas/v1/login", json={
            "email": "real-owner@example.test", "password": "incorrect",
        })
        assert wrong_password.status_code == 401
        login = client.post("/api/saas/v1/login", json={
            "email": "real-owner@example.test",
            "password": "a-secure-unique-test-password-2026",
        })
        assert login.status_code == 200
        assert client.get("/api/saas/v1/me", headers={
            "Authorization": "Bearer " + login.json()["token"]
        }).status_code == 200
        assert _register(client).status_code == 409
        landing = client.get("/api/saas/v1/landing")
        assert landing.status_code == 200
        assert "/chat?token=" not in landing.text
        assert "j.token.slice(" not in landing.text
        assert "location.href='/login'" in landing.text
    with sqlite3.connect(db) as stored:
        assert stored.execute("SELECT plan FROM saas_tenants").fetchone()[0] == "basic"
        assert stored.execute("SELECT plan FROM saas_users").fetchone()[0] == "basic"


def test_trial_subscription_must_commit_in_same_transaction(tmp_path, monkeypatch):
    db = tmp_path / "entitled-only-when-recorded.sqlite"
    with sqlite3.connect(db) as stored:
        stored.execute("""CREATE TABLE aios_subscription (
            subscription_id TEXT,tenant_id TEXT,industry TEXT,plan TEXT,
            sku_code TEXT,amount_cny INTEGER,status TEXT,
            activated_at TEXT,expires_at TEXT,created_at TEXT
        )""")
    client = _app(monkeypatch, db)
    with client:
        result = _register(client, "subscribed@example.test")
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["plan"] == "pro"
        assert body["trial_days"] == 7
        assert body["trial_end_at"]
    with sqlite3.connect(db) as stored:
        assert stored.execute("SELECT plan FROM saas_tenants").fetchone()[0] == "pro"
        assert stored.execute("SELECT plan FROM saas_users").fetchone()[0] == "pro"
        subscription = stored.execute(
            "SELECT tenant_id,amount_cny,status FROM aios_subscription"
        ).fetchone()
        assert subscription == (body["tenant_id"], 0, "active")


def test_tenant_membership_revocation_blocks_signed_bearer(tmp_path, monkeypatch):
    db = tmp_path / "revocation-by-tenant.sqlite"
    client = _app(monkeypatch, db)
    with client:
        result = _register(client)
        assert result.status_code == 200
        token = result.json()["token"]
        assert client.get("/api/saas/v1/me", headers={
            "Authorization": "Bearer " + token
        }).status_code == 200
        with sqlite3.connect(db) as stored:
            stored.execute("UPDATE saas_tenants SET active=0")
        assert client.get("/api/saas/v1/me", headers={
            "Authorization": "Bearer " + token
        }).status_code == 403


def test_missing_signing_secret_never_creates_unverified_user(tmp_path, monkeypatch):
    db = tmp_path / "no-secret.sqlite"
    client = _app(monkeypatch, db)
    monkeypatch.delenv("CLOUDTECH_SAAS_JWT_SECRET", raising=False)
    monkeypatch.delenv("V4_JWT_SECRET", raising=False)
    with client:
        denied = _register(client)
        assert denied.status_code == 503
    with sqlite3.connect(db) as stored:
        assert stored.execute("SELECT COUNT(*) FROM saas_users").fetchone()[0] == 0
