"""API endpoint tests for CloudTech v2.1"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from admin_dashboard import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# ── Core endpoints ──
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"html" in r.data.lower() or b"<!DOCTYPE" in r.data


def test_admin(client):
    r = client.get("/admin")
    assert r.status_code == 200


def test_login_page(client):
    r = client.get("/login.html")
    assert r.status_code == 200


def test_register_page(client):
    r = client.get("/register.html")
    assert r.status_code == 200


# ── Auth API ──
def test_login_missing_fields(client):
    r = client.post("/api/auth/login", json={})
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_register_missing_fields(client):
    r = client.post("/api/auth/register", json={})
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_register_weak_password(client):
    r = client.post("/api/auth/register", json={
        "email": "test@test.com", "password": "123", "name": "Test"
    })
    assert r.status_code == 400


# ── System API ──
def test_system_status(client):
    r = client.get("/api/system/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["app"] == "CloudTech v2.0.0"


def test_api_status(client):
    r = client.get("/api/status")
    assert r.status_code == 200


# ── Payment API ──
def test_create_order(client):
    r = client.post("/api/payment/create-order", json={
        "plan_id": "starter", "user_id": "test-user"
    })
    assert r.status_code == 200
    data = r.get_json()
    assert "order_id" in data or "error" in data


# ── Ops API ──
def test_ops_dashboard(client):
    r = client.get("/api/admin/ops")
    assert r.status_code == 200
    data = r.get_json()
    assert "mrr" in data
    assert "users" in data
    assert "tenants" in data


# ── Error tracking ──
def test_error_stats(client):
    r = client.get("/api/admin/errors")
    assert r.status_code == 200
    data = r.get_json()
    assert "total" in data


# ── 404 ──
def test_404(client):
    r = client.get("/nonexistent-path-xyz")
    assert r.status_code == 404
