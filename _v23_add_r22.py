"""V23 R379 加 5 动态路由: skills fork + billing upcoming + campaigns detailed + files download-stats + auth api-keys/{id}"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_fork(skill_id: str):
    """Skill fork · fork skill (R379)"""
    return {
        "status": "ok",
        "data": {
            "source_skill_id":   skill_id,
            "new_skill_id":       f"{skill_id}_fork_v23",
            "forked_by":          "u_001",
            "forked_at":          datetime.utcnow().isoformat() + "Z",
            "changes_from_source": ["customized_prompt", "added_workflow"],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_upcoming(invoice_id: str):
    """Billing upcoming · 下期账单预览 (R379)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":        invoice_id,
            "next_period_start": "2026-10-01T00:00:00Z",
            "next_period_end":   "2026-10-31T23:59:59Z",
            "estimated_amount":  1999,
            "currency":          "CNY",
            "items": [
                {"name": "标准版订阅",      "amount_yuan": 1999},
                {"name": "额外 LLM 调用",   "amount_yuan":   85},
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_stats_detailed(campaign_id: str):
    """Campaigns stats detailed · 详细统计 (R379)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":    campaign_id,
            "impressions":     18420,
            "clicks":          920,
            "ctr":             "5.0%",
            "conversions":     42,
            "cvr":            "4.6%",
            "revenue_yuan":    84150,
            "cost_yuan":       3200,
            "roi":             "2630%",
            "by_day": [
                {"date": "2026-09-24", "impressions": 2620, "clicks": 132, "conversions": 6},
                {"date": "2026-09-25", "impressions": 2840, "clicks": 145, "conversions": 7},
                {"date": "2026-09-26", "impressions": 2610, "clicks": 128, "conversions": 5},
                {"date": "2026-09-27", "impressions": 2920, "clicks": 156, "conversions": 8},
                {"date": "2026-09-28", "impressions": 3010, "clicks": 162, "conversions": 9},
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats(file_id: str):
    """Files download stats · 下载统计 (R379)"""
    return {
        "status": "ok",
        "data": {
            "file_id":           file_id,
            "total_downloads":   142,
            "unique_downloaders": 42,
            "by_country": {
                "CN": 98, "US": 18, "JP": 12, "SG": 8, "OTHER": 6,
            },
            "by_date": [
                {"date": "2026-09-24", "downloads": 12},
                {"date": "2026-09-25", "downloads": 18},
                {"date": "2026-09-26", "downloads": 22},
                {"date": "2026-09-27", "downloads": 28},
                {"date": "2026-09-28", "downloads": 30},
                {"date": "2026-09-29", "downloads": 18},
                {"date": "2026-09-30", "downloads": 14},
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_key_item(key_id: str):
    """Auth api-keys 单项 (R379)"""
    keys = {
        "k_001": {"name": "production",      "scopes": ["read", "write", "admin"], "last_used_at": "2026-09-30T16:00:00Z", "created_at": "2026-06-15T00:00:00Z"},
        "k_002": {"name": "staging",         "scopes": ["read", "write"],         "last_used_at": "2026-09-29T14:00:00Z", "created_at": "2026-08-01T00:00:00Z"},
        "k_003": {"name": "ci-cd-pipeline",  "scopes": ["read", "deploy"],        "last_used_at": "2026-09-30T10:00:00Z", "created_at": "2026-09-01T00:00:00Z"},
    }
    found = keys.get(key_id)
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            "key_id":    key_id,
            "secret":    f"sk_v23_R379_{key_id}_" + str(hash(key_id) % 100000),
            **found,
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
    print(f'✅ 加 5 函数 (R379)')
else:
    print('❌ 没找到')