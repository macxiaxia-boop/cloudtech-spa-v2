"""V23 R371 加 5 动态路由: files delete + workflow runs + agents test + email clear + auth activity"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_files_delete(file_id: str):
    """Files delete · 删除文件 (R371)"""
    return {
        "status": "ok",
        "data": {
            "file_id":   file_id,
            "deleted":   True,
            "deleted_at": datetime.utcnow().isoformat() + "Z",
            "deleted_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_workflows_run(workflow_id: str):
    """Workflows run · 触发工作流 (R371)"""
    return {
        "status": "ok",
        "data": {
            "workflow_id":   workflow_id,
            "run_id":        f"r_{workflow_id}_v23_R371",
            "status":        "running",
            "started_at":    datetime.utcnow().isoformat() + "Z",
            "duration_s":    0,
            "nodes_total":   5,
            "nodes_done":    0,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_agents_test(agent_id: str):
    """Agents test · 测试智能体 (R371)"""
    return {
        "status": "ok",
        "data": {
            "agent_id":     agent_id,
            "test_status":  "passed",
            "test_input":   "你好，帮我分析下最近的市场趋势",
            "test_output":  "（AI 助手 demo）根据近期数据，建议关注 SaaS 行业...",
            "tokens_used":  128,
            "latency_ms":   412,
            "tested_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_clear():
    """Email queue clear · 清空邮件队列 (R371)"""
    return {
        "status": "ok",
        "data": {
            "cleared_count": 12,
            "cleared_at":    datetime.utcnow().isoformat() + "Z",
            "kept_sent":     True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_activity():
    """Auth activity · 活动日志 (R371)"""
    return {
        "status": "ok",
        "data": [
            {"id": "a_001", "action": "login",         "ip": "127.0.0.1",     "device": "Edge/Windows", "at": "2026-09-30T16:00:00Z"},
            {"id": "a_002", "action": "view_dashboard", "ip": "127.0.0.1",     "device": "Edge/Windows", "at": "2026-09-30T16:01:00Z"},
            {"id": "a_003", "action": "create_workflow", "ip": "127.0.0.1",   "device": "Edge/Windows", "at": "2026-09-30T16:05:00Z"},
            {"id": "a_004", "action": "deploy_agent",   "ip": "127.0.0.1",     "device": "Edge/Windows", "at": "2026-09-30T16:10:00Z"},
            {"id": "a_005", "action": "send_email",     "ip": "127.0.0.1",     "device": "Edge/Windows", "at": "2026-09-30T16:12:00Z"},
            {"id": "a_006", "action": "view_report",    "ip": "127.0.0.1",     "device": "Edge/Windows", "at": "2026-09-30T16:14:00Z"},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R371)')
else:
    print('❌ 没找到')