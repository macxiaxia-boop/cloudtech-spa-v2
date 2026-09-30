"""V23 R376 加 5 动态路由: skills metrics + billing invoice-pdf + campaigns audience-list + files preview + auth tokens"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_metrics(skill_id: str):
    """Skill metrics · skill 性能指标 (R376)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "total_uses":     1248,
            "success_rate":   "96.4%",
            "avg_latency_ms": 412,
            "p95_latency_ms": 1280,
            "p99_latency_ms": 3200,
            "user_rating":     "4.7/5",
            "last_used_at":   "2026-09-30T16:14:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_pdf(invoice_id: str):
    """Billing invoice PDF · 账单 PDF (R376)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "pdf_url":      f"/api/v2/billing/{invoice_id}/invoice.pdf",
            "size_bytes":   124578,
            "pages":        2,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_list(campaign_id: str):
    """Campaigns audience list · 受众列表 (R376)"""
    return {
        "status": "ok",
        "data": [
            {"user_id": "u_001", "name": "心之所向便是光", "segment": "owner",     "engagement_score": 0.95},
            {"user_id": "u_002", "name": "运维",          "segment": "admin",     "engagement_score": 0.82},
            {"user_id": "u_003", "name": "销售",          "segment": "member",    "engagement_score": 0.74},
            {"user_id": "u_004", "name": "客服",          "segment": "member",    "engagement_score": 0.68},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_preview(file_id: str):
    """Files preview · 文件预览 (R376)"""
    return {
        "status": "ok",
        "data": {
            "file_id":      file_id,
            "preview_url":  f"https://cloudtech.example.com/api/v2/files/{file_id}/preview.html",
            "thumbnail_url": f"https://cloudtech.example.com/api/v2/files/{file_id}/thumb.png",
            "format":       "pdf",
            "size_bytes":   2400000,
            "expires_at":   "2026-09-30T19:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_tokens():
    """Auth tokens · 当前用户所有 token (R376)"""
    return {
        "status": "ok",
        "data": [
            {"token_id": "t_001", "name": "web-spa",       "scopes": ["read", "write"], "last_used_at": "2026-09-30T16:00:00Z", "created_at": "2026-01-15T00:00:00Z", "expires_at": "2027-01-15T00:00:00Z"},
            {"token_id": "t_002", "name": "mobile-app",    "scopes": ["read"],         "last_used_at": "2026-09-30T15:30:00Z", "created_at": "2026-03-01T00:00:00Z", "expires_at": "2027-03-01T00:00:00Z"},
            {"token_id": "t_003", "name": "ci-cd",         "scopes": ["read", "deploy"], "last_used_at": "2026-09-30T10:00:00Z", "created_at": "2026-06-01T00:00:00Z", "expires_at": "2026-12-01T00:00:00Z"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R376)')
else:
    print('❌ 没找到')