"""V23 R405 加 5 动态路由: skills import-template + billing payment-methods/{id}/set-primary + campaign audience-visit-frequency + file download-top + auth api-keys/{id}/regenerate-secret"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_import_template(skill_id: str):
    """Skill import-template · 导入模板 (R405)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":         skill_id,
            "imported_template": f"tpl_v23_R405_{skill_id}",
            "imported_at":      datetime.utcnow().isoformat() + "Z",
            "imported_from":    f"https://marketplace.example.com/templates/{skill_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_primary(method_id: str):
    """Billing payment-methods/{id}/set-primary · 设主要 (R405)"""
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


def get_campaigns_audience_visit_frequency(campaign_id: str):
    """Campaigns audience-visit-frequency · 访问频次 (R405)"""
    return {
        "status": "ok",
        "data": [
            {"freq": "1次",    "users": 4180, "pct": 22.7},
            {"freq": "2-3次",  "users": 6840, "pct": 37.1},
            {"freq": "4-7次",  "users": 4180, "pct": 22.7},
            {"freq": "8-15次", "users": 2180, "pct": 11.8},
            {"freq": "16+次",  "users": 1040, "pct":  5.7},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_top(file_id: str):
    """Files download-top · 下载排行榜 (R405)"""
    return {
        "status": "ok",
        "data": [
            {"rank": 1, "user_id": "u_001", "name": "心之所向便是光", "downloads": 12, "last_at": "2026-09-30T16:00:00Z"},
            {"rank": 2, "user_id": "u_002", "name": "运维",          "downloads":  9, "last_at": "2026-09-29T15:00:00Z"},
            {"rank": 3, "user_id": "u_003", "name": "销售",          "downloads":  7, "last_at": "2026-09-28T11:00:00Z"},
            {"rank": 4, "user_id": "u_004", "name": "客服",          "downloads":  5, "last_at": "2026-09-27T14:00:00Z"},
            {"rank": 5, "user_id": "u_005", "name": "匿名",          "downloads":  4, "last_at": "2026-09-26T10:00:00Z"},
        ],
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_regenerate_secret(key_id: str):
    """Auth api-keys/{id}/regenerate-secret · 重生 secret (R405)"""
    import hashlib
    new_secret = "sk_v23_R405_" + hashlib.sha256((key_id + "regen").encode()).hexdigest()[:16]
    return {
        "status": "ok",
        "data": {
            "key_id":       key_id,
            "new_secret":   new_secret,
            "regenerated_at": datetime.utcnow().isoformat() + "Z",
            "regenerated_by": "u_001",
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
    print(f'✅ 加 5 函数 (R405)')
else:
    print('❌ 没找到')