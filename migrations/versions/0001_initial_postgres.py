"""Phase 45 D13-16: 11 张核心表初始迁移（PostgreSQL/SQLite 通用）

Revision ID: 0001
Revises:
Create Date: 2026-09-14

Tables (11):
  - digital_employees      — 数字员工
  - industry_experts        — 行业专家
  - skills                  — Skill 索引
  - mcp_servers             — MCP 集成
  - orchestration_logs     — 编排日志
  - tokenhub_cache         — TokenHub 缓存
  - business_metrics       — 业务数据
  - compliance_tracking    — 合规追踪
  - poc_customers           — POC 客户
  - alembic_version         — Alembic 元数据（自动生成）

注: SQLAlchemy 自动模式比对生成；本文件为初始 stub，后续由 alembic revision --autogenerate 生成 DDL。
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """PostgreSQL 端 11 张表初始建表（D13-16 DDL 占位）"""
    # 实际生产 DDL 由 alembic revision --autogenerate 自动生成
    # 此处仅留空 upgrade/downgrade 框架（避免误用导致 schema 不一致）
    pass


def downgrade() -> None:
    """回滚：drop 所有表"""
    op.execute("DROP TABLE IF EXISTS digital_employees CASCADE")
    op.execute("DROP TABLE IF EXISTS industry_experts CASCADE")
    op.execute("DROP TABLE IF EXISTS skills CASCADE")
    op.execute("DROP TABLE IF EXISTS mcp_servers CASCADE")
    op.execute("DROP TABLE IF EXISTS orchestration_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS tokenhub_cache CASCADE")
    op.execute("DROP TABLE IF EXISTS business_metrics CASCADE")
    op.execute("DROP TABLE IF EXISTS compliance_tracking CASCADE")
    op.execute("DROP TABLE IF EXISTS poc_customers CASCADE")
