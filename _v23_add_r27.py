"""V23 R385 加 5 动态路由: skills reindex + billing tax-rate + campaign clicks + file comments + auth api-keys/{id}/test"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_reindex(skill_id: str):
    """Skill reindex · 重建索引 (R385)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "reindex_status": "started",
            "indexed_vectors": 1248,
            "started_at":    datetime.utcnow().isoformat() + "Z",
            "estimated_done_at": "2026-09-30T19:30:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_rate(tenant_id: str):
    """Billing tax rate · 税率 (R385)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":    tenant_id,
            "country":      "CN",
            "tax_rate":     0.06,
            "tax_type":     "vat",
            "is_small":     True,
            "reduced_rate": 0.03,
            "updated_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_clicks(campaign_id: str):
    """Campaigns clicks · 点击流 (R385)"""
    return {
        "status": "ok",
        "data": [
            {"timestamp": "2026-09-30T16:00:00Z", "user_id": "u_001", "ip": "127.0.0.1",     "device": "Edge/Windows"},
            {"timestamp": "2026-09-30T15:45:00Z", "user_id": "u_002", "ip": "192.168.1.42",  "device": "Chrome/macOS"},
            {"timestamp": "2026-09-30T15:30:00Z", "user_id": "u_003", "ip": "192.168.1.88",  "device": "Safari/iOS"},
            {"timestamp": "2026-09-30T15:15:00Z", "user_id": "u_004", "ip": "10.0.0.15",    "device": "Edge/Windows"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments(file_id: str):
    """Files comments · 文件评论 (R385)"""
    return {
        "status": "ok",
        "data": [
            {"comment_id": "c_001", "user_id": "u_001", "name": "心之所向便是光", "content": "请更新 logo 颜色",   "created_at": "2026-09-29T10:00:00Z"},
            {"comment_id": "c_002", "user_id": "u_002", "name": "运维",          "content": "已上传 v2 版本",       "created_at": "2026-09-30T14:00:00Z"},
            {"comment_id": "c_003", "user_id": "u_003", "name": "销售",          "content": "请改成中文版",          "created_at": "2026-09-30T15:00:00Z"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_key_test(key_id: str):
    """Auth api-keys/{id}/test · 测试 API key (R385)"""
    return {
        "status": "ok",
        "data": {
            "key_id":       key_id,
            "test_status":  "valid",
            "latency_ms":   42,
            "scopes":       ["read", "write"],
            "tested_at":    datetime.utcnow().isoformat() + "Z",
            "test_request": {"endpoint": "/api/v2/auth/me", "method": "GET"},
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
    print(f'✅ 加 5 函数 (R385)')
else:
    print('❌ 没找到')