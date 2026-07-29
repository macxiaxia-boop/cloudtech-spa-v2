#!/usr/bin/env python3
"""
CloudTech PostgreSQL Migration Tool
Usage: python migrate_pg.py --check    (dry-run: check connection)
       python migrate_pg.py --migrate  (apply migrations)
       python migrate_pg.py --status   (show migration status)
"""
import sys, os, json
from pathlib import Path
from datetime import datetime

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
PG_DSN = os.environ.get("PG_DSN", "postgresql://cloudtech:cloudtech_pg_2026@localhost:5432/cloudtech")


def get_connection():
    try:
        import psycopg2
        return psycopg2.connect(PG_DSN)
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Cannot connect to PostgreSQL: {e}")
        print(f"DSN: {PG_DSN}")
        sys.exit(1)


def check():
    """Verify PostgreSQL connection"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        ver = cur.fetchone()[0]
        print(f"✅ PostgreSQL connected: {ver[:60]}...")
        cur.execute("SELECT 1 FROM pg_database WHERE datname='cloudtech'")
        if cur.fetchone():
            print("✅ Database 'cloudtech' exists")
        cur.close(); conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


def migrate():
    """Apply all pending migrations"""
    conn = get_connection()
    cur = conn.cursor()

    # Create migrations tracking table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # Get already applied migrations
    cur.execute("SELECT filename FROM _migrations")
    applied = {r[0] for r in cur.fetchall()}

    # Apply pending migrations
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for mf in migration_files:
        if mf.name in applied:
            print(f"⏭️  {mf.name} — already applied")
            continue

        print(f"🔄 {mf.name} — applying...")
        try:
            sql = mf.read_text(encoding="utf-8")
            cur.execute(sql)
            cur.execute("INSERT INTO _migrations (filename) VALUES (%s)", [mf.name])
            conn.commit()
            print(f"✅ {mf.name} — applied successfully")
        except Exception as e:
            conn.rollback()
            print(f"❌ {mf.name} — FAILED: {e}")
            cur.close(); conn.close()
            sys.exit(1)

    cur.close(); conn.close()
    print("\n✅ All migrations applied.")


def status():
    """Show migration status"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT filename, applied_at FROM _migrations ORDER BY id")
        rows = cur.fetchall()
        print(f"Applied migrations: {len(rows)}")
        for r in rows:
            print(f"  ✅ {r[0]} — {r[1]}")
    except Exception:
        print("No migrations table found. Run --migrate first.")
    cur.close(); conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "--check":
        check()
    elif cmd == "--migrate":
        migrate()
    elif cmd == "--status":
        status()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
