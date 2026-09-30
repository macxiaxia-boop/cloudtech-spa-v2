"""V23 R388 加 5 动态路由: skills rollback + billing dunning + campaign budget-pacing + file external-share + auth sessions/{id}/trust"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_rollback(skill_id: str):
    """Skill rollback · 回滚 skill (R388)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":         skill_id,
            "rolled_back_to":   "v2.0.5",
            "rolled_back_at":   datetime.utcnow().isoformat() + "Z",
            "previous_version": "v2.1.0",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_dunning(invoice_id: str):
    """Billing dunning · 催收 (R388)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "dunning_sent": True,
            "reminders":    2,
            "level":        "final",
            "next_action":  "账户暂停 (7 天后)",
            "sent_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_budget_pacing(campaign_id: str):
    """Campaigns budget pacing · 预算节奏 (R388)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":     campaign_id,
            "daily_budget":    500,
            "spent_today":     287,
            "pace_left":       213,
            "pace_pct":        "57.4%",
            "expected_pace":   "62.5%",
            "recommendation":  "✓ 节奏正常",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_external_share(file_id: str):
    """Files external share · 外部分享 (R388)"""
    return {
        "status": "ok",
        "data": {
            "file_id":         file_id,
            "external_url":    f"https://ext.cloudtech.example.com/share/{file_id}?token=v23_R388",
            "external_token":  "ext_v23_R388_" + file_id,
            "expires_at":      "2026-10-30T00:00:00Z",
            "password_protected": True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_trust(session_id: str):
    """Auth sessions/{id}/trust · 信任设备 (R388)"""
    return {
        "status": "ok",
        "data": {
            "session_id":      session_id,
            "trusted":         True,
            "trusted_until":   "2027-09-30T00:00:00Z",
            "trusted_by":      "u_001",
            "trusted_at":      datetime.utcnow().isoformat() + "Z",
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
    print(f'✅ 加 5 函数 (R388)')
else:
    print('❌ 没找到')