"""
Alembic env.py — CloudTech SaaS Phase 45 D13-16
================================================
PostgreSQL 迁移环境配置：从 database.py 读 Base.metadata，自动对比 schema。

执行流程:
  alembic revision --autogenerate -m "init"   # 生成迁移
  alembic upgrade head                          # 升级到最新
  alembic downgrade -1                          # 回滚

环境变量:
  DATABASE_URL=postgresql://user:pass@localhost:5432/cloudtech
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 把 data-layer 加入 path（让 alembic 找到 database.py）
PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
DATA_LAYER = PROJECT_ROOT / "data-layer"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DATA_LAYER))

# Alembic Config 对象
config = context.config

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 关键：从 database.py 导入 Base.metadata（11 个 ORM 模型）
# 注：必须用 importlib 加载（data-layer 不在 PYTHONPATH 包内）
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("cloudtech_database", str(DATA_LAYER / "database.py"))
_db_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_db_mod)
Base = _db_mod.Base
target_metadata = Base.metadata

# DATABASE_URL 优先从环境变量读
_db_url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
    """离线模式：仅生成 SQL 不连接"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接 DB 执行迁移"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
