"""V23 R368 加 5 动态路由: billing pay + email stats + notifications mark-all + files upload-url + campaigns export"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_billing_pay(invoice_id: str):
    """Billing pay · 支付 (R368)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "payment_id":    f"pay_{invoice_id}_v23_R368",
            "amount_yuan":   1999,
            "method":        "wechat_pay",
            "paid_at":       datetime.utcnow().isoformat() + "Z",
            "receipt_url":   f"/api/v2/billing/{invoice_id}/receipt.pdf",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_stats():
    """Email queue stats · 邮件统计 (R368)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    total = db_query("SELECT COUNT(*) AS c FROM email_queue")[0]["c"]
    sent  = db_query("SELECT COUNT(*) AS c FROM email_queue WHERE status='sent'")[0]["c"]
    by_template = db_query("SELECT template, COUNT(*) AS c FROM email_queue GROUP BY template")
    return {
        "status": "ok",
        "data": {
            "total":     total,
            "sent":      sent,
            "pending":   total - sent,
            "by_template": {r["template"]: r["c"] for r in by_template},
            "delivery_rate":  round(sent / max(total, 1) * 100, 2),
        },
        "source": "cloudtech.db.email_queue",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications_mark_all():
    """Notifications mark-all · 全部标记已读 (R368)"""
    return {
        "status": "ok",
        "data": {
            "marked_count": 12,
            "marked_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_upload_url():
    """Files upload-url · 上传链接 (R368)"""
    return {
        "status": "ok",
        "data": {
            "upload_url":  "https://cloudtech.example.com/api/v2/files/upload?token=v23_R368",
            "upload_id":   "up_v23_R368_demo",
            "expires_at": "2026-09-30T17:00:00Z",
            "max_size_mb": 100,
            "accept":      ["image/*", "application/pdf", "video/mp4", ".zip"],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_export(campaign_id: str):
    """Campaigns export · 数据导出 (R368)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":  campaign_id,
            "export_url":   f"/api/v2/campaigns/{campaign_id}/export.csv",
            "format":       "csv",
            "rows":         312,
            "size_bytes":   245760,
            "expires_at":   "2026-10-01T00:00:00Z",
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
    print(f'✅ 加 5 函数 (R368)')
else:
    print('❌ 没找到')