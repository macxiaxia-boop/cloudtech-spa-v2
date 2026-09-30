"""V23 R370 加 5 动态路由函数: skills delete + billing cancel + campaigns duplicate + files rename + auth sessions"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_delete(skill_id: str):
    """Skill delete · 删除 skill (R370)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "deleted":    True,
            "deleted_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_cancel(invoice_id: str):
    """Billing cancel · 取消账单 (R370)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "cancelled":    True,
            "cancelled_at": datetime.utcnow().isoformat() + "Z",
            "reason":       "user_requested",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_duplicate(campaign_id: str):
    """Campaigns duplicate · 复制活动 (R370)"""
    return {
        "status": "ok",
        "data": {
            "source_campaign_id":  campaign_id,
            "new_campaign_id":     f"c_{campaign_id}_copy_v23",
            "name":                f"{campaign_id} 副本",
            "starts_at":           datetime.utcnow().isoformat() + "Z",
            "cloned_at":           datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_rename(file_id: str):
    """Files rename · 重命名文件 (R370)"""
    return {
        "status": "ok",
        "data": {
            "file_id":       file_id,
            "previous_name": f"file_{file_id}.bin",
            "new_name":      f"renamed_{file_id}_v23.pdf",
            "renamed_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions():
    """Auth sessions · 当前用户所有 session (R370)"""
    return {
        "status": "ok",
        "data": [
            {"session_id": "s_001", "ip": "127.0.0.1",     "device": "Edge/Windows", "last_active_at": "2026-09-30T16:14:00Z", "current": True},
            {"session_id": "s_002", "ip": "192.168.1.42",  "device": "Chrome/macOS", "last_active_at": "2026-09-30T16:10:00Z", "current": False},
            {"session_id": "s_003", "ip": "192.168.1.88",  "device": "Safari/iOS",  "last_active_at": "2026-09-30T15:30:00Z", "current": False},
            {"session_id": "s_004", "ip": "10.0.0.15",    "device": "Edge/Windows", "last_active_at": "2026-09-30T14:20:00Z", "current": False},
        ],
        "count":       4,
        "current_id": "s_001",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R370)')
else:
    print('❌ 没找到')