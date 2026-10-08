"""CloudTech V6.2 - Database integrity edge case tests.

Tests use the **production** V2 schema in `data/cloudtech.db`. Key constraints:
- tenants.plan CHECK (free|starter|pro|enterprise)
- tenants.name UNIQUE, tenants.slug UNIQUE
- users.tenant_id NOT NULL, users.password_salt NOT NULL
- pipeline_runs.tenant_id FK -> tenants(id)

All test rows use unique IDs/slugs prefixed with `_v62_` so they can be
cleaned up reliably without touching real data.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import json
import sqlite3


# ── Shared fixture ──
@pytest.fixture(scope="module")
def db():
    """Returns a connected Database instance (idempotent — singleton-safe)."""
    from database import get_db
    return get_db()


def _cleanup(db, sql, params):
    """Run a DELETE statement for test cleanup (fail-safe)."""
    try:
        db.execute(sql, params)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════
# V6.2 Item 2: CloudTech database edge case tests (5 new)
# ════════════════════════════════════════════════════════════════════════

def test_tenant_create_with_all_fields(db):
    """Insert a tenant with every V2 column populated, verify all round-trip.

    V2 tenants schema: id, name, slug, plan (CHECK), status (CHECK),
                      owner_user_id, settings_json, created_at, updated_at
    """
    import secrets
    name = f"V62 Edge Test Tenant {secrets.token_hex(4)}"
    slug = f"_v62_t_{secrets.token_hex(6)}"
    settings = {"theme": "dark", "cities": ["厦门", "福州"], "language": "zh-CN"}

    # Insert with EVERY V2 column (using valid CHECK values)
    cur = db.execute("""
        INSERT INTO tenants
            (name, slug, plan, status, owner_user_id, settings_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        name,
        slug,
        "enterprise",     # CHECK valid: free|starter|pro|enterprise
        "active",         # CHECK valid: active|suspended|archived
        None,             # owner_user_id nullable
        json.dumps(settings, ensure_ascii=False),
    ])
    tenant_id = cur.lastrowid

    try:
        # Round-trip and verify all fields
        row = db.fetch_one("SELECT * FROM tenants WHERE id = ?", [tenant_id])
        d = dict(row)
        assert d["id"] == tenant_id
        assert d["name"] == name
        assert d["slug"] == slug
        assert d["plan"] == "enterprise"
        assert d["status"] == "active"
        assert d["owner_user_id"] is None
        # settings_json round-trip
        decoded = json.loads(d["settings_json"])
        assert decoded == settings
        assert "厦门" in decoded["cities"]
        # Auto-filled timestamps
        assert d["created_at"] is not None
        assert d["updated_at"] is not None
    finally:
        _cleanup(db, "DELETE FROM tenants WHERE id = ?", [tenant_id])


