"""V23 R390 加 5 动态路由: skills deprecate + billing subscription-pause + campaign audience-stats + file duplicate-rename + auth sessions/{id}/impersonate"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_deprecate(skill_id: str):
    """Skill deprecate · 弃用 skill (R390)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "deprecated":    True,
            "deprecated_at": datetime.utcnow().isoformat() + "Z",
            "grace_until":    "2026-12-30T00:00:00Z",
            "migration":      "plan_global_skill_v3_v23",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_pause(tenant_id: str):
    """Billing subscription pause · 暂停订阅 (R390)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R390",
            "paused":          True,
            "paused_at":       datetime.utcnow().isoformat() + "Z",
            "resume_at":      "2026-11-30T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_stats(campaign_id: str):
    """Campaigns audience stats · 受众统计 (R390)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":      campaign_id,
            "total_reached":    18420,
            "engaged":          4180,
            "engagement_rate":  "22.7%",
            "by_age": {
                "18-24": 1840, "25-34": 6280, "35-44": 5240, "45-54": 3240, "55+": 1820,
            },
            "by_gender": {
                "male":   9240, "female": 8640, "other": 540,
            },
            "by_location": {
                "深圳": 2840, "上海": 2280, "北京": 2120, "广州": 1820, "其他": 9360,
            },
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_duplicate_rename(file_id: str):
    """Files duplicate-rename · 复制+重命名 (R390)"""
    return {
        "status": "ok",
        "data": {
            "source_file_id": file_id,
            "new_file_id":    f"{file_id}_v23_R390",
            "new_name":       f"副本_{file_id}_R390.pdf",
            "duplicated_at":  datetime.utcnow().isoformat() + "Z",
            "renamed_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_impersonate(session_id: str):
    """Auth sessions/{id}/impersonate · 模拟 session (R390)"""
    return {
        "status": "ok",
        "data": {
            "impersonated_session_id":  session_id,
            "impersonated_by":           "u_001",
            "impersonated_user":         "u_002",
            "impersonated_at":           datetime.utcnow().isoformat() + "Z",
            "expires_at":                "2026-09-30T20:00:00Z",
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
    print(f'✅ 加 5 函数 (R390)')
else:
    print('❌ 没找到')