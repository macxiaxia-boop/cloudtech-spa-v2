"""V23 R387 加 5 动态路由: skills analytics + billing refund-history + campaign abtest + file download-list + auth sessions/{id}/refresh"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_analytics(skill_id: str):
    """Skill analytics · skill 分析 (R387)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":          skill_id,
            "total_invocations": 1248,
            "by_user": [
                {"user_id": "u_001", "name": "心之所向便是光", "invocations": 487},
                {"user_id": "u_002", "name": "运维",          "invocations": 312},
                {"user_id": "u_003", "name": "销售",          "invocations": 248},
            ],
            "by_hour": [
                {"hour": 9,  "invocations": 124},
                {"hour": 10, "invocations": 187},
                {"hour": 11, "invocations": 220},
                {"hour": 14, "invocations": 198},
                {"hour": 15, "invocations": 165},
            ],
            "error_rate": "3.6%",
            "avg_latency_ms": 412,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_refund_history(invoice_id: str):
    """Billing refund history · 退款历史 (R387)"""
    return {
        "status": "ok",
        "data": [
            {"refund_id": "rfd_001", "amount_yuan": 1999, "reason": "user_requested", "status": "completed", "at": "2026-09-15T10:00:00Z"},
            {"refund_id": "rfd_002", "amount_yuan":  500, "reason": "service_issue",  "status": "completed", "at": "2026-08-20T14:00:00Z"},
            {"refund_id": "rfd_003", "amount_yuan":  200, "reason": "duplicate",       "status": "pending",   "at": "2026-09-25T11:00:00Z"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_abtest(campaign_id: str):
    """Campaigns abtest · A/B 测试 (R387)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "abtest_status": "running",
            "variants": [
                {"variant": "A", "name": "原版本",      "conversions": 18, "traffic_pct": 50, "ctr": "4.5%"},
                {"variant": "B", "name": "优化文案",    "conversions": 24, "traffic_pct": 50, "ctr": "6.0%"},
            ],
            "winner": "B",
            "confidence": "98%",
            "improvement": "+33%",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_list(file_id: str):
    """Files download list · 下载列表 (R387)"""
    return {
        "status": "ok",
        "data": [
            {"download_id": "dl_001", "user_id": "u_001", "name": "心之所向便是光", "at": "2026-09-30T16:00:00Z", "ip": "127.0.0.1"},
            {"download_id": "dl_002", "user_id": "u_002", "name": "运维",          "at": "2026-09-29T14:30:00Z", "ip": "192.168.1.42"},
            {"download_id": "dl_003", "user_id": "u_003", "name": "销售",          "at": "2026-09-28T10:15:00Z", "ip": "192.168.1.88"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_refresh(session_id: str):
    """Auth sessions/{id}/refresh · 刷新单 session (R387)"""
    return {
        "status": "ok",
        "data": {
            "session_id":       session_id,
            "refreshed":        True,
            "new_expires_at":   "2026-10-30T00:00:00Z",
            "refreshed_at":     datetime.utcnow().isoformat() + "Z",
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
    print(f'✅ 加 5 函数 (R387)')
else:
    print('❌ 没找到')