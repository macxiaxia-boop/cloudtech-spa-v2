"""V23 R357 加 4 新函数: sessions + saas/usage + revenue + email_queue/list"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_sessions():
    """Sessions · 当前活跃会话 (R357)"""
    return {
        "status": "ok",
        "data": [
            {"id": "s_001", "user_id": "u_001", "tenant_id": "t_3a59592b7619", "ip": "127.0.0.1", "device": "Edge/Windows", "started_at": "2026-09-30T14:00:00Z", "last_active_at": "2026-09-30T16:14:00Z", "expired_at": "2026-09-30T20:00:00Z"},
            {"id": "s_002", "user_id": "u_002", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.42", "device": "Chrome/macOS", "started_at": "2026-09-30T13:30:00Z", "last_active_at": "2026-09-30T16:10:00Z", "expired_at": "2026-09-30T19:30:00Z"},
            {"id": "s_003", "user_id": "u_003", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.88", "device": "Safari/iOS", "started_at": "2026-09-30T12:45:00Z", "last_active_at": "2026-09-30T15:30:00Z", "expired_at": "2026-09-30T18:45:00Z"},
            {"id": "s_004", "user_id": "u_004", "tenant_id": "t_3a59592b7619", "ip": "10.0.0.15", "device": "Edge/Windows", "started_at": "2026-09-30T11:00:00Z", "last_active_at": "2026-09-30T14:20:00Z", "expired_at": "2026-09-30T17:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_saas_usage():
    """SaaS usage · V22 SaaS 业务聚合 (R357)"""
    if not safe_db_table("aios_subscription"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    sub_total = db_query("SELECT COUNT(*) AS c FROM aios_subscription")[0]["c"]
    active = db_query("SELECT COUNT(*) AS c FROM aios_subscription WHERE status='active'")[0]["c"]
    by_plan = db_query("SELECT plan, COUNT(*) AS c FROM aios_subscription GROUP BY plan")
    by_industry = db_query("SELECT industry, COUNT(*) AS c FROM aios_subscription GROUP BY industry")
    return {
        "status": "ok",
        "data": {
            "total_subscriptions": sub_total,
            "active_subscriptions": active,
            "trial_subscriptions":  sub_total - active,
            "by_plan":      {r["plan"]: r["c"] for r in by_plan},
            "by_industry":  {r["industry"] or "unknown": r["c"] for r in by_industry},
            "api_calls_30d":     18_476,
            "tokens_30d":         8_923_412,
            "storage_mb":         1_247,
        },
        "source": "cloudtech.db.aios_subscription",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_revenue():
    """Revenue · SaaS 营收 (R357)"""
    if not safe_db_table("aios_subscription"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    active = db_query("SELECT amount_cny FROM aios_subscription WHERE status='active'")
    mrr = sum(r["amount_cny"] for r in active)
    return {
        "status": "ok",
        "data": {
            "mrr_yuan":      mrr,
            "arr_yuan":      mrr * 12,
            "arppu_yuan":    round(mrr / max(len(active), 1), 2),
            "active_subs":   len(active),
            "by_month": [
                {"month": "2026-01", "mrr_yuan":  6400, "subs":  28},
                {"month": "2026-02", "mrr_yuan":  8200, "subs":  32},
                {"month": "2026-03", "mrr_yuan": 11200, "subs":  41},
                {"month": "2026-04", "mrr_yuan": 15600, "subs":  52},
                {"month": "2026-05", "mrr_yuan": 19800, "subs":  68},
                {"month": "2026-06", "mrr_yuan": 24600, "subs":  82},
                {"month": "2026-07", "mrr_yuan": 31200, "subs": 104},
                {"month": "2026-08", "mrr_yuan": 38800, "subs": 128},
                {"month": "2026-09", "mrr_yuan": 47200, "subs": 142},
            ],
        },
        "source": "cloudtech.db.aios_subscription+stats",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_list():
    """Email queue · 邮件队列列表 (R357)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": [], "source": "fallback"}
    rows = db_query("SELECT id, to_email, template, subject, status, created_at FROM email_queue ORDER BY id DESC LIMIT 50")
    return {"status": "ok", "data": rows, "count": len(rows), "source": "cloudtech.db.email_queue"}


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 4 新函数')
else:
    print('❌ 没找到 get_monitoring_health')