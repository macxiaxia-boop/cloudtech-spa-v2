"""V23 R426 加 5 动态路由: skills export-to-marketplace + billing payment-methods/{id}/validate-all + campaign audience-source-list + file download-by-year-list + auth api-keys/{id}/rotate-secret-v2"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_export_to_marketplace(skill_id: str):
    """Skill export-to-marketplace · 导出到 marketplace (R426)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "marketplace_url": f"https://marketplace.v23.com/skills/{skill_id}",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "visibility": "public",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_validate_all(method_id: str):
    """Billing payment-methods/{id}/validate-all · 验证所有 (R426)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "all_valid":   True,
            "checks":      [
                {"name": "card_number",   "valid": True},
                {"name": "expiry",        "valid": True},
                {"name": "cvv",           "valid": True},
                {"name": "3d_secure",     "valid": True},
                {"name": "balance",       "valid": True},
                {"name": "3ds_enrolled",  "valid": True},
                {"name": "address_verified","valid": True},
            ],
            "validated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_list(campaign_id: str):
    """Campaigns audience-source-list · 来源列表 (R426)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year_list(file_id: str):
    """Files download-by-year-list · 按年下载列表 (R426)"""
    return {
        "status": "ok",
        "data": [
            {"year": "2024", "downloads":  680},
            {"year": "2025", "downloads": 4180},
            {"year": "2026", "downloads": 3280},
        ],
        "total": 8140,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v2(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v2 · 轮换 secret v2 (R426)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v2",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R426)')
else:
    print('❌ 没找到')