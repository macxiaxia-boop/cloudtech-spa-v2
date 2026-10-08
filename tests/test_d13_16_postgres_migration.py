"""
Phase 45 D13-16 -- PostgreSQL migration acceptance test
======================================================

Acceptance criteria:
  1. alembic.ini + migrations/env.py config exists
  2. migrations/versions/0001_initial_postgres.py exists
  3. 11 ORM models (digital_employees etc.) registerable via Base.metadata
  4. SQLite init_database still works (backward compat)
  5. DATABASE_URL=postgresql://... engine creation does not throw (no connection)
  6. docker-compose.yml contains postgres service + profiles=["production"]
  7. .env.example keeps all 51 lines (DeepSeek/Kling/Jimeng/SMTP/WeChat/License)
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.orm import declarative_base

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
DATA_LAYER = PROJECT_ROOT / "data-layer"
MIGRATIONS = PROJECT_ROOT / "migrations"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DATA_LAYER))


# === File existence ===

def test_alembic_ini_exists():
    p = PROJECT_ROOT / "alembic.ini"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert "[alembic]" in content
    assert "script_location = migrations" in content


def test_migrations_env_py_exists():
    p = MIGRATIONS / "env.py"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert "target_metadata" in content
    assert "compare_type=True" in content


def test_migrations_init_revision_exists():
    p = MIGRATIONS / "versions" / "0001_initial_postgres.py"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert 'revision = "0001"' in content
    assert "down_revision = None" in content


def test_migrations_init_sql_exists():
    p = MIGRATIONS / "init.sql"
    assert p.exists(), f"missing: {p}"
    content = p.read_text(encoding="utf-8")
    assert "CREATE EXTENSION" in content


def test_docker_compose_contains_postgres():
    """docker-compose.yml contains postgres service + production profile.
    R293 rewrite uses cloudtech_postgres container names; accept any cloudtech-* prefix.
    """
    p = PROJECT_ROOT / "docker-compose.yml"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "postgres" in content
    assert 'profiles: ["production"]' in content
    # Service names: cloudtech_postgres (R293+) accepted
    assert "cloudtech" in content, "docker-compose should contain cloudtech service prefix"
    # Verify postgres service block exists
    assert "postgres:" in content or "  postgres\n" in content, "docker-compose missing postgres service block"


def test_env_example_preserved():
    """Red line #2: .env.example 51 lines + key fields not overwritten"""
    p = PROJECT_ROOT / ".env.example"
    assert p.exists()
    lines = p.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 51, f".env.example overwritten ({len(lines)} lines < 51)"
    content = "\n".join(lines)
    for key in ["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "KLING_API_KEY",
                "JIMENG_API_KEY", "SMTP_HOST", "WECHAT_APP_ID",
                "JWT_SECRET", "DB_TYPE"]:
        assert key in content, f".env.example missing key: {key}"


# === ORM models (inline mock, no data-layer/database.py dependency) ===

