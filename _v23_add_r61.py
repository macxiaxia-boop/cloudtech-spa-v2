"""V23 R419 加 5 动态路由: skills sync-from-instance + billing payment-methods/{id}/set-backup-payment + campaign audience-tech-list + file download-by-month-chart + auth api-keys/{id}/throttle-limit-history"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_sync_from_instance(skill_id: str):
    """Skill sync-from-instance · 从实例同步 (R419)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
            "instance_id": f"inst_v23_R419_{skill_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_backup_payment(method_id: str):
    """Billing payment-methods/{id}/set-backup-payment · 设备用 (R419)"""
    return {
        "status": "ok",
        "data": {
            "method_id":    method_id,
            "is_backup":    True,
            "set_at":       datetime.utcnow().isoformat() + "Z",
            "set_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list(campaign_id: str):
    """Campaigns audience-tech-list · 技术列表 (R419)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iPhone",     "users": 6840, "pct": 37.1},
            {"tech": "Android",    "users": 5240, "pct": 28.4},
            {"tech": "Windows PC", "users": 2180, "pct": 11.8},
            {"tech": "Mac",        "users": 1420, "pct":  7.7},
            {"tech": "iPad",       "users":  980, "pct":  5.3},
            {"tech": "Linux",      "users":  580, "pct":  3.1},
            {"tech": "Other",      "users": 1180, "pct":  6.6},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_chart(file_id: str):
    """Files download-by-month-chart · 按月下载 chart (R419)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"],
            "datasets": [
                {"label": "下载",   "data": [168, 248, 312, 428, 487, 312], "type": "bar"},
                {"label": "唯一访客", "data": [118, 178, 218, 312, 348, 220], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_limit_history(key_id: str):
    """Auth api-keys/{id}/throttle-limit-history · 限流历史 (R419)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-23T00:00:00Z", "limit": "50 req/min",  "set_by": "u_001"},
            {"at": "2026-09-26T00:00:00Z", "limit": "100 req/min", "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "limit": "500 req/min", "set_by": "u_001"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R419)')
else:
    print('❌ 没找到')