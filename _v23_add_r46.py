"""V23 R404 加 5 动态路由: skills clone-template + billing payment-methods/{id}/verify + campaign audience-active-history + file download-stats-recent + auth api-keys/{id}/quota-update"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_clone_template(skill_id: str):
    """Skill clone-template · 克隆模板 (R404)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "cloned_id":      f"{skill_id}_template_v23_R404",
            "cloned_at":     datetime.utcnow().isoformat() + "Z",
            "cloned_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify(method_id: str):
    """Billing payment-methods/{id}/verify · 验证支付方式 (R404)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "verified":    True,
            "verified_at": datetime.utcnow().isoformat() + "Z",
            "limit_yuan":  50000,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_active_history(campaign_id: str):
    """Campaigns audience-active-history · 活跃历史 (R404)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1",  "active_users": 8240},
            {"week": "2026-09-W2",  "active_users": 9120},
            {"week": "2026-09-W3",  "active_users": 8780},
            {"week": "2026-09-W4",  "active_users": 10120},
            {"week": "2026-09-W5",  "active_users": 10540},
        ],
        "trend":        "+5.2%",
        "average":      9360,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_recent(file_id: str):
    """Files download-stats-recent · 最近下载 (R404)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T16:30:00Z", "user_id": "u_001", "ip": "127.0.0.1"},
            {"at": "2026-09-30T16:15:00Z", "user_id": "u_002", "ip": "192.168.1.42"},
            {"at": "2026-09-30T16:00:00Z", "user_id": "u_003", "ip": "192.168.1.88"},
            {"at": "2026-09-30T15:45:00Z", "user_id": "u_004", "ip": "10.0.0.15"},
            {"at": "2026-09-30T15:30:00Z", "user_id": "u_001", "ip": "127.0.0.1"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_update(key_id: str):
    """Auth api-keys/{id}/quota-update · 更新配额 (R404)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "new_quota":      20000,
            "previous_quota": 10000,
            "updated_at":     datetime.utcnow().isoformat() + "Z",
            "updated_by":     "u_001",
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
    print(f'✅ 加 5 函数 (R404)')
else:
    print('❌ 没找到')