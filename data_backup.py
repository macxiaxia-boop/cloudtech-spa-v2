"""
Tenant Data Backup — Scheduled backup with rotation
Supports: SQLite file copy + PostgreSQL pg_dump
"""
import os, shutil, json, sqlite3
from datetime import datetime, timedelta
from pathlib import Path


BACKUP_DIR = Path(os.environ.get("CLOUDTECH_BACKUP_DIR", Path(__file__).parent / "backups"))
KEEP_DAYS = int(os.environ.get("CLOUDTECH_BACKUP_KEEP_DAYS", "30"))


def backup_sqlite(db_path: str = None) -> dict:
    """Backup SQLite database to timestamped file"""
    if db_path is None:
        try:
            from database import DB_PATH
            db_path = str(DB_PATH)
        except Exception:
            db_path = str(Path(__file__).parent / "cloudtech.db")

    src = Path(db_path)
    if not src.exists():
        return {"success": False, "error": f"DB not found: {db_path}"}

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"cloudtech-{stamp}.db"

    # Use SQLite backup API for safe copy
    try:
        src_conn = sqlite3.connect(str(src))
        dest_conn = sqlite3.connect(str(dest))
        src_conn.backup(dest_conn)
        src_conn.close()
        dest_conn.close()

        size_mb = dest.stat().st_size / (1024 * 1024)

        # Write backup manifest
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "source": str(src),
            "destination": str(dest),
            "size_mb": round(size_mb, 2),
            "type": "sqlite",
        }
        manifest_path = dest.with_suffix(".json")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

        return {"success": True, "file": str(dest), "size_mb": round(size_mb, 2)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_postgresql(dsn: str = None) -> dict:
    """Backup PostgreSQL database using pg_dump"""
    if dsn is None:
        dsn = os.environ.get("PG_DSN", "")

    if not dsn:
        return {"success": False, "error": "PG_DSN not set"}

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"cloudtech-{stamp}.sql.gz"

    import subprocess
    try:
        result = subprocess.run(
            ["pg_dump", dsn, "|", "gzip"],
            shell=True, capture_output=True, text=True, timeout=300
        )
        dest.write_bytes(result.stdout.encode() if isinstance(result.stdout, str) else result.stdout)

        size_mb = dest.stat().st_size / (1024 * 1024)
        return {"success": True, "file": str(dest), "size_mb": round(size_mb, 2)}
    except FileNotFoundError:
        return {"success": False, "error": "pg_dump not found — install PostgreSQL client tools"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def backup_all() -> dict:
    """Run all applicable backups"""
    results = {}

    # SQLite
    sqlite_result = backup_sqlite()
    results["sqlite"] = sqlite_result

    # PostgreSQL (if configured)
    if os.environ.get("PG_DSN"):
        pg_result = backup_postgresql()
        results["postgresql"] = pg_result

    return results


def cleanup_old_backups():
    """Remove backups older than KEEP_DAYS"""
    if not BACKUP_DIR.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0

    for f in BACKUP_DIR.iterdir():
        if f.suffix in (".db", ".sql", ".gz", ".json"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                continue

    return removed


def get_backup_status() -> dict:
    """Get backup system status"""
    if not BACKUP_DIR.exists():
        return {"backups": [], "total_size_mb": 0, "oldest": None, "newest": None}

    backups = []
    total_size = 0
    for f in sorted(BACKUP_DIR.iterdir()):
        if f.suffix in (".db", ".sql", ".gz"):
            size_mb = f.stat().st_size / (1024 * 1024)
            total_size += size_mb
            backups.append({
                "file": f.name,
                "size_mb": round(size_mb, 2),
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

    return {
        "backups": backups,
        "count": len(backups),
        "total_size_mb": round(total_size, 2),
        "oldest": backups[0]["created"] if backups else None,
        "newest": backups[-1]["created"] if backups else None,
    }
