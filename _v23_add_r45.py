"""V23 R403 加 5 动态路由: skills export-template + billing payment-methods/{id}/delete + campaign audience-frequency + file download-stats-by-file-type + auth api-keys/{id}/rotate-secret"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_export_template(skill_id: str):
    """Skill export-template · 导出模板 (R403)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "export_url":    f"/api/v2/skills/{skill_id}/export.yaml",
            "size_bytes":   8192,
            "format":       "yaml",
            "exported_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_delete(method_id: str):
    """Billing payment-methods/{id}/delete · 删除支付方式 (R403)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "deleted":   True,
            "deleted_at":datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_frequency(campaign_id: str):
    """Campaigns audience-frequency · 受众访问频次 (R403)"""
    return {
        "status": "ok",
        "data": [
            {"frequency": "daily",    "users": 6840, "pct": 37.1},
            {"frequency": "weekly",   "users": 8240, "pct": 44.7},
            {"frequency": "monthly",  "users": 2840, "pct": 15.4},
            {"frequency": "rarely",   "users":  500, "pct":  2.7},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_by_file_type(file_id: str):
    """Files download-stats-by-file-type · 按文件类型下载 (R403)"""
    return {
        "status": "ok",
        "data": [
            {"type": "PDF",    "count": 145, "pct": 46.5},
            {"type": "Image",  "count":  82, "pct": 26.3},
            {"type": "Video",  "count":  48, "pct": 15.4},
            {"type": "Doc",    "count":  24, "pct":  7.7},
            {"type": "Other",  "count":  13, "pct":  4.2},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret(key_id: str):
    """Auth api-keys/{id}/rotate-secret · 仅轮换 secret (R403)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "rotated":     False,
            "reason":      "rotate-secret 仅在 secret 暴露时用",
            "rotated_at":  None,
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
    print(f'✅ 加 5 函数 (R403)')
else:
    print('❌ 没找到')