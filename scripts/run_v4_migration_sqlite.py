"""V4 — SQLite migration (Docker 没跑时的 fallback)
不依赖 Postgres; CloudTech 已有 SQLite 默认 dev 模式
按红线 #22 #60: 本地 SQLite 不算不可逆, 用户随时可删
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = Path("D:/AIOS/_workzone/cloudtech_v4_dev.db")


def main():
    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()
        print(f"[SQLITE] 删旧 db: {SQLITE_PATH}")
    conn = sqlite3.connect(str(SQLITE_PATH))
    cur = conn.cursor()

    # 11 张表 (简化 pg_v4_migration.sql, SQLite 兼容版)
    DDL = [
        """CREATE TABLE workpath_definition (
            id TEXT PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 1,
            domain TEXT NOT NULL, title TEXT NOT NULL, goal TEXT NOT NULL,
            triggers_json TEXT NOT NULL DEFAULT '[]',
            preconditions_json TEXT NOT NULL DEFAULT '[]',
            planner TEXT NOT NULL DEFAULT 'default',
            steps_json TEXT NOT NULL DEFAULT '[]',
            quality_gates_json TEXT NOT NULL DEFAULT '[]',
            exported_artifacts_json TEXT NOT NULL DEFAULT '[]',
            recovery_json TEXT NOT NULL DEFAULT '{}',
            privacy_class TEXT NOT NULL DEFAULT 'public',
            permissions_json TEXT NOT NULL DEFAULT '[]',
            billing_policy TEXT NOT NULL DEFAULT 'FREE_LOCAL',
            evidence_template TEXT NOT NULL DEFAULT '{}',
            version_hash TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE workpath_run (
            id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT,
            conversation_id TEXT, path_id TEXT NOT NULL, path_revision INTEGER NOT NULL,
            input_bindings_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'PLANNED',
            scope TEXT NOT NULL DEFAULT 'tenant',
            budget_cap_cents INTEGER NOT NULL DEFAULT 0,
            budget_spent_cents INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT UNIQUE,
            last_node_id TEXT, error_code TEXT, error_message TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE workflow_node_run (
            id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
            node_id TEXT NOT NULL, node_kind TEXT NOT NULL,
            operation TEXT NOT NULL, requires_json TEXT,
            produces_json TEXT, input_hash TEXT NOT NULL,
            output_ref TEXT, provider_req_id TEXT,
            provider_name TEXT, retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,
            status TEXT NOT NULL DEFAULT 'PENDING',
            cost_cents INTEGER NOT NULL DEFAULT 0,
            cost_class TEXT NOT NULL DEFAULT 'FREE_LOCAL',
            error_code TEXT, error_message TEXT,
            started_at TEXT, finished_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES workpath_run(id)
        )""",
        """CREATE TABLE asset_role_binding (
            id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT,
            conversation_id TEXT NOT NULL, alias TEXT NOT NULL,
            role TEXT NOT NULL, asset_id TEXT NOT NULL,
            version_id TEXT NOT NULL, message_id TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE alias_snapshot (
            id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
            message_id TEXT NOT NULL, alias TEXT NOT NULL,
            asset_id TEXT NOT NULL, version_id TEXT NOT NULL,
            snapshot_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE budget_reservation (
            id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, run_id TEXT NOT NULL,
            node_id TEXT, cost_class TEXT NOT NULL,
            reserved_cents INTEGER NOT NULL, settled_cents INTEGER NOT NULL DEFAULT 0,
            released_cents INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'reserved',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            settled_at TEXT
        )""",
        """CREATE TABLE content_source (
            id TEXT PRIMARY KEY, asset_id TEXT NOT NULL,
            source_platform TEXT, source_url TEXT,
            source_author TEXT, source_time TEXT,
            retrieval_policy TEXT, rights_status TEXT NOT NULL DEFAULT 'unknown',
            extraction_method TEXT, reference_ids TEXT,
            version_hash TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE derivative_lineage (
            id TEXT PRIMARY KEY, derivative_asset_id TEXT NOT NULL,
            source_asset_id TEXT, parent_run_id TEXT,
            operation TEXT NOT NULL, similarity_score REAL,
            notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE provider_usage (
            id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            run_id TEXT, node_id TEXT,
            provider_name TEXT NOT NULL, operation TEXT NOT NULL,
            cost_cents INTEGER NOT NULL DEFAULT 0,
            cost_class TEXT NOT NULL,
            external_request_id TEXT, input_hash TEXT,
            started_at TEXT, finished_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending', error_code TEXT
        )""",
        """CREATE TABLE approvals (
            id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL, approver_user_id TEXT,
            decision TEXT NOT NULL,
            approved_budget_cents INTEGER,
            notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE audit_evidence (
            id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
            node_id TEXT, evidence_kind TEXT NOT NULL,
            payload_json TEXT NOT NULL, evidence_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    for sql in DDL:
        cur.execute(sql)
    conn.commit()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    print(f"[SQLITE] ✅ 创建 {len(tables)} 张表: {tables}")
    print(f"[SQLITE] path: {SQLITE_PATH}")


if __name__ == "__main__":
    main()
