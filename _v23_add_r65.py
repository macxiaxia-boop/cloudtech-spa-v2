"""V23 R423 加 5 动态路由: skills export-instance + billing payment-methods/{id}/unset-default-payment + campaign audience-grade-stats + file download-by-month-stats + auth api-keys/{id}/burst-quota-reset"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_export_instance(skill_id: str):
    """Skill export-instance · 导出实例 (R423)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "exported_to":  f"instance_v23_R423_{skill_id}",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "size_bytes":  16384,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_payment(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment · 取消默认 (R423)"""
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


def get_campaigns_audience_grade_stats(campaign_id: str):
    """Campaigns audience-grade-stats · 等级统计 (R423)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_stats(file_id: str):
    """Files download-by-month-stats · 按月统计 (R423)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1955,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota_reset(key_id: str):
    """Auth api-keys/{id}/burst-quota-reset · 重置突发 (R423)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "burst_quota_reset": True,
            "new_burst_quota":   1000,
            "reset_at":          datetime.utcnow().isoformat() + "Z",
            "reset_by":          "u_001",
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
    print(f'✅ 加 5 函数 (R423)')
else:
    print('❌ 没找到')