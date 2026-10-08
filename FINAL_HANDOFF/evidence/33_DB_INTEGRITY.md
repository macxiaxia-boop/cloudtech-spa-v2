# V6.2 DB INTEGRITY — 5 CloudTech Edge Case Tests

**Date**: 2026-10-08T21:45:00+08:00
**Author**: Codex sub-agent #73 (Shannon)
**File created**: `tests/test_db_integration.py` (NEW, 13.3 KB, 5 tests)
**Verification**: `pytest tests/test_db_integration.py -q` → **5/5 PASS**

---

## What was added

5 new database integrity tests targeting the **production V2 schema**
in `data/cloudtech.db`. Each test inserts real rows with `_v62_` prefix
in IDs/slugs so they can be cleaned up without touching customer data.

### Tests added

| # | Test name | What it covers | V2 schema constraint |
|---|-----------|----------------|----------------------|
| 1 | `test_tenant_create_with_all_fields` | Insert tenant with every column populated, verify round-trip | `tenants.plan CHECK (free\|starter\|pro\|enterprise)`, `tenants.slug UNIQUE` |
| 2 | `test_tenant_unique_id_enforcement` | Two tenants with same PRIMARY KEY → IntegrityError; same slug → IntegrityError | `tenants.id INTEGER PK`, `tenants.slug UNIQUE` |
| 3 | `test_tenant_metadata_json_serialization` | settings_json preserves CJK + emoji + nested dicts + arrays (no `\u` escape artifacts) | `tenants.settings_json TEXT NOT NULL` |
| 4 | `test_user_email_uniqueness` | Two users with same email → IntegrityError | `users.email UNIQUE NOT NULL`, `users.tenant_id NOT NULL`, `users.password_salt NOT NULL`, `users.created_at NOT NULL` |
| 5 | `test_workflow_run_state_machine_transitions` | running → completed / running → failed with all completion fields | `pipeline_runs.tenant_id FK → tenants.id`, `pipeline_runs.status TEXT` |

---

## Test run output (machine-verified)

```
$ cd D:\CloudTech-Portable && python -m pytest tests/test_db_integration.py --tb=short -q
.....                                                                    [100%]
5 passed in 0.13s
```

Breakdown:
- `test_tenant_create_with_all_fields` ✓ (plan='enterprise', settings_json with 厦门)
- `test_tenant_unique_id_enforcement` ✓ (negative IDs avoid AUTOINCREMENT collisions)
- `test_tenant_metadata_json_serialization` ✓ (装修老板 👷 测试 preserved raw UTF-8)
- `test_user_email_uniqueness` ✓ (parent tenant created first for FK)
- `test_workflow_run_state_machine_transitions` ✓ (3 distinct states coexist)

---

## Schema constraints discovered (live introspection)

```
=== tenants ===
id            INTEGER PRIMARY KEY AUTOINCREMENT,
name          TEXT    NOT NULL UNIQUE,
slug          TEXT    NOT NULL UNIQUE,
plan          TEXT    NOT NULL DEFAULT 'free'
              CHECK (plan IN ('free','starter','pro','enterprise')),
status        TEXT    NOT NULL DEFAULT 'active'
              CHECK (status IN ('active','suspended','archived')),
owner_user_id INTEGER,
settings_json TEXT    NOT NULL DEFAULT '{}',
created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP

=== users ===
id TEXT PRIMARY KEY,
email TEXT UNIQUE NOT NULL,
name TEXT,
password_hash TEXT NOT NULL,
password_salt TEXT NOT NULL,           ← must supply
tenant_id TEXT NOT NULL,                ← FK to tenants(id) (implicit via app)
industry TEXT DEFAULT 'decoration',
role TEXT DEFAULT 'user',
created_at TEXT NOT NULL,               ← must supply
last_login_at TEXT,
plan TEXT DEFAULT 'free',
is_active INTEGER DEFAULT 1

=== pipeline_runs ===
id TEXT PRIMARY KEY,
tenant_id TEXT REFERENCES tenants(id),  ← FK enforced
pipeline_name TEXT NOT NULL,
status TEXT DEFAULT 'running',
started_at TEXT NOT NULL DEFAULT (datetime('now')),
completed_at TEXT,
total_elapsed REAL,
success_rate REAL,
error_message TEXT,
output_summary TEXT
```

Key constraint: **plan CHECK** — original draft used 'business' which
silently failed until live run revealed it. Now tests use 'enterprise'
as the highest valid plan.

---

## Cleanup guarantee

All tests use `try/finally` with `_cleanup()` to DELETE inserted rows,
even on assertion failure. IDs/slugs prefixed with `_v62_` ensure no
collision with production data. If a test crashes mid-execution, the
test order is **independent** (no shared state) — pytest-xdist safe.

Sample cleanup verification:
```python
# Test 5 leaves the DB with:
# - 1 tenant (slug: _v62_wsm_xxxxxx)
# - 3 pipeline_runs (id: _v62_wfa/b/c_xxxxxx)
# After finally clause: 0 rows remain.
```

---

## Why these specific tests

1. **Full-column round-trip** — Catches schema drift between migrations
   and live DB (we found V1 schema in migrations, V2 schema in live DB).
   A future schema change should still keep this test passing.

2. **PK + UNIQUE enforcement** — These are SQLite's last-line-of-defense
   data integrity guards. Test confirms they're active and behaving as
   expected (not silently swallowed by app code).

3. **JSON serialization** — settings_json is the canonical place to
   store tenant preferences. CJK + emoji round-trip without escaping
   matters for the dashboard UI (which reads this field).

4. **Email uniqueness** — Two users signing up with same email is the
   most common production data error. Test enforces the DB-level
   uniqueness constraint, complementing the app-level dedup.

5. **State machine** — Every workflow in CloudTech goes through
   pipeline_runs. The state transitions (running → completed / failed)
   are critical for billing (success_rate drives quota usage) and
   observability (status drives the admin dashboard).

---

## Out-of-scope (NOT covered)

- Concurrent INSERT (would need multi-threading; tested separately in
  test_integration.py::test_concurrent_tenant_ops)
- PostgreSQL compatibility (only SQLite tested; production uses both)
- Large BLOB / CLOB handling
- Disk-full / quota-exhausted failure modes
- WAL checkpoint behavior under high concurrency

---

## Combined with Item 1

```
$ pytest tests/test_models.py tests/test_db_integration.py -q
..................                                                       [100%]
18 passed in 0.53s
```

This turn total: **+10 PASS** (5 email edge + 5 DB integrity), 0 FAIL, 0 SKIP.

---

**Sign-off**: Codex sub-agent #73 (Shannon) completed V6.2 Item 2.
All 5 database integrity tests pass against production V2 schema.
Constraint discovery documented for future maintainers.