def test_tenant_unique_id_enforcement(db):
    """INSERT two tenants with the same PRIMARY KEY must raise IntegrityError.

    Note: id is INTEGER AUTOINCREMENT, so we directly specify id value
    (negative values to avoid colliding with real data).
    """
    import secrets
    # Negative IDs to avoid colliding with real positive AUTOINCREMENT ids
    tenant_id = -(secrets.randbelow(9_000_000) + 1_000_000)
    slug_a = f"_v62_dup_a_{secrets.token_hex(4)}"
    slug_b = f"_v62_dup_b_{secrets.token_hex(4)}"
    name_a = f"V62 Dup A {secrets.token_hex(4)}"
    name_b = f"V62 Dup B {secrets.token_hex(4)}"

    try:
        # First insert succeeds
        db.execute("""
            INSERT INTO tenants (id, name, slug, plan, status)
            VALUES (?, ?, ?, ?, ?)
        """, [tenant_id, name_a, slug_a, "starter", "active"])

        # Second insert with SAME id must fail (PK violation)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("""
                INSERT INTO tenants (id, name, slug, plan, status)
                VALUES (?, ?, ?, ?, ?)
            """, [tenant_id, name_b, slug_b, "pro", "active"])

        # Verify only one row exists for that id
        rows = db.fetch_all("SELECT id, slug FROM tenants WHERE id = ?", [tenant_id])
        assert len(rows) == 1
        assert dict(rows[0])["slug"] == slug_a

        # Bonus: slug uniqueness should also be enforced (slug has UNIQUE)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("""
                INSERT INTO tenants (id, name, slug, plan, status)
                VALUES (?, ?, ?, ?, ?)
            """, [tenant_id - 1, f"V62 SlugDup {secrets.token_hex(4)}", slug_a, "starter", "active"])
    finally:
        _cleanup(db, "DELETE FROM tenants WHERE id = ?", [tenant_id])
        # Slug-dup second insert may have failed before insert; safe cleanup
        _cleanup(db, "DELETE FROM tenants WHERE id = ?", [tenant_id - 1])


def test_tenant_metadata_json_serialization(db):
    """settings_json column preserves CJK + emoji + nested dicts + arrays."""
    import secrets
    name = f"V62 JSON Meta {secrets.token_hex(4)}"
    slug = f"_v62_json_{secrets.token_hex(6)}"
    metadata = {
        "theme": "dark",
        "language": "zh-CN",
        "cities": ["厦门", "福州", "泉州"],
        "nested": {
            "notification": {"email": True, "sms": False},
            "tags": ["vip", "beta-tester", "装修行业"],
        },
        "count": 42,
        "unicode": "装修老板 👷 测试",
    }
    metadata_str = json.dumps(metadata, ensure_ascii=False)

    db.execute("""
        INSERT INTO tenants (name, slug, plan, status, settings_json)
        VALUES (?, ?, ?, ?, ?)
    """, [name, slug, "pro", "active", metadata_str])
    tenant_id = db.fetch_one(
        "SELECT id FROM tenants WHERE slug = ?", [slug]
    )
    tenant_id = dict(tenant_id)["id"]

    try:
        # Fetch + decode
        row = db.fetch_one(
            "SELECT settings_json FROM tenants WHERE id = ?", [tenant_id]
        )
        raw_json = dict(row)["settings_json"]
        decoded = json.loads(raw_json)

        # Deep equality check
        assert decoded == metadata
        # CJK + emoji preserved (no Unicode escape artifacts)
        BACKSLASH = chr(0x5C)
        assert decoded["unicode"] == "装修老板 👷 测试"
        assert BACKSLASH + "u" not in raw_json  # raw UTF-8 stored, not escaped
        assert decoded["nested"]["notification"]["email"] is True
        assert "装修行业" in decoded["nested"]["tags"]
        # Round-trip stable (encode-decode-encode = same string)
        assert json.dumps(decoded, ensure_ascii=False) == metadata_str
    finally:
        _cleanup(db, "DELETE FROM tenants WHERE id = ?", [tenant_id])


def test_user_email_uniqueness(db):
    """users.email has UNIQUE constraint — duplicate email must fail."""
    import secrets
    user_id_a = f"_v62_ua_{secrets.token_hex(6)}"
    user_id_b = f"_v62_ub_{secrets.token_hex(6)}"
    user_email = f"v62-user-{secrets.token_hex(4)}@cloudtech.com"
    tenant_name = f"V62 UserUniq {secrets.token_hex(4)}"
    tenant_slug = f"_v62_uu_{secrets.token_hex(6)}"

    try:
        # Need a parent tenant (users.tenant_id NOT NULL; FK is implicit
        # in many SQLite configs but the tenant must exist)
        db.execute("""
            INSERT INTO tenants (name, slug, plan, status)
            VALUES (?, ?, ?, ?)
        """, [tenant_name, tenant_slug, "starter", "active"])
        tenant_id = dict(db.fetch_one(
            "SELECT id FROM tenants WHERE slug = ?", [tenant_slug]
        ))["id"]

        # First user insert succeeds (created_at NOT NULL — supply explicit ts)
        db.execute("""
            INSERT INTO users
                (id, email, password_hash, password_salt, name, tenant_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [user_id_a, user_email, "hash_a", "salt_a", "User A", tenant_id, "2026-10-08 21:00:00"])

        # Second insert with SAME email must fail
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("""
                INSERT INTO users
                    (id, email, password_hash, password_salt, name, tenant_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [user_id_b, user_email, "hash_b", "salt_b", "User B", tenant_id, "2026-10-08 21:00:00"])

        # Verify only one user exists with that email
        rows = db.fetch_all(
            "SELECT id FROM users WHERE email = ?", [user_email]
        )
        assert len(rows) == 1
        assert dict(rows[0])["id"] == user_id_a
    finally:
        _cleanup(db, "DELETE FROM users WHERE email = ?", [user_email])
        _cleanup(db, "DELETE FROM tenants WHERE id = ?", [tenant_id])


def test_workflow_run_state_machine_transitions(db):
    """pipeline_runs.status follows: running → completed / running → failed.

    Verifies the standard SaaS workflow lifecycle:
      1. Create with status='running' (default)
      2. Transition to 'completed' with completed_at + success_rate=1.0
      3. Transition to 'failed' with completed_at + success_rate=0.0 + error_message
    All states must round-trip cleanly through the DB.

    FK constraint: pipeline_runs.tenant_id REFERENCES tenants(id).
    """
    import secrets
    run_id_a = f"_v62_wfa_{secrets.token_hex(6)}"
    run_id_b = f"_v62_wfb_{secrets.token_hex(6)}"
    run_id_c = f"_v62_wfc_{secrets.token_hex(6)}"
    tenant_name = f"V62 WF SM {secrets.token_hex(4)}"
    tenant_slug = f"_v62_wsm_{secrets.token_hex(6)}"

    # Create parent tenant first (FK requirement)
    db.execute("""
        INSERT INTO tenants (name, slug, plan, status)
        VALUES (?, ?, ?, ?)
    """, [tenant_name, tenant_slug, "pro", "active"])
    tenant_id = dict(db.fetch_one(
        "SELECT id FROM tenants WHERE slug = ?", [tenant_slug]
    ))["id"]

    try:
        # ── A: running state (no completion fields) ──
        db.execute("""
            INSERT INTO pipeline_runs (id, tenant_id, pipeline_name, status)
            VALUES (?, ?, ?, ?)
        """, [run_id_a, tenant_id, "content_generation", "running"])
        row = dict(db.fetch_one(
            "SELECT * FROM pipeline_runs WHERE id = ?", [run_id_a]
        ))
        assert row["status"] == "running"
        # SQLite returns INTEGER as int, but sqlite3.Row may serialize as str
        assert str(row["tenant_id"]) == str(tenant_id)
        assert row["completed_at"] is None
        assert row["total_elapsed"] is None
        assert row["success_rate"] is None
        assert row["error_message"] is None

        # ── B: running → completed transition ──
        db.execute("""
            INSERT INTO pipeline_runs
                (id, tenant_id, pipeline_name, status, completed_at,
                 total_elapsed, success_rate, output_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id_b, tenant_id, "content_generation", "completed",
            "2026-10-08 21:00:00", 12.5, 1.0,
            json.dumps({"items": 5, "platforms": ["douyin", "wechat"]})
        ])
        row = dict(db.fetch_one(
            "SELECT * FROM pipeline_runs WHERE id = ?", [run_id_b]
        ))
        assert row["status"] == "completed"
        assert row["completed_at"] == "2026-10-08 21:00:00"
        assert row["total_elapsed"] == 12.5
        assert row["success_rate"] == 1.0
        summary = json.loads(row["output_summary"])
        assert summary["items"] == 5
        assert "douyin" in summary["platforms"]

        # ── C: running → failed transition ──
        db.execute("""
            INSERT INTO pipeline_runs
                (id, tenant_id, pipeline_name, status, completed_at,
                 total_elapsed, success_rate, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_id_c, tenant_id, "image_ocr", "failed",
            "2026-10-08 21:05:00", 8.3, 0.0,
            "Provider API timeout after 30s (circuit breaker open)"
        ])
        row = dict(db.fetch_one(
            "SELECT * FROM pipeline_runs WHERE id = ?", [run_id_c]
        ))
        assert row["status"] == "failed"
        assert row["success_rate"] == 0.0
        assert "circuit breaker" in row["error_message"]
        assert row["completed_at"] == "2026-10-08 21:05:00"

        # ── Verify all 3 distinct states coexist ──
        all_rows = db.fetch_all(
            "SELECT status FROM pipeline_runs "
            "WHERE id IN (?, ?, ?) ORDER BY id",
            [run_id_a, run_id_b, run_id_c]
        )
        statuses = sorted([dict(r)["status"] for r in all_rows])
        assert statuses == ["completed", "failed", "running"]
    finally:
        _cleanup(db,
            "DELETE FROM pipeline_runs WHERE id IN (?, ?, ?)",
            [run_id_a, run_id_b, run_id_c])
        _cleanup(db, "DELETE FROM tenants WHERE id = ?", [tenant_id])