"""V23 R411 加 5 动态路由: skills fork-from-template + billing payment-methods/{id}/verify-amount + campaign audience-language-stats + file download-by-day-of-week + auth api-keys/{id}/activity-log"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_fork_from_template(skill_id: str):
    """Skill fork-from-template · fork 模板 (R411)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "forked_id":  f"{skill_id}_fork_v23_R411",
            "forked_at": datetime.utcnow().isoformat() + "Z",
            "forked_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_amount(method_id: str):
    """Billing payment-methods/{id}/verify-amount · 验证金额 (R411)"""
    return {
        "status": "ok",
        "data": {
            "method_id":     method_id,
            "amount_yuan":   1999,
            "verified":      True,
            "verified_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_language_stats(campaign_id: str):
    """Campaigns audience-language-stats · 受众语言 (R411)"""
    return {
        "status": "ok",
        "data": [
            {"language": "中文",     "users": 16840, "pct": 91.4},
            {"language": "English",  "users":   920, "pct":  5.0},
            {"language": "日本語",    "users":   280, "pct":  1.5},
            {"language": "Español", "users":   180, "pct":  1.0},
            {"language": "Other",    "users":   200, "pct":  1.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_of_week(file_id: str):
    """Files download-by-day-of-week · 按周天下载 (R411)"""
    return {
        "status": "ok",
        "data": [
            {"dow": "Mon", "count":  52, "pct": 16.7},
            {"dow": "Tue", "count":  68, "pct": 21.8},
            {"dow": "Wed", "count":  72, "pct": 23.1},
            {"dow": "Thu", "count":  58, "pct": 18.6},
            {"dow": "Fri", "count":  42, "pct": 13.5},
            {"dow": "Sat", "count":  12, "pct":  3.8},
            {"dow": "Sun", "count":   8, "pct":  2.5},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_activity_log(key_id: str):
    """Auth api-keys/{id}/activity-log · 活动日志 (R411)"""
    return {
        "status": "ok",
        "data": [
            {"action": "view_dashboard", "at": "2026-09-30T16:00:00Z", "ip": "127.0.0.1"},
            {"action": "create_workflow","at": "2026-09-30T16:05:00Z", "ip": "127.0.0.1"},
            {"action": "deploy_agent",   "at": "2026-09-30T16:10:00Z", "ip": "127.0.0.1"},
            {"action": "send_email",     "at": "2026-09-30T16:12:00Z", "ip": "127.0.0.1"},
            {"action": "view_report",    "at": "2026-09-30T16:14:00Z", "ip": "127.0.0.1"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R411)')
else:
    print('❌ 没找到')