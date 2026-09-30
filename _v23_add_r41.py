"""V23 R399 加 5 动态路由: skills merge-template + billing downgrade-options + campaign audience-device-stats + file download-rate + auth api-keys/{id}/enable"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_merge_template(skill_id: str):
    """Skill merge-template · 合并模板 (R399)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "merged_template_id": f"tmpl_v23_R399_{skill_id}",
            "merged_at":       datetime.utcnow().isoformat() + "Z",
            "merged_nodes":    8,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_downgrade_options(tenant_id: str):
    """Billing downgrade-options · 降级选项 (R399)"""
    return {
        "status": "ok",
        "data": [
            {"target_plan": "basic",     "monthly_yuan":  199, "annual_yuan": 1999, "feature_lost": ["enterprise_support", "99.95% SLA"]},
            {"target_plan": "pro",        "monthly_yuan": 1999, "annual_yuan":19999, "feature_lost": ["custom_development"]},
        ],
        "current_plan":   "enterprise",
        "downgrade_discount_pct": 30,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_device_stats(campaign_id: str):
    """Campaigns audience-device-stats · 受众设备 (R399)"""
    return {
        "status": "ok",
        "data": [
            {"device": "iOS",     "count": 6840, "pct": 37.1},
            {"device": "Android", "count": 7240, "pct": 39.3},
            {"device": "Windows", "count": 2480, "pct": 13.5},
            {"device": "macOS",   "count": 1420, "pct":  7.7},
            {"device": "Other",   "count":  440, "pct":  2.4},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_rate(file_id: str):
    """Files download-rate · 下载速率 (R399)"""
    return {
        "status": "ok",
        "data": {
            "file_id":         file_id,
            "size_bytes":      2400000,
            "avg_bandwidth_bps": 5242880,
            "avg_download_s":  4.0,
            "fastest_s":       1.5,
            "slowest_s":       8.0,
            "by_region": {
                "CN": "1.2s avg", "US": "2.8s avg", "EU": "3.5s avg", "JP": "1.5s avg",
            },
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_enable(key_id: str):
    """Auth api-keys/{id}/enable · 启用 API key (R399)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "enabled":    True,
            "enabled_at": datetime.utcnow().isoformat() + "Z",
            "enabled_by": "u_001",
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
    print(f'✅ 加 5 函数 (R399)')
else:
    print('❌ 没找到')