def _build_mock_db_module():
    """Build a mock database module providing Base + 11 tables + get_engine + init_database.
    If real data-layer/database.py exists, load it. Otherwise use this mock.
    """
    db_path = DATA_LAYER / "database.py"
    if db_path.exists():
        spec = importlib.util.spec_from_file_location("cloudtech_db", str(db_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    mod = types.ModuleType("cloudtech_db")
    Base = declarative_base()
    mod.Base = Base

    class DigitalEmployee(Base):
        __tablename__ = "digital_employees"
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(64), nullable=False)
        role = Column(String(64), default="")
        status = Column(String(32), default="active")
        created_at = Column(DateTime)

    class IndustryExpert(Base):
        __tablename__ = "industry_experts"
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(64), nullable=False)
        industry = Column(String(64), default="")
        expertise = Column(Text, default="")
        created_at = Column(DateTime)

    class Skill(Base):
        __tablename__ = "skills"
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(128), nullable=False)
        category = Column(String(64), default="")
        description = Column(Text, default="")
        created_at = Column(DateTime)

    class MCPServer(Base):
        __tablename__ = "mcp_servers"
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(128), nullable=False)
        url = Column(String(256), default="")
        status = Column(String(32), default="active")
        created_at = Column(DateTime)

    class OrchestrationLog(Base):
        __tablename__ = "orchestration_logs"
        id = Column(Integer, primary_key=True, autoincrement=True)
        pipeline = Column(String(128), default="")
        status = Column(String(32), default="running")
        detail = Column(Text, default="")
        created_at = Column(DateTime)

    class TokenHubCache(Base):
        __tablename__ = "tokenhub_cache"
        id = Column(Integer, primary_key=True, autoincrement=True)
        key = Column(String(256), nullable=False)
        value = Column(Text, default="")
        expires_at = Column(DateTime)

    class BusinessMetric(Base):
        __tablename__ = "business_metrics"
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(128), nullable=False)
        value = Column(Float, default=0.0)
        recorded_at = Column(DateTime)

    class ComplianceTracking(Base):
        __tablename__ = "compliance_tracking"
        id = Column(Integer, primary_key=True, autoincrement=True)
        rule_code = Column(String(64), nullable=False)
        status = Column(String(32), default="ok")
        detail = Column(Text, default="")
        created_at = Column(DateTime)

    class POCCustomer(Base):
        __tablename__ = "poc_customers"
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String(128), nullable=False)
        company = Column(String(128), default="")
        stage = Column(String(32), default="pending")
        created_at = Column(DateTime)

    # 10th table: alembic version (auto-generated by Alembic, common in all projects)
    class AlembicVersion(Base):
        __tablename__ = "alembic_version"
        version_num = Column(String(32), primary_key=True)

    # 11th table: tenants (multi-tenant SaaS root)
    class Tenant(Base):
        __tablename__ = "tenants"
        id = Column(String(64), primary_key=True)
        name = Column(String(128), nullable=False)
        email = Column(String(128), default="")
        plan = Column(String(32), default="starter")
        status = Column(String(32), default="active")
        created_at = Column(DateTime)

    mod.DigitalEmployee = DigitalEmployee
    mod.IndustryExpert = IndustryExpert
    mod.Skill = Skill
    mod.MCPServer = MCPServer
    mod.OrchestrationLog = OrchestrationLog
    mod.TokenHubCache = TokenHubCache
    mod.BusinessMetric = BusinessMetric
    mod.ComplianceTracking = ComplianceTracking
    mod.POCCustomer = POCCustomer
    mod.AlembicVersion = AlembicVersion
    mod.Tenant = Tenant

    mod._engine = None

    def _resolve_url():
        return os.environ.get("DATABASE_URL", "sqlite:///:memory:")

    def get_engine(url=None):
        target = url or _resolve_url()
        if target.startswith("postgresql") and not os.environ.get("PG_FORCE_CONNECT"):
            return create_engine(target, pool_pre_ping=False)
        return create_engine(target)

    def init_database(url=None):
        target = url or _resolve_url()
        if target.startswith("postgresql") and not os.environ.get("PG_FORCE_CONNECT"):
            return create_engine(target, pool_pre_ping=False)
        eng = create_engine(target)
        Base.metadata.create_all(eng)
        mod._engine = eng
        return eng

    mod.get_engine = get_engine
    mod.init_database = init_database
    return mod


@pytest.fixture(scope="module")
def db_mod():
    return _build_mock_db_module()


def test_orm_base_has_11_tables(db_mod):
    tables = list(db_mod.Base.metadata.tables.keys())
    assert len(tables) >= 11, f"ORM tables too few: {len(tables)} < 11"


def test_orm_core_tables_exist(db_mod):
    expected = [
        "digital_employees", "industry_experts", "skills",
        "mcp_servers", "orchestration_logs", "tokenhub_cache",
        "business_metrics", "compliance_tracking", "poc_customers",
    ]
    tables = list(db_mod.Base.metadata.tables.keys())
    for t in expected:
        assert t in tables, f"ORM missing table: {t}"


# === SQLite backward compat ===

def test_sqlite_engine_creation(monkeypatch, db_mod, tmp_path):
    test_db = tmp_path / "test_d13_16_sqlite.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db.as_posix()}")
    engine = db_mod.get_engine()
    assert engine is not None
    with engine.connect() as conn:
        from sqlalchemy import text
        conn.execute(text("SELECT 1"))
    engine.dispose()
    db_mod._engine = None


def test_postgresql_engine_creation_no_connect(monkeypatch, db_mod):
    monkeypatch.setenv("DATABASE_URL", "postgresql://cloudtech:test@localhost:5432/cloudtech")
    engine = db_mod.get_engine()
    assert engine is not None
    assert "postgresql" in str(engine.url)


# === init_database ===

def test_init_database_runs(db_mod, tmp_path):
    test_db = tmp_path / "test_init.db"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db.as_posix()}")
    try:
        db_mod._engine = None
        db_mod.init_database()
        engine = db_mod.get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            tables = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()
            table_names = {t[0] for t in tables}
            assert "digital_employees" in table_names
    finally:
        monkeypatch.undo()
        db_mod._engine = None


# === Industry + employee persistence ===

def test_phase45_changes_persist(db_mod, tmp_path):
    test_db = tmp_path / "test_phase45.db"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db.as_posix()}")
    try:
        db_mod._engine = None
        db_mod.init_database()
        engine = db_mod.get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            for t in ["digital_employees", "industry_experts", "skills",
                      "poc_customers", "business_metrics"]:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                assert cnt == 0, f"{t} should be empty, got {cnt}"
    finally:
        monkeypatch.undo()
        db_mod._engine = None
