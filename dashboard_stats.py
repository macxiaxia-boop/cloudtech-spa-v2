"""
实时仪表盘统计 — Real-time Dashboard Statistics
直接扫描数据目录·统计文件数·Token用量·磁盘·服务状态
"""
import json, os, shutil
from pathlib import Path
from datetime import datetime

# ═══════════════════════════════════
# 数据目录扫描
# ═══════════════════════════════════

CONTENT_DIRS = [
    Path("D:/个人文件/AI/云数科技/tenants"),
    Path("D:/个人文件/AI/05 项目生产系统/内容生产"),
    Path("D:/个人文件/电商图片/装企孵化/01-管线自动产物/01-脚本输出"),
]

def get_content_stats() -> dict:
    """扫描所有内容目录统计文件数和大小"""
    stats = {"total_files": 0, "total_size_kb": 0, "by_dir": {}}
    for d in CONTENT_DIRS:
        if not d.exists():
            continue
        files = list(d.rglob("*"))
        md_files = [f for f in files if f.suffix in (".md", ".txt")]
        total_size = sum(f.stat().st_size for f in md_files if f.is_file())
        stats["by_dir"][str(d)[:60]] = {"files": len(md_files), "size_kb": round(total_size / 1024)}
        stats["total_files"] += len(md_files)
        stats["total_size_kb"] += total_size
    stats["total_size_kb"] = round(stats["total_size_kb"] / 1024)  # KB→MB
    return stats


def get_tenant_stats() -> dict:
    """统计所有租户"""
    tenant_dir = Path("D:/个人文件/AI/云数科技/tenants")
    tenants = []
    for f in sorted(tenant_dir.glob("*.json")):
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
            content_dir = tenant_dir / t.get("id", "")
            content_count = len(list(content_dir.rglob("*.md"))) if content_dir.exists() else 0
            tenants.append({
                "id": t.get("id"), "name": t.get("name"), "plan": t.get("plan"),
                "status": t.get("status", "active"),
                "content_count": content_count,
                "monthly_used": t.get("monthly_used", 0),
                "monthly_quota": t.get("monthly_quota", 0),
                "total_tokens": t.get("total_tokens", 0),
                "created": t.get("created", "")[:10],
            })
        except:
            pass
    return {"total": len(tenants), "active": sum(1 for t in tenants if t.get("status") == "active"), "tenants": tenants}


def get_publish_stats() -> dict:
    """统计发布队列"""
    schedule_dir = Path("D:/个人文件/AI/云数科技/schedules")
    total_queued, total_scheduled, total_published = 0, 0, 0
    for f in schedule_dir.glob("queue_*.json"):
        try:
            q = json.loads(f.read_text(encoding="utf-8"))
            total_queued += len(q.get("queue", []))
            total_scheduled += len(q.get("scheduled", []))
            total_published += len(q.get("published", []))
        except:
            pass
    return {"queued": total_queued, "scheduled": total_scheduled, "published": total_published}


def get_system_health() -> dict:
    """系统健康检查"""
    import socket, platform

    # 磁盘
    try:
        usage = shutil.disk_usage("C:\\")
        disk_free_gb = round(usage.free / 1024 / 1024 / 1024, 1)
        disk_pct = round((1 - usage.free / usage.total) * 100)
    except:
        disk_free_gb, disk_pct = 0, 0

    # 内存（Windows）
    try:
        import subprocess
        r = subprocess.run(["wmic", "OS", "get", "FreePhysicalMemory", "/Value"], capture_output=True, text=True, timeout=10)
        mem_free_mb = int(r.stdout.split("=")[-1].strip()) // 1024 if "=" in r.stdout else 0
    except:
        mem_free_mb = 0

    # Python进程
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10)
        py_count = len([l for l in r.stdout.split("\n") if "python" in l.lower()])
    except:
        py_count = 0

    return {
        "hostname": socket.gethostname(),
        "platform": platform.system() + " " + platform.release(),
        "disk_free_gb": disk_free_gb,
        "disk_usage_pct": disk_pct,
        "memory_free_mb": mem_free_mb,
        "python_processes": py_count,
        "checked_at": datetime.now().isoformat()[:19],
    }


def get_full_stats() -> dict:
    """聚合所有统计数据"""
    return {
        "content": get_content_stats(),
        "tenants": get_tenant_stats(),
        "publish": get_publish_stats(),
        "system": get_system_health(),
        "generated_at": datetime.now().isoformat()[:19],
    }
