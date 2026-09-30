"""V23 R364 加 5 动态路由函数: sessions revoke + billing invoice + notifications read + leads update + campaigns pause"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_session_revoke(item_id: str):
    """Sessions revoke · 撤销会话 (R364)"""
    return {
        "status": "ok",
        "data": {
            "session_id":   item_id,
            "revoked":      True,
            "revoked_at":   datetime.utcnow().isoformat() + "Z",
            "active_sessions_remaining": 3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice(invoice_id: str):
    """Billing invoice · 账单 (R364)"""
    invoices = {
        "inv_001": {"amount_yuan": 1999, "plan": "pro",       "status": "paid"},
        "inv_002": {"amount_yuan": 2999, "plan": "enterprise","status": "paid"},
        "inv_003": {"amount_yuan": 199,  "plan": "basic",    "status": "pending"},
        "inv_004": {"amount_yuan": 1999, "plan": "pro",       "status": "overdue"},
    }
    inv = invoices.get(invoice_id)
    if not inv:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            **inv,
            "tenant_id":    "t_3a59592b7619",
            "created_at":   "2026-09-30T00:00:00Z",
            "due_at":       "2026-10-15T00:00:00Z",
            "pdf_url":      f"/api/v2/billing/{invoice_id}/invoice.pdf",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications_read(notif_id: str):
    """Notifications read · 标记已读 (R364)"""
    return {
        "status": "ok",
        "data": {
            "notif_id":  notif_id,
            "read":      True,
            "read_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_lead_update(lead_id: str):
    """Leads update · 客户阶段更新 (R364)"""
    if not safe_db_table("leads"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    rows = db_query("SELECT id, customer_name, industry, stage FROM leads WHERE id=? LIMIT 1", (lead_id,))
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    # 模拟 stage 推进 pending → contacted
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "previous_stage":   "pending",
            "updated_stage":    "contacted",
            "updated_at":       datetime.utcnow().isoformat() + "Z",
            "next_action":      "已安排外呼，下周一 14:00",
        },
        "source": "cloudtech.db.leads",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_pause(campaign_id: str):
    """Campaigns pause · 暂停营销活动 (R364)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "previous_status": "active",
            "updated_status":  "paused",
            "paused_at":        datetime.utcnow().isoformat() + "Z",
            "remaining_budget":  0,
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
    print(f'✅ 加 5 函数 (R364)')
else:
    print('❌ 没找到')