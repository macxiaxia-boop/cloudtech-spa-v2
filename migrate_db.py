"""Database Migration — SQLite to PostgreSQL"""
import os, sys, sqlite3
from pathlib import Path

PROJECT = Path(__file__).parent
DB_SQLITE = PROJECT / "cloudtech.db"
PG_DSN = os.environ.get("PG_DSN", "")

def export_sqlite_schema():
    """Export SQLite schema as SQL"""
    if not DB_SQLITE.exists():
        print(f"No SQLite DB at {DB_SQLITE}")
        return None

    conn = sqlite3.connect(str(DB_SQLITE))
    cursor = conn.cursor()

    # Get all table schemas
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()

    schema = []
    for name, sql in tables:
        # Convert SQLite types to PostgreSQL
        sql_pg = sql
        sql_pg = sql_pg.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql_pg = sql_pg.replace("INTEGER", "INTEGER")
        sql_pg = sql_pg.replace("TEXT", "TEXT")
        sql_pg = sql_pg.replace("REAL", "DOUBLE PRECISION")
        sql_pg = sql_pg.replace("BLOB", "BYTEA")
        schema.append(sql_pg + ";")

    conn.close()
    return schema

def export_sqlite_data():
    """Export all data from SQLite"""
    if not DB_SQLITE.exists():
        return None

    conn = sqlite3.connect(str(DB_SQLITE))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]

    data = {}
    for table in tables:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        data[table] = {"columns": columns, "rows": [dict(zip(columns, row)) for row in rows]}

    conn.close()
    return data

if __name__ == "__main__":
    print("CloudTech Database Migration Tool")
    print("=" * 40)

    schema = export_sqlite_schema()
    if schema:
        print(f"\nSchema ({len(schema)} tables):")
        for s in schema:
            print(f"  {s[:80]}...")
    else:
        print("No SQLite database found — starting fresh is OK")

    if PG_DSN:
        print(f"\nTarget: {PG_DSN[:50]}...")
        print("Run: python migrate_db.py --execute")
    else:
        print("\nSet PG_DSN env var to PostgreSQL connection string")
        print("Then run: python migrate_db.py --execute")
