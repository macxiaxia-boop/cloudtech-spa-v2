"""V23 R375 加 5 动态路由: skills test + billing usage + campaigns launch + files restore + auth webhooks"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skills_test(skill_id: str):
    """Skill test · 测试 skill (R375)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "test_status":   "passed",
            "test_input":    "测试输入 demo",
            "test_output":   "测试输出 demo 通过",
            "duration_ms":   248,
            "tokens_used":   64,
            "tested_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_usage(period: str = "current"):
    """Billing usage · 用量统计 (R375)"""
    return {
        "status": "ok",
        "data": {
            "period":            period,
            "total_yuan":        1284.50,
            "breakdown": {
                "llm_calls":      4280,
                "video_minutes":   120,
                "storage_gb":      12.5,
                "api_requests":    18420,
                "seats":           4,
            },
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_launch(campaign_id: str):
    """Campaigns launch · 启动活动 (R375)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "launch_status": "launched",
            "channel":       "all",
            "started_at":    datetime.utcnow().isoformat() + "Z",
            "estimated_reach": 18420,
            "daily_budget_yuan": 500,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_restore(file_id: str):
    """Files restore · 恢复文件 (R375)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "restored":    True,
            "restored_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_webhooks():
    """Auth webhooks · webhook 列表 (R375)"""
    return {
        "status": "ok",
        "data": [
            {"webhook_id": "w_001", "url": "https://example.com/webhook/user-created",  "events": ["user.created", "user.updated"],  "status": "active",   "last_triggered_at": "2026-09-30T15:30:00Z"},
            {"webhook_id": "w_002", "url": "https://example.com/webhook/payment-completed", "events": ["payment.completed", "invoice.created"], "status": "active",   "last_triggered_at": "2026-09-30T14:00:00Z"},
            {"webhook_id": "w_003", "url": "https://example.com/webhook/workflow-failed", "events": ["workflow.failed"],         "status": "paused",  "last_triggered_at": "2026-09-25T10:00:00Z"},
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
    print(f'✅ 加 5 函数 (R375)')
else:
    print('❌ 没找到')