"""V23 R381 加 5 动态路由: skills truncate + billing subscription-cancel + campaign report-pdf/download + file permissions + auth api-keys/{id}/delete"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_truncate(skill_id: str):
    """Skill truncate · 截断 skill (R381)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "truncated":       True,
            "truncated_at":    datetime.utcnow().isoformat() + "Z",
            "kept_versions":   3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_cancel(tenant_id: str):
    """Billing subscription cancel · 取消订阅 (R381)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":      tenant_id,
            "subscription_id": "sub_v23_R381",
            "canceled":       True,
            "reason":         "user_requested",
            "effective_at":   "2026-10-15T00:00:00Z",  # 当前周期结束
            "refund_yuan":    0,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_report_pdf_download(campaign_id: str):
    """Campaigns report PDF download · PDF 报告下载 (R381)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "pdf_url":       f"https://cloudtech.example.com/api/v2/campaigns/{campaign_id}/report.pdf?token=v23_R381",
            "filename":      f"rpt_{campaign_id}_v23.pdf",
            "size_bytes":    524288,
            "pages":         12,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_permissions(file_id: str):
    """Files permissions · 文件权限 (R381)"""
    return {
        "status": "ok",
        "data": [
            {"user_id": "u_001", "name": "心之所向便是光", "permission": "owner",    "granted_at": "2026-06-15T00:00:00Z"},
            {"user_id": "u_002", "name": "运维",          "permission": "editor",   "granted_at": "2026-08-01T00:00:00Z"},
            {"user_id": "u_003", "name": "销售",          "permission": "viewer",   "granted_at": "2026-09-01T00:00:00Z"},
            {"user_id": "u_004", "name": "客服",          "permission": "viewer",   "granted_at": "2026-09-15T00:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_key_delete(key_id: str):
    """Auth api-keys/{id}/delete · 删除 API key (R381)"""
    return {
        "status": "ok",
        "data": {
            "key_id":    key_id,
            "deleted":   True,
            "deleted_at": datetime.utcnow().isoformat() + "Z",
            "deleted_by": "u_001",
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
    print(f'✅ 加 5 函数 (R381)')
else:
    print('❌ 没找到')