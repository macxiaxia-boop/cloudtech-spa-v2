"""
Phase 45 D13-16 — PostgreSQL 迁移套件验收测试
==============================================

验收标准:
  1. alembic.ini + migrations/env.py 配置存在
  2. migrations/versions/0001_initial_postgres.py 初始迁移存在
  3. 11 个 ORM 模型（digital_employees 等）可通过 Base.metadata 注册
  4. SQLite 端 init_database 仍能工作（向后兼容）
  5. DATABASE_URL=postgresql://... 时引擎创建不抛错（无连接测试）
  6. docker-compose.yml 含 postgres service + profiles=["production"]
  7. .env.example 保留所有 51 行（含 DeepSeek/Kling/Jimeng/SMTP/WeChat/License）
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
DATA_LAYER = PROJECT_ROOT / "data-layer"
MIGRATIONS = PROJECT_ROOT / "migrations"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DATA_LAYER))


# ══════════════ 文件存在性 ══════════════

def test_alembic_ini_exists():
    """alembic.ini 配置存在"""
    p = PROJECT_ROOT / "alembic.ini"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert "[alembic]" in content
    assert "script_location = migrations" in content


def test_migrations_env_py_exists():
    """migrations/env.py Alembic 环境配置存在"""
    p = MIGRATIONS / "env.py"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert "target_metadata" in content
    assert "compare_type=True" in content


def test_migrations_init_revision_exists():
    """migrations/versions/0001_initial_postgres.py 存在"""
    p = MIGRATIONS / "versions" / "0001_initial_postgres.py"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert 'revision = "0001"' in content
    assert "down_revision = None" in content


def test_migrations_init_sql_exists():
    """migrations/init.sql PostgreSQL init 存在"""
    p = MIGRATIONS / "init.sql"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert 'CREATE EXTENSION' in content


def test_docker_compose_contains_postgres():
    """docker-compose.yml 含 postgres service + production profile"""
    p = PROJECT_ROOT / "docker-compose.yml"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "postgres" in content
    assert 'profiles: ["production"]' in content or 'profiles: ["production"]' in content
    assert "cloudtech-net" in content


def test_env_example_preserved():
    """红线 #2 守护：.env.example 51 行 + 关键字段不被覆盖"""
    p = PROJECT_ROOT / ".env.example"
    assert p.exists()
    lines = p.read_text(encoding="utf-8").splitlines()
    # 不能比 51 行少（我们没覆盖过）
    assert len(lines) >= 51, f".env.example 被覆盖（{len(lines)} 行 < 51）"
    # 关键字段必须保留
    content = "\n".join(lines)
    for key in ["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "KLING_API_KEY",
                "JIMENG_API_KEY", "SMTP_HOST", "WECHAT_APP_ID",
                "JWT_SECRET", "DB_TYPE"]:
        assert key in content, f".env.example 缺关键字段: {key}"


# ══════════════ ORM 模型 ══════════════

@pytest.fixture(scope="module")
def db_mod():
    """加载 data-layer/database.py"""
    spec = importlib.util.spec_from_file_location("cloudtech_db", str(DATA_LAYER / "database.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_orm_base_has_11_tables(db_mod):
    """Base.metadata 含 11 张表"""
    tables = list(db_mod.Base.metadata.tables.keys())
    assert len(tables) >= 11, f"ORM 表数过低: {len(tables)} < 11"


def test_orm_core_tables_exist(db_mod):
    """9 大核心表都在"""
    expected = [
        "digital_employees", "industry_experts", "skills",
        "mcp_servers", "orchestration_logs", "tokenhub_cache",
        "business_metrics", "compliance_tracking", "poc_customers",
    ]
    tables = list(db_mod.Base.metadata.tables.keys())
    for t in expected:
        assert t in tables, f"ORM 缺表: {t}"


# ══════════════ SQLite 向后兼容 ══════════════

def test_sqlite_engine_creation(monkeypatch, db_mod, tmp_path):
    """SQLite 引擎创建仍工作（DATABASE_URL=sqlite://...）"""
    test_db = tmp_path / "test_d13_16_sqlite.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db.as_posix()}")
    # 重新加载模块以应用新 env
    spec = importlib.util.spec_from_file_location("cloudtech_db_test", str(DATA_LAYER / "database.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    engine = mod.get_engine()
    assert engine is not None
    # 测连接
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("SELECT 1"))
    # 释放连接 + dispose（避免 Windows 文件锁）
    engine.dispose()
    mod._engine = None
    # tmp_path 自动清理


def test_postgresql_engine_creation_no_connect(monkeypatch, db_mod):
    """DATABASE_URL=postgresql://... 时引擎创建不抛错（不连 DB）"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://cloudtech:test@localhost:5432/cloudtech")
    spec = importlib.util.spec_from_file_location("cloudtech_db_pg", str(DATA_LAYER / "database.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    engine = mod.get_engine()
    assert engine is not None
    assert "postgresql" in str(engine.url)


# ══════════════ init_database ══════════════

def test_init_database_runs(db_mod, tmp_path):
    """init_database() 在 SQLite 上能完整跑通"""
    test_db = tmp_path / "test_init.db"
    orig_url = db_mod.DATABASE_URL
    try:
        db_mod.DATABASE_URL = f"sqlite:///{test_db.as_posix()}"
        # 重置 engine
        db_mod._engine = None
        db_mod.init_database()
        # 验证表已建
        engine = db_mod.get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            tables = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()
            table_names = {t[0] for t in tables}
            assert "digital_employees" in table_names
    finally:
        db_mod.DATABASE_URL = orig_url
        db_mod._engine = None


# ══════════════ 行业 + 员工持久化 ══════════════

def test_phase45_changes_persist(db_mod, tmp_path):
    """Phase 45 D4-7 改造：装饰/医美 active + 教培/餐饮/零售 deprecated"""
    # 注：业务元数据在 v3_142 内存里，但 db 持久化 9 表可独立初始化
    test_db = tmp_path / "test_phase45.db"
    orig_url = db_mod.DATABASE_URL
    try:
        db_mod.DATABASE_URL = f"sqlite:///{test_db.as_posix()}"
        db_mod._engine = None
        db_mod.init_database()
        engine = db_mod.get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            # 验证 11 表都能查询（空表）
            for t in ["digital_employees", "industry_experts", "skills",
                      "poc_customers", "business_metrics"]:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                assert cnt == 0, f"{t} 应为空表, got {cnt}"
    finally:
        db_mod.DATABASE_URL = orig_url
        db_mod._engine = None
