"""V23 R400 加 5 动态路由: skills sync-template + billing payment-failed + campaign conversion-by-channel + file download-geo + auth api-keys/{id}/reset-quota"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_sync_template(skill_id: str):
    """Skill sync-template · 同步模板 (R400)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced":      True,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_with": "https://marketplace.example.com/templates/" + skill_id,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_failed(invoice_id: str):
    """Billing payment-failed · 支付失败 (R400)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "payment_id":    f"pay_{invoice_id}_v23",
            "failed":        True,
            "reason":        "card_declined",
            "retry_url":     f"https://cloudtech.example.com/billing/{invoice_id}/retry",
            "failed_at":     datetime.utcnow().isoformat() + "Z",
            "next_attempt_at": "2026-10-01T08:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_conversion_by_channel(campaign_id: str):
    """Campaigns conversion-by-channel · 按渠道转化 (R400)"""
    return {
        "status": "ok",
        "data": [
            {"channel": "小红书",   "impressions": 8240, "leads": 487, "conversions": 31, "cvr": "6.4%"},
            {"channel": "抖音",     "impressions": 6320, "leads": 312, "conversions": 24, "cvr": "7.7%"},
            {"channel": "公众号",   "impressions": 4180, "leads": 218, "conversions": 12, "cvr": "5.5%"},
            {"channel": "微信群",   "impressions": 3640, "leads": 156, "conversions": 8,  "cvr": "5.1%"},
            {"channel": "直接访问", "impressions": 3120, "leads": 64,  "conversions": 3,  "cvr": "4.7%"},
        ],
        "total_conversions": 78,
        "best_channel":      "抖音",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_geo(file_id: str):
    """Files download-geo · 下载地理 (R400)"""
    return {
        "status": "ok",
        "data": [
            {"country": "CN",  "city": "深圳",     "count":  98, "pct": 30.5},
            {"country": "CN",  "city": "上海",     "count":  68, "pct": 21.2},
            {"country": "CN",  "city": "北京",     "count":  56, "pct": 17.4},
            {"country": "US",  "city": "San Francisco", "count":  32, "pct": 10.0},
            {"country": "JP",  "city": "Tokyo",       "count":  18, "pct":  5.6},
            {"country": "EU",  "city": "London",      "count":  12, "pct":  3.7},
            {"country": "OTHER","city": "Other",       "count":  37, "pct": 11.5},
        ],
        "total": 321,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_reset_quota(key_id: str):
    """Auth api-keys/{id}/reset-quota · 重置配额 (R400)"""
    return {
        "status": "ok",
        "data": {
            "key_id":           key_id,
            "quota_reset":      True,
            "previous_quota":   5000,
            "new_quota":        10000,
            "reset_at":         datetime.utcnow().isoformat() + "Z",
            "reset_by":         "u_001",
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
    print(f'✅ 加 5 函数 (R400)')
else:
    print('❌ 没找到')