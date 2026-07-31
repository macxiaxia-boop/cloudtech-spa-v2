"""
内容日历与定时调度 — Content Calendar & Scheduler
对标筷子: 矩阵调度·定时发布·内容日历
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

BASE = Path(__file__).parent
SCHEDULE_DIR = Path("D:/个人文件/AI/云数科技/schedules")
SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 发布队列操作
# ═══════════════════════════════════

def get_queue(tid: str = "zq-5bb59623") -> dict:
    """获取租户发布队列"""
    qf = SCHEDULE_DIR / f"queue_{tid}.json"
    if qf.exists():
        return json.loads(qf.read_text(encoding="utf-8"))
    return {"tenant_id": tid, "queue": [], "scheduled": [], "published": []}


def _save_queue(tid: str, queue: dict):
    qf = SCHEDULE_DIR / f"queue_{tid}.json"
    qf.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue(tid: str, content: dict) -> dict:
    """内容入队"""
    q = get_queue(tid)
    item = {
        "id": f"pub-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(q['queue'])}",
        "content": content,
        "queued_at": datetime.now().isoformat()[:19],
        "priority": content.get("priority", 5),
        "status": "queued",
    }
    q["queue"].append(item)
    _save_queue(tid, q)
    return {"ok": True, "item": item, "queue_size": len(q["queue"])}


def schedule(tid: str, item_id: str, publish_at: str) -> dict:
    """将内容从队列移到定时发布"""
    q = get_queue(tid)
    item = next((i for i in q["queue"] if i["id"] == item_id), None)
    if not item:
        return {"ok": False, "error": "未找到该内容"}

    q["queue"].remove(item)
    item["status"] = "scheduled"
    item["scheduled_at"] = publish_at
    q["scheduled"].append(item)
    _save_queue(tid, q)
    return {"ok": True, "item": item}


def publish_now(tid: str, item_id: str = None) -> dict:
    """立即发布（从队列或定时中取出并标记发布）"""
    q = get_queue(tid)
    # 如果指定了item_id，发布该项；否则发布队列第一项
    if item_id:
        item = next((i for i in q["queue"] + q["scheduled"] if i["id"] == item_id), None)
    else:
        item = q["queue"][0] if q["queue"] else (q["scheduled"][0] if q["scheduled"] else None)

    if not item:
        return {"ok": False, "error": "队列为空"}

    # 从原列表移除
    for lst in [q["queue"], q["scheduled"]]:
        if item in lst:
            lst.remove(item)

    item["status"] = "published"
    item["published_at"] = datetime.now().isoformat()[:19]
    q["published"].append(item)
    _save_queue(tid, q)

    # 发送通知
    try:
        from notifications import notify_publish_done
        notify_publish_done(tid, item["content"].get("account", ""), item["content"].get("platform", ""))
    except: pass

    return {"ok": True, "item": item, "queue_remaining": len(q["queue"]) + len(q["scheduled"])}


def get_calendar(tid: str, days: int = 7) -> dict:
    """获取内容日历"""
    q = get_queue(tid)
    now = datetime.now()
    calendar = []

    for d in range(days):
        day = (now + timedelta(days=d)).strftime("%Y-%m-%d")
        daily = {
            "date": day,
            "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][(now + timedelta(days=d)).weekday()],
            "scheduled": [i for i in q["scheduled"] if (i.get("scheduled_at", "")[:10] == day)],
            "queued": len(q["queue"]),
        }
        calendar.append(daily)

    return {
        "tenant_id": tid,
        "calendar": calendar,
        "total_queued": len(q["queue"]),
        "total_scheduled": len(q["scheduled"]),
        "total_published": len(q["published"]),
    }


def get_stats(tid: str) -> dict:
    """发布统计"""
    q = get_queue(tid)
    today = datetime.now().strftime("%Y-%m-%d")
    published_today = [i for i in q["published"] if i.get("published_at", "")[:10] == today]
    scheduled_today = [i for i in q["scheduled"] if (i.get("scheduled_at", "")[:10] == today)]

    return {
        "queued": len(q["queue"]),
        "scheduled": len(q["scheduled"]),
        "published_total": len(q["published"]),
        "published_today": len(published_today),
        "scheduled_today": len(scheduled_today),
    }


# ═══════════════════════════════════
# 矩阵分发执行（替代tenant_platform的queued-only）
# ═══════════════════════════════════

def execute_distribution(tid: str, topic: str, content_type: str = "article") -> dict:
    """执行内容分发: 生成分发计划 → 入队 → 部分立即排期"""
    from tenant_service import distribute_content

    dist = distribute_content(tid, topic, content_type)
    if not dist.get("plan"):
        return {"ok": False, "error": "无可用账号"}

    # 每个分发项入队
    enqueued = []
    for plan_item in dist["plan"]:
        result = enqueue(tid, {
            "topic": plan_item["topic"],
            "account": plan_item["account"],
            "city": plan_item["city"],
            "platform": plan_item["platform"],
            "content_type": plan_item["content_type"],
            "priority": 5,
        })
        enqueued.append(result)

    # 高优先级内容自动排期（当天）
    scheduled = []
    for i, plan_item in enumerate(dist["plan"][:3]):  # 前3个自动排期
        if i < len(enqueued):
            schedule(tid, enqueued[i]["item"]["id"], datetime.now().strftime("%Y-%m-%d") + " 10:00")

    return {
        "ok": True,
        "total_distributions": dist["total_distributions"],
        "enqueued": len(enqueued),
        "auto_scheduled": min(3, len(enqueued)),
    }
