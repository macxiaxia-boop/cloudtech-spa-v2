"""V23 R398 加 5 动态路由: skills share-template + billing subscription-upgrade-options + campaign audience-region-stats + file popular-times + auth api-keys/{id}/disable"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_share_template(skill_id: str):
    """Skill share-template · 分享 skill 模板 (R398)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "share_template_url": f"https://marketplace.example.com/templates/{skill_id}.yaml",
            "share_token":       "share_v23_R398",
            "permissions":      ["view", "import", "fork"],
            "expires_at":       "2030-01-01T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_upgrade_options(tenant_id: str):
    """Billing subscription upgrade-options · 升级选项 (R398)"""
    return {
        "status": "ok",
        "data": [
            {"target_plan": "basic",     "monthly_yuan":  199,  "annual_yuan": 1999,  "savings_yuan":  389},
            {"target_plan": "pro",        "monthly_yuan": 1999,  "annual_yuan":19999,  "savings_yuan": 3989},
            {"target_plan": "enterprise", "monthly_yuan": 2999,  "annual_yuan":29999,  "savings_yuan": 5989},
        ],
        "current_plan": "basic",
        "upgrade_discount_pct": 20,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_stats(campaign_id: str):
    """Campaigns audience-region-stats · 受众地域 (R398)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",   "count": 2840, "pct": 15.4},
            {"region": "上海",   "count": 2280, "pct": 12.4},
            {"region": "北京",   "count": 2120, "pct": 11.5},
            {"region": "广州",   "count": 1820, "pct":  9.9},
            {"region": "杭州",   "count": 1240, "pct":  6.7},
            {"region": "成都",   "count":  980, "pct":  5.3},
            {"region": "武汉",   "count":  720, "pct":  3.9},
            {"region": "其他",   "count": 6420, "pct": 34.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_popular_times(file_id: str):
    """Files popular-times · 文件下载热门时段 (R398)"""
    return {
        "status": "ok",
        "data": [
            {"hour": 9,  "downloads":  28, "pct":  4.5},
            {"hour": 10, "downloads":  62, "pct": 10.0},
            {"hour": 11, "downloads":  85, "pct": 13.7},
            {"hour": 14, "downloads":  98, "pct": 15.8},
            {"hour": 15, "downloads": 112, "pct": 18.1},
            {"hour": 16, "downloads":  98, "pct": 15.8},
            {"hour": 17, "downloads":  68, "pct": 11.0},
            {"hour": 20, "downloads":  42, "pct":  6.8},
            {"hour": 21, "downloads":  28, "pct":  4.5},
        ],
        "total_downloads": 621,
        "peak_hour":      15,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_disable(key_id: str):
    """Auth api-keys/{id}/disable · 禁用 API key (R398)"""
    return {
        "status": "ok",
        "data": {
            "key_id":        key_id,
            "disabled":     True,
            "disabled_at":  datetime.utcnow().isoformat() + "Z",
            "disabled_by":  "u_001",
            "reactivated_at": None,
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
    print(f'✅ 加 5 函数 (R398)')
else:
    print('❌ 没找到')