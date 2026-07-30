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

    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()

    schema = []
    for name, sql in tables:
        sql_pg = sql
        sql_pg = sql_pg.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
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


def execute_migration():
    """Actually execute migration to PostgreSQL"""
    if not PG_DSN:
        print("ERROR: PG_DSN environment variable not set")
        print("Example: PG_DSN=postgresql://user:pass@localhost:5432/cloudtech")
        return False

    try:
        import psycopg2
        conn = psycopg2.connect(PG_DSN)
        conn.autocommit = True
        cur = conn.cursor()
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"ERROR: Cannot connect to PostgreSQL: {e}")
        return False

    # Create schema
    schema = export_sqlite_schema()
    if not schema:
        print("No SQLite schema to migrate")
        conn.close()
        return False

    print(f"Migrating {len(schema)} tables to PostgreSQL...")
    for s in schema:
        try:
            cur.execute(s)
            print(f"  ✅ {s.split()[1][:40]}...")
        except Exception as e:
            print(f"  ⚠️  {s.split()[1][:40]}: {str(e)[:80]}")

    # Migrate data
    data = export_sqlite_data()
    if data:
        for table, info in data.items():
            if not info["rows"]:
                continue
            cols = info["columns"]
            placeholders = ", ".join(["%s"] * len(cols))
            col_names = ", ".join(cols)
            try:
                for row in info["rows"]:
                    values = [row[c] for c in cols]
                    cur.execute(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING', values)
                print(f"  📦 {table}: {len(info['rows'])} rows migrated")
            except Exception as e:
                print(f"  ⚠️  {table} data: {str(e)[:80]}")

    cur.close()
    conn.close()
    print("\n✅ Migration complete!")
    return True


if __name__ == "__main__":
    print("CloudTech Database Migration Tool")
    print("=" * 40)

    if "--execute" in sys.argv:
        execute_migration()
    else:
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
