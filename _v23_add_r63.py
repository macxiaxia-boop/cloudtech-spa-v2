"""V23 R421 加 5 动态路由: skills unsync + billing payment-methods/{id}/verify-billing-cycle + campaign audience-grade-list + file download-by-year-chart + auth api-keys/{id}/burst-quota-history"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_unsync(skill_id: str):
    """Skill unsync · 撤销同步 (R421)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "unsynced_at": datetime.utcnow().isoformat() + "Z",
            "unsynced_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_billing_cycle(method_id: str):
    """Billing payment-methods/{id}/verify-billing-cycle · 验证账单周期 (R421)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "verified":      True,
            "cycle":         "monthly",
            "next_billing_at": "2026-10-15T00:00:00Z",
            "verified_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_grade_list(campaign_id: str):
    """Campaigns audience-grade-list · 等级列表 (R421)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "min_score": 800, "max_score": 1000, "count": 4180},
            {"grade": "B 良好", "min_score": 600, "max_score": 799,  "count": 6240},
            {"grade": "C 普通", "min_score": 400, "max_score": 599,  "count": 5240},
            {"grade": "D 低质", "min_score":   0, "max_score": 399,  "count": 2760},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year_chart(file_id: str):
    """Files download-by-year-chart · 按年下载 chart (R421)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["2024", "2025", "2026"],
            "datasets": [
                {"label": "下载",   "data": [ 680, 4180, 3280], "type": "bar"},
                {"label": "唯一访客", "data": [ 480, 3120, 2280], "type": "bar"},
            ],
            "chart_type": "bar",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota_history(key_id: str):
    """Auth api-keys/{id}/burst-quota-history · 突发配额历史 (R421)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-25T00:00:00Z", "burst_quota": 100, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "burst_quota": 300, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "burst_quota": 500, "set_by": "u_001"},
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
    print(f'✅ 加 5 函数 (R421)')
else:
    print('❌ 没找到')