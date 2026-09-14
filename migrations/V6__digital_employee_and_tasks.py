"""
V6__digital_employee_and_tasks
==============================
Phase 2-4 核心表：数字员工 + 任务系统 + 知识库 + 工作流 + 内容资产

执行时间：CloudTech v3.0 Phase1
创建者：Claude Code v3.0 Architecture
"""


def up(conn: sqlite3.Connection) -> None:
    # ══════════════════════════════════════════════════════════════════════
    # 数字员工核心 (digital_employees + employee_messages)
    # ══════════════════════════════════════════════════════════════════════

    conn.execute("""
        CREATE TABLE IF NOT EXISTS digital_employees (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            template_id TEXT NOT NULL,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '🤖',
            description TEXT,
            system_prompt TEXT NOT NULL DEFAULT '',
            bound_skills TEXT DEFAULT '[]',
            knowledge_base_ids TEXT DEFAULT '[]',
            default_model TEXT DEFAULT 'zhipu/glm-4-flash',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(tenant_id, template_id)
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_de_tenant
        ON digital_employees(tenant_id, is_active)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS employee_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant','system','tool')),
            content TEXT NOT NULL,
            meta TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (employee_id) REFERENCES digital_employees(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_em_employee_session
        ON employee_messages(employee_id, session_id, created_at)
    """)

    # ══════════════════════════════════════════════════════════════════════
    # 任务系统 (tasks + task_runs)
    # ══════════════════════════════════════════════════════════════════════

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            task_type TEXT NOT NULL
                CHECK(task_type IN ('skill','workflow','schedule','webhook','script')),
            status TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','running','completed','failed','cancelled')),
            priority INTEGER DEFAULT 0 CHECK(priority BETWEEN 0 AND 9),
            due_at TEXT,
            assigned_to TEXT,
            workflow_instance_id TEXT,
            context TEXT DEFAULT '{}',
            result TEXT,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_tenant_status
        ON tasks(tenant_id, status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_assigned
        ON tasks(assigned_to, status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_due
        ON tasks(tenant_id, due_at)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            run_index INTEGER NOT NULL,
            status TEXT NOT NULL
                CHECK(status IN ('running','completed','failed')),
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            duration_ms INTEGER,
            input TEXT,
            output TEXT,
            error TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tr_task
        ON task_runs(task_id, run_index)
    """)

    # ══════════════════════════════════════════════════════════════════════
    # 知识库 (knowledge_docs + knowledge_chunks)
    # ══════════════════════════════════════════════════════════════════════

    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_docs (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            title TEXT NOT NULL,
            doc_type TEXT NOT NULL
                CHECK(doc_type IN ('pdf','docx','txt','url','notion','html','md')),
            source_url TEXT,
            tag TEXT,
            status TEXT DEFAULT 'processing'
                CHECK(status IN ('processing','ready','failed')),
            chunk_count INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            meta TEXT DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_kd_tenant_status
        ON knowledge_docs(tenant_id, status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_kd_tag
        ON knowledge_docs(tenant_id, tag)
    """)

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

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_kc_doc
        ON knowledge_chunks(doc_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_kc_vector
        ON knowledge_chunks(vector_id)
    """)

    # ══════════════════════════════════════════════════════════════════════
    # 定时任务 (scheduled_tasks)
    # ══════════════════════════════════════════════════════════════════════

    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            name TEXT NOT NULL,
            task_type TEXT NOT NULL
                CHECK(task_type IN ('workflow','skill','script','http')),
            schedule_type TEXT NOT NULL
                CHECK(schedule_type IN ('cron','interval','once','daily','weekly')),
            schedule_value TEXT NOT NULL,
            payload TEXT NOT NULL DEFAULT '{}',
            is_enabled INTEGER DEFAULT 1,
            last_run_at TEXT,
            last_status TEXT
                CHECK(last_status IN ('success','failure','null')),
            last_run_id TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_st_tenant_enabled
        ON scheduled_tasks(tenant_id, is_enabled)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_st_next_run
        ON scheduled_tasks(next_run_at) WHERE is_enabled=1
    """)

    # ══════════════════════════════════════════════════════════════════════
    # 工作流 (workflow_definitions + workflow_instances)
    # ══════════════════════════════════════════════════════════════════════

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

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_wd_tenant
        ON workflow_definitions(tenant_id, is_active)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflow_instances (
            id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            definition_id TEXT NOT NULL,
            definition_version INTEGER NOT NULL,
            status TEXT DEFAULT 'running'
                CHECK(status IN ('running','waiting','completed','rejected',
                                 'cancelled','error','timed_out')),
            current_node_id TEXT,
            context TEXT DEFAULT '{}',
            result TEXT,
            error TEXT,
            started_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            FOREIGN KEY (definition_id)
                REFERENCES workflow_definitions(id) ON DELETE RESTRICT
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_wi_tenant_status
        ON workflow_instances(tenant_id, status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_wi_definition
        ON workflow_instances(definition_id)
    """)

    # ══════════════════════════════════════════════════════════════════════
    # 内容资产 (content_assets)
    # ══════════════════════════════════════════════════════════════════════

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

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ca_tenant_type
        ON content_assets(tenant_id, asset_type)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ca_tag
        ON content_assets(tenant_id, tag)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ca_workflow
        ON content_assets(workflow_run_id)
    """)

    # ══════════════════════════════════════════════════════════════════════
    # 技能定义表 (skill_definitions)
    # ══════════════════════════════════════════════════════════════════════

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

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sd_tenant_category
        ON skill_definitions(tenant_id, category, is_active)
    """)

    conn.commit()
    print("  ✅ V6: digital_employee, tasks, knowledge, workflow, content_assets, skill_definitions created")


# 显式导入sqlite3（migration_runner.py已导入，但直接执行时需要）
import sqlite3
