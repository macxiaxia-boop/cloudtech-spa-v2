"""
内容效果追踪 — Content Performance Analytics
对标筷子: 视频数据反馈·内容效果评估·ROI分析
"""
import json, secrets
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE = Path(__file__).parent
ANALYTICS_DIR = Path("D:/个人文件/AI/云数科技/analytics")
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

METRICS = ["impressions", "reads", "likes", "comments", "shares", "saves", "follows", "completion_rate", "click_rate"]


def track_content(tid: str, content_id: str, platform: str, metrics: dict) -> dict:
    """记录内容表现数据"""
    entry = {
        "id": f"perf-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}",
        "tenant_id": tid, "content_id": content_id, "platform": platform,
        "metrics": {k: metrics.get(k, 0) for k in METRICS},
        "recorded_at": datetime.now().isoformat()[:19],
    }
    af = ANALYTICS_DIR / f"{entry['id']}.json"
    af.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "entry": entry}


def get_content_performance(tid: str, days: int = 30) -> dict:
    """内容效果总览"""
    cutoff = (datetime.now() - timedelta(days=days))
    entries = []
    totals = {m: 0 for m in METRICS}
    for f in ANALYTICS_DIR.glob("perf-*.json"):
        try:
            e = json.loads(f.read_text(encoding="utf-8"))
            if e.get("tenant_id") != tid: continue
            dt = datetime.fromisoformat(e["recorded_at"])
            if dt < cutoff: continue
            entries.append(e)
            for m in METRICS:
                totals[m] += e["metrics"].get(m, 0)
        except Exception: pass

    # 计算互动率
    if totals["impressions"] > 0:
        engagement = round((totals["likes"] + totals["comments"] + totals["shares"] + totals["saves"]) / totals["impressions"] * 100, 2)
    else:
        engagement = 0

    return {
        "tenant_id": tid, "days": days, "content_count": len(entries),
        "totals": totals, "engagement_rate": engagement,
        "entries": sorted(entries, key=lambda x: x["recorded_at"], reverse=True)[:20],
    }


def get_platform_breakdown(tid: str, days: int = 30) -> dict:
    """按平台拆分效果"""
    cutoff = (datetime.now() - timedelta(days=days))
    by_platform = defaultdict(lambda: {"count": 0, "total_impressions": 0, "total_engagement": 0})
    for f in ANALYTICS_DIR.glob("perf-*.json"):
        try:
            e = json.loads(f.read_text(encoding="utf-8"))
            if e.get("tenant_id") != tid: continue
            if datetime.fromisoformat(e["recorded_at"]) < cutoff: continue
            p = e["platform"]
            by_platform[p]["count"] += 1
            by_platform[p]["total_impressions"] += e["metrics"].get("impressions", 0)
            by_platform[p]["total_engagement"] += sum(e["metrics"].get(m, 0) for m in ["likes", "comments", "shares", "saves"])
        except Exception: pass
    return {"tenant_id": tid, "by_platform": dict(by_platform)}


def get_content_roi(tid: str) -> dict:
    """内容ROI估算"""
    perf = get_content_performance(tid, 90)
    from payment_orders import get_tenant_orders
    orders = get_tenant_orders(tid)
    total_spent = sum(o["amount"] for o in orders if o["status"] == "paid")
    total_impressions = perf["totals"]["impressions"]
    cpm = round(total_spent / (total_impressions / 1000), 2) if total_impressions > 0 else 0
    return {
        "tenant_id": tid, "total_spent": total_spent,
        "total_impressions": total_impressions,
        "cpm": cpm,  # Cost per 1000 impressions
        "engagement_rate": perf["engagement_rate"],
        "content_count": perf["content_count"],
    }
