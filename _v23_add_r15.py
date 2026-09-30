"""V23 R372 加 5 动态路由: skills import + billing receipt + campaign report/export + file versions + auth logout-all"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_import(skill_id: str):
    """Skill import · 导入 skill (R372)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "imported":       True,
            "imported_from":  f"https://marketplace.example.com/skills/{skill_id}",
            "imported_at":    datetime.utcnow().isoformat() + "Z",
            "size_kb":        12,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_receipt(invoice_id: str):
    """Billing receipt · 收据 (R372)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "receipt_id":    f"rcpt_{invoice_id}_v23",
            "amount_yuan":   1999,
            "pdf_url":       f"/api/v2/billing/{invoice_id}/receipt.pdf",
            "issued_at":     datetime.utcnow().isoformat() + "Z",
            "tenant_id":     "t_3a59592b7619",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_report_export(campaign_id: str):
    """Campaigns report export · 报告导出 (R372)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":  campaign_id,
            "report_id":    f"rpt_{campaign_id}_v23_R372",
            "format":       "pdf",
            "url":          f"/api/v2/campaigns/{campaign_id}/report.pdf",
            "size_bytes":   524288,
            "pages":        12,
            "exported_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_versions(file_id: str):
    """Files versions · 文件版本 (R372)"""
    return {
        "status": "ok",
        "data": [
            {"version": 5, "size_bytes": 2400000, "created_at": "2026-09-30T10:00:00Z", "author": "u_001", "comment": "Latest version"},
            {"version": 4, "size_bytes": 2350000, "created_at": "2026-09-29T15:30:00Z", "author": "u_002", "comment": "Updated content"},
            {"version": 3, "size_bytes": 2300000, "created_at": "2026-09-28T11:00:00Z", "author": "u_001", "comment": "Initial upload"},
            {"version": 2, "size_bytes": 2100000, "created_at": "2026-09-27T14:00:00Z", "author": "u_001", "comment": "First draft"},
            {"version": 1, "size_bytes": 1800000, "created_at": "2026-09-26T09:00:00Z", "author": "u_002", "comment": "Created"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_logout_all():
    """Auth logout-all · 全设备注销 (R372)"""
    return {
        "status": "ok",
        "data": {
            "logged_out_devices": 4,
            "kept_current":       False,
            "logged_out_at":      datetime.utcnow().isoformat() + "Z",
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
    print(f'✅ 加 5 函数 (R372)')
else:
    print('❌ 没找到')