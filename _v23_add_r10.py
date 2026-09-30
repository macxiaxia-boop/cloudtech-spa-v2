"""V23 R366 加 5 动态路由函数: campaigns budget/audience + email preview + files share + auth 2fa"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_campaign_budget(campaign_id: str):
    """Campaign budget · 调整预算 (R366)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "previous_budget_yuan": 18000,
            "updated_budget_yuan":  25000,
            "spent_yuan":           8420,
            "remaining_yuan":       16580,
            "updated_at":           datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_audience(campaign_id: str):
    """Campaign audience · 受众细分 (R366)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id": campaign_id,
            "total_audience": 18420,
            "by_segment": [
                {"segment": "装企老板",     "count": 5240, "pct": 28.5},
                {"segment": "装企员工",     "count": 3120, "pct": 16.9},
                {"segment": "医美院长",     "count": 2180, "pct": 11.8},
                {"segment": "教育机构",     "count": 1980, "pct": 10.8},
                {"segment": "制造业老板",   "count": 2640, "pct": 14.3},
                {"segment": "服务从业者",   "count": 3260, "pct": 17.7},
            ],
            "by_channel": {
                "微信": 8240, "小红书": 4180, "抖音": 3640, "公众号": 2360,
            },
            "updated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_preview(item_id: str):
    """Email queue preview · 邮件预览 (R366)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    try:
        item_id_int = int(item_id)
        rows = db_query("SELECT id, to_email, template, subject, body_html FROM email_queue WHERE id=? LIMIT 1", (item_id_int,))
    except (ValueError, TypeError):
        rows = []
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "rendered":    True,
            "preview_url": f"/api/v2/email_queue/{item_id}/preview.html",
        },
        "source": "cloudtech.db.email_queue",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_file_share(file_id: str):
    """File share · 文件分享链接 (R366)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "share_url":   f"https://cloudtech.example.com/share/{file_id}?token=v23_R366",
            "share_token": "share_v23_R366_" + file_id,
            "expires_at":  "2026-10-07T00:00:00Z",
            "permissions": ["view", "download"],
            "password_protected": False,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_2fa():
    """Auth 2FA · 两步验证 (R366)"""
    return {
        "status": "ok",
        "data": {
            "challenge_id":   "ch_v23_R366_2fa_demo",
            "method":         "totp",
            "qr_code_url":    "/api/v2/auth/2fa/qr.png",
            "backup_codes":   ["backup_001", "backup_002", "backup_003"],
            "expires_in":     300,
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
    print(f'✅ 加 5 函数 (R366)')
else:
    print('❌ 没找到')