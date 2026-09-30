"""V23 R427 加 5 动态路由: skills unsubscribe + billing payment-methods/{id}/set-default-for + campaign audience-region-detailed + file download-by-quarter-list + auth api-keys/{id}/throttle-events"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8")

new_funcs = '''def get_skills_unsubscribe(skill_id: str):
    """Skill unsubscribe · 取消订阅 (R427)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "unsubscribed_at": datetime.utcnow().isoformat() + "Z",
            "unsubscribed_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_for(method_id: str):
    """Billing payment-methods/{id}/set-default-for · 设默认给 (R427)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "set_for":    ["subscription", "billing"],
            "set_at":     datetime.utcnow().isoformat() + "Z",
            "set_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_detailed(campaign_id: str):
    """Campaigns audience-region-detailed · 地域详细 (R427)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",   "city": "深圳",   "count": 11800, "pct": 64.1},
            {"region": "上海",   "city": "上海",   "count":  2780, "pct": 15.1},
            {"region": "北京",   "city": "北京",   "count":  2120, "pct": 11.5},
            {"region": "广州",   "city": "广州",   "count":  1820, "pct":  9.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_list(file_id: str):
    """Files download-by-quarter-list · 按季度列表 (R427)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads":  428},
            {"quarter": "Q2 2026", "downloads":  728},
            {"quarter": "Q3 2026", "downloads": 1287},
        ],
        "total": 2443,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_events(key_id: str):
    """Auth api-keys/{id}/throttle-events · 限流事件 (R427)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T15:30:00Z", "rate": 89,  "limit": 100, "action": "ok"},
            {"at": "2026-09-30T16:00:00Z", "rate": 102, "limit": 100, "action": "throttle"},
            {"at": "2026-09-30T16:15:00Z", "rate": 42,  "limit": 100, "action": "ok"},
            {"at": "2026-09-30T16:30:00Z", "rate": 67,  "limit": 100, "action": "ok"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R427)')
else:
    print('❌ 没找到')