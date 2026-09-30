"""V23 R377 加 5 动态路由: skills version + billing charge + campaigns schedule + files lock + auth sso"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_version(skill_id: str):
    """Skill version · 版本管理 (R377)"""
    return {
        "status": "ok",
        "data": [
            {"version": "v2.1.0", "created_at": "2026-09-30T10:00:00Z", "is_latest": True,  "deprecated": False, "changelog": "+ 新增对话缓存 + 优化 prompt"},
            {"version": "v2.0.5", "created_at": "2026-09-15T10:00:00Z", "is_latest": False, "deprecated": False, "changelog": "+ 修复边界条件"},
            {"version": "v2.0.0", "created_at": "2026-09-01T10:00:00Z", "is_latest": False, "deprecated": False, "changelog": "+ 全新 UI"},
            {"version": "v1.5.0", "created_at": "2026-08-01T10:00:00Z", "is_latest": False, "deprecated": True,  "changelog": "+ 旧版本"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_charge(invoice_id: str):
    """Billing charge · 扣款 (R377)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "charge_id":     f"chg_{invoice_id}_v23",
            "amount_yuan":   1999,
            "method":        "wechat_pay",
            "success":       True,
            "transaction_id": f"txn_{invoice_id}_v23",
            "charged_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_schedule(campaign_id: str):
    """Campaigns schedule · 排期 (R377)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "scheduled_at":  "2026-10-01T09:00:00Z",
            "duration_days": 14,
            "timezone":      "Asia/Shanghai",
            "auto_publish":  True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_lock(file_id: str):
    """Files lock · 文件锁 (R377)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "locked":      True,
            "locked_by":   "u_001",
            "locked_at":   datetime.utcnow().isoformat() + "Z",
            "expires_at":  "2026-09-30T20:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sso():
    """Auth SSO · 单点登录 (R377)"""
    return {
        "status": "ok",
        "data": {
            "sso_url":      "https://cloudtech.example.com/api/v2/auth/sso/redirect?token=sso_v23_R377&return=/dashboard",
            "providers":    ["wechat_work", "feishu", "dingtalk", "microsoft", "google", "github"],
            "current":      "wechat_work",
            "expires_in":   3600,
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
    print(f'✅ 加 5 函数 (R377)')
else:
    print('❌ 没找到')