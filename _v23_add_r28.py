"""V23 R386 加 5 动态路由: skills reset + billing coupon + campaign recipients + file share-list + auth sessions/{id}/signout"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_reset(skill_id: str):
    """Skill reset · 重置 skill (R386)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "reset":       True,
            "reset_at":    datetime.utcnow().isoformat() + "Z",
            "kept_stats":  True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_coupon(coupon_code: str):
    """Billing coupon · 优惠券 (R386)"""
    coupons = {
        "V23_R386":     {"discount_pct": 50, "valid_until": "2026-10-30T00:00:00Z", "min_amount_yuan": 1000},
        "EARLY_BIRD":  {"discount_pct": 30, "valid_until": "2026-09-30T23:59:59Z", "min_amount_yuan": 500},
        "FRIENDS_50":  {"discount_pct": 50, "valid_until": "2026-12-31T23:59:59Z", "min_amount_yuan": 199},
    }
    found = coupons.get(coupon_code)
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            "coupon_code":  coupon_code,
            **found,
            "applied_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_recipients(campaign_id: str):
    """Campaigns recipients · 收件人 (R386)"""
    return {
        "status": "ok",
        "data": [
            {"user_id": "u_001", "name": "心之所向便是光", "channel": "微信",   "status": "delivered", "at": "2026-09-30T16:00:00Z"},
            {"user_id": "u_002", "name": "运维",          "channel": "邮件",   "status": "delivered", "at": "2026-09-30T16:00:01Z"},
            {"user_id": "u_003", "name": "销售",          "channel": "微信",   "status": "delivered", "at": "2026-09-30T16:00:02Z"},
            {"user_id": "u_004", "name": "客服",          "channel": "短信",   "status": "pending",   "at": "2026-09-30T16:00:03Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_list(file_id: str):
    """Files share list · 分享链接列表 (R386)"""
    return {
        "status": "ok",
        "data": [
            {"link_id": "l_001", "url": f"https://cloudtech.example.com/share/{file_id}", "permissions": ["view"],          "views": 65, "created_at": "2026-09-25T10:00:00Z"},
            {"link_id": "l_002", "url": f"https://cloudtech.example.com/share/{file_id}/e",  "permissions": ["view", "download"], "views": 42, "created_at": "2026-09-28T10:00:00Z"},
        ],
        "count": 2,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_signout(session_id: str):
    """Auth sessions/{id}/signout · 撤销单 session (R386)"""
    return {
        "status": "ok",
        "data": {
            "session_id":   session_id,
            "signed_out":   True,
            "signed_out_at": datetime.utcnow().isoformat() + "Z",
            "active_sessions_remaining": 3,
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
    print(f'✅ 加 5 函数 (R386)')
else:
    print('❌ 没找到')