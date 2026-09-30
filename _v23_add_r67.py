"""V23 R425 加 5 动态路由: skills merge-stats + billing payment-methods/{id}/unset-default-billing + campaign audience-tech-list-v3 + file download-by-month-stats-v2 + auth api-keys/{id}/quota-history-v2"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_merge_stats(skill_id: str):
    """Skill merge-stats · 合并统计 (R425)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "merge_count":  24,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_billing(method_id: str):
    """Billing payment-methods/{id}/unset-default-billing · 取消默认账单支付 (R425)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list_v3(campaign_id: str):
    """Campaigns audience-tech-list-v3 · 技术列表 v3 (R425)"""
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
        "version": "v3",
    }


def get_files_download_by_month_stats_v2(file_id: str):
    """Files download-by-month-stats-v2 · 按月统计 v2 (R425)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4, "median_size_mb": 2.3},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5, "median_size_mb": 2.4},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "median_size_mb": 2.3},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6, "median_size_mb": 2.5},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "median_size_mb": 2.4},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "median_size_mb": 2.3},
        ],
        "total": 1955,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v2(key_id: str):
    """Auth api-keys/{id}/quota-history-v2 · quota 历史 v2 (R425)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-23T00:00:00Z", "quota":  1000, "set_by": "u_001"},
            {"at": "2026-09-26T00:00:00Z", "quota":  5000, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "quota": 10000, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "quota": 20000, "set_by": "u_001"},
            {"at": "2026-09-30T16:00:00Z", "quota": 50000, "set_by": "u_001"},
        ],
        "count": 5,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R425)')
else:
    print('❌ 没找到')