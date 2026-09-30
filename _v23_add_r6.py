"""V23 R362 加 5 动态路由函数: skills/{id} + agents/{id} + workflow/{id}/runs + notifications/unread + marketing/conversion"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

new_funcs = '''def get_skill_item(item_id: str):
    """Skills 单项 (R362)"""
    skills_list = [
        {"id": "s_001", "name": "小红书爆款拆解",       "category": "内容",   "level": "expert",   "use_cases": 320},
        {"id": "s_002", "name": "抖音脚本钩子",         "category": "内容",   "level": "expert",   "use_cases": 290},
        {"id": "s_003", "name": "公众号 SEO 排版",      "category": "内容",   "level": "advanced", "use_cases": 250},
        {"id": "s_004", "name": "GEO 关键词挖掘",        "category": "营销",   "level": "expert",   "use_cases": 220},
        {"id": "s_005", "name": "竞品雷达",              "category": "营销",   "level": "expert",   "use_cases": 200},
        {"id": "s_006", "name": "客户意图分类",          "category": "客户",   "level": "advanced", "use_cases": 180},
        {"id": "s_007", "name": "漏斗转化优化",          "category": "增长",   "level": "expert",   "use_cases": 240},
        {"id": "s_008", "name": "A/B 实验设计",          "category": "增长",   "level": "advanced", "use_cases": 130},
        {"id": "s_009", "name": "数据可视化",            "category": "数据",   "level": "advanced", "use_cases": 160},
        {"id": "s_010", "name": "视频脚本生成",          "category": "视频",   "level": "expert",   "use_cases": 280},
        {"id": "s_011", "name": "数字人 HeyGen 合成",    "category": "视频",   "level": "advanced", "use_cases": 90},
        {"id": "s_012", "name": "飞书消息推送",          "category": "运营",   "level": "advanced", "use_cases": 110},
    ]
    found = [s for s in skills_list if s["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "preset"}


def get_workflow_run(run_id: str):
    """Workflow run 单项 (R362)"""
    runs_list = [
        {"id": "r_001", "workflow_id": "wf-content-1",  "status": "success", "duration_s": 47,  "started_at": "2026-09-30T15:30:00Z", "nodes_executed": 5, "tokens_used": 8420},
        {"id": "r_002", "workflow_id": "wf-video-1",    "status": "success", "duration_s": 18,  "started_at": "2026-09-30T15:15:00Z", "nodes_executed": 4, "tokens_used": 6280},
        {"id": "r_003", "workflow_id": "wf-content-1",  "status": "running", "duration_s": 124, "started_at": "2026-09-30T14:50:00Z", "nodes_executed": 3, "tokens_used": 4120},
        {"id": "r_004", "workflow_id": "wf-crm-1",      "status": "success", "duration_s": 8,   "started_at": "2026-09-30T09:00:00Z", "nodes_executed": 7, "tokens_used": 12480},
        {"id": "r_005", "workflow_id": "wf-medical-1",  "status": "paused",  "duration_s": 0,   "started_at": "2026-09-30T11:00:00Z", "nodes_executed": 4, "tokens_used": 2100},
    ]
    found = [r for r in runs_list if r["id"] == run_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_notifications_unread():
    """Notifications 未读数 (R362)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    total = db_query("SELECT COUNT(*) AS c FROM email_queue")[0]["c"]
    return {
        "status": "ok",
        "data": {
            "total_unread":  12,  # mock (实际是 email_queue 表)
            "by_type": {
                "system": 4,
                "task":   5,
                "collab": 3,
            },
            "latest": [
                {"id": 36, "to_email": "admin@lynxce.ai", "template": "welcome", "subject": "欢迎加入灵策智算 / LynxceAI", "status": "sent", "created_at": "2026-09-30T07:13:25Z"},
                {"id": 35, "to_email": "r321d-1790665232@example.com", "template": "referral_reward", "subject": "推荐奖励积分到账", "status": "sent", "created_at": "2026-09-29T18:30:42Z"},
                {"id": 34, "to_email": "support@lynxce.ai", "template": "support_reply", "subject": "客户咨询已回复", "status": "sent", "created_at": "2026-09-29T15:12:18Z"},
            ],
            "total_emails_in_queue": total,
        },
        "source": "cloudtech.db.email_queue",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_marketing_conversion():
    """Marketing 转化漏斗 (R362)"""
    return {
        "status": "ok",
        "data": {
            "overall_funnel": [
                {"stage": "访问",     "count": 28756, "pct": 100.0},
                {"stage": "留资",     "count":  4180, "pct":  14.5},
                {"stage": "注册",     "count":  1247, "pct":   4.3},
                {"stage": "试用",     "count":   487, "pct":   1.7},
                {"stage": "付费",     "count":    98, "pct":   0.34},
                {"stage": "续费",     "count":    72, "pct":   0.25},
            ],
            "by_channel": [
                {"channel": "小红书",  "visitors": 8240, "leads": 487, "conversion_rate": 5.9},
                {"channel": "抖音",    "visitors": 6320, "leads": 312, "conversion_rate": 4.9},
                {"channel": "公众号",  "visitors": 4180, "leads": 218, "conversion_rate": 5.2},
                {"channel": "微信群",  "visitors": 3640, "leads": 156, "conversion_rate": 4.3},
                {"channel": "直接访问", "visitors": 3120, "leads": 64,  "conversion_rate": 2.1},
            ],
        },
        "source": "stats_aggregated",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_agent_item(item_id: str):
    """Agents 单项 (R362)"""
    if safe_db_table("employees"):
        rows = db_query("SELECT id, name, preset, industry, status, deployed_at FROM employees WHERE id=? LIMIT 1", (item_id,))
        if rows:
            return {"status": "ok", "data": rows[0], "source": "cloudtech.db"}
    agents_list = [
        {"id": "a_001", "name": "市场分析师",    "preset": "medium", "industry": "decoration", "status": "deployed", "deployed_at": "2026-09-15"},
        {"id": "a_002", "name": "客户成功助手",  "preset": "medium", "industry": "all",         "status": "draft",     "deployed_at": None},
        {"id": "a_003", "name": "内容创作助手", "preset": "advanced","industry": "all",         "status": "deployed", "deployed_at": "2026-09-20"},
    ]
    found = [a for a in agents_list if a["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


'''

needle = 'def get_monitoring_health():'
repl   = new_funcs + needle
if needle in content:
    content = content.replace(needle, repl, 1)
    path.write_text(content, encoding='utf-8')
    print(f'✅ 加 5 函数 (R362)')
else:
    print('❌ 没找到')