"""V23 R422 加 5 动态路由: skills merge-with-bundle + billing payment-methods/{id}/set-default-payment-method + campaign audience-region-stats + file download-by-day-chart-v3 + auth api-keys/{id}/quota-reset"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_merge_with_bundle(skill_id: str):
    """Skill merge-with-bundle · 合并到 bundle (R422)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "merged_with": f"bundle_v23_R422_{skill_id}",
            "merged_at":  datetime.utcnow().isoformat() + "Z",
            "size_bytes": 18432,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_payment_method(method_id: str):
    """Billing payment-methods/{id}/set-default-payment-method · 设默认支付方式 (R422)"""
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


def get_campaigns_audience_region_stats(campaign_id: str):
    """Campaigns audience-region-stats · 地域统计 (R422)"""
    return {
        "status": "ok",
        "data": [
            {"region": "一线城市",  "count": 6240, "pct": 33.9, "avg_ltv": 1999},
            {"region": "新一线",    "count": 4180, "pct": 22.7, "avg_ltv": 1680},
            {"region": "二线城市",  "count": 3120, "pct": 16.9, "avg_ltv": 1450},
            {"region": "三线城市",  "count": 2280, "pct": 12.4, "avg_ltv": 1180},
            {"region": "四线+",      "count": 1840, "pct": 10.0, "avg_ltv":  920},
            {"region": "海外",       "count":  760, "pct":  4.1, "avg_ltv": 2680},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart_v3(file_id: str):
    """Files download-by-day-chart-v3 · 按日下载 chart v3 (R422)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载",       "data": [28, 42, 38, 56, 68, 42, 38], "type": "bar"},
                {"label": "唯一访客",   "data": [18, 28, 22, 38, 45, 28, 24], "type": "bar"},
                {"label": "新访客",     "data": [ 8, 14, 12, 18, 22, 14, 14], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset(key_id: str):
    """Auth api-keys/{id}/quota-reset · 重置 quota (R422)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      20000,
            "previous_quota": 10000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
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
    print(f'✅ 加 5 函数 (R422)')
else:
    print('❌ 没找到')