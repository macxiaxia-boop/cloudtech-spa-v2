"""V23 R359 加 3 新函数: get_email_queue_item + get_session_item + get_campaign_stats"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_email_queue_item(item_id: str):
    """Email queue 单项 (R359)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    rows = db_query("SELECT id, to_email, template, subject, body_html, status, attempts, created_at FROM email_queue WHERE id=? LIMIT 1", (item_id,))
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": rows[0], "source": "cloudtech.db.email_queue"}


def get_session_item(item_id: str):
    """Session 单项 (R359)"""
    sessions_list = [
        {"id": "s_001", "user_id": "u_001", "tenant_id": "t_3a59592b7619", "ip": "127.0.0.1", "device": "Edge/Windows", "started_at": "2026-09-30T14:00:00Z", "last_active_at": "2026-09-30T16:14:00Z", "expired_at": "2026-09-30T20:00:00Z"},
        {"id": "s_002", "user_id": "u_002", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.42", "device": "Chrome/macOS", "started_at": "2026-09-30T13:30:00Z", "last_active_at": "2026-09-30T16:10:00Z", "expired_at": "2026-09-30T19:30:00Z"},
        {"id": "s_003", "user_id": "u_003", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.88", "device": "Safari/iOS", "started_at": "2026-09-30T12:45:00Z", "last_active_at": "2026-09-30T15:30:00Z", "expired_at": "2026-09-30T18:45:00Z"},
        {"id": "s_004", "user_id": "u_004", "tenant_id": "t_3a59592b7619", "ip": "10.0.0.15", "device": "Edge/Windows", "started_at": "2026-09-30T11:00:00Z", "last_active_at": "2026-09-30T14:20:00Z", "expired_at": "2026-09-30T17:00:00Z"},
    ]
    found = [s for s in sessions_list if s["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_campaign_stats(campaign_id: str):
    """Campaign 单项 stats (R359)"""
    campaigns = [
        {"id": "c001", "name": "新客 7 天试用",     "status": "active",  "channel": "邮件",   "budget_yuan": 5000,  "leads": 142, "conversions": 18},
        {"id": "c002", "name": "老客推荐激励",     "status": "active",  "channel": "微信",   "budget_yuan": 3000,  "leads": 87,  "conversions": 24},
        {"id": "c003", "name": "小红书 KOL 投放",   "status": "paused",  "channel": "小红书", "budget_yuan": 12000, "leads": 256, "conversions": 31},
        {"id": "c004", "name": "抖音矩阵投放",     "status": "active",  "channel": "抖音",   "budget_yuan": 18000, "leads": 312, "conversions": 42},
        {"id": "c005", "name": "公众号长文推送",   "status": "active",  "channel": "公众号", "budget_yuan": 0,     "leads": 89,  "conversions": 12},
        {"id": "c006", "name": "微信社群裂变",     "status": "draft",   "channel": "微信群", "budget_yuan": 0,     "leads": 0,   "conversions": 0},
        {"id": "c007", "name": "抖音直播切片",     "status": "active",  "channel": "抖音",   "budget_yuan": 8000,  "leads": 178, "conversions": 19},
        {"id": "c008", "name": "百度 SEM 投放",    "status": "paused",  "channel": "百度",   "budget_yuan": 15000, "leads": 198, "conversions": 15},
    ]
    found = [c for c in campaigns if c["id"] == campaign_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    c = found[0]
    return {
        "status": "ok",
        "data": {
            **c,
            "ctr":            round(c["conversions"] / max(c["leads"], 1) * 100, 2),
            "cpl_yuan":       round(c["budget_yuan"] / max(c["leads"], 1), 2) if c["budget_yuan"] > 0 else 0,
            "roas":           round(c["conversions"] * 999 / max(c["budget_yuan"], 1), 2) if c["budget_yuan"] > 0 else 0,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_by_id(item_id: str):
    """Alias · GET /api/v2/email_queue/{id}"""
    return get_email_queue_item(item_id)


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 4 函数')
else:
    print('❌ 没找到')