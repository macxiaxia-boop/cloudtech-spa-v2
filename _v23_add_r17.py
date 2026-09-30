"""V23 R374 加 5 动态路由: skills train + billing subscription + campaigns optimize + files trash + auth api-keys"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_train(skill_id: str):
    """Skill train · 训练 skill (R374)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "training_status": "started",
            "epochs":          10,
            "batch_size":      32,
            "started_at":      datetime.utcnow().isoformat() + "Z",
            "estimated_done_at": "2026-10-01T08:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription(tenant_id: str):
    """Billing subscription · 订阅 (R374)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":      tenant_id,
            "subscription_id": "sub_v23_R374",
            "plan":           "pro",
            "status":         "active",
            "renews_at":      "2026-10-15T00:00:00Z",
            "auto_renew":     True,
            "monthly_yuan":   1999,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_optimize(campaign_id: str):
    """Campaigns optimize · AI 优化 (R374)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":       campaign_id,
            "optimize_status":   "applied",
            "before_ctr":        "4.5%",
            "after_ctr":         "8.2%",
            "improvement_pct":   "82.2",
            "applied_changes":   [
                "调整投放时段到 18-22 点 (CTR +32%)",
                "优化文案关键词 (CTR +28%)",
                "调整人群定向 (CTR +22%)",
            ],
            "optimized_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_trash(file_id: str):
    """Files trash · 移到回收站 (R374)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "trashed":     True,
            "trashed_at":  datetime.utcnow().isoformat() + "Z",
            "purge_after": "2026-11-15T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys():
    """Auth api-keys · API key 列表 (R374)"""
    return {
        "status": "ok",
        "data": [
            {"key_id": "k_001", "name": "production",     "scopes": ["read", "write", "admin"], "last_used_at": "2026-09-30T16:00:00Z", "created_at": "2026-06-15T00:00:00Z"},
            {"key_id": "k_002", "name": "staging",        "scopes": ["read", "write"],         "last_used_at": "2026-09-29T14:00:00Z", "created_at": "2026-08-01T00:00:00Z"},
            {"key_id": "k_003", "name": "ci-cd-pipeline", "scopes": ["read", "deploy"],        "last_used_at": "2026-09-30T10:00:00Z", "created_at": "2026-09-01T00:00:00Z"},
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
    print(f'✅ 加 5 函数 (R374)')
else:
    print('❌ 没找到')