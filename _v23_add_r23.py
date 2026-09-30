"""V23 R380 加 5 动态路由: skills merge + billing invoice-pdf/download + campaign budget-history + file upload-stats + auth api-keys/{id}/rotate"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_merge(skill_id: str):
    """Skill merge · 合并 skill (R380)"""
    return {
        "status": "ok",
        "data": {
            "source_skill_id":   skill_id,
            "target_skill_id":   f"{skill_id}_merged_v23",
            "merged_at":          datetime.utcnow().isoformat() + "Z",
            "merged_by":          "u_001",
            "merged_nodes":       47,
            "merged_skills":      3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_pdf_download(invoice_id: str):
    """Billing invoice PDF download · 账单 PDF 下载 (R380)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "pdf_url":      f"https://cloudtech.example.com/api/v2/billing/{invoice_id}/invoice.pdf?token=v23_R380",
            "filename":     f"invoice_{invoice_id}.pdf",
            "size_bytes":   124578,
            "download_id":  f"dl_{invoice_id}_v23",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_budget_history(campaign_id: str):
    """Campaigns budget history · 预算变更历史 (R380)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-30T15:00:00Z", "action": "increased",  "from_yuan": 18000, "to_yuan": 25000, "reason": "AI optimize"},
            {"date": "2026-09-25T10:00:00Z", "action": "decreased",  "from_yuan": 20000, "to_yuan": 18000, "reason": "budget control"},
            {"date": "2026-09-15T14:00:00Z", "action": "set",        "from_yuan":     0, "to_yuan": 20000, "reason": "launch"},
            {"date": "2026-09-01T09:00:00Z", "action": "draft",      "from_yuan":     0, "to_yuan":     0, "reason": "created"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_upload_stats(file_id: str):
    """Files upload stats · 上传统计 (R380)"""
    return {
        "status": "ok",
        "data": {
            "file_id":           file_id,
            "total_uploads":     12,
            "by_user": [
                {"user_id": "u_001", "name": "心之所向便是光", "uploads": 8},
                {"user_id": "u_002", "name": "运维",          "uploads": 4},
            ],
            "by_size_mb":        "124.5",
            "last_upload_at":    "2026-09-30T16:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_key_rotate(key_id: str):
    """Auth api-keys/{id}/rotate · 轮换 API key (R380)"""
    return {
        "status": "ok",
        "data": {
            "key_id":        key_id,
            "new_key_id":    f"{key_id}_rotated_v23",
            "new_secret":    f"sk_v23_R380_{key_id}_rotated",
            "old_expires_at":"2026-10-15T00:00:00Z",
            "new_expires_at":"2027-10-15T00:00:00Z",
            "rotated_at":    datetime.utcnow().isoformat() + "Z",
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
    print(f'✅ 加 5 函数 (R380)')
else:
    print('❌ 没找到')