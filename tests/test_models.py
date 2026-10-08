"""Unit tests for core business logic modules"""
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ── Database ──
def test_db_connection():
    from database import get_db
    db = get_db()
    assert db is not None


def test_db_crud():
    from database import get_db
    db = get_db()
    # Create test table
    db.execute("""
        CREATE TABLE IF NOT EXISTS _test_crud (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """)
    # Insert
    row_id = db.insert("_test_crud", {"name": "test-value"})
    assert row_id is not None
    # Fetch
    row = db.fetch_one("SELECT * FROM _test_crud WHERE id = ?", [row_id])
    assert dict(row)["name"] == "test-value"
    # Update
    db.update("_test_crud", {"name": "updated"}, "id = ?", [row_id])
    row = db.fetch_one("SELECT * FROM _test_crud WHERE id = ?", [row_id])
    assert dict(row)["name"] == "updated"
    # Cleanup
    db.execute("DROP TABLE _test_crud")


# ── JWT Secret persistence ──
def test_jwt_secret_file():
    from auth import JWT_SECRET, _JWT_SECRET_FILE
    assert JWT_SECRET is not None
    assert len(JWT_SECRET) == 64  # 32 bytes hex
    assert _JWT_SECRET_FILE.exists()


# ── Password hashing ──
def test_password_hash():
    from auth import hash_password, verify_password
    pw = "test-password-123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrong", hashed)


# ── WeChat Pay plans ──
def test_pricing_plans():
    from wechat_pay import PRICING_PLANS
    assert "starter" in PRICING_PLANS
    assert "pro" in PRICING_PLANS
    assert "business" in PRICING_PLANS
    assert PRICING_PLANS["starter"]["price_yuan"] == 99
    assert PRICING_PLANS["pro"]["price_yuan"] == 299


# ── Tenant isolation ──
def test_tenant_scoped_db():
    from tenant_isolation import TenantScopedDB
    from database import get_db
    # Create test table
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS _test_tenant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            name TEXT
        )
    """)
    # Insert with scoped DB
    scoped = TenantScopedDB("tenant-A")
    scoped.insert("_test_tenant", {"name": "data-A"})
    scoped2 = TenantScopedDB("tenant-B")
    scoped2.insert("_test_tenant", {"name": "data-B"})
    # Verify isolation
    rows_a = scoped.fetch_all("SELECT * FROM _test_tenant")
    rows_b = scoped2.fetch_all("SELECT * FROM _test_tenant")
    assert len(rows_a) == 1
    assert len(rows_b) == 1
    assert dict(rows_a[0])["name"] == "data-A"
    assert dict(rows_b[0])["name"] == "data-B"
    # Cleanup
    db.execute("DROP TABLE _test_tenant")


# ── Email service ──
def test_email_mock(monkeypatch):
    monkeypatch.setattr("email_service.SMTP_HOST", "")
    from email_service import send_welcome, send_billing
    assert send_welcome("test@test.com", "TestUser", "入门版") is True
    assert send_billing("test@test.com", "TestUser", "入门版", 99.0, "2026-08-01") is True


# ── Error tracker ──
def test_error_capture():
    from error_tracker import capture_exception, get_error_stats
    try:
        raise ValueError("test-error-for-tracking")
    except ValueError as e:
        fp = capture_exception(e, {"test": True})
        assert fp is not None
        assert len(fp) == 12
    stats = get_error_stats(days=1)
    assert stats["total"] >= 1
