"""CloudTech SQLite → PostgreSQL 数据迁移脚本 · 2026-09-25 R288

用法:
  docker compose up -d                  # 先启 postgres
  python pg_migrate.py                  # 跑迁移
  python pg_migrate.py --verify-only    # 只验证不迁移

逻辑:
  - 读 SQLite DB (D:\CloudTech-Portable\data\cloudtech.db)
  - 通过环境变量 PG_* 连接 Postgres
  - 9 张表 100% 迁移 (users / leads / employees / content_history / quota / invoice / aios_user / aios_subscription / bridge_incident)
  - 已存在则 ON CONFLICT 跳过
  - 进度打印
"""
import os
import sqlite3
import sys
from pathlib import Path

# 默认配置 (可用 env 覆盖)
SQLITE_PATH = Path(os.environ.get("SQLITE_PATH", r"D:\CloudTech-Portable\data\cloudtech.db"))
PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_USER = os.environ.get("PG_USER", "cloudtech")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "cloudtech_dev_pwd")
PG_DB = os.environ.get("PG_DB", "cloudtech")

TABLES = [
    "users", "leads", "employees", "content_history",
    "quota", "invoice",
    "aios_user", "aios_subscription", "bridge_incident",
]


def get_sqlite_conn():
    if not SQLITE_PATH.exists():
        print(f"SQLITE_NOT_FOUND: {SQLITE_PATH}")
        sys.exit(1)
    c = sqlite3.connect(str(SQLITE_PATH))
    c.row_factory = sqlite3.Row
    return c


def get_pg_conn():
    try:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
    except ImportError:
        print("MISSING_DEPENDENCY: psycopg2 — pip install psycopg2-binary")
        sys.exit(1)
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASSWORD, dbname=PG_DB,
        connect_timeout=10,
    )


def sqlite_to_pg_value(v):
    """SQLite 类型 → PG 类型简单转换."""
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return v
    return str(v)


def migrate_table(sqlite_cur, pg_cur, table: str) -> tuple[int, int]:
    rows = sqlite_cur.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        return 0, 0
    cols = rows[0].keys()
    placeholders = ", ".join(["%s"] * len(cols))
    col_list = ", ".join(cols)
    # 用 ON CONFLICT DO NOTHING 幂等
    insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    inserted = 0
    skipped = 0
    for r in rows:
        vals = tuple(sqlite_to_pg_value(r[c]) for c in cols)
        try:
            pg_cur.execute(insert_sql, vals)
            if pg_cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ! skip row {table}: {e}")
            skipped += 1
    return inserted, skipped


def verify_table(pg_cur, table: str) -> int:
    try:
        pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
        return pg_cur.fetchone()[0]
    except Exception:
        return -1


def main():
    verify_only = "--verify-only" in sys.argv
    print(f"=== CloudTech SQLite → PostgreSQL Migration (R288) ===")
    print(f"SQLite: {SQLITE_PATH}")
    print(f"Postgres: {PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}")
    print()

    sc = get_sqlite_conn()
    pg = get_pg_conn()
    import psycopg2.extras  # type: ignore

    if not verify_only:
        with pg:
            with pg.cursor() as cur:
                for t in TABLES:
                    src = sc.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
                    ins, skp = migrate_table(sc, cur, t)
                    print(f"  {t:25s} src={src:4d}  inserted={ins:4d}  skipped={skp:4d}")

    print()
    print("=== Verify (Postgres row counts) ===")
    with pg.cursor() as cur:
        for t in TABLES:
            n = verify_table(cur, t)
            sqlite_n = sc.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
            mark = "✓" if n >= sqlite_n else "✗"
            print(f"  {mark} {t:25s} pg={n:4d}  sqlite={sqlite_n:4d}")

    print()
    print("Migration done.")


if __name__ == "__main__":
    main()
