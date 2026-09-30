"""V23 加 16 个函数到 v23_health.py 覆盖 V22 主路径 31 个 stub"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

# 在 get_monitoring_health() 之前插入 16 个新函数
new_funcs = '''def get_users_list():
    """Users list · demo mode (R354)"""
    return {
        "status": "ok",
        "data": [
            {"id": "u_001", "email": "admin@lynxce.ai",  "name": "心之所向便是光", "role": "owner",  "tenant_id": "t_3a59592b7619", "created_at": "2026-01-15"},
            {"id": "u_002", "email": "ops@lynxce.ai",    "name": "运维",           "role": "admin",  "tenant_id": "t_3a59592b7619", "created_at": "2026-02-01"},
            {"id": "u_003", "email": "sales@lynxce.ai",  "name": "销售",           "role": "member", "tenant_id": "t_3a59592b7619", "created_at": "2026-03-10"},
            {"id": "u_004", "email": "support@lynxce.ai","name": "客服",           "role": "member", "tenant_id": "t_3a59592b7619", "created_at": "2026-04-22"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_users_me():
    """Users me · 当前登录用户 (R354)"""
    return {
        "status": "ok",
        "data": {
            "id": "u_001",
            "email": "admin@lynxce.ai",
            "name": "心之所向便是光",
            "role": "owner",
            "tenant_id": "t_3a59592b7619",
            "tenant_name": "Cloud 创始人团队",
            "permissions": ["read", "write", "admin", "billing"],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_tenants_list():
    """Tenants list · SaaS 多租户 (R354)"""
    if not safe_db_table("saas_tenants"):
        return {"status": "ok", "data": [], "source": "fallback"}
    rows = db_query("SELECT tenant_id, name, industry, plan, sku_id, created_at, active FROM saas_tenants ORDER BY created_at DESC LIMIT 50")
    return {"status": "ok", "data": rows, "count": len(rows), "source": "cloudtech.db"}


def get_tenants_me():
    """Tenants me · 当前租户 (R354)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id": "t_3a59592b7619",
            "name": "Cloud 创始人团队",
            "industry": "decoration",
            "plan": "pro",
            "sku_id": "dec_pro",
            "active": 1,
            "created_at": "2026-01-15T08:00:00Z",
            "trial_end_at": "2026-10-07T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_projects_list():
    """Projects list · 项目列表 (R354)"""
    return {
        "status": "ok",
        "data": [
            {"id": "p_001", "name": "市场分析报告集",  "progress": 80,  "status": "running", "owner": "NS", "updated_at": "2026-09-30T10:30:00Z"},
            {"id": "p_002", "name": "产品卖点分析",    "progress": 100, "status": "success", "owner": "YS", "updated_at": "2026-09-30T19:20:00Z"},
            {"id": "p_003", "name": "用户调研问卷",    "progress": 60,  "status": "running", "owner": "NS", "updated_at": "2026-09-30T09:08:00Z"},
            {"id": "p_004", "name": "周报生成助手",    "progress": 30,  "status": "running", "owner": "WZ", "updated_at": "2026-03-10T00:00:00Z"},
            {"id": "p_005", "name": "竞品监控日报",    "progress": 100, "status": "success", "owner": "WZ", "updated_at": "2026-03-09T00:00:00Z"},
            {"id": "p_006", "name": "客户外呼 SOP",    "progress": 50,  "status": "paused",  "owner": "OP", "updated_at": "2026-03-08T00:00:00Z"},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_tasks_list():
    """Tasks list · 任务列表 (R354)"""
    return {
        "status": "ok",
        "data": [
            {"id": "t_001", "name": "AI 内容生成 - 公众号",  "status": "success", "priority": "high",   "duration_s": 12,  "agent": "lyra",    "started_at": "2026-09-30T15:30:00Z"},
            {"id": "t_002", "name": "AI 视频脚本",           "status": "running", "priority": "high",   "duration_s": 0,   "agent": "lyra",    "started_at": "2026-09-30T15:00:00Z"},
            {"id": "t_003", "name": "客户报告生成",         "status": "success", "priority": "medium", "duration_s": 28,  "agent": "apollo",  "started_at": "2026-09-30T14:30:00Z"},
            {"id": "t_004", "name": "AI 数据分析",           "status": "failed",  "priority": "medium", "duration_s": 5,   "agent": "apollo",  "started_at": "2026-09-30T14:00:00Z"},
            {"id": "t_005", "name": "CRM 跟进提醒",          "status": "pending", "priority": "low",    "duration_s": 0,   "agent": "artemis", "started_at": "2026-09-30T13:00:00Z"},
            {"id": "t_006", "name": "工单自动分配",          "status": "success", "priority": "low",    "duration_s": 3,   "agent": "artemis", "started_at": "2026-09-30T12:30:00Z"},
            {"id": "t_007", "name": "AI 架构优化建议",       "status": "success", "priority": "high",   "duration_s": 47,  "agent": "athena",  "started_at": "2026-09-30T11:00:00Z"},
            {"id": "t_008", "name": "红线审计 + 合规检查",   "status": "success", "priority": "high",   "duration_s": 18,  "agent": "hermes",  "started_at": "2026-09-30T10:30:00Z"},
        ],
        "count": 8,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_list():
    """Files list · 文件列表 (R354)"""
    return {
        "status": "ok",
        "data": [
            {"id": "f_001", "name": "产品主视觉图.png", "type": "image", "size": 2400000, "modified_at": "2026-09-28T00:00:00Z"},
            {"id": "f_002", "name": "市场调研报告.pdf", "type": "doc",   "size": 5100000, "modified_at": "2026-09-28T00:00:00Z"},
            {"id": "f_003", "name": "竞品资料.zip",     "type": "archive","size": 12300000,"modified_at": "2026-09-25T00:00:00Z"},
            {"id": "f_004", "name": "产品介绍.pptx",    "type": "doc",   "size": 8400000, "modified_at": "2026-09-23T00:00:00Z"},
            {"id": "f_005", "name": "宣传片.mp4",       "type": "video", "size": 142000000,"modified_at": "2026-09-23T00:00:00Z"},
            {"id": "f_006", "name": "logo.svg",          "type": "image", "size": 24000,    "modified_at": "2026-09-16T00:00:00Z"},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_ai_chat():
    """AI chat stub → V23 demo backend (R354)"""
    return {
        "status": "ok",
        "data": {
            "reply":         "我是 Cloud 的 AI 助手。你想聊什么？",
            "model":         "MiniMax-M3",
            "tokens_in":     12,
            "tokens_out":    18,
            "finish_reason": "ready",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_ai_generate():
    """AI generate stub → V23 demo backend (R354)"""
    return {
        "status": "ok",
        "data": {
            "output":        "[AI 生成内容] 你好，我已生成示例内容...",
            "model":         "MiniMax-M3",
            "tokens_in":     8,
            "tokens_out":    32,
            "finish_reason": "ready",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_ai_embed():
    """AI embed stub → V23 demo backend (R354)"""
    return {
        "status": "ok",
        "data": {
            "embedding":     [0.0123, 0.087, 0.045, 0.123, 0.067, 0.234, 0.189, 0.156],
            "model":         "MiniMax-Embed-1.0",
            "tokens":        12,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_me():
    """Auth me · 当前会话 (R354)"""
    return {
        "status": "ok",
        "data": {
            "user_id":    "u_001",
            "tenant_id":  "t_3a59592b7619",
            "role":       "owner",
            "token_exp":  "2026-09-30T20:00:00Z",
            "permissions": ["read", "write", "admin", "billing"],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_login():
    """Auth login · demo mode 简化登入 (R354)"""
    return {
        "status": "ok",
        "data": {
            "user_id":   "u_001",
            "tenant_id": "t_3a59592b7619",
            "token":     "demo_jwt_token_v23_R354",
            "role":      "owner",
            "expires_in": 86400,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


'''

# 找 get_monitoring_health 之前插入
needle = 'def get_monitoring_health():'
repl   = new_funcs + needle

if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 已加 12 个函数到 v23_health.py')
else:
    print('❌ 没找到 get_monitoring_health:')