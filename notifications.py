"""
应用内通知中心 — In-App Notification Center
实时提醒: 配额告警·发布完成·新内容·系统事件
"""
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
NOTIFY_DIR = Path("D:/个人文件/AI/云数科技/notifications")
NOTIFY_DIR.mkdir(parents=True, exist_ok=True)


def notify(tid: str, event_type: str, title: str, body: str = "", level: str = "info") -> dict:
    """发送通知"""
    nid = f"notify-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(list(NOTIFY_DIR.glob(f'{tid}_*.json')))}"
    notification = {
        "id": nid, "tenant_id": tid, "type": event_type, "title": title,
        "body": body, "level": level,  # info / warning / error / success
        "read": False, "created_at": datetime.now().isoformat()[:19],
    }
    nf = NOTIFY_DIR / f"{tid}_{nid}.json"
    nf.write_text(json.dumps(notification, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "notification": notification}


def get_notifications(tid: str, limit: int = 20, unread_only: bool = False) -> list:
    """获取通知列表"""
    notifications = []
    for f in sorted(NOTIFY_DIR.glob(f"{tid}_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            n = json.loads(f.read_text(encoding="utf-8"))
            if unread_only and n.get("read"):
                continue
            notifications.append(n)
            if len(notifications) >= limit:
                break
        except:
            pass
    return notifications


def mark_read(tid: str, nid: str = None) -> dict:
    """标记已读"""
    count = 0
    for f in NOTIFY_DIR.glob(f"{tid}_*.json"):
        if nid and nid not in f.name:
            continue
        try:
            n = json.loads(f.read_text(encoding="utf-8"))
            if not n.get("read"):
                n["read"] = True
                n["read_at"] = datetime.now().isoformat()[:19]
                f.write_text(json.dumps(n, ensure_ascii=False, indent=2), encoding="utf-8")
                count += 1
        except:
            pass
    return {"ok": True, "marked_read": count}


def get_unread_count(tid: str) -> int:
    return len(get_notifications(tid, limit=100, unread_only=True))


# ── 自动通知触发器 ──

def notify_quota_warning(tid: str, usage_pct: int):
    if usage_pct > 90:
        notify(tid, "quota", "配额即将用尽", f"已使用 {usage_pct}%，请升级套餐", "error")
    elif usage_pct > 80:
        notify(tid, "quota", "配额使用预警", f"已使用 {usage_pct}%", "warning")


def notify_content_ready(tid: str, topic: str, count: int = 1):
    notify(tid, "content", "内容生产完成", f"「{topic[:30]}」等 {count} 篇已生成", "success")


def notify_publish_done(tid: str, account: str, platform: str):
    notify(tid, "publish", "内容已发布", f"{account} 已发布到 {platform}", "info")


def notify_system_event(title: str, body: str = "", level: str = "info"):
    notify("system", "system", title, body, level)
