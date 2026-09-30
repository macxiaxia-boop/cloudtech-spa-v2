"""V23 R418 加 5 动态路由: skills revert + billing payment-methods/{id}/set-primary-payment + campaign audience-language-list + file download-by-week-chart + auth api-keys/{id}/throttle-history"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_revert(skill_id: str):
    """Skill revert · 回滚 skill (R418)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "rolled_back_to": "v2.0.5",
            "rolled_back_at": datetime.utcnow().isoformat() + "Z",
            "rolled_back_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_primary_payment(method_id: str):
    """Billing payment-methods/{id}/set-primary-payment · 设主要支付 (R418)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_primary":  True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_language_list(campaign_id: str):
    """Campaigns audience-language-list · 语言列表 (R418)"""
    return {
        "status": "ok",
        "data": [
            {"language": "zh-CN", "name": "简体中文",  "users": 16840, "pct": 91.4},
            {"language": "en-US", "name": "English",   "users":   920, "pct":  5.0},
            {"language": "ja-JP", "name": "日本語",     "users":   280, "pct":  1.5},
            {"language": "es-ES", "name": "Español",   "users":   180, "pct":  1.0},
            {"language": "other", "name": "其他",       "users":   200, "pct":  1.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_chart(file_id: str):
    """Files download-by-week-chart · 按周下载 chart (R418)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["W36", "W37", "W38", "W39", "W40"],
            "datasets": [
                {"label": "下载",   "data": [312, 428, 487, 312, 178], "type": "bar"},
                {"label": "唯一访客", "data": [218, 312, 348, 220, 124], "type": "bar"},
            ],
            "chart_type": "bar",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_history(key_id: str):
    """Auth api-keys/{id}/throttle-history · 限流历史 (R418)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T15:30:00Z", "current_rate": 89, "limit": 100, "throttled": False},
            {"at": "2026-09-30T15:45:00Z", "current_rate": 95, "limit": 100, "throttled": False},
            {"at": "2026-09-30T16:00:00Z", "current_rate": 102, "limit": 100, "throttled": True},
            {"at": "2026-09-30T16:15:00Z", "current_rate": 42, "limit": 100, "throttled": False},
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
    print(f'✅ 加 5 函数 (R418)')
else:
    print('❌ 没找到')