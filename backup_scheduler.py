"""
自动备份调度 — Automated Backup Scheduler
定时备份·保留策略·状态监控·一键恢复
"""
import json, shutil
from pathlib import Path
from datetime import datetime, timedelta

BASE = Path(__file__).parent
BACKUP_DIR = Path("D:/个人文件/AI/云数科技/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

RETENTION = {"hourly": 24, "daily": 7, "weekly": 4, "monthly": 3}


def run_backup(label: str = "auto") -> dict:
    """执行备份"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bid = f"backup-{ts}-{label}"
    backup_path = BACKUP_DIR / bid
    backup_path.mkdir(parents=True, exist_ok=True)

    files_backed_up = 0
    total_size = 0

    # 备份租户数据
    tenant_dir = Path("D:/个人文件/AI/云数科技/tenants")
    if tenant_dir.exists():
        dest = backup_path / "tenants"
        shutil.copytree(tenant_dir, dest, dirs_exist_ok=True)
        for f in dest.rglob("*"):
            if f.is_file():
                files_backed_up += 1
                total_size += f.stat().st_size

    # 备份调度数据
    sched_dir = Path("D:/个人文件/AI/云数科技/schedules")
    if sched_dir.exists():
        shutil.copytree(sched_dir, backup_path / "schedules", dirs_exist_ok=True)

    # 备份配置
    env_file = BASE / ".env"
    if env_file.exists():
        shutil.copy(env_file, backup_path / ".env.bak")

    # SQLite备份
    db_path = Path("C:/Users/xinzh/.openclaw/state/pipeline.db")
    if db_path.exists():
        shutil.copy(db_path, backup_path / "pipeline.db")

    info = {
        "id": bid, "label": label, "created_at": datetime.now().isoformat()[:19],
        "files": files_backed_up, "size_mb": round(total_size / 1024 / 1024, 1),
    }
    (backup_path / "backup-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "backup": info}


def list_backups(limit: int = 20) -> list:
    """列出备份"""
    backups = []
    for d in sorted(BACKUP_DIR.glob("backup-*"), reverse=True):
        info_file = d / "backup-info.json"
        if info_file.exists():
            try:
                backups.append(json.loads(info_file.read_text(encoding="utf-8")))
            except Exception: pass
        if len(backups) >= limit: break
    return backups


def cleanup_old_backups() -> dict:
    """清理过期备份"""
    removed = 0
    backups = list_backups(50)
    now = datetime.now()

    thresholds = {
        "hourly": now - timedelta(hours=RETENTION["hourly"]),
        "daily": now - timedelta(days=RETENTION["daily"]),
        "weekly": now - timedelta(weeks=RETENTION["weekly"]),
        "monthly": now - timedelta(days=RETENTION["monthly"] * 30),
    }

    for b in backups:
        created = datetime.fromisoformat(b["created_at"])
        if b["label"] in thresholds and created < thresholds[b["label"]]:
            d = BACKUP_DIR / b["id"]
            if d.exists():
                shutil.rmtree(d)
                removed += 1

    return {"ok": True, "removed": removed}


def get_backup_status() -> dict:
    """备份状态总览"""
    backups = list_backups()
    total_size = sum(b.get("size_mb", 0) for b in backups)
    last = backups[0] if backups else None
    return {
        "total_backups": len(backups), "total_size_mb": round(total_size, 1),
        "last_backup": last["created_at"] if last else None,
        "last_backup_size_mb": last["size_mb"] if last else 0,
        "retention_policy": RETENTION,
    }
