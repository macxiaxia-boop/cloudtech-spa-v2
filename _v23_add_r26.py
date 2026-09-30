"""V23 R383 加 5 动态路由: skills stats + billing invoice-template + campaign cost-breakdown + file share-stats + auth 2fa/regenerate"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_stats(skill_id: str):
    """Skill stats · skill 统计 (R383)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "active_users":   87,
            "total_invocations": 1248,
            "success_rate":   "96.4%",
            "avg_response_ms": 412,
            "by_day": [
                {"date": "2026-09-24", "invocations": 145},
                {"date": "2026-09-25", "invocations": 168},
                {"date": "2026-09-26", "invocations": 192},
                {"date": "2026-09-27", "invocations": 184},
                {"date": "2026-09-28", "invocations": 210},
                {"date": "2026-09-29", "invocations": 178},
                {"date": "2026-09-30", "invocations": 171},
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_template():
    """Billing invoice template · 账单模板 (R383)"""
    return {
        "status": "ok",
        "data": {
            "templates": [
                {"template_id": "tpl_001", "name": "标准发票",     "language": "zh-CN", "fields": ["invoice_no", "tenant", "amount", "items", "tax_id"]},
                {"template_id": "tpl_002", "name": "增值税专票", "language": "zh-CN", "fields": ["invoice_no", "tenant", "amount", "items", "tax_id", "bank_info"]},
                {"template_id": "tpl_003", "name": "英文发票",   "language": "en-US", "fields": ["invoice_no", "tenant", "amount", "items", "tax_id"]},
            ],
            "default_template": "tpl_001",
            "source": "demo_seed",
            "ts": datetime.utcnow().isoformat() + "Z",
        },
    }


def get_campaigns_cost_breakdown(campaign_id: str):
    """Campaigns cost breakdown · 成本细分 (R383)"""
    return {
        "status": "ok",
        "data": [
            {"category": "ad_spend",   "amount_yuan": 2800, "pct": 87.5},
            {"category": "creative",   "amount_yuan":  200, "pct":  6.3},
            {"category": "platform_fee","amount_yuan":  150, "pct":  4.7},
            {"category": "tools",       "amount_yuan":   50, "pct":  1.5},
        ],
        "total_yuan": 3200,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_stats(file_id: str):
    """Files share stats · 分享统计 (R383)"""
    return {
        "status": "ok",
        "data": {
            "file_id":           file_id,
            "total_shares":      8,
            "active_share_links": 5,
            "total_views":       142,
            "by_link": [
                {"link_id": "l_001", "views": 65, "unique": 18},
                {"link_id": "l_002", "views": 42, "unique": 12},
                {"link_id": "l_003", "views": 28, "unique": 8},
                {"link_id": "l_004", "views": 5,  "unique": 3},
                {"link_id": "l_005", "views": 2,  "unique": 1},
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_2fa_regenerate():
    """Auth 2FA regenerate · 重新生成 2FA 备份码 (R383)"""
    return {
        "status": "ok",
        "data": {
            "user_id":     "u_001",
            "backup_codes": [
                "v23_R383_bk_001",
                "v23_R383_bk_002",
                "v23_R383_bk_003",
                "v23_R383_bk_004",
                "v23_R383_bk_005",
                "v23_R383_bk_006",
                "v23_R383_bk_007",
                "v23_R383_bk_008",
                "v23_R383_bk_009",
                "v23_R383_bk_010",
            ],
            "regenerated_at": datetime.utcnow().isoformat() + "Z",
            "old_codes_invalidated": True,
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
    print(f'✅ 加 5 函数 (R383)')
else:
    print('❌ 没找到')