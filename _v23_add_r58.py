"""V23 R416 加 5 动态路由: skills import-from-instance + billing payment-methods/{id}/set-default-payment + campaign audience-tag-list + file download-by-year + auth api-keys/{id}/burst-quota"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_import_from_instance(skill_id: str):
    """Skill import-from-instance · 从实例导入 (R416)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "imported_id":  f"inst_v23_R416_{skill_id}",
            "imported_at": datetime.utcnow().isoformat() + "Z",
            "size_bytes":  16384,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_payment(method_id: str):
    """Billing payment-methods/{id}/set-default-payment · 设默认 (R416)"""
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


def get_campaigns_audience_tag_list(campaign_id: str):
    """Campaigns audience-tag-list · 受众标签 (R416)"""
    return {
        "status": "ok",
        "data": [
            {"tag_id": "t_001", "name": "vip",         "users":  680, "pct":  3.7},
            {"tag_id": "t_002", "name": "new",         "users": 4180, "pct": 22.7},
            {"tag_id": "t_003", "name": "loyal",       "users": 3280, "pct": 17.8},
            {"tag_id": "t_004", "name": "inactive",    "users": 2240, "pct": 12.2},
            {"tag_id": "t_005", "name": "high-value",  "users":  980, "pct":  5.3},
            {"tag_id": "t_006", "name": "lead",        "users": 6240, "pct": 33.9},
            {"tag_id": "t_007", "name": "competitor",  "users":  180, "pct":  1.0},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year(file_id: str):
    """Files download-by-year · 按年下载 (R416)"""
    return {
        "status": "ok",
        "data": [
            {"year": "2024", "downloads":  680},
            {"year": "2025", "downloads": 4180},
            {"year": "2026", "downloads": 3280},
        ],
        "total": 8140,
        "trend":        "+25%",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota(key_id: str):
    """Auth api-keys/{id}/burst-quota · 突发配额 (R416)"""
    return {
        "status": "ok",
        "data": {
            "key_id":            key_id,
            "burst_quota":       500,
            "burst_window":      "1 min",
            "current_usage":     58,
            "headroom":          42,
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
    print(f'✅ 加 5 函数 (R416)')
else:
    print('❌ 没找到')