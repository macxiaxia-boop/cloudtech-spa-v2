"""V23 R382 加 5 动态路由: skills duplicate + billing charge-history + campaign conversion-funnel + file download-history + auth 2fa/disable"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_duplicate(skill_id: str):
    """Skill duplicate · 复制 skill (R382)"""
    return {
        "status": "ok",
        "data": {
            "source_skill_id": skill_id,
            "new_skill_id":    f"{skill_id}_copy_v23",
            "new_name":        f"{skill_id} 副本",
            "duplicated_at":   datetime.utcnow().isoformat() + "Z",
            "duplicated_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_charge_history(invoice_id: str):
    """Billing charge history · 扣款历史 (R382)"""
    return {
        "status": "ok",
        "data": [
            {"charge_id": "chg_001", "amount_yuan": 1999, "method": "wechat_pay", "success": True,  "at": "2026-08-15T03:00:00Z"},
            {"charge_id": "chg_002", "amount_yuan": 2999, "method": "alipay",     "success": True,  "at": "2026-09-01T03:00:00Z"},
            {"charge_id": "chg_003", "amount_yuan":  199, "method": "wechat_pay", "success": False, "at": "2026-09-15T03:00:00Z"},
            {"charge_id": "chg_004", "amount_yuan": 1999, "method": "wechat_pay", "success": True,  "at": "2026-09-25T03:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_conversion_funnel(campaign_id: str):
    """Campaigns conversion funnel · 转化漏斗 (R382)"""
    return {
        "status": "ok",
        "data": [
            {"stage": "曝光",  "count": 18420, "pct": 100.0},
            {"stage": "点击",  "count":   920, "pct":   5.0},
            {"stage": "访问",  "count":   480, "pct":   2.6},
            {"stage": "注册",  "count":   180, "pct":   0.98},
            {"stage": "试用",  "count":    72, "pct":   0.39},
            {"stage": "付费",  "count":    42, "pct":   0.23},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_history(file_id: str):
    """Files download history · 下载历史 (R382)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T16:00:00Z", "user_id": "u_001", "ip": "127.0.0.1",     "user_agent": "Edge/Windows"},
            {"at": "2026-09-29T14:30:00Z", "user_id": "u_002", "ip": "192.168.1.42",  "user_agent": "Chrome/macOS"},
            {"at": "2026-09-28T10:15:00Z", "user_id": "u_003", "ip": "192.168.1.88",  "user_agent": "Safari/iOS"},
            {"at": "2026-09-27T16:45:00Z", "user_id": "u_004", "ip": "10.0.0.15",    "user_agent": "Edge/Windows"},
            {"at": "2026-09-26T11:30:00Z", "user_id": "u_001", "ip": "127.0.0.1",     "user_agent": "Edge/Windows"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_2fa_disable():
    """Auth 2FA disable · 关闭 2FA (R382)"""
    return {
        "status": "ok",
        "data": {
            "user_id":      "u_001",
            "2fa_status":   "disabled",
            "disabled_at":  datetime.utcnow().isoformat() + "Z",
            "disabled_by":  "u_001",
            "backup_codes_deleted": 10,
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
    print(f'✅ 加 5 函数 (R382)')
else:
    print('❌ 没找到')