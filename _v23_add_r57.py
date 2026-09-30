"""V23 R415 加 5 动态路由: skills unapply-template + billing payment-methods/{id}/set-inactive + campaign audience-segment-list + file download-by-month + auth api-keys/{id}/rate-limit"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_unapply_template(skill_id: str):
    """Skill unapply-template · 撤销模板应用 (R415)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "unapplied_at": datetime.utcnow().isoformat() + "Z",
            "unapplied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_inactive(method_id: str):
    """Billing payment-methods/{id}/set-inactive · 取消激活 (R415)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_segment_list(campaign_id: str):
    """Campaigns audience-segment-list · 受众分群列表 (R415)"""
    return {
        "status": "ok",
        "data": [
            {"segment_id": "seg_001", "name": "装企老板",   "size": 4280, "rule": "industry=decoration & role=owner"},
            {"segment_id": "seg_002", "name": "医美院长",   "size": 2180, "rule": "industry=medical & role=owner"},
            {"segment_id": "seg_003", "name": "教育机构",   "size": 1240, "rule": "industry=education & role=owner"},
            {"segment_id": "seg_004", "name": "制造老板",   "size": 2640, "rule": "industry=manufacturing & role=owner"},
            {"segment_id": "seg_005", "name": "服务从业",   "size": 3260, "rule": "industry=service & role=owner"},
            {"segment_id": "seg_006", "name": "高活跃用户", "size": 1840, "rule": "last_active_at >= 7d ago"},
            {"segment_id": "seg_007", "name": "低活跃用户", "size":  980, "rule": "last_active_at < 30d ago"},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month(file_id: str):
    """Files download-by-month · 按月下载 (R415)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168},
            {"month": "2026-05", "downloads": 248},
            {"month": "2026-06", "downloads": 312},
            {"month": "2026-07", "downloads": 428},
            {"month": "2026-08", "downloads": 487},
            {"month": "2026-09", "downloads": 312},
        ],
        "total": 1955,
        "peak_month": "2026-08",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rate_limit(key_id: str):
    """Auth api-keys/{id}/rate-limit · 限流 (R415)"""
    return {
        "status": "ok",
        "data": {
            "key_id":        key_id,
            "limit":         "100 req/min",
            "remaining":     58,
            "reset_at":      "2026-09-30T21:00:00Z",
            "current_usage": "42 req/min",
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
    print(f'✅ 加 5 函数 (R415)')
else:
    print('❌ 没找到')