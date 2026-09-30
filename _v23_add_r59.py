"""V23 R417 加 5 动态路由: skills export-merge + billing payment-methods/{id}/verify-default + campaign audience-cohort-list + file download-top-10 + auth api-keys/{id}/throttle-rate-set"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_export_merge(skill_id: str):
    """Skill export-merge · 合并导出 (R417)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "merged_to":    f"merge_v23_R417_{skill_id}",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "size_bytes":  18432,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_default(method_id: str):
    """Billing payment-methods/{id}/verify-default · 验证默认 (R417)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "verified_at": datetime.utcnow().isoformat() + "Z",
            "verified_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_cohort_list(campaign_id: str):
    """Campaigns audience-cohort-list · cohort 列表 (R417)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "avg_ltv_yuan": 1999, "retention_pct": "100%"},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "avg_ltv_yuan": 1680, "retention_pct": "75.7%"},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "avg_ltv_yuan": 1450, "retention_pct": "50.7%"},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "avg_ltv_yuan": 1180, "retention_pct": "39.3%"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_top_10(file_id: str):
    """Files download-top-10 · 下载 Top 10 (R417)"""
    return {
        "status": "ok",
        "data": [
            {"rank":  1, "user_id": "u_001", "name": "心之所向便是光", "downloads": 12},
            {"rank":  2, "user_id": "u_002", "name": "运维",          "downloads":  9},
            {"rank":  3, "user_id": "u_003", "name": "销售",          "downloads":  7},
            {"rank":  4, "user_id": "u_004", "name": "客服",          "downloads":  5},
            {"rank":  5, "user_id": "u_005", "name": "匿名",          "downloads":  4},
            {"rank":  6, "user_id": "u_006", "name": "用户6",         "downloads":  3},
            {"rank":  7, "user_id": "u_007", "name": "用户7",         "downloads":  2},
            {"rank":  8, "user_id": "u_008", "name": "用户8",         "downloads":  2},
            {"rank":  9, "user_id": "u_009", "name": "用户9",         "downloads":  1},
            {"rank": 10, "user_id": "u_010", "name": "用户10",        "downloads":  1},
        ],
        "total_top10": 46,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_rate_set(key_id: str):
    """Auth api-keys/{id}/throttle-rate-set · 设限流率 (R417)"""
    return {
        "status": "ok",
        "data": {
            "key_id":            key_id,
            "previous_rate":    "100 req/min",
            "new_rate":         "500 req/min",
            "set_at":           datetime.utcnow().isoformat() + "Z",
            "set_by":           "u_001",
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
    print(f'✅ 加 5 函数 (R417)')
else:
    print('❌ 没找到')