"""V23 R424 加 5 动态路由: skills sync-stats + billing payment-methods/{id}/set-default-billing + campaign audience-tech-list-v2 + file download-by-week-stats + auth api-keys/{id}/quota-history"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_sync_stats(skill_id: str):
    """Skill sync-stats · 同步统计 (R424)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "sync_count":  42,
            "last_synced_at": datetime.utcnow().isoformat() + "Z",
            "last_synced_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_billing(method_id: str):
    """Billing payment-methods/{id}/set-default-billing · 设默认账单支付 (R424)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "for_billing": True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list_v2(campaign_id: str):
    """Campaigns audience-tech-list-v2 · 技术列表 v2 (R424)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats(file_id: str):
    """Files download-by-week-stats · 按周统计 (R424)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220},
        ],
        "total": 1539,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history(key_id: str):
    """Auth api-keys/{id}/quota-history · quota 历史 (R424)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-23T00:00:00Z", "quota":  1000, "set_by": "u_001"},
            {"at": "2026-09-26T00:00:00Z", "quota":  5000, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "quota": 10000, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "quota": 20000, "set_by": "u_001"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R424)')
else:
    print('❌ 没找到')