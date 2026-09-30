"""V23 R401 加 5 动态路由: skills validate-template + billing payment-retry + campaign engagement-rate + file download-stats-geo + auth api-keys/{id}/permissions-update"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_validate_template(skill_id: str):
    """Skill validate-template · 验证模板 (R401)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "valid":           True,
            "validated_at":    datetime.utcnow().isoformat() + "Z",
            "errors":          [],
            "warnings":        [],
            "stats":           {"nodes": 5, "edges": 4, "triggers": 1, "actions": 2},
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_retry(invoice_id: str):
    """Billing payment-retry · 重新支付 (R401)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "retry_id":     f"retry_{invoice_id}_v23",
            "success":      True,
            "method":       "wechat_pay",
            "retry_at":     datetime.utcnow().isoformat() + "Z",
            "amount_yuan":  1999,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_engagement_rate(campaign_id: str):
    """Campaigns engagement-rate · 互动率 (R401)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "views": 8240, "engagements": 248, "rate": "3.0%"},
            {"date": "2026-09-25", "views": 9120, "engagements": 312, "rate": "3.4%"},
            {"date": "2026-09-26", "views": 8780, "engagements": 287, "rate": "3.3%"},
            {"date": "2026-09-27", "views": 9420, "engagements": 348, "rate": "3.7%"},
            {"date": "2026-09-28", "views": 10120, "engagements": 412, "rate": "4.1%"},
            {"date": "2026-09-29", "views": 9870, "engagements": 398, "rate": "4.0%"},
            {"date": "2026-09-30", "views": 10540, "engagements": 456, "rate": "4.3%"},
        ],
        "average_rate": "3.7%",
        "trend":        "+0.7%",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_geo(file_id: str):
    """Files download-stats-geo · 下载地理统计 (R401)"""
    return {
        "status": "ok",
        "data": [
            {"country": "CN",  "city": "深圳",  "downloads":  98, "unique":  62},
            {"country": "CN",  "city": "上海",  "downloads":  68, "unique":  45},
            {"country": "CN",  "city": "北京",  "downloads":  56, "unique":  38},
            {"country": "US",  "city": "SF",    "downloads":  32, "unique":  28},
            {"country": "JP",  "city": "Tokyo", "downloads":  18, "unique":  16},
            {"country": "EU",  "city": "Lon",   "downloads":  12, "unique":  10},
        ],
        "total_downloads": 284,
        "total_unique":     199,
        "top_country":      "CN (深圳)",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_permissions_update(key_id: str):
    """Auth api-keys/{id}/permissions-update · 更新权限 (R401)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "scopes":      ["read", "write", "deploy", "admin"],
            "updated_at":  datetime.utcnow().isoformat() + "Z",
            "updated_by":  "u_001",
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
    print(f'✅ 加 5 函数 (R401)')
else:
    print('❌ 没找到')