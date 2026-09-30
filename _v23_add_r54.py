"""V23 R412 加 5 动态路由: skills export-bundle + billing payment-methods/{id}/validate-balance + campaign audience-tech-stats + file download-by-hour + auth api-keys/{id}/usage-stats"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_export_bundle(skill_id: str):
    """Skill export-bundle · 导出 bundle (R412)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "bundle_id":  f"bundle_v23_R412_{skill_id}",
            "exported_at":datetime.utcnow().isoformat() + "Z",
            "size_bytes": 24576,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_validate_balance(method_id: str):
    """Billing payment-methods/{id}/validate-balance · 验证余额 (R412)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "balance_yuan":   50000,
            "is_sufficient":  True,
            "validated_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_stats(campaign_id: str):
    """Campaigns audience-tech-stats · 受众技术 (R412)"""
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
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_hour(file_id: str):
    """Files download-by-hour · 按小时下载 (R412)"""
    return {
        "status": "ok",
        "data": [
            {"hour":  0, "count":  2},
            {"hour":  1, "count":  1},
            {"hour":  2, "count":  0},
            {"hour":  3, "count":  1},
            {"hour":  4, "count":  0},
            {"hour":  5, "count":  0},
            {"hour":  6, "count":  0},
            {"hour":  7, "count":  2},
            {"hour":  8, "count":  8},
            {"hour":  9, "count":  28},
            {"hour": 10, "count":  42},
            {"hour": 11, "count":  38},
            {"hour": 12, "count":  48},
            {"hour": 13, "count":  42},
            {"hour": 14, "count":  56},
            {"hour": 15, "count":  42},
            {"hour": 16, "count":  28},
            {"hour": 17, "count":  18},
            {"hour": 18, "count":  12},
            {"hour": 19, "count":  8},
            {"hour": 20, "count":  4},
            {"hour": 21, "count":  2},
            {"hour": 22, "count":  2},
            {"hour": 23, "count":  0},
        ],
        "peak_hour":   14,
        "peak_count":  56,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_usage_stats(key_id: str):
    """Auth api-keys/{id}/usage-stats · 使用统计 (R412)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "total_calls":     8247,
            "by_day": [
                {"date": "2026-09-24", "calls": 1248},
                {"date": "2026-09-25", "calls": 1362},
                {"date": "2026-09-26", "calls": 1148},
                {"date": "2026-09-27", "calls": 1287},
                {"date": "2026-09-28", "calls": 1428},
                {"date": "2026-09-29", "calls": 1042},
                {"date": "2026-09-30", "calls":  732},
            ],
            "quota_used":     "8247/10000",
            "remaining":      1753,
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
    print(f'✅ 加 5 函数 (R412)')
else:
    print('❌ 没找到')