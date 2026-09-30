"""V23 R407 加 5 动态路由: skills push-template + billing payment-methods/{id}/verify-default + campaign audience-utm-stats + file download-rank + auth api-keys/{id}/rotate-quota"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_push_template(skill_id: str):
    """Skill push-template · 推送模板 (R407)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "pushed_to":  f"https://marketplace.example.com/templates/{skill_id}",
            "pushed_at": datetime.utcnow().isoformat() + "Z",
            "version":   "v2.1.0",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_default(method_id: str):
    """Billing payment-methods/{id}/verify-default · 验证默认 (R407)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "is_default":     True,
            "verified_at":   datetime.utcnow().isoformat() + "Z",
            "verified_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_utm_stats(campaign_id: str):
    """Campaigns audience-utm-stats · UTM 来源 (R407)"""
    return {
        "status": "ok",
        "data": [
            {"utm_source": "xhs",         "sessions": 4180, "pct": 22.7},
            {"utm_source": "douyin",      "sessions": 3640, "pct": 19.8},
            {"utm_source": "wechat",      "sessions": 4180, "pct": 22.7},
            {"utm_source": "baidu",       "sessions": 1820, "pct":  9.9},
            {"utm_source": "google",      "sessions": 1280, "pct":  6.9},
            {"utm_source": "email",       "sessions":  920, "pct":  5.0},
            {"utm_source": "direct",      "sessions":  680, "pct":  3.7},
            {"utm_source": "other",       "sessions":  720, "pct":  9.3},
        ],
        "total_sessions": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_rank(file_id: str):
    """Files download-rank · 下载排名 (R407)"""
    return {
        "status": "ok",
        "data": [
            {"rank": 1, "user_id": "u_001", "name": "心之所向便是光", "count":  12},
            {"rank": 2, "user_id": "u_002", "name": "运维",          "count":   9},
            {"rank": 3, "user_id": "u_003", "name": "销售",          "count":   7},
            {"rank": 4, "user_id": "u_004", "name": "客服",          "count":   5},
            {"rank": 5, "user_id": "u_005", "name": "匿名",          "count":   4},
        ],
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_quota(key_id: str):
    """Auth api-keys/{id}/rotate-quota · 重置 quota (R407)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_rotated":  True,
            "new_quota":      20000,
            "previous_quota": 10000,
            "rotated_at":    datetime.utcnow().isoformat() + "Z",
            "rotated_by":    "u_001",
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
    print(f'✅ 加 5 函数 (R407)')
else:
    print('❌ 没找到')