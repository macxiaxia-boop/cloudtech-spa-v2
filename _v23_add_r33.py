"""V23 R391 加 5 动态路由: skills import + billing subscription-resume + campaign audience-aggressive + file restore-from-trash + auth sessions/{id}/forget-device"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_import_v2(skill_id: str):
    """Skill import v2 · 导入 (R391)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "imported":        True,
            "imported_from":   f"https://marketplace.v23.com/skills/{skill_id}.yaml",
            "size_kb":         18,
            "dependencies":    ["@xyflow/react", "lucide-react", "tailwindcss"],
            "imported_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_resume(tenant_id: str):
    """Billing subscription resume · 恢复订阅 (R391)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R391",
            "resumed":         True,
            "resumed_at":      datetime.utcnow().isoformat() + "Z",
            "next_billing_at": "2026-10-15T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_aggressive(campaign_id: str):
    """Campaigns audience-aggressive · 受众激增 (R391)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "aggressive":    True,
            "expansion_pct":  "+200%",
            "new_segments":  12,
            "extra_reach":    36840,
            "applied_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_restore_from_trash(file_id: str):
    """Files restore-from-trash · 从回收站恢复 (R391)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "restored":    True,
            "restored_at": datetime.utcnow().isoformat() + "Z",
            "from_trash":  True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_forget_device(session_id: str):
    """Auth sessions/{id}/forget-device · 忘记设备 (R391)"""
    return {
        "status": "ok",
        "data": {
            "session_id":     session_id,
            "device_forgot":  True,
            "forgot_at":      datetime.utcnow().isoformat() + "Z",
            "trusted_until":  None,
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
    print(f'✅ 加 5 函数 (R391)')
else:
    print('❌ 没找到')