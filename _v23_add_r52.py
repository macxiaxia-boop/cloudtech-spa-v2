"""V23 R410 加 5 动态路由: skills version-from-template + billing payment-methods/{id}/check + campaign audience-region-detail + file download-by-channel + auth api-keys/{id}/scopes-list"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_version_from_template(skill_id: str):
    """Skill version-from-template · 从模板创建版本 (R410)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "new_version":   f"v3.0.0-{skill_id}",
            "from_template": f"tpl_v23_R410_{skill_id}",
            "created_at":   datetime.utcnow().isoformat() + "Z",
            "created_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_check(method_id: str):
    """Billing payment-methods/{id}/check · 检查支付 (R410)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "valid":      True,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "checks":     [
                "card_number_valid", "expiry_valid", "cvv_valid", "3d_secure_pass", "balance_sufficient",
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_detail(campaign_id: str):
    """Campaigns audience-region-detail · 地域详细 (R410)"""
    return {
        "status": "ok",
        "data": [
            {"region": "一线城市",  "users": 6240, "pct": 33.9},
            {"region": "新一线",    "users": 4180, "pct": 22.7},
            {"region": "二线城市",  "users": 3120, "pct": 16.9},
            {"region": "三线城市",  "users": 2280, "pct": 12.4},
            {"region": "四线+",      "users": 1840, "pct": 10.0},
            {"region": "海外",       "users":  760, "pct":  4.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_channel(file_id: str):
    """Files download-by-channel · 按渠道下载 (R410)"""
    return {
        "status": "ok",
        "data": [
            {"channel": "网站",     "count": 142, "pct": 45.5},
            {"channel": "邮件",     "count":  68, "pct": 21.8},
            {"channel": "Slack",    "count":  42, "pct": 13.5},
            {"channel": "微信群",   "count":  38, "pct": 12.2},
            {"channel": "短信",     "count":  22, "pct":  7.0},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_scopes_list(key_id: str):
    """Auth api-keys/{id}/scopes-list · scopes 列表 (R410)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "scopes":      [
                "read:own",
                "read:all",
                "write:own",
                "write:all",
                "deploy:own",
                "deploy:all",
                "admin:tenant",
                "admin:global",
            ],
            "listed_at":  datetime.utcnow().isoformat() + "Z",
            "total_count": 8,
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
    print(f'✅ 加 5 函数 (R410)')
else:
    print('❌ 没找到')