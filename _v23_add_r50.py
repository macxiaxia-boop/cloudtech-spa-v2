"""V23 R408 加 5 动态路由: skills merge-with-target + billing payment-methods/{id}/card-expire + campaign audience-referrer + file download-by-day-chart + auth api-keys/{id}/set-quota-to-limited"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_merge_with_target(skill_id: str):
    """Skill merge-with-target · 合并到 target (R408)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "target_id":    f"{skill_id}_target_v23_R408",
            "merged_at":    datetime.utcnow().isoformat() + "Z",
            "merged_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_card_expire(method_id: str):
    """Billing payment-methods/{id}/card-expire · 卡到期 (R408)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "expires_at":  "2027-09-30T00:00:00Z",
            "expired":     False,
            "warning":     "card expires in 12 months",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_referrer(campaign_id: str):
    """Campaigns audience-referrer · 引荐来源 (R408)"""
    return {
        "status": "ok",
        "data": [
            {"referrer": "google.com",     "users": 4280, "pct": 23.2},
            {"referrer": "baidu.com",      "users": 3120, "pct": 16.9},
            {"referrer": "xhs.com",        "users": 2840, "pct": 15.4},
            {"referrer": "douyin.com",     "users": 2280, "pct": 12.4},
            {"referrer": "linkedin.com",   "users": 1280, "pct":  6.9},
            {"referrer": "github.com",     "users":  980, "pct":  5.3},
            {"referrer": "其他",            "users": 3640, "pct": 19.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart(file_id: str):
    """Files download-by-day-chart · 按日下载 chart (R408)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载",   "data": [28, 42, 38, 56, 68, 42, 38]},
                {"label": "唯一访客", "data": [18, 28, 22, 38, 45, 28, 24]},
            ],
            "chart_type": "line",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_set_quota_to_limited(key_id: str):
    """Auth api-keys/{id}/set-quota-to-limited · 设 quota (R408)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "previous_quota": 99999,
            "new_quota":      5000,
            "set_at":         datetime.utcnow().isoformat() + "Z",
            "set_by":         "u_001",
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
    print(f'✅ 加 5 函数 (R408)')
else:
    print('❌ 没找到')