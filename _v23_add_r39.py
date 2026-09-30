"""V23 R397 加 5 动态路由: skills analytics-advanced + billing subscription-downgrade + campaign audience-gender-stats + file share-stats-by-day + auth api-keys/create"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_analytics_advanced(skill_id: str):
    """Skill analytics-advanced · 高级分析 (R397)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":          skill_id,
            "trend":             "up",
            "trend_pct":         "+18.2",
            "retention_d1":       "82%",
            "retention_d7":       "64%",
            "retention_d30":      "48%",
            "user_satisfaction":  "4.6/5",
            "nps_score":          42,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_downgrade(tenant_id: str):
    """Billing subscription-downgrade · 降级订阅 (R397)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R397_down",
            "previous_plan":   "enterprise",
            "downgraded_to":   "pro",
            "downgraded_at":   datetime.utcnow().isoformat() + "Z",
            "refund_yuan":     5000,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_gender_stats(campaign_id: str):
    """Campaigns audience-gender-stats · 受众性别 (R397)"""
    return {
        "status": "ok",
        "data": [
            {"gender": "male",   "count": 9240, "pct": 50.2},
            {"gender": "female", "count": 8640, "pct": 46.9},
            {"gender": "other",  "count":  540, "pct":  2.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_stats_by_day(file_id: str):
    """Files share-stats-by-day · 分享按日 (R397)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "shares": 5,  "views": 28},
            {"date": "2026-09-25", "shares": 3,  "views": 18},
            {"date": "2026-09-26", "shares": 4,  "views": 24},
            {"date": "2026-09-27", "shares": 6,  "views": 35},
            {"date": "2026-09-28", "shares": 8,  "views": 42},
            {"date": "2026-09-29", "shares": 5,  "views": 22},
            {"date": "2026-09-30", "shares": 3,  "views": 18},
        ],
        "total_shares": 34,
        "total_views":  187,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_create():
    """Auth api-keys/create · 创建 API key (R397)"""
    return {
        "status": "ok",
        "data": {
            "key_id":    "k_v23_R397_" + str(hash("create_key")) % 10000,
            "name":      "新创建 key",
            "secret":    "sk_v23_R397_" + str(hash("secret_value")) % 100000,
            "scopes":    ["read"],
            "created_by": "u_001",
            "created_at": datetime.utcnow().isoformat() + "Z",
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
    print(f'✅ 加 5 函数 (R397)')
else:
    print('❌ 没找到')