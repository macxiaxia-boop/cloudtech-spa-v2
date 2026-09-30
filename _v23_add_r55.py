"""V23 R413 加 5 动态路由: skills import-bundle + billing payment-methods/{id}/history + campaign audience-cohort + file download-by-day-chart-v2 + auth api-keys/{id}/quota-histogram"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_import_bundle(skill_id: str):
    """Skill import-bundle · 导入 bundle (R413)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "imported_id":  f"imp_v23_R413_{skill_id}",
            "imported_at": datetime.utcnow().isoformat() + "Z",
            "size_bytes":  24576,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_history(method_id: str):
    """Billing payment-methods/{id}/history · 历史 (R413)"""
    return {
        "status": "ok",
        "data": [
            {"event": "added",    "at": "2025-06-15T10:00:00Z", "actor": "u_001"},
            {"event": "verified",  "at": "2025-06-15T10:00:01Z", "actor": "system"},
            {"event": "default",   "at": "2025-06-15T10:00:02Z", "actor": "u_001"},
            {"event": "charged",   "at": "2025-06-15T10:00:10Z", "amount_yuan": 1999},
            {"event": "charged",   "at": "2025-07-15T10:00:00Z", "amount_yuan": 1999},
            {"event": "charged",   "at": "2025-08-15T10:00:00Z", "amount_yuan": 1999},
            {"event": "default",   "at": "2025-09-15T10:00:00Z", "actor": "u_001"},
            {"event": "charged",   "at": "2025-09-15T10:00:10Z", "amount_yuan": 1999},
        ],
        "count": 8,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_cohort(campaign_id: str):
    """Campaigns audience-cohort · 同龄群 (R413)"""
    return {
        "status": "ok",
        "data": [
            {"cohort": "2026-09-W1", "active_users": 8240, "retention_pct": "100%"},
            {"cohort": "2026-09-W2", "active_users": 6240, "retention_pct": "75.7%"},
            {"cohort": "2026-09-W3", "active_users": 4180, "retention_pct": "50.7%"},
            {"cohort": "2026-09-W4", "active_users": 3240, "retention_pct": "39.3%"},
        ],
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart_v2(file_id: str):
    """Files download-by-day-chart-v2 · 按日下载 chart v2 (R413)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载",       "data": [28, 42, 38, 56, 68, 42, 38], "type": "bar"},
                {"label": "唯一访客",   "data": [18, 28, 22, 38, 45, 28, 24], "type": "bar"},
                {"label": "趋势",       "data": [22, 35, 30, 47, 56, 35, 31], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_histogram(key_id: str):
    """Auth api-keys/{id}/quota-histogram · quota 直方图 (R413)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "buckets": [
                {"range": "0-1000",    "count": 3},
                {"range": "1000-2000", "count": 1},
                {"range": "2000-5000", "count": 0},
                {"range": "5000+",     "count": 0},
            ],
            "max_quota":     10000,
            "current_total": 8247,
            "source": "demo_seed",
            "ts": datetime.utcnow().isoformat() + "Z",
        },
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R413)')
else:
    print('❌ 没找到')