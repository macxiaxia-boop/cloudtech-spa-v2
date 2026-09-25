"""
V7__sync_domain_schema
=======================
在 pipeline.db (实际运行数据库) 上同步 v3.0 Domain schema。

问题：V6在cloudtech.db上创建了新表，但Flask实际用的是pipeline.db。
pipeline.db已有digital_employees（旧版缺列），需要ALTER TABLE补充。

执行时间：CloudTech v3.0 Phase3
"""
import sqlite3


def _add_column_if_not_exists(conn, table, column, col_def):
    """安全添加列（如果不存在）"""
    existing = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")


def up(conn: sqlite3.Connection) -> None:
    # ── digital_employees: 补充v3.0新列 ──
    _add_column_if_not_exists(conn, "digital_employees", "template_id", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_not_exists(conn, "digital_employees", "description", "TEXT")
    _add_column_if_not_exists(conn, "digital_employees", "system_prompt", "TEXT NOT NULL DEFAULT ''")
    _add_column_if_not_exists(conn, "digital_employees", "bound_skills", "TEXT DEFAULT '[]'")
    _add_column_if_not_exists(conn, "digital_employees", "knowledge_base_ids", "TEXT DEFAULT '[]'")
    _add_column_if_not_exists(conn, "digital_employees", "default_model", "TEXT DEFAULT 'deepseek-v4-flash'")
    _add_column_if_not_exists(conn, "digital_employees", "is_active", "INTEGER DEFAULT 1")

    # ── employee_messages: 新增列 ──
    try:
        _add_column_if_not_exists(conn, "employee_messages", "session_id", "TEXT NOT NULL")
        _add_column_if_not_exists(conn, "employee_messages", "meta", "TEXT DEFAULT '{}'")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_em_employee_session
            ON employee_messages(employee_id, session_id, created_at)
        """)
    except sqlite3.OperationalError:
        pass  # 表可能不存在或已有索引

    # ── task_runs ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            run_index INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('running','completed','failed')),
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            duration_ms INTEGER,
            input TEXT,
            output TEXT,
            error TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tr_task ON task_runs(task_id, run_index)")

    # ── knowledge_chunks ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            token_count INTEGER DEFAULT 0,
            vector_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (doc_id) REFERENCES knowledge_docs(id) ON DELETE CASCADE,
            UNIQUE(doc_id, chunk_index)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kc_doc ON knowledge_chunks(doc_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_kc_vector ON knowledge_chunks(vector_id)")

    # ── workflow_definitions ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflow_definitions (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            definition TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(tenant_id, name, version)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wd_tenant ON workflow_definitions(tenant_id, is_active)")

    # ── workflow_instances ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflow_instances (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            definition_id TEXT NOT NULL,
            definition_version INTEGER NOT NULL,
            status TEXT DEFAULT 'running'
                CHECK(status IN ('running','waiting','completed','rejected','cancelled','error','timed_out')),
            current_node_id TEXT,
            context TEXT DEFAULT '{}',
            result TEXT,
            error TEXT,
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wi_tenant_status ON workflow_instances(tenant_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wi_definition ON workflow_instances(definition_id)")

    # ── content_assets ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_assets (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            asset_type TEXT NOT NULL
                CHECK(asset_type IN ('video','image','audio','document','other')),
            title TEXT NOT NULL,
            file_path TEXT,
            file_size INTEGER,
            mime_type TEXT,
            metadata TEXT DEFAULT '{}',
            source_platform TEXT,
            source_url TEXT,
            workflow_run_id TEXT,
            tag TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_tenant_type ON content_assets(tenant_id, asset_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_tag ON content_assets(tenant_id, tag)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_workflow ON content_assets(workflow_run_id)")

    # ── skill_definitions ──
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_definitions (
            name TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            description TEXT NOT NULL,
            version TEXT DEFAULT '1.0.0',
            category TEXT DEFAULT '通用',
            handler TEXT,
            params TEXT DEFAULT '[]',
            body TEXT,
            source_file TEXT,
            is_builtin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(tenant_id, name)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sd_tenant_category ON skill_definitions(tenant_id, category, is_active)")

    conn.commit()
    print("  ✅ V7: synced digital_employees columns + created missing tables")
