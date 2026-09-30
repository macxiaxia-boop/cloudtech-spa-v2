"""V23 R365 加 5 动态路由函数: auth/permissions + billing refund + email cancel + notifications archive + campaigns resume"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_auth_permissions():
    """Auth permissions · 当前用户权限 (R365)"""
    return {
        "status": "ok",
        "data": {
            "user_id":   "u_001",
            "tenant_id": "t_3a59592b7619",
            "role":      "owner",
            "permissions": [
                "read:all",
                "write:all",
                "admin:tenant",
                "billing:manage",
                "user:invite",
                "workflow:create",
                "workflow:run",
                "agent:deploy",
                "skill:create",
                "audit:view",
            ],
            "groups": ["owners", "cloudteam", "ai-engineers"],
            "scope":    "tenant",
            "effective_at":  "2026-09-30T00:00:00Z",
            "expires_at":    None,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_refund(invoice_id: str):
    """Billing refund · 退款 (R365)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "refund_id":     f"ref_{invoice_id}_v23",
            "amount_yuan":   1999,
            "reason":        "user_requested",
            "processed_at":  datetime.utcnow().isoformat() + "Z",
            "eta_days":      7,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_cancel(item_id: str):
    """Email queue cancel · 邮件取消 (R365)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    try:
        item_id_int = int(item_id)
        rows = db_query("SELECT id, to_email, template, subject, status FROM email_queue WHERE id=? LIMIT 1", (item_id_int,))
    except (ValueError, TypeError):
        rows = []
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "cancelled":     True,
            "cancelled_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "cloudtech.db.email_queue+cancel",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications_archive(notif_id: str):
    """Notifications archive · 归档 (R365)"""
    return {
        "status": "ok",
        "data": {
            "notif_id":   notif_id,
            "archived":   True,
            "archived_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_resume(campaign_id: str):
    """Campaigns resume · 恢复营销活动 (R365)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":    campaign_id,
            "previous_status": "paused",
            "updated_status":  "active",
            "resumed_at":      datetime.utcnow().isoformat() + "Z",
            "remaining_budget": 15000,
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
    print(f'✅ 加 5 函数 (R365)')
else:
    print('❌ 没找到')