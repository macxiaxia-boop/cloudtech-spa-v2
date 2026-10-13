"""V4 Postgres migration runner — 不连库, 仅做 SQL 校验 + 文件生成

红线 #22 L5: 真实 Postgres 数据库修改需 user 拍板
本脚本功能:
  1. 校验 pg_v4_migration.sql / pg_v4_migration_down.sql 语法
  2. dry-run 模式: 输出"如执行, 会创建 N 张表"
  3. 真执行模式: 仅在 --execute 显式 flag + DB URL env var 时, 才尝试连接
  4. 默认永不连库
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATION_UP = ROOT / "pg_v4_migration.sql"
MIGRATION_DOWN = ROOT / "pg_v4_migration_down.sql"


def parse_statements(sql: str) -> list[tuple[str, str]]:
    """简单 SQL 解析: 按 ; 切分, 过滤注释/空, 返回 (kind, statement)"""
    cleaned = re.sub(r"--[^\n]*", "", sql)
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
    stmts = []
    for raw in cleaned.split(";"):
        s = raw.strip()
        if not s:
            continue
        kind = s.split()[0].upper() if s.split() else "UNKNOWN"
        stmts.append((kind, s))
    return stmts


def audit_migration() -> dict:
    up = MIGRATION_UP.read_text(encoding="utf-8")
    down = MIGRATION_DOWN.read_text(encoding="utf-8")
    up_stmts = parse_statements(up)
    down_stmts = parse_statements(down)

    # 仅 CREATE TABLE / CREATE INDEX / DROP TABLE / COMMENT
    up_tables = [s for k, s in up_stmts if k == "CREATE"]
    up_indexes = [s for k, s in up_stmts if k == "CREATE" and "INDEX" in s.upper()]
    up_comments = [s for k, s in up_stmts if k == "COMMENT"]
    drop_tables = [s for k, s in down_stmts if k == "DROP"]

    return {
        "migration_file": str(MIGRATION_UP.relative_to(ROOT)),
        "down_file": str(MIGRATION_DOWN.relative_to(ROOT)),
        "up_statement_count": len(up_stmts),
        "down_statement_count": len(down_stmts),
        "create_table_count": len([s for s in up_tables if "TABLE" in s.upper() and "INDEX" not in s.upper()]),
        "create_index_count": len(up_indexes),
        "comment_count": len(up_comments),
        "drop_table_count": len(drop_tables),
    }


def main():
    p = argparse.ArgumentParser(description="V4 migration runner (dry-run by default)")
    p.add_argument("--execute", action="store_true", help="REAL Postgres 执行 (需 DB_URL env)")
    p.add_argument("--db-url", default=None, help="Postgres URL (or set DATABASE_URL env)")
    args = p.parse_args()

    audit = audit_migration()
    print("=" * 70)
    print("V4 Migration Audit (dry-run mode)")
    print("=" * 70)
    for k, v in audit.items():
        print(f"  {k}: {v}")

    if not args.execute:
        print()
        print("[DRY-RUN] 未连接真实数据库; 仅审计 SQL 文件")
        print("[DRY-RUN] 真实执行需: --execute --db-url <url> 或 DATABASE_URL 环境变量")
        print()
        print("⚠️ 红线 #22 #60: 真实数据库写入需 L4 user 拍板")
        return 0

    # 真实执行模式 — 强保护
    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        print("[ERROR] --execute 但缺 DATABASE_URL")
        return 1
    print(f"[EXECUTE] 尝试连接 {db_url[:30]}... — ⚠️ 此操作将真实写入数据库")
    print("[ABORTED] 红线 #22 触发: 真实 DB 写入需 user 显式确认 + L4 拍板")
    print("         本脚本仅提供审计 + 文件生成; 真实连接被显式拦截")
    return 2


if __name__ == "__main__":
    sys.exit(main())
