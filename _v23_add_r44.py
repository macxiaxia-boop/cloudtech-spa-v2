"""V23 R402 加 5 动态路由: skills run-template + billing payment-methods/{id}/set-default + campaign audience-active-rate + file download-stats-by-day + auth api-keys/{id}/scopes-update"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_run_template(skill_id: str):
    """Skill run-template · 运行模板 (R402)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "run_id":      f"run_v23_R402_{skill_id}",
            "status":      "running",
            "started_at":  datetime.utcnow().isoformat() + "Z",
            "estimated_done_at": "2026-09-30T20:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default(method_id: str):
    """Billing payment-methods/{id}/set-default · 设默认 (R402)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_active_rate(campaign_id: str):
    """Campaigns audience-active-rate · 活跃率 (R402)"""
    return {
        "status": "ok",
        "data": [
            {"cohort": "1d",   "active_users": 8240,  "active_rate": "82.4%"},
            {"cohort": "7d",   "active_users": 6280,  "active_rate": "62.8%"},
            {"cohort": "30d",  "active_users": 4180,  "active_rate": "41.8%"},
            {"cohort": "90d",  "active_users": 2180,  "active_rate": "21.8%"},
        ],
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_by_day(file_id: str):
    """Files download-stats-by-day · 按日下载 (R402)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique": 18},
            {"date": "2026-09-25", "downloads": 42, "unique": 28},
            {"date": "2026-09-26", "downloads": 38, "unique": 22},
            {"date": "2026-09-27", "downloads": 56, "unique": 38},
            {"date": "2026-09-28", "downloads": 68, "unique": 45},
            {"date": "2026-09-29", "downloads": 42, "unique": 28},
            {"date": "2026-09-30", "downloads": 38, "unique": 24},
        ],
        "total": 312,
        "peak_day": "2026-09-28",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_scopes_update(key_id: str):
    """Auth api-keys/{id}/scopes-update · 更新 scopes (R402)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "scopes":      ["read", "write", "admin"],
            "updated_at":  datetime.utcnow().isoformat() + "Z",
            "updated_by":  "u_001",
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
    print(f'✅ 加 5 函数 (R402)')
else:
    print('❌ 没找到')