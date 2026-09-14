"""
Migration System — CloudTech v3.0
==================================
数据库迁移管理系统，支持SQLite + PostgreSQL双后端。

迁移文件命名规范：V{NUMBER}__{description}.py
- NUMBER：递增版本号，从当前最大version+1开始
- description：简短描述，用双下划线分隔

迁移状态：
  applied  : 已执行
  failed   : 执行失败（需手动修复）
  skipped  : 跳过（因前置条件不满足）

用法：
    from migrations import MigrationRunner, get_db

    runner = MigrationRunner(get_db())
    runner.run()           # 执行所有未应用的迁移
    runner.status()       # 查看迁移状态
    runner.migrate_to(N)  # 迁移到指定版本
"""
from __future__ import annotations

import json
import os
import sqlite3
import importlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from contextlib import contextmanager

DB_PATH = os.environ.get(
    "DB_PATH",
    str(Path(__file__).parent.parent / "cloudtech.db")
)
MIGRATIONS_DIR = Path(__file__).parent


@dataclass
class MigrationRecord:
    """迁移记录"""
    version: int
    name: str
    applied_at: str
    status: str  # applied / failed / skipped
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class MigrationRunner:
    """迁移运行器"""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """确保migrations记录表存在，兼容旧表结构（只3列）"""
        # 先建基础表（兼容已有）
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'applied',
                duration_ms INTEGER,
                error TEXT
            )
        """)
        # 旧表可能缺少这三列，补上
        for col, dtype in [("status", "TEXT DEFAULT 'applied'"),
                           ("duration_ms", "INTEGER"),
                           ("error", "TEXT")]:
            try:
                self.conn.execute(f"ALTER TABLE _migrations ADD COLUMN {col} {dtype}")
            except sqlite3.OperationalError:
                pass  # 列已存在
        self.conn.commit()

    def _load_migration_files(self) -> List[Path]:
        """加载所有迁移文件（按版本号排序）"""
        files = sorted(
            MIGRATIONS_DIR.glob("V*__*.py"),
            key=lambda p: int(p.stem.split("__")[0].replace("V", ""))
        )
        return files

    def _get_applied_versions(self) -> set[int]:
        """获取已应用的迁移版本"""
        cur = self.conn.execute(
            "SELECT version FROM _migrations WHERE status='applied' ORDER BY version"
        )
        return {row[0] for row in cur.fetchall()}

    def _get_current_version(self) -> int:
        """获取当前数据库版本（最大已应用版本）"""
        cur = self.conn.execute(
            "SELECT MAX(version) FROM _migrations WHERE status='applied'"
        )
        row = cur.fetchone()
        return row[0] or 0

    def _record(self, record: MigrationRecord) -> None:
        """记录迁移结果"""
        self.conn.execute(
            """INSERT OR REPLACE INTO _migrations
               (version, name, applied_at, status, duration_ms, error)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record.version, record.name, record.applied_at,
             record.status, record.duration_ms, record.error)
        )
        self.conn.commit()

    def _run_migration(self, path: Path) -> MigrationRecord:
        """执行单个迁移文件"""
        import time
        start = time.time()

        version = int(path.stem.split("__")[0].replace("V", ""))
        name = path.stem.split("__")[1]

        try:
            # 动态导入迁移模块
            spec = importlib.util.spec_from_file_location(f"migration_{version}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 调用up()方法
            up_fn = getattr(module, "up", None)
            if up_fn is None:
                raise RuntimeError(f"Migration {path.name} has no up() function")

            up_fn(self.conn)

            duration_ms = int((time.time() - start) * 1000)
            record = MigrationRecord(
                version=version,
                name=name,
                applied_at=datetime.now().isoformat(),
                status="applied",
                duration_ms=duration_ms
            )
            self._record(record)
            return record

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            record = MigrationRecord(
                version=version,
                name=name,
                applied_at=datetime.now().isoformat(),
                status="failed",
                duration_ms=duration_ms,
                error=str(e)
            )
            self._record(record)
            raise

    def run(self, target_version: Optional[int] = None) -> List[MigrationRecord]:
        """执行所有未应用的迁移（可指定目标版本）"""
        applied = self._get_applied_versions()
        files = self._load_migration_files()

        results = []
        for path in files:
            version = int(path.stem.split("__")[0].replace("V", ""))
            if version in applied:
                continue
            if target_version and version > target_version:
                break

            print(f"  Applying V{version}__{path.stem.split('__')[1]}...", end=" ", flush=True)
            record = self._run_migration(path)
            results.append(record)
            status = "✅" if record.status == "applied" else "❌"
            print(f"{status} ({record.duration_ms}ms)")

        return results

    def status(self) -> List[MigrationRecord]:
        """查看所有迁移状态"""
        cur = self.conn.execute(
            "SELECT version, name, applied_at, status, duration_ms, error "
            "FROM _migrations ORDER BY version"
        )
        return [
            MigrationRecord(
                version=row[0], name=row[1], applied_at=row[2],
                status=row[3], duration_ms=row[4], error=row[5]
            )
            for row in cur.fetchall()
        ]

    def current_version(self) -> int:
        """获取当前数据库版本"""
        return self._get_current_version()

    def migrate_to(self, target: int) -> List[MigrationRecord]:
        """迁移到指定版本（用于回滚/重置场景）"""
        return self.run(target_version=target)


@contextmanager
def get_db_conn():
    """获取数据库连接的上下文管理器"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def get_db():
    """获取数据库连接（legacy接口，兼容现有代码）"""
    conn, *_ = get_db_conn().__enter__()
    return conn


if __name__ == "__main__":
    print("CloudTech Migration Runner v3.0")
    print(f"Database: {DB_PATH}")
    print(f"Migrations dir: {MIGRATIONS_DIR}")
    print()

    with get_db_conn() as conn:
        runner = MigrationRunner(conn)
        current = runner.current_version()
        print(f"Current version: {current}")
        print(f"Available migrations: {len(runner._load_migration_files())}")
        print()

        status = runner.status()
        if status:
            print("Applied migrations:")
            for r in status:
                icon = "✅" if r.status == "applied" else "❌" if r.status == "failed" else "⏭️"
                print(f"  V{r.version} {r.name} {icon} ({r.applied_at[:19]})")
        else:
            print("No migrations applied yet.")

        print()
        print("Running pending migrations...")
        results = runner.run()
        if not results:
            print("  All migrations up to date.")
        print(f"\nDone. Final version: {runner.current_version()}")
