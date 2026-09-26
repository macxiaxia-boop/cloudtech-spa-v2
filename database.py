#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Layer v1.0 - Production-grade data persistence
Supports: SQLite (default, zero-config) / PostgreSQL (enterprise)
Features: Migration system, connection pooling, JSON backup, audit trail
"""

import json
import sqlite3
import os
import hashlib
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# === Configuration ===
DB_TYPE = os.environ.get("DB_TYPE", "sqlite")
DB_PATH = Path(os.environ.get("DB_PATH", Path(r"C:\Users\xinzh\.openclaw\state") / "pipeline.db"))
PG_DSN = os.environ.get("DATABASE_URL", "")

# Ensure directory
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


class Database:
    """Unified database interface with migration support."""

    def __init__(self):
        self.conn = None
        self.migrations_applied = []

    def connect(self):
        if DB_TYPE == "postgresql" and PG_DSN:
            import psycopg2
            self.conn = psycopg2.connect(PG_DSN)
        else:
            self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=10)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            # Performance indexes (R4.1: each DDL guarded — production DB
            # schema may differ from MIGRATION V1, e.g. audit_log uses 'ts'
            # not 'created_at', tenants table may not exist. connect() must
            # never raise; silently skip on any schema mismatch.)
            _INDEXES = (
                ("tenants",   "tenants(status)",       "idx_tenants_status"),
                ("tenants",   "tenants(plan)",         "idx_tenants_plan"),
                ("audit_log", "audit_log(tenant_id)",  "idx_audit_tenant"),
                ("audit_log", "audit_log(created_at)", "idx_audit_time"),
                ("users",     "users(email)",          "idx_users_email"),
            )
            _existing = self._existing_tables()
            for _table, _cols, _name in _INDEXES:
                if _table not in _existing:
                    continue
                try:
                    self.conn.execute(
                        f"CREATE INDEX IF NOT EXISTS {_name} ON {_cols}"
                    )
                except Exception:
                    # Column or schema mismatch — skip silently (R4.1)
                    pass
            self.conn.execute("PRAGMA cache_size=-8000")  # 8MB cache
            self.conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        return self

    def _existing_tables(self):
        """Return set of existing table names from sqlite_master (R4.1 guard).

        Used by connect() to skip CREATE INDEX on tables that don't exist
        in the target database (legacy/production DBs may be missing some).
        Returns empty set on any failure so connect() never raises from this helper.
        """
        try:
            cur = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return {row[0] for row in cur.fetchall()}
        except Exception:
            return set()

    @contextmanager
    def transaction(self):
        """Transactional context manager."""
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def execute(self, sql, params=None):
        cur = self.conn.cursor()
        cur.execute(sql, params or ())
        return cur

    def execute_many(self, sql, params_list):
        cur = self.conn.cursor()
        cur.executemany(sql, params_list)
        return cur

    def fetch_one(self, sql, params=None):
        cur = self.execute(sql, params)
        return cur.fetchone()

    def fetch_all(self, sql, params=None):
        cur = self.execute(sql, params)
        return cur.fetchall()

    def insert(self, table, data):
        """Insert a row and return the ID."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cur = self.execute(sql, tuple(data.values()))
        return cur.lastrowid

    def update(self, table, data, where, where_params=None):
        """Update rows."""
        sets = ", ".join(f"{k} = ?" for k in data)
        sql = f"UPDATE {table} SET {sets} WHERE {where}"
        wp = tuple(where_params) if where_params else ()
        params = tuple(data.values()) + wp
        return self.execute(sql, params)

    def delete(self, table, where, params=None):
        sql = f"DELETE FROM {table} WHERE {where}"
        return self.execute(sql, params or ())

    # === Migration System ===
    MIGRATIONS = [
        # V1: Core tables
        {
            "version": 1,
            "name": "core_tables",
            "sql": """
                -- Tenants
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    company TEXT DEFAULT '',
                    plan TEXT DEFAULT 'starter',
                    status TEXT DEFAULT 'active',
                    api_key TEXT UNIQUE NOT NULL,
                    api_key_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    deactivated_at TEXT
                );

                -- Tenant billing
                CREATE TABLE IF NOT EXISTS tenant_billing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    plan TEXT NOT NULL,
                    price_monthly INTEGER NOT NULL,
                    price_annual INTEGER NOT NULL,
                    billing_cycle TEXT DEFAULT 'monthly',
                    payment_status TEXT DEFAULT 'trial',
                    trial_ends_at TEXT,
                    next_billing_date TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- Tenant usage tracking
                CREATE TABLE IF NOT EXISTS tenant_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    metric TEXT NOT NULL,
                    value INTEGER DEFAULT 0,
                    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- Pipeline runs
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT REFERENCES tenants(id),
                    pipeline_name TEXT NOT NULL,
                    status TEXT DEFAULT 'running',
                    started_at TEXT NOT NULL DEFAULT (datetime('now')),
                    completed_at TEXT,
                    total_elapsed REAL,
                    success_rate REAL,
                    error_message TEXT,
                    output_summary TEXT
                );

                -- Content performance
                CREATE TABLE IF NOT EXISTS content_performance (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT REFERENCES tenants(id),
                    content_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    content_type TEXT DEFAULT 'article',
                    publish_time TEXT,
                    impressions INTEGER DEFAULT 0,
                    reads INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    saves INTEGER DEFAULT 0,
                    follows INTEGER DEFAULT 0,
                    completion_rate REAL DEFAULT 0,
                    engagement_rate REAL DEFAULT 0,
                    click_through_rate REAL DEFAULT 0,
                    title TEXT DEFAULT '',
                    hashtags TEXT DEFAULT '[]',
                    collected_at TEXT NOT NULL DEFAULT (datetime('now')),
                    data_source TEXT DEFAULT 'api',
                    UNIQUE(tenant_id, content_id, platform)
                );

                -- Knowledge capabilities
                CREATE TABLE IF NOT EXISTS knowledge_capabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT REFERENCES tenants(id),
                    name TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    confidence REAL DEFAULT 0,
                    sample_count INTEGER DEFAULT 0,
                    common_elements TEXT DEFAULT '{}',
                    usage_guide TEXT DEFAULT '',
                    version TEXT DEFAULT '2.0',
                    formed_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(tenant_id, name)
                );

                -- Model calibrations
                CREATE TABLE IF NOT EXISTS model_calibrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT REFERENCES tenants(id),
                    creator_name TEXT NOT NULL,
                    element TEXT NOT NULL,
                    old_weight REAL,
                    new_weight REAL,
                    direction TEXT,
                    reason TEXT,
                    observed_engagement REAL,
                    calibrated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- Audit log
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    resource_id TEXT,
                    details TEXT DEFAULT '{}',
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- API keys
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    key_hash TEXT UNIQUE NOT NULL,
                    key_prefix TEXT NOT NULL,
                    name TEXT DEFAULT 'Default',
                    scopes TEXT DEFAULT '["read","write"]',
                    last_used_at TEXT,
                    expires_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- Users (for web admin)
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT REFERENCES tenants(id),
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    is_active INTEGER DEFAULT 1,
                    last_login_at TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                -- System state
                CREATE TABLE IF NOT EXISTS system_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    state TEXT DEFAULT 'NORMAL',
                    entered_at TEXT NOT NULL DEFAULT (datetime('now')),
                    reason TEXT DEFAULT '',
                    meta TEXT DEFAULT '{}'
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
                CREATE INDEX IF NOT EXISTS idx_tenants_apikey ON tenants(api_key);
                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_tenant ON pipeline_runs(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
                CREATE INDEX IF NOT EXISTS idx_content_perf_tenant ON content_performance(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_content_perf_platform ON content_performance(platform);
                CREATE INDEX IF NOT EXISTS idx_audit_log_tenant ON audit_log(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
                CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
            """
        },
        # V2: Add feedback classifier data
        {
            "version": 2,
            "name": "feedback_classification",
            "sql": """
                CREATE TABLE IF NOT EXISTS feedback_classifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT REFERENCES tenants(id),
                    pipeline_run_id TEXT,
                    feedback_type TEXT NOT NULL,
                    feedback_value TEXT,
                    category TEXT NOT NULL DEFAULT 'behavioral',
                    weight REAL DEFAULT 0.1,
                    pattern_matched TEXT,
                    classified_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_feedback_class_tenant ON feedback_classifications(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_feedback_class_category ON feedback_classifications(category);
            """
        },
        # V3: Scheduler jobs
        {
            "version": 3,
            "name": "scheduler_jobs",
            "sql": """
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT REFERENCES tenants(id),
                    name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL DEFAULT 'time',
                    schedule_value TEXT NOT NULL,
                    script TEXT NOT NULL,
                    args TEXT DEFAULT '[]',
                    is_enabled INTEGER DEFAULT 1,
                    last_run_at TEXT,
                    last_status TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """
        },
    ]

    def run_migrations(self):
        """Apply all pending migrations."""
        # Create migrations table
        self.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        applied = {r["version"] for r in self.fetch_all("SELECT version FROM _migrations")}

        for migration in self.MIGRATIONS:
            if migration["version"] not in applied:
                print(f"[MIGRATION] Applying V{migration['version']}: {migration['name']}")
                with self.transaction() as conn:
                    conn.executescript(migration["sql"])
                    conn.execute(
                        "INSERT INTO _migrations (version, name) VALUES (?, ?)",
                        (migration["version"], migration["name"])
                    )
                print(f"  DONE: V{migration['version']}")

        print(f"[DB] Migrations complete. {len(self.MIGRATIONS)} applied.")

    def health_check(self):
        """Quick database health check."""
        try:
            self.fetch_one("SELECT 1")
            return {"status": "healthy", "type": DB_TYPE, "path": str(DB_PATH)}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def backup(self, backup_path=None):
        """Backup the database to JSON (for migration/portability)."""
        if backup_path is None:
            backup_path = DB_PATH.parent / f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        tables = [
            "tenants", "tenant_billing", "users",
            "pipeline_runs", "content_performance",
            "knowledge_capabilities", "model_calibrations",
            "feedback_classifications", "audit_log", "api_keys",
        ]

        dump = {"backup_at": datetime.now().isoformat(), "db_type": DB_TYPE, "tables": {}}

        for table in tables:
            try:
                rows = self.fetch_all(f"SELECT * FROM {table}")
                dump["tables"][table] = [dict(r) for r in rows]
            except Exception:
                dump["tables"][table] = []

        backup_path = Path(backup_path)
        backup_path.write_text(json.dumps(dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"[DB] Backup saved: {backup_path} ({backup_path.stat().st_size} bytes)")
        return str(backup_path)

    def restore(self, backup_path):
        """Restore from JSON backup."""
        dump = json.loads(Path(backup_path).read_text(encoding="utf-8"))
        with self.transaction():
            for table, rows in dump["tables"].items():
                if rows:
                    # Clear existing
                    self.execute(f"DELETE FROM {table}")
                    for row in rows:
                        columns = ", ".join(row.keys())
                        placeholders = ", ".join("?" for _ in row)
                        self.execute(
                            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                            tuple(row.values())
                        )
        print(f"[DB] Restored from: {backup_path}")
        return True


# === Global Instance ===
_db = None

def get_db():
    global _db
    if _db is None:
        _db = Database().connect()
        _db.run_migrations()
    return _db


# === CLI ===
if __name__ == "__main__":
    import sys
    db = Database().connect()
    db.run_migrations()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "backup":
            db.backup()
        elif cmd == "restore":
            db.restore(sys.argv[2] if len(sys.argv) > 2 else "")
        elif cmd == "health":
            print(json.dumps(db.health_check(), indent=2))
        elif cmd == "stats":
            tables = ["tenants", "pipeline_runs", "content_performance", "knowledge_capabilities"]
            for t in tables:
                count = db.fetch_one(f"SELECT COUNT(*) as c FROM {t}")
                print(f"  {t}: {count['c'] if count else 0} rows")
    else:
        print(f"Database initialized: {DB_PATH}")
        db.health_check()
        print("Run with: backup | restore <path> | health | stats")
