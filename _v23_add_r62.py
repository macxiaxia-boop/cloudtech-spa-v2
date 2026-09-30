"""V23 R420 加 5 动态路由: skills push-to-marketplace + billing payment-methods/{id}/unset-backup + campaign audience-region-list + file download-quarter-chart + auth api-keys/{id}/throttle-current-state"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_push_to_marketplace(skill_id: str):
    """Skill push-to-marketplace · 推到 marketplace (R420)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "pushed_to":    f"marketplace_v23_R420_{skill_id}",
            "pushed_at":   datetime.utcnow().isoformat() + "Z",
            "visibility":  "public",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_backup(method_id: str):
    """Billing payment-methods/{id}/unset-backup · 取消备用 (R420)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_backup":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_list(campaign_id: str):
    """Campaigns audience-region-list · 地域列表 (R420)"""
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
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_quarter_chart(file_id: str):
    """Files download-quarter-chart · 按季度下载 chart (R420)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Q1 2026", "Q2 2026", "Q3 2026"],
            "datasets": [
                {"label": "下载",   "data": [428, 728, 1287], "type": "bar"},
                {"label": "唯一访客", "data": [318, 528,  920], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_current_state(key_id: str):
    """Auth api-keys/{id}/throttle-current-state · 当前限流状态 (R420)"""
    return {
        "status": "ok",
        "data": {
            "key_id":            key_id,
            "current_rate":      42,
            "limit":             500,
            "headroom":          458,
            "reset_in_seconds":  48,
            "state":             "healthy",
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
    print(f'✅ 加 5 函数 (R420)')
else:
    print('❌ 没找到')