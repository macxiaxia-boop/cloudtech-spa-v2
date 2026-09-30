"""V23 R393 加 5 动态路由: skills retire + billing tax-rate-update + campaign recipients-stats + file comments/{id}/reply + auth devices/{id}/revoke"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_retire(skill_id: str):
    """Skill retire · 退役 skill (R393)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "retired":    True,
            "retired_at": datetime.utcnow().isoformat() + "Z",
            "archived":   True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_rate_update(tenant_id: str):
    """Billing tax-rate-update · 更新税率 (R393)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":   tenant_id,
            "previous_rate": 0.13,
            "updated_rate":  0.06,
            "updated_at":   datetime.utcnow().isoformat() + "Z",
            "reason":       "增值税改革",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_recipients_stats(campaign_id: str):
    """Campaigns recipients-stats · 收件人统计 (R393)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "total_sent":    4,
            "delivered":      3,
            "pending":       1,
            "delivery_rate": "75%",
            "by_channel": {
                "微信": {"sent": 2, "delivered": 2, "pending": 0},
                "邮件": {"sent": 1, "delivered": 1, "pending": 0},
                "短信": {"sent": 1, "delivered": 0, "pending": 1},
            },
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_reply(comment_id: str):
    """Files comments/{id}/reply · 评论回复 (R393)"""
    return {
        "status": "ok",
        "data": {
            "comment_id":   comment_id,
            "reply_id":     f"rep_{comment_id}_v23",
            "reply":        "已修复，请刷新查看",
            "replied_by":   "u_001",
            "replied_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_devices_revoke(device_id: str):
    """Auth devices/{id}/revoke · 撤销设备 (R393)"""
    return {
        "status": "ok",
        "data": {
            "device_id":   device_id,
            "revoked":     True,
            "revoked_at":  datetime.utcnow().isoformat() + "Z",
            "sessions_today":14,
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
    print(f'✅ 加 5 函数 (R393)')
else:
    print('❌ 没找到')