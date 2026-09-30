"""V23 R406 加 5 动态路由: skills pull-template + billing payment-methods/{id}/remove-primary + campaign audience-source-stats + file download-leaderboard + auth api-keys/{id}/reset-quota-unlimited"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_pull_template(skill_id: str):
    """Skill pull-template · 拉取模板 (R406)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "pulled_at": datetime.utcnow().isoformat() + "Z",
            "version":   "v2.1.0",
            "size_bytes":12288,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_remove_primary(method_id: str):
    """Billing payment-methods/{id}/remove-primary · 移除主要 (R406)"""
    return {
        "status": "ok",
        "data": {
            "method_id":     method_id,
            "is_primary":    False,
            "removed_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_stats(campaign_id: str):
    """Campaigns audience-source-stats · 来源统计 (R406)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "search",       "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_leaderboard(file_id: str):
    """Files download leaderboard · 下载排行榜 (R406)"""
    return {
        "status": "ok",
        "data": [
            {"rank": 1, "user_id": "u_001", "name": "心之所向便是光", "count": 12, "period": "weekly"},
            {"rank": 2, "user_id": "u_002", "name": "运维",          "count":  9, "period": "weekly"},
            {"rank": 3, "user_id": "u_003", "name": "销售",          "count":  7, "period": "weekly"},
            {"rank": 4, "user_id": "u_004", "name": "客服",          "count":  5, "period": "weekly"},
            {"rank": 5, "user_id": "u_005", "name": "匿名",          "count":  4, "period": "weekly"},
        ],
        "period": "weekly",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_reset_quota_unlimited(key_id: str):
    """Auth api-keys/{id}/reset-quota-unlimited · 重置配额无限 (R406)"""
    return {
        "status": "ok",
        "data": {
            "key_id":       key_id,
            "quota_unlimited": True,
            "previous_quota":  10000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
            "expires_at":      "2026-12-31T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R406)')
else:
    print('❌ 没找到')