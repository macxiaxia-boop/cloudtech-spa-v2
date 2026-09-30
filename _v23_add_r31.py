"""V23 R389 加 5 动态路由: skills promote + billing tax-invoice + campaign creatives + file download-url-token + auth sessions/{id}/revoke-all-others"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_promote(skill_id: str):
    """Skill promote · 推广 skill (R389)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "promoted":       True,
            "promoted_to":    "marketplace",
            "promoted_at":    datetime.utcnow().isoformat() + "Z",
            "visibility_boost": "10x",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_invoice(invoice_id: str):
    """Billing tax invoice · 增值税发票 (R389)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "tax_invoice_id": f"tax_{invoice_id}_v23",
            "amount_yuan":   1999,
            "tax_rate":      0.06,
            "tax_yuan":      120,
            "url":           f"/api/v2/billing/{invoice_id}/tax-invoice.pdf",
            "issued_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_creatives(campaign_id: str):
    """Campaigns creatives · 创意素材 (R389)"""
    return {
        "status": "ok",
        "data": [
            {"creative_id": "cr_001", "type": "image", "url": "/media/creatives/c001_1.jpg", "clicks": 87,  "ctr": "4.5%"},
            {"creative_id": "cr_002", "type": "video", "url": "/media/creatives/c001_1.mp4", "clicks": 142, "ctr": "6.8%"},
            {"creative_id": "cr_003", "type": "text",  "url": "/media/creatives/c001_1.txt", "clicks": 65,  "ctr": "3.8%"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_url_token(file_id: str):
    """Files download url token · 一次性下载 URL (R389)"""
    return {
        "status": "ok",
        "data": {
            "file_id":         file_id,
            "download_url":    f"https://cloudtech.example.com/api/v2/files/{file_id}/stream?token=once_v23_R389",
            "token":           f"once_v23_R389_{file_id}",
            "expires_at":      "2030-01-01T00:00:00Z",
            "single_use":      True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_revoke_all_others(session_id: str):
    """Auth sessions/{id}/revoke-all-others · 撤销其他 (R389)"""
    return {
        "status": "ok",
        "data": {
            "current_session_id":   session_id,
            "revoked_count":         3,
            "kept_session_id":       session_id,
            "revoked_at":            datetime.utcnow().isoformat() + "Z",
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
    print(f'✅ 加 5 函数 (R389)')
else:
    print('❌ 没找到')