"""
租户活动审计 — Tenant Activity Audit & Monitoring
全平台操作日志·租户行为追踪·异常检测
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE = Path(__file__).parent
AUDIT_DIR = Path("D:/个人文件/AI/云数科技/audit")
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def log_activity(tid: str, action: str, detail: dict = None, ip: str = ""):
    """记录租户活动"""
    entry = {
        "time": datetime.now().isoformat()[:19], "tenant_id": tid,
        "action": action, "detail": detail or {}, "ip": ip,
    }
    # 按天分文件
    day = datetime.now().strftime("%Y-%m-%d")
    af = AUDIT_DIR / f"audit-{day}.jsonl"
    with open(af, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_tenant_activity(tid: str, days: int = 7, action: str = "", limit: int = 100) -> list:
    """查询租户活动"""
    activities = []
    cutoff = (datetime.now() - timedelta(days=days))
    for f in sorted(AUDIT_DIR.glob("audit-*.jsonl"), reverse=True):
        try:
            for line in open(f, encoding="utf-8"):
                entry = json.loads(line.strip())
                if entry.get("tenant_id") != tid: continue
                if action and entry.get("action") != action: continue
                if datetime.fromisoformat(entry["time"]) < cutoff: continue
                activities.append(entry)
                if len(activities) >= limit: break
        except Exception: pass
        if len(activities) >= limit: break
    return activities


def get_activity_summary(days: int = 7) -> dict:
    """全局活动摘要"""
    cutoff = (datetime.now() - timedelta(days=days))
    by_action = defaultdict(int)
    by_tenant = defaultdict(int)
    by_day = defaultdict(int)
    total = 0

    for f in AUDIT_DIR.glob("audit-*.jsonl"):
        try:
            for line in open(f, encoding="utf-8"):
                entry = json.loads(line.strip())
                if datetime.fromisoformat(entry["time"]) < cutoff: continue
                total += 1
                by_action[entry["action"]] += 1
                by_tenant[entry.get("tenant_id", "?")] += 1
                by_day[entry["time"][:10]] += 1
        except Exception: pass

    return {
        "total_activities": total, "days": days,
        "top_actions": dict(sorted(by_action.items(), key=lambda x: -x[1])[:10]),
        "top_tenants": dict(sorted(by_tenant.items(), key=lambda x: -x[1])[:10]),
        "by_day": dict(sorted(by_day.items())),
    }
