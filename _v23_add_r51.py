"""V23 R409 加 5 动态路由: skills export-from-instance + billing payment-methods/{id}/verify-billing + campaign audience-source-detail + file download-by-user-type + auth api-keys/{id}/permissions-list"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_export_from_instance(skill_id: str):
    """Skill export-from-instance · 导出实例 (R409)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "exported_id":  f"instance_v23_R409_{skill_id}",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "format":      "yaml",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_billing(method_id: str):
    """Billing payment-methods/{id}/verify-billing · 验证账单 (R409)"""
    return {
        "status": "ok",
        "data": {
            "method_id":    method_id,
            "verified":     True,
            "verified_at": datetime.utcnow().isoformat() + "Z",
            "verified_by": "u_001",
            "billing_verified_for": "subscription_v23_R409",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_detail(campaign_id: str):
    """Campaigns audience-source-detail · 来源详细 (R409)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "medium": "social", "count": 6280, "pct": 34.1},
            {"source": "xhs",          "medium": "social", "count": 4180, "pct": 22.7},
            {"source": "douyin",       "medium": "social", "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "medium": "social", "count": 1840, "pct": 10.0},
            {"source": "email",        "medium": "email",  "count": 1240, "pct":  6.7},
            {"source": "direct",       "medium": "direct", "count": 1180, "pct":  6.4},
            {"source": "baidu",        "medium": "search", "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_user_type(file_id: str):
    """Files download-by-user-type · 按用户类型下载 (R409)"""
    return {
        "status": "ok",
        "data": [
            {"user_type": "owner",     "count":  98, "pct": 31.4},
            {"user_type": "admin",     "count":  62, "pct": 19.9},
            {"user_type": "member",    "count":  84, "pct": 26.9},
            {"user_type": "viewer",    "count":  42, "pct": 13.5},
            {"user_type": "anonymous", "count":  26, "pct":  8.3},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_permissions_list(key_id: str):
    """Auth api-keys/{id}/permissions-list · 权限列表 (R409)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "permissions": [
                {"name": "read",       "enabled": True,  "scope": "all"},
                {"name": "write",      "enabled": True,  "scope": "all"},
                {"name": "deploy",     "enabled": False, "scope": "all"},
                {"name": "admin",      "enabled": False, "scope": "admin_only"},
                {"name": "billing",    "enabled": False, "scope": "billing_only"},
            ],
            "listed_at":   datetime.utcnow().isoformat() + "Z",
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
    print(f'✅ 加 5 函数 (R409)')
else:
    print('❌ 没找到')