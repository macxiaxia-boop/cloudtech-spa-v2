"""V23 R396 加 5 动态路由: skills merge-multiple + billing subscription-upgrade + campaign audience-age-stats + file comments-count + auth api-keys/rotate-all"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_merge_multiple(skill_ids: str):
    """Skill merge-multiple · 合并多个 skill (R396)"""
    ids = skill_ids.split(',') if ',' in skill_ids else [skill_ids]
    return {
        "status": "ok",
        "data": {
            "merged_count":  len(ids),
            "merged_ids":    ids,
            "new_skill_id":  f"merged_v23_R396_{len(ids)}",
            "merged_at":     datetime.utcnow().isoformat() + "Z",
            "merged_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_upgrade(tenant_id: str):
    """Billing subscription-upgrade · 升级订阅 (R396)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R396_up",
            "previous_plan":   "basic",
            "upgraded_to":     "pro",
            "upgraded_at":     datetime.utcnow().isoformat() + "Z",
            "prorated_yuan":   500,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_age_stats(campaign_id: str):
    """Campaigns audience-age-stats · 受众年龄分布 (R396)"""
    return {
        "status": "ok",
        "data": [
            {"age_range": "13-17", "count":  980,  "pct":  5.3},
            {"age_range": "18-24", "count": 3680,  "pct": 20.0},
            {"age_range": "25-34", "count": 6280,  "pct": 34.1},
            {"age_range": "35-44", "count": 4120,  "pct": 22.3},
            {"age_range": "45-54", "count": 2180,  "pct": 11.8},
            {"age_range": "55-64", "count":  980,  "pct":  5.3},
            {"age_range": "65+",   "count":  200,  "pct":  1.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_count(file_id: str):
    """Files comments-count · 评论计数 (R396)"""
    return {
        "status": "ok",
        "data": {
            "file_id":        file_id,
            "total_comments": 3,
            "unresolved":     1,
            "resolved":       2,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_all():
    """Auth api-keys/rotate-all · 全部轮换 (R396)"""
    return {
        "status": "ok",
        "data": {
            "rotated_count":   3,
            "rotated_at":      datetime.utcnow().isoformat() + "Z",
            "rotated_by":       "u_001",
            "old_keys_invalidated": True,
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
    print(f'✅ 加 5 函数 (R396)')
else:
    print('❌ 没找到')