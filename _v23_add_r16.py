"""V23 R373 加 5 动态路由: skills export + billing invoice-list + campaigns pause-all + files duplicate + auth backup-codes"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_export(skill_id: str):
    """Skill export · 导出 skill (R373)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "export_url":   f"/api/v2/skills/{skill_id}/export.json",
            "format":       "json",
            "size_bytes":   4096,
            "exported_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_list():
    """Billing invoice list · 账单列表 (R373)"""
    return {
        "status": "ok",
        "data": [
            {"invoice_id": "inv_001", "amount_yuan": 1999, "status": "paid",    "created_at": "2026-08-15T00:00:00Z"},
            {"invoice_id": "inv_002", "amount_yuan": 2999, "status": "paid",    "created_at": "2026-09-01T00:00:00Z"},
            {"invoice_id": "inv_003", "amount_yuan":  199, "status": "pending", "created_at": "2026-09-15T00:00:00Z"},
            {"invoice_id": "inv_004", "amount_yuan": 1999, "status": "overdue", "created_at": "2026-09-25T00:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_pause_all():
    """Campaigns pause-all · 全部暂停 (R373)"""
    return {
        "status": "ok",
        "data": {
            "paused_count":  5,
            "previous_total_active": 6,
            "remaining_active":     1,
            "paused_at":            datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_duplicate(file_id: str):
    """Files duplicate · 复制文件 (R373)"""
    return {
        "status": "ok",
        "data": {
            "original_file_id": file_id,
            "new_file_id":      f"{file_id}_copy_v23",
            "new_name":         f"副本_{file_id}.pdf",
            "duplicated_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_backup_codes():
    """Auth backup codes · 备份码 (R373)"""
    return {
        "status": "ok",
        "data": {
            "codes": [
                "v23_R373_bk_001",
                "v23_R373_bk_002",
                "v23_R373_bk_003",
                "v23_R373_bk_004",
                "v23_R373_bk_005",
                "v23_R373_bk_006",
                "v23_R373_bk_007",
                "v23_R373_bk_008",
                "v23_R373_bk_009",
                "v23_R373_bk_010",
            ],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "regenerate_at": "2026-10-30T00:00:00Z",
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
    print(f'✅ 加 5 函数 (R373)')
else:
    print('❌ 没找到')