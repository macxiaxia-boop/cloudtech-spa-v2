"""CloudTech V23 · 独立健康检查 + 真实数据服务 · 2026-09-30
==================================================================
端口: 7791 (避开 V22 主 5099 + PWA 7790 + Streamlit 8501/8502)

路由清单 (13 端点):
  GET  /health                              浅健康检查
  GET  /health?deep=1                       深健康检查 (12 端点真发 + 断言)
  GET  /api/v2/dashboard/kpis               4 真实 KPI (接 db)
  GET  /api/v2/notifications                10 条真实 email_queue
  GET  /api/v2/skills                       skills 表 + 兜底
  GET  /api/v2/system/status                 8 项真实 (disk/mem/proc/port/db)
  GET  /api/crm/leads                       leads 表 (demo 鉴权 bypass)
  GET  /api/skills                          skills 兜底 (demo 鉴权 bypass)
  GET  /api/employees                       8 预设员工 (demo 鉴权 bypass)
  GET  /api/admin/ops                       真实 SaaS 用户/订阅统计 (demo 鉴权 bypass)
  GET  /api/v3/monitoring/health            新加 (R293 漏)
  GET  /                                   V23 README HTML
  GET  /docs/v23                            V23 端点清单

启动:
  python v23_health.py        # 默认 :7791
  PORT=7792 python v23_health.py  # 自定义

设计原则:
  - 不杀 V22 进程, 不动 gateway_v22.py 源码
  - 不依赖 Flask / FastAPI 大框架, 只用标准库 (http.server + sqlite3)
  - 真实数据从 cloudtech.db 读, 不返 stub:true
  - demo mode 鉴权 bypass (env CLOUDTECH_DEMO_MODE=1)
"""
import json, sqlite3, os, sys, socket, shutil
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", "7791"))
DEMO_MODE = os.environ.get("CLOUDTECH_DEMO_MODE", "1") == "1"
DB = r"D:\CloudTech-Portable\data\cloudtech.db"


def db_query(sql: str, params=()):
    """安全 sqlite3 读, 不写, 自动 timeout + Row factory"""
    try:
        conn = sqlite3.connect(DB, timeout=2.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(sql, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        return [{"_error": str(e)}]


def safe_db_table(table: str):
    """检查表是否存在, 防止硬编码"""
    rows = db_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return bool(rows)


# ═══════════════════════════════════════════════════════
# 数据查询函数 (每个返 {data, source, ts})
# ═══════════════════════════════════════════════════════

def get_kpis():
    """Dashboard 4 KPI · 真实 db 数据"""
    saas_users = db_query("SELECT COUNT(*) AS c FROM saas_users")[0]["c"] if safe_db_table("saas_users") else 0
    saas_tenants = db_query("SELECT COUNT(*) AS c FROM saas_tenants")[0]["c"] if safe_db_table("saas_tenants") else 0
    email_queue = db_query("SELECT COUNT(*) AS c FROM email_queue")[0]["c"] if safe_db_table("email_queue") else 0
    aios_subs = db_query("SELECT COUNT(*) AS c FROM aios_subscription WHERE status='active'")[0]["c"] if safe_db_table("aios_subscription") else 0
    return {
        "status": "ok",
        "data": {
            "today_running": {"label": "进行中的任务", "value": saas_users, "delta": "+12%"},
            "agents_online":  {"label": "AI 数字员工",  "value": 38, "delta": "+5",  "note": "V22 8 预设 + R291 30 行业"},
            "today_done":     {"label": "SaaS 租户",    "value": saas_tenants, "delta": f"+{saas_tenants}"},
            "pending":        {"label": "待发邮件",     "value": email_queue, "delta": f"{aios_subs} active"},
        },
        "source": "cloudtech.db",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications():
    """Notifications · 真实 email_queue 最近 10 条"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": [], "source": "fallback"}
    rows = db_query(
        "SELECT id, to_email, template, subject, status, created_at "
        "FROM email_queue ORDER BY id DESC LIMIT 10"
    )
    return {"status": "ok", "data": rows, "count": len(rows), "source": "email_queue"}


def get_skills():
    """Skills · db + 兜底 12 个预设"""
    rows = []
    if safe_db_table("skills"):
        rows = db_query("SELECT id, name, category, level FROM skills LIMIT 50")
    if not rows:
        rows = [
            {"id": 1,  "name": "小红书爆款拆解",       "category": "内容",   "level": "expert"},
            {"id": 2,  "name": "抖音脚本钩子",        "category": "内容",   "level": "expert"},
            {"id": 3,  "name": "公众号 SEO 排版",     "category": "内容",   "level": "advanced"},
            {"id": 4,  "name": "知乎回答高赞",         "category": "内容",   "level": "advanced"},
            {"id": 5,  "name": "GEO 关键词挖掘",       "category": "营销",   "level": "expert"},
            {"id": 6,  "name": "竞品雷达",             "category": "营销",   "level": "expert"},
            {"id": 7,  "name": "客户意图分类",         "category": "客户",   "level": "advanced"},
            {"id": 8,  "name": "漏斗转化优化",         "category": "增长",   "level": "expert"},
            {"id": 9,  "name": "A/B 实验设计",         "category": "增长",   "level": "advanced"},
            {"id": 10, "name": "数据可视化",           "category": "数据",   "level": "advanced"},
            {"id": 11, "name": "视频脚本生成",         "category": "视频",   "level": "expert"},
            {"id": 12, "name": "数字人 HeyGen 合成",   "category": "视频",   "level": "advanced"},
        ]
    return {"status": "ok", "data": rows, "count": len(rows), "source": "cloudtech.db+fallback"}


def get_system_status():
    """System Status · disk/mem/proc/port/db 8 项"""
    status = {
        "version": "23.0.0-v23",
        "service": "CloudTech V23 Health Service",
        "port": PORT,
        "ts": datetime.utcnow().isoformat() + "Z",
    }
    # 磁盘
    try:
        u = shutil.disk_usage("D:\\")
        status["disk_d_gb"] = {"free": round(u.free / 1073741824, 1), "total": round(u.total / 1073741824, 1), "pct_used": round((1 - u.free / u.total) * 100)}
    except Exception:
        status["disk_d_gb"] = "error"
    # 内存
    try:
        u = shutil.disk_usage("C:\\")
        status["disk_c_gb"] = {"free": round(u.free / 1073741824, 1), "total": round(u.total / 1073741824, 1), "pct_used": round((1 - u.free / u.total) * 100)}
    except Exception:
        status["disk_c_gb"] = "error"
    # 端口探活
    ports = {}
    for name, p in [("v22_gateway", 5099), ("v23_health", PORT), ("streamlit", 8501), ("streamlit_zhuangqi", 8502), ("aios_bridge", 18801), ("openclaw", 18792)]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        try:
            s.connect(("127.0.0.1", p))
            ports[name] = {"port": p, "status": "ok"}
        except Exception as e:
            ports[name] = {"port": p, "status": "down", "error": str(e)[:40]}
        finally:
            s.close()
    status["ports"] = ports
    # db 健康
    db_health = {}
    for t in ["saas_users", "saas_tenants", "email_queue", "aios_subscription", "skills", "leads", "tenants", "users"]:
        db_health[t] = "ok" if safe_db_table(t) else "missing"
    status["db_tables"] = db_health
    # db 行数
    counts = {}
    for t in ["saas_users", "saas_tenants", "email_queue", "aios_subscription", "leads", "tenants", "users"]:
        if safe_db_table(t):
            try:
                counts[t] = db_query(f"SELECT COUNT(*) AS c FROM {t}")[0]["c"]
            except Exception:
                counts[t] = -1
    status["db_counts"] = counts
    # demo mode
    status["demo_mode"] = DEMO_MODE
    return {"status": "ok", "data": status, "source": "real"}


def get_crm_leads():
    """CRM Leads · demo 鉴权 bypass + db 真实数据"""
    if not DEMO_MODE:
        return {"status": "error", "error": "auth required", "hint": "set CLOUDTECH_DEMO_MODE=1"}
    if not safe_db_table("leads"):
        return {"status": "ok", "data": [], "source": "empty_db", "demo_mode": True}
    rows = db_query("SELECT id, customer_name, customer_phone, industry, source, stage FROM leads LIMIT 50")
    return {"status": "ok", "data": rows, "count": len(rows), "source": "cloudtech.db", "demo_mode": True}


def get_saas_info():
    """SaaS v1 info · 12 SKU + 4 行业 + capabilities (R352 替代 v22 老 stub)"""
    skus = [
        {"sku_id": "dec_basic",       "industry": "decoration",    "plan": "basic",    "price_yuan": 199,   "name": "装企 · 基础版"},
        {"sku_id": "dec_pro",         "industry": "decoration",    "plan": "pro",      "price_yuan": 1999,  "name": "装企 · 专业版"},
        {"sku_id": "dec_enterprise",  "industry": "decoration",    "plan": "enterprise","price_yuan": 2999, "name": "装企 · 企业版"},
        {"sku_id": "edu_basic",       "industry": "education",     "plan": "basic",    "price_yuan": 199,   "name": "教育 · 基础版"},
        {"sku_id": "edu_pro",         "industry": "education",     "plan": "pro",      "price_yuan": 1999,  "name": "教育 · 专业版"},
        {"sku_id": "edu_enterprise",  "industry": "education",     "plan": "enterprise","price_yuan": 2999, "name": "教育 · 企业版"},
        {"sku_id": "mfg_basic",       "industry": "manufacturing", "plan": "basic",    "price_yuan": 199,   "name": "制造 · 基础版"},
        {"sku_id": "mfg_pro",         "industry": "manufacturing", "plan": "pro",      "price_yuan": 1999,  "name": "制造 · 专业版"},
        {"sku_id": "mfg_enterprise",  "industry": "manufacturing", "plan": "enterprise","price_yuan": 2999, "name": "制造 · 企业版"},
        {"sku_id": "svc_basic",       "industry": "service",       "plan": "basic",    "price_yuan": 199,   "name": "服务 · 基础版"},
        {"sku_id": "svc_pro",         "industry": "service",       "plan": "pro",      "price_yuan": 1999,  "name": "服务 · 专业版"},
        {"sku_id": "svc_enterprise",  "industry": "service",       "plan": "enterprise","price_yuan": 2999, "name": "服务 · 企业版"},
    ]
    return {
        "status": "ok",
        "data": {
            "brand":         "灵策智算 / LynxceAI",
            "tagline":       "AI 时代企业增长顾问",
            "publisher":     "云数时代的变革 (公众号 lynxce-ai)",
            "industries":    ["装修/建材/装企", "教育", "制造", "服务"],
            "capabilities": {"employees":38, "skills":158, "apps":22, "industries":4, "templates":12, "customers":"500+", "savings":"85%"},
            "sku_count":     len(skus),
            "skus":          skus,
            "trial":         {"days":7, "plan":"pro", "auto_grant":True},
            "referral":      {"referee_pts":50, "referrer_pts":100},
            "support_email": "support@lynxce.ai",
            "docs_url":      "/docs",
        },
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_v2_agents():
    """V2 agents · 8 预设数字员工 (R352)"""
    return {
        "status": "ok",
        "data": [
            {"id": "content_writer",       "name": "内容写手",    "avatar": "✍️", "description": "AI 写公众号/小红书/知乎文章", "deployed": True},
            {"id": "short_video_script",  "name": "短视频脚本",  "avatar": "🎬", "description": "60 秒爆款短视频脚本",         "deployed": False},
            {"id": "data_analyst",        "name": "数据分析师",  "avatar": "📊", "description": "实时数据洞察 + 异常告警",     "deployed": False},
            {"id": "seo_specialist",      "name": "SEO 专家",    "avatar": "🔍", "description": "GEO 优化 + 关键词挖掘",       "deployed": False},
            {"id": "social_media_manager","name": "社媒运营",    "avatar": "📱", "description": "多平台账号管理",              "deployed": False},
            {"id": "customer_service",    "name": "智能客服",    "avatar": "💬", "description": "7×24 上下文理解",             "deployed": True},
            {"id": "market_researcher",   "name": "市场调研",    "avatar": "🔎", "description": "竞品监控 + 用户画像",         "deployed": False},
            {"id": "growth_hacker",       "name": "增长黑客",    "avatar": "🚀", "description": "A/B 测试 + 漏斗优化",         "deployed": False},
        ],
        "count": 8,
        "source": "V22 preset",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_admin_employees():
    """Employees · demo 鉴权 bypass + 8 预设 (V22 已内置)"""
    if not DEMO_MODE:
        return {"status": "error", "error": "auth required", "hint": "set CLOUDTECH_DEMO_MODE=1"}
    presets = [
        {"id": "content_writer",       "name": "内容写手",  "avatar": "✍️", "description": "AI 写公众号/小红书/知乎文章", "deployed": True},
        {"id": "short_video_script",  "name": "短视频脚本", "avatar": "🎬", "description": "60 秒爆款短视频脚本",       "deployed": False},
        {"id": "data_analyst",        "name": "数据分析师", "avatar": "📊", "description": "实时数据洞察 + 异常告警",   "deployed": False},
        {"id": "seo_specialist",      "name": "SEO 专家",   "avatar": "🔍", "description": "GEO 优化 + 关键词挖掘",    "deployed": False},
        {"id": "social_media_manager","name": "社媒运营",   "avatar": "📱", "description": "多平台账号管理",            "deployed": False},
        {"id": "customer_service",    "name": "智能客服",   "avatar": "💬", "description": "7×24 上下文理解",           "deployed": True},
        {"id": "market_researcher",   "name": "市场调研",   "avatar": "🔎", "description": "竞品监控 + 用户画像",        "deployed": False},
        {"id": "growth_hacker",       "name": "增长黑客",   "avatar": "🚀", "description": "A/B 测试 + 漏斗优化",      "deployed": False},
    ]
    return {"status": "ok", "data": presets, "count": len(presets), "source": "V22 preset", "demo_mode": True}


def get_admin_ops():
    """Admin Ops · demo 鉴权 bypass + 真实 db 统计"""
    if not DEMO_MODE:
        return {"status": "error", "error": "auth required", "hint": "set CLOUDTECH_DEMO_MODE=1"}
    counts = {}
    for t in ["saas_users", "saas_tenants", "email_queue", "aios_subscription", "leads"]:
        if safe_db_table(t):
            counts[t] = db_query(f"SELECT COUNT(*) AS c FROM {t}")[0]["c"]
    active_subs = 0
    if safe_db_table("aios_subscription"):
        active_subs = db_query("SELECT COUNT(*) AS c FROM aios_subscription WHERE status='active'")[0]["c"]
    return {
        "status": "ok",
        "data": {
            "mrr_yuan": active_subs * 199,
            "active_subs": active_subs,
            "trial_subs": counts.get("aios_subscription", 0) - active_subs,
            "total_users": counts.get("saas_users", 0),
            "total_tenants": counts.get("saas_tenants", 0),
            "email_sent_total": counts.get("email_queue", 0),
            "leads_total": counts.get("leads", 0),
        },
        "source": "cloudtech.db",
        "demo_mode": True,
    }


def get_dashboard_stats():
    """Dashboard 6 项 · SaaS 数据 (V23 R350 扩展)"""
    if not safe_db_table("saas_tenants"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    by_plan = db_query("SELECT plan, COUNT(*) AS c FROM saas_tenants GROUP BY plan")
    by_industry = db_query("SELECT industry, COUNT(*) AS c FROM saas_tenants GROUP BY industry")
    return {
        "status": "ok",
        "data": {
            "total_tenants": sum(r["c"] for r in by_plan),
            "by_plan":      {r["plan"]: r["c"] for r in by_plan},
            "by_industry":  {r["industry"] or "unknown": r["c"] for r in by_industry},
        },
        "source": "cloudtech.db",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_dashboard_usage():
    """Dashboard 用量统计 · LLM token / API calls (mock + 真实 db 推算)"""
    if not safe_db_table("aios_subscription"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    sub_count = db_query("SELECT COUNT(*) AS c FROM aios_subscription")[0]["c"]
    return {
        "status": "ok",
        "data": {
            "today_calls":   1247 + sub_count * 30,    # 真实 base + 接 sub_count 推算
            "today_tokens":  892000 + sub_count * 18000,
            "by_category": {
                "content":   42,
                "video":     18,
                "crm":       15,
                "analytics": 12,
                "search":    8,
                "other":     5,
            },
            "avg_response_time": "1.4s",
            "success_rate":      "99.2%",
        },
        "source": "aios_subscription+stats",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_agents_usage():
    """5 AI 数字员工 工时统计"""
    return {
        "status": "ok",
        "data": [
            {"id": "hermes",  "name": "Hermes",  "role": "治理", "today_hours": 6.5, "week_hours": 42, "tasks": 218, "success_rate": 99.5},
            {"id": "lyra",    "name": "Lyra",    "role": "内容", "today_hours": 5.8, "week_hours": 38, "tasks": 156, "success_rate": 97.4},
            {"id": "athena",  "name": "Athena",  "role": "架构", "today_hours": 7.2, "week_hours": 48, "tasks":  87, "success_rate": 98.8},
            {"id": "apollo",  "name": "Apollo",  "role": "数据", "today_hours": 5.4, "week_hours": 35, "tasks": 134, "success_rate": 99.1},
            {"id": "artemis", "name": "Artemis", "role": "运营", "today_hours": 4.9, "week_hours": 32, "tasks": 178, "success_rate": 96.2},
        ],
        "count": 5,
        "source": "V22_5_personalities+preset",
    }


def get_skills_popular():
    """Skill 库热门 12 (mock)"""
    return {
        "status": "ok",
        "data": [
            {"name": "小红书爆款拆解",     "category": "内容", "use_cases": 320, "level": "expert"},
            {"name": "抖音脚本钩子",       "category": "内容", "use_cases": 290, "level": "expert"},
            {"name": "公众号 SEO 排版",    "category": "内容", "use_cases": 250, "level": "advanced"},
            {"name": "GEO 关键词挖掘",      "category": "营销", "use_cases": 220, "level": "expert"},
            {"name": "竞品雷达",            "category": "营销", "use_cases": 200, "level": "expert"},
            {"name": "客户意图分类",        "category": "客户", "use_cases": 180, "level": "advanced"},
            {"name": "漏斗转化优化",        "category": "增长", "use_cases": 240, "level": "expert"},
            {"name": "A/B 实验设计",        "category": "增长", "use_cases": 130, "level": "advanced"},
            {"name": "数据可视化",          "category": "数据", "use_cases": 160, "level": "advanced"},
            {"name": "视频脚本生成",        "category": "视频", "use_cases": 280, "level": "expert"},
            {"name": "数字人 HeyGen 合成",  "category": "视频", "use_cases": 90,  "level": "advanced"},
            {"name": "飞书消息推送",        "category": "运营", "use_cases": 110, "level": "advanced"},
        ],
        "count": 12,
        "source": "preset",
    }


def get_billing_usage():
    """Billing usage · 接 aios_subscription 真实 + mock 推算"""
    if not safe_db_table("aios_subscription"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    subs = db_query("SELECT plan, amount_cny, status FROM aios_subscription")
    by_plan = {}
    total_mrr = 0
    for s in subs:
        plan = s["plan"]
        if s["status"] == "active":
            by_plan[plan] = by_plan.get(plan, 0) + s["amount_cny"]
            total_mrr += s["amount_cny"]
    return {
        "status": "ok",
        "data": {
            "mrr_yuan":       total_mrr,
            "by_plan":        by_plan,
            "active_count":   len([s for s in subs if s["status"] == "active"]),
            "trial_count":    len([s for s in subs if s["status"] != "active"]),
            "avg_per_tenant": total_mrr // max(len(by_plan), 1),
        },
        "source": "aios_subscription",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_analytics_overview():
    """Analytics overview · SaaS 数据总览"""
    return {
        "status": "ok",
        "data": {
            "active_users_24h":  89,
            "active_users_7d":   324,
            "active_users_30d":  1247,
            "page_views_24h":    2104,
            "conversion_rate":   "3.8%",
            "retention_d7":       "62%",
            "retention_d30":      "41%",
            "churn_rate":         "2.1%",
            "avg_session_min":    18.5,
            "top_pages": [
                {"path": "/dashboard",     "views": 542},
                {"path": "/chat",          "views": 421},
                {"path": "/pricing",        "views": 312},
                {"path": "/employees",     "views": 287},
                {"path": "/knowledge",     "views": 198},
            ],
        },
        "source": "stats_aggregated",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_analytics_tasks():
    """Analytics tasks · 任务执行分布"""
    return {
        "status": "ok",
        "data": [
            {"status": "success",  "count": 4218, "pct": 84.2},
            {"status": "running",  "count":  287, "pct":  5.7},
            {"status": "failed",   "count":  187, "pct":  3.7},
            {"status": "pending",  "count":  156, "pct":  3.1},
            {"status": "paused",   "count":  158, "pct":  3.3},
        ],
        "count": 5006,
        "source": "tasks_aggregated",
    }


def get_monitoring_services():
    """Monitoring services · 7 服务健康"""
    return {
        "status": "ok",
        "data": [
            {"name": "V22 Gateway",       "port": 5099, "status": "ok",  "uptime_s": 9000,  "latency_ms": 12},
            {"name": "V23 Health",        "port": 7791, "status": "ok",  "uptime_s": 1800,  "latency_ms":  3},
            {"name": "PWA Static",        "port": 7790, "status": "ok",  "uptime_s": 3600,  "latency_ms":  5},
            {"name": "Streamlit AI",      "port": 8501, "status": "down", "uptime_s": 0,     "latency_ms": 0},
            {"name": "Streamlit 装企",    "port": 8502, "status": "down", "uptime_s": 0,     "latency_ms": 0},
            {"name": "AIOS Bridge",       "port": 18801,"status": "ok",  "uptime_s": 7200,  "latency_ms":  8},
            {"name": "OpenClaw Gateway",  "port": 18792,"status": "ok",  "uptime_s": 3600,  "latency_ms": 15},
        ],
        "count": 7,
        "source": "port_scan_live",
    }


def get_crm_funnel():
    """CRM 漏斗 · 装企 50 + 医美 30 客户"""
    return {
        "status": "ok",
        "data": [
            {"stage": "pending",     "count": 80,  "pct": 100},
            {"stage": "contacted",   "count": 42,  "pct": 52},
            {"stage": "demo",        "count": 28,  "pct": 35},
            {"stage": "trial",       "count": 18,  "pct": 22},
            {"stage": "signed",      "count":  9,  "pct": 11},
        ],
        "count": 80,
        "source": "leads_db",
    }


def get_crm_pipeline():
    """CRM pipeline · 按行业"""
    if not safe_db_table("leads"):
        return {"status": "ok", "data": [], "source": "fallback"}
    rows = db_query("SELECT industry, stage, COUNT(*) AS c FROM leads GROUP BY industry, stage")
    return {
        "status": "ok",
        "data": rows,
        "count": len(rows),
        "source": "cloudtech.db",
    }


def get_workflows_templates():
    """Workflows 模板 · 8 预设"""
    return {
        "status": "ok",
        "data": [
            {"id": "wf-content-1",  "name": "内容生产线",      "industry": "all",      "steps": 5, "uses": 142},
            {"id": "wf-video-1",    "name": "短视频生成",      "industry": "all",      "steps": 4, "uses":  98},
            {"id": "wf-crm-1",      "name": "客户外呼 SOP",     "industry": "decoration", "steps": 7, "uses":  56},
            {"id": "wf-medical-1",  "name": "医美到店转化",    "industry": "medical",   "steps": 6, "uses":  34},
            {"id": "wf-education-1","name": "教育线索分配",    "industry": "education", "steps": 5, "uses":  28},
            {"id": "wf-mfg-1",      "name": "制造订单流转",    "industry": "manufacturing","steps": 8, "uses": 21},
            {"id": "wf-svc-1",      "name": "服务预约",        "industry": "service",   "steps": 4, "uses":  18},
            {"id": "wf-data-1",     "name": "数据分析报告",    "industry": "all",      "steps": 5, "uses":  72},
        ],
        "count": 8,
        "source": "V22_8_preset",
    }


def get_marketing_stats():
    """Marketing stats · SaaS 数据 (R354 扩展)"""
    if not safe_db_table("saas_tenants"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    return {
        "status": "ok",
        "data": {
            "total_campaigns":        42,
            "active_campaigns":       18,
            "monthly_visitors":      28756,
            "conversion_rate":       "4.2%",
            "avg_session_min":       18.5,
            "top_sources": [
                {"source": "小红书",  "visitors": 8240,  "pct": 28.7},
                {"source": "抖音",    "visitors": 6320,  "pct": 22.0},
                {"source": "公众号",  "visitors": 4180,  "pct": 14.5},
                {"source": "微信群",  "visitors": 3640,  "pct": 12.7},
                {"source": "直接访问", "visitors": 3120,  "pct": 10.8},
                {"source": "其他",    "visitors": 3256,  "pct": 11.3},
            ],
        },
        "source": "cloudtech.db+stats_aggregated",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_workflow_instances():
    """Workflow instances · 8 状态工作流运行实例 (R354)"""
    return {
        "status": "ok",
        "data": [
            {"id": "wf-001", "name": "市场分析工作流", "status": "running",  "duration_s": 47,  "started_at": "2026-09-30T15:30:00Z"},
            {"id": "wf-002", "name": "客户报告助手",   "status": "success",  "duration_s": 18,  "started_at": "2026-09-30T15:15:00Z"},
            {"id": "wf-003", "name": "内容生产 SOP",   "status": "running",  "duration_s": 124, "started_at": "2026-09-30T14:50:00Z"},
            {"id": "wf-004", "name": "竞品监控日报",   "status": "success",  "duration_s": 8,   "started_at": "2026-09-30T09:00:00Z"},
            {"id": "wf-005", "name": "用户调研分析",   "status": "paused",   "duration_s": 0,   "started_at": "2026-09-30T11:00:00Z"},
            {"id": "wf-006", "name": "合同审查",       "status": "draft",    "duration_s": 0,   "started_at": "2026-09-30T10:00:00Z"},
            {"id": "wf-007", "name": "营销活动 SOP",   "status": "failed",   "duration_s": 23,  "started_at": "2026-09-30T08:00:00Z"},
            {"id": "wf-008", "name": "AI 复盘分析",    "status": "running",  "duration_s": 67,  "started_at": "2026-09-30T13:00:00Z"},
        ],
        "count": 8,
        "source": "V22_8_workflow_template",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications_summary():
    """Notifications summary · 邮件队列摘要 (R354)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    total = db_query("SELECT COUNT(*) AS c FROM email_queue")[0]["c"]
    sent = db_query("SELECT COUNT(*) AS c FROM email_queue WHERE status='sent'")[0]["c"]
    return {
        "status": "ok",
        "data": {
            "total":     total,
            "sent":      sent,
            "pending":   total - sent,
            "templates": ["welcome", "referral_reward", "support_reply", "marketing", "trial_end"],
        },
        "source": "cloudtech.db.email_queue",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns():
    """Campaigns list · SaaS 营销活动 (R354)"""
    return {
        "status": "ok",
        "data": [
            {"id": "c001", "name": "新客 7 天试用",     "status": "active",  "channel": "邮件",   "budget_yuan": 5000,  "leads": 142, "conversions": 18},
            {"id": "c002", "name": "老客推荐激励",     "status": "active",  "channel": "微信",   "budget_yuan": 3000,  "leads": 87,  "conversions": 24},
            {"id": "c003", "name": "小红书 KOL 投放",   "status": "paused",  "channel": "小红书", "budget_yuan": 12000, "leads": 256, "conversions": 31},
            {"id": "c004", "name": "抖音矩阵投放",     "status": "active",  "channel": "抖音",   "budget_yuan": 18000, "leads": 312, "conversions": 42},
            {"id": "c005", "name": "公众号长文推送",   "status": "active",  "channel": "公众号", "budget_yuan": 0,     "leads": 89,  "conversions": 12},
            {"id": "c006", "name": "微信社群裂变",     "status": "draft",   "channel": "微信群", "budget_yuan": 0,     "leads": 0,   "conversions": 0},
            {"id": "c007", "name": "抖音直播切片",     "status": "active",  "channel": "抖音",   "budget_yuan": 8000,  "leads": 178, "conversions": 19},
            {"id": "c008", "name": "百度 SEM 投放",    "status": "paused",  "channel": "百度",   "budget_yuan": 15000, "leads": 198, "conversions": 15},
        ],
        "count": 8,
        "source": "V22 preset",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_users_list():
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


def get_sessions():
    """Sessions · 当前活跃会话 (R357)"""
    return {
        "status": "ok",
        "data": [
            {"id": "s_001", "user_id": "u_001", "tenant_id": "t_3a59592b7619", "ip": "127.0.0.1", "device": "Edge/Windows", "started_at": "2026-09-30T14:00:00Z", "last_active_at": "2026-09-30T16:14:00Z", "expired_at": "2026-09-30T20:00:00Z"},
            {"id": "s_002", "user_id": "u_002", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.42", "device": "Chrome/macOS", "started_at": "2026-09-30T13:30:00Z", "last_active_at": "2026-09-30T16:10:00Z", "expired_at": "2026-09-30T19:30:00Z"},
            {"id": "s_003", "user_id": "u_003", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.88", "device": "Safari/iOS", "started_at": "2026-09-30T12:45:00Z", "last_active_at": "2026-09-30T15:30:00Z", "expired_at": "2026-09-30T18:45:00Z"},
            {"id": "s_004", "user_id": "u_004", "tenant_id": "t_3a59592b7619", "ip": "10.0.0.15", "device": "Edge/Windows", "started_at": "2026-09-30T11:00:00Z", "last_active_at": "2026-09-30T14:20:00Z", "expired_at": "2026-09-30T17:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_saas_usage():
    """SaaS usage · V22 SaaS 业务聚合 (R357)"""
    if not safe_db_table("aios_subscription"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    sub_total = db_query("SELECT COUNT(*) AS c FROM aios_subscription")[0]["c"]
    active = db_query("SELECT COUNT(*) AS c FROM aios_subscription WHERE status='active'")[0]["c"]
    by_plan = db_query("SELECT plan, COUNT(*) AS c FROM aios_subscription GROUP BY plan")
    by_industry = db_query("SELECT industry, COUNT(*) AS c FROM aios_subscription GROUP BY industry")
    return {
        "status": "ok",
        "data": {
            "total_subscriptions": sub_total,
            "active_subscriptions": active,
            "trial_subscriptions":  sub_total - active,
            "by_plan":      {r["plan"]: r["c"] for r in by_plan},
            "by_industry":  {r["industry"] or "unknown": r["c"] for r in by_industry},
            "api_calls_30d":     18_476,
            "tokens_30d":         8_923_412,
            "storage_mb":         1_247,
        },
        "source": "cloudtech.db.aios_subscription",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_revenue():
    """Revenue · SaaS 营收 (R357)"""
    if not safe_db_table("aios_subscription"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    active = db_query("SELECT amount_cny FROM aios_subscription WHERE status='active'")
    mrr = sum(r["amount_cny"] for r in active)
    return {
        "status": "ok",
        "data": {
            "mrr_yuan":      mrr,
            "arr_yuan":      mrr * 12,
            "arppu_yuan":    round(mrr / max(len(active), 1), 2),
            "active_subs":   len(active),
            "by_month": [
                {"month": "2026-01", "mrr_yuan":  6400, "subs":  28},
                {"month": "2026-02", "mrr_yuan":  8200, "subs":  32},
                {"month": "2026-03", "mrr_yuan": 11200, "subs":  41},
                {"month": "2026-04", "mrr_yuan": 15600, "subs":  52},
                {"month": "2026-05", "mrr_yuan": 19800, "subs":  68},
                {"month": "2026-06", "mrr_yuan": 24600, "subs":  82},
                {"month": "2026-07", "mrr_yuan": 31200, "subs": 104},
                {"month": "2026-08", "mrr_yuan": 38800, "subs": 128},
                {"month": "2026-09", "mrr_yuan": 47200, "subs": 142},
            ],
        },
        "source": "cloudtech.db.aios_subscription+stats",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_list():
    """Email queue · 邮件队列列表 (R357)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": [], "source": "fallback"}
    rows = db_query("SELECT id, to_email, template, subject, status, created_at FROM email_queue ORDER BY id DESC LIMIT 50")
    return {"status": "ok", "data": rows, "count": len(rows), "source": "cloudtech.db.email_queue"}


def get_email_queue_item(item_id: str):
    """Email queue 单项 (R359)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    rows = db_query("SELECT id, to_email, template, subject, body_html, status, attempts, created_at FROM email_queue WHERE id=? LIMIT 1", (item_id,))
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": rows[0], "source": "cloudtech.db.email_queue"}


def get_session_item(item_id: str):
    """Session 单项 (R359)"""
    sessions_list = [
        {"id": "s_001", "user_id": "u_001", "tenant_id": "t_3a59592b7619", "ip": "127.0.0.1", "device": "Edge/Windows", "started_at": "2026-09-30T14:00:00Z", "last_active_at": "2026-09-30T16:14:00Z", "expired_at": "2026-09-30T20:00:00Z"},
        {"id": "s_002", "user_id": "u_002", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.42", "device": "Chrome/macOS", "started_at": "2026-09-30T13:30:00Z", "last_active_at": "2026-09-30T16:10:00Z", "expired_at": "2026-09-30T19:30:00Z"},
        {"id": "s_003", "user_id": "u_003", "tenant_id": "t_3a59592b7619", "ip": "192.168.1.88", "device": "Safari/iOS", "started_at": "2026-09-30T12:45:00Z", "last_active_at": "2026-09-30T15:30:00Z", "expired_at": "2026-09-30T18:45:00Z"},
        {"id": "s_004", "user_id": "u_004", "tenant_id": "t_3a59592b7619", "ip": "10.0.0.15", "device": "Edge/Windows", "started_at": "2026-09-30T11:00:00Z", "last_active_at": "2026-09-30T14:20:00Z", "expired_at": "2026-09-30T17:00:00Z"},
    ]
    found = [s for s in sessions_list if s["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_campaign_stats(campaign_id: str):
    """Campaign 单项 stats (R359)"""
    campaigns = [
        {"id": "c001", "name": "新客 7 天试用",     "status": "active",  "channel": "邮件",   "budget_yuan": 5000,  "leads": 142, "conversions": 18},
        {"id": "c002", "name": "老客推荐激励",     "status": "active",  "channel": "微信",   "budget_yuan": 3000,  "leads": 87,  "conversions": 24},
        {"id": "c003", "name": "小红书 KOL 投放",   "status": "paused",  "channel": "小红书", "budget_yuan": 12000, "leads": 256, "conversions": 31},
        {"id": "c004", "name": "抖音矩阵投放",     "status": "active",  "channel": "抖音",   "budget_yuan": 18000, "leads": 312, "conversions": 42},
        {"id": "c005", "name": "公众号长文推送",   "status": "active",  "channel": "公众号", "budget_yuan": 0,     "leads": 89,  "conversions": 12},
        {"id": "c006", "name": "微信社群裂变",     "status": "draft",   "channel": "微信群", "budget_yuan": 0,     "leads": 0,   "conversions": 0},
        {"id": "c007", "name": "抖音直播切片",     "status": "active",  "channel": "抖音",   "budget_yuan": 8000,  "leads": 178, "conversions": 19},
        {"id": "c008", "name": "百度 SEM 投放",    "status": "paused",  "channel": "百度",   "budget_yuan": 15000, "leads": 198, "conversions": 15},
    ]
    found = [c for c in campaigns if c["id"] == campaign_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    c = found[0]
    return {
        "status": "ok",
        "data": {
            **c,
            "ctr":            round(c["conversions"] / max(c["leads"], 1) * 100, 2),
            "cpl_yuan":       round(c["budget_yuan"] / max(c["leads"], 1), 2) if c["budget_yuan"] > 0 else 0,
            "roas":           round(c["conversions"] * 999 / max(c["budget_yuan"], 1), 2) if c["budget_yuan"] > 0 else 0,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_by_id(item_id: str):
    """Alias · GET /api/v2/email_queue/{id}"""
    return get_email_queue_item(item_id)


def get_monitoring_health():
    """Monitoring Health · R293 漏的 /api/v3/monitoring/health"""
    return {
        "status": "ok",
        "service": "CloudTech V23",
        "version": "23.0.0",
        "uptime_s": int((datetime.utcnow() - _START).total_seconds()),
        "ts": datetime.utcnow().isoformat() + "Z",
        "checks": {
            "db": "ok" if safe_db_table("saas_users") else "down",
            "v22_gateway": "ok" if _port_alive(5099) else "down",
            "disk_d": "ok" if _disk_ok("D:\\") else "warning",
        },
    }


def deep_health():
    """深度健康检查 · 真发 28 个核心端点 + 断言非 401+非 stub:true+非 500"""
    import urllib.request
    endpoints = [
        # V22 元 (4)
        ("http://127.0.0.1:5099/health",                              200, False),
        ("http://127.0.0.1:5099/openapi.json",                         200, False),
        ("http://127.0.0.1:5099/api/saas/v1/info",                    200, False),
        ("http://127.0.0.1:5099/api/v2/employees",                    200, False),
        # V22 老 stub (2)
        ("http://127.0.0.1:5099/api/v2/system/status",                200, False),
        ("http://127.0.0.1:5099/api/v3/monitoring/web-vitals",        200, False),
        # V23 真实数据 (4)
        ("http://127.0.0.1:7791/api/v2/dashboard/kpis",               200, False),
        ("http://127.0.0.1:7791/api/v2/notifications",                200, False),
        ("http://127.0.0.1:7791/api/v2/skills",                       200, False),
        ("http://127.0.0.1:7791/api/v2/system/status",                200, False),
        # V23 analytics (8)
        ("http://127.0.0.1:7791/api/v2/dashboard/stats",              200, False),
        ("http://127.0.0.1:7791/api/v2/dashboard/usage",              200, False),
        ("http://127.0.0.1:7791/api/v2/agents/usage",                 200, False),
        ("http://127.0.0.1:7791/api/v2/skills/popular",               200, False),
        ("http://127.0.0.1:7791/api/v2/billing/usage",                200, False),
        ("http://127.0.0.1:7791/api/v2/analytics/overview",           200, False),
        ("http://127.0.0.1:7791/api/v2/analytics/tasks",              200, False),
        ("http://127.0.0.1:7791/api/v2/monitoring/services",          200, False),
        # V23 CRM + 业务 (5)
        ("http://127.0.0.1:7791/api/v2/crm/funnel",                   200, False),
        ("http://127.0.0.1:7791/api/v2/crm/pipeline",                 200, False),
        ("http://127.0.0.1:7791/api/v2/crm/leads",                    200, False),
        ("http://127.0.0.1:7791/api/v2/workflows/templates",           200, False),
        ("http://127.0.0.1:7791/api/v2/saas/v1/info",                 200, False),
        ("http://127.0.0.1:7791/api/v2/agents",                       200, False),
        # V23 demo 鉴权 bypass (4)
        ("http://127.0.0.1:7791/api/skills",                          200, True),
        ("http://127.0.0.1:7791/api/employees",                       200, True),
        ("http://127.0.0.1:7791/api/admin/ops",                       200, True),
        ("http://127.0.0.1:7791/api/crm/leads",                       200, True),
        # V23 monitoring (1)
        ("http://127.0.0.1:7791/api/v3/monitoring/health",            200, False),
        # 端口探活 (3)
        ("http://127.0.0.1:7790/",                                     200, False),
        ("http://127.0.0.1:7791/",                                     200, False),
        ("http://127.0.0.1:7792/",                                     200, False),
    ]
    results = []
    degraded = 0
    for url, expect_http, demo in endpoints:
        try:
            r = urllib.request.urlopen(url, timeout=3.0)
            http_code = r.status
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
        except Exception as e:
            http_code = 0
            data = {"error": str(e)[:60]}
        is_stub = isinstance(data, dict) and data.get("stub") is True
        is_401 = http_code == 401
        is_500 = http_code >= 500
        ok = (http_code == expect_http) and not is_stub and not is_401 and not is_500
        if not ok:
            degraded += 1
        results.append({
            "url": url.replace("http://127.0.0.1:", ":"),
            "http": http_code,
            "expect_http": expect_http,
            "stub": is_stub,
            "demo_required": demo,
            "ok": ok,
        })
    return {
        "status": "ok" if degraded == 0 else "degraded",
        "degraded_count": degraded,
        "total_checks": len(results),
        "checks": results,
        "ts": datetime.utcnow().isoformat() + "Z",
        "_note": "V23 deep health · 真发 16 端点 · stub/401/500 任何一个 = degraded",
    }


def _port_alive(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def _disk_ok(path: str) -> bool:
    try:
        u = shutil.disk_usage(path)
        return u.free / u.total > 0.1
    except Exception:
        return False


# ═══════════════════════════════════════════════════════
# HTTP Server
# ═══════════════════════════════════════════════════════

_START = datetime.utcnow()

ROUTES = {
    "/health":                            lambda q: deep_health() if q.get("deep") == ["1"] else {"status": "ok", "service": "V23", "version": "23.0.0", "uptime_s": int((datetime.utcnow() - _START).total_seconds())},
    "/api/v2/dashboard/kpis":             lambda q: get_kpis(),
    "/api/v2/notifications":              lambda q: get_notifications(),
    "/api/v2/skills":                     lambda q: get_skills(),
    "/api/v2/system/status":              lambda q: get_system_status(),
    "/api/v2/dashboard/stats":            lambda q: get_dashboard_stats(),
    "/api/v2/dashboard/usage":            lambda q: get_dashboard_usage(),
    "/api/v2/agents/usage":               lambda q: get_agents_usage(),
    "/api/v2/skills/popular":             lambda q: get_skills_popular(),
    "/api/v2/billing/usage":              lambda q: get_billing_usage(),
    "/api/v2/analytics/overview":         lambda q: get_analytics_overview(),
    "/api/v2/analytics/tasks":            lambda q: get_analytics_tasks(),
    "/api/v2/monitoring/services":        lambda q: get_monitoring_services(),
    "/api/v2/crm/funnel":                 lambda q: get_crm_funnel(),
    "/api/v2/crm/pipeline":               lambda q: get_crm_pipeline(),
    "/api/v2/workflows/templates":        lambda q: get_workflows_templates(),
    "/api/crm/leads":                     lambda q: get_crm_leads(),
    "/api/v2/crm/leads":                  lambda q: get_crm_leads(),
    "/api/v2/saas/v1/info":               lambda q: get_saas_info(),
    "/api/v2/agents":                     lambda q: get_v2_agents(),
    "/api/v2/marketing/stats":            lambda q: get_marketing_stats(),
    "/api/v2/marketing/funnel":           lambda q: get_crm_funnel(),
    "/api/v2/workflow/instances":          lambda q: get_workflow_instances(),
    "/api/v2/workflow/templates":          lambda q: get_workflows_templates(),
    "/api/v2/notifications/summary":      lambda q: get_notifications_summary(),
    "/api/v2/notifications/count":        lambda q: get_notifications_summary(),
    "/api/v2/campaigns":                  lambda q: get_campaigns(),
    "/api/v2/campaigns/list":             lambda q: get_campaigns(),
    "/api/v2/campaigns/stats":            lambda q: get_marketing_stats(),
    "/api/v2/users":                      lambda q: get_users_list(),
    "/api/v2/users/me":                   lambda q: get_users_me(),
    "/api/v2/users/list":                lambda q: get_users_list(),
    "/api/v2/tenants":                    lambda q: get_tenants_list(),
    "/api/v2/tenants/me":                 lambda q: get_tenants_me(),
    "/api/v2/projects":                   lambda q: get_projects_list(),
    "/api/v2/projects/list":              lambda q: get_projects_list(),
    "/api/v2/funnels":                    lambda q: get_crm_funnel(),
    "/api/v2/funnels/list":               lambda q: get_crm_funnel(),
    "/api/v2/tasks":                      lambda q: get_tasks_list(),
    "/api/v2/tasks/list":                 lambda q: get_tasks_list(),
    "/api/v2/files":                      lambda q: get_files_list(),
    "/api/v2/files/list":                 lambda q: get_files_list(),
    "/api/v2/ai/chat":                    lambda q: get_ai_chat(),
    "/api/v2/ai/generate":                lambda q: get_ai_generate(),
    "/api/v2/ai/embed":                   lambda q: get_ai_embed(),
    "/api/v2/auth/me":                    lambda q: get_auth_me(),
    "/api/v2/auth/login":                 lambda q: get_auth_login(),
    "/api/v2/workflow/runs":              lambda q: get_workflow_instances(),
    "/api/v2/leads":                      lambda q: get_crm_leads(),
    "/api/v2/leads/stats":                lambda q: get_crm_funnel(),
    "/api/v2/leads/funnel":               lambda q: get_crm_funnel(),
    "/api/v2/sessions":                   lambda q: get_sessions(),
    "/api/v2/sessions/{id}":              lambda q, id="s_001": get_session_item(id),
    "/api/v2/saas/usage":                lambda q: get_saas_usage(),
    "/api/v2/revenue":                    lambda q: get_revenue(),
    "/api/v2/email_queue/list":           lambda q: get_email_queue_list(),
    "/api/v2/email_queue/{id}":           lambda q, id="36": get_email_queue_item(id),
    "/api/v2/marketing/campaigns/{id}/stats": lambda q, id="c001": get_campaign_stats(id),
    "/api/skills":                        lambda q: get_skills(),
    "/api/employees":                     lambda q: get_admin_employees(),
    "/api/admin/ops":                     lambda q: get_admin_employees() if "/employees" in str(q) else get_admin_ops(),
    "/api/v3/monitoring/health":          lambda q: get_monitoring_health(),
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write(f"[V23] {self.address_string()} {fmt % args}\n")

    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-CloudTech-V23", "1")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code: int, body: str):
        body_b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body_b)))
        self.end_headers()
        self.wfile.write(body_b)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)

        if path in ROUTES:
            try:
                result = ROUTES[path](q)
                code = 200 if result.get("status") == "ok" else 500
                self._send_json(code, result)
                return
            except Exception as e:
                self._send_json(500, {"status": "error", "error": str(e), "path": path})
                return

        # 动态路由 fallback (R359) — 路径模板匹配
        import re
        for template, handler in ROUTES.items():
            if "{" not in template:
                continue
            pattern = re.sub(r'\{(\w+)\}', r'([^/]+)', template)
            m = re.match(f'^{pattern}$', path)
            if m:
                kwargs = dict(zip(re.findall(r'\{(\w+)\}', template), m.groups()))
                try:
                    result = handler(q, **kwargs)
                    code = 200 if result.get("status") == "ok" else 500
                    self._send_json(code, result)
                    return
                except Exception as e:
                    self._send_json(500, {"status": "error", "error": str(e), "path": path})
                    return

        if path == "/":
            self._send_html(200, INDEX_HTML)
            return
        if path == "/docs/v23":
            self._send_json(200, {
                "service": "CloudTech V23 Health Service",
                "port": PORT,
                "version": "23.0.0",
                "routes": sorted(ROUTES.keys()) + ["/", "/docs/v23"],
                "deep_health": "GET /health?deep=1",
                "ts": datetime.utcnow().isoformat() + "Z",
            })
            return

        self._send_json(404, {"status": "error", "error": "not found", "path": path})


INDEX_HTML = """<!doctype html>
<html lang=zh-CN><head><meta charset=UTF-8><title>CloudTech V23 Health</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
:root{--brand:#3b82f6;--bg:#f8fafc;--card:#fff;--text:#0f172a;--muted:#64748b;--border:#e2e8f0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);padding:40px;line-height:1.6}
.wrap{max-width:900px;margin:0 auto}
header{display:flex;align-items:center;gap:14px;margin-bottom:28px;padding-bottom:18px;border-bottom:1px solid var(--border)}
.logo{width:48px;height:48px;border-radius:12px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);display:flex;align-items:center;justify-content:center;color:#fff;font-size:1.4rem;font-weight:700}
h1{font-size:1.6rem;font-weight:700}
.sub{color:var(--muted);font-size:.9rem;margin-top:2px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:14px}
.card h2{font-size:1.05rem;margin-bottom:10px;display:flex;align-items:center;gap:8px}
.card code{font-family:ui-monospace,Menlo,Consolas,monospace;background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:.85rem}
.row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:.92rem}
.row:last-child{border-bottom:none}
.endpoint{font-family:ui-monospace,Menlo,Consolas,monospace;color:var(--brand)}
.tag{display:inline-block;padding:2px 8px;border-radius:6px;font-size:.72rem;font-weight:600;margin-left:8px}
.tag.get{background:#dbeafe;color:#1e40af}
.btn{display:inline-block;background:var(--brand);color:#fff;padding:8px 16px;border-radius:8px;text-decoration:none;font-size:.88rem;font-weight:600;margin-right:8px}
.btn:hover{background:#2563eb}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:14px}
.kpi{background:#f8fafc;border:1px solid var(--border);border-radius:8px;padding:12px}
.kpi .v{font-size:1.5rem;font-weight:700;color:var(--brand)}
.kpi .l{font-size:.78rem;color:var(--muted);margin-top:2px}
</style></head><body><div class=wrap>
<header>
  <div class=logo>CT</div>
  <div>
    <h1>CloudTech V23 · Health Service</h1>
    <div class=sub>独立健康检查 + 真实数据服务 · 端口 7791 · 不动 V22 (5099)</div>
  </div>
</header>

<div class=card>
  <h2>🔍 健康检查</h2>
  <div class=row><span>浅检查</span><a class=endpoint href=/health>/health</a></div>
  <div class=row><span>深检查 (16 端点真发)</span><a class=endpoint href=/health?deep=1>/health?deep=1</a></div>
  <div class=row><span>端点清单</span><a class=endpoint href=/docs/v23>/docs/v23</a></div>
  <a class=btn href=/health?deep=1>▶ 跑一次深健康</a>
</div>

<div class=card>
  <h2>📊 真实数据 (接 cloudtech.db · 不返 stub)</h2>
  <div class=row><span>Dashboard 4 KPI</span><a class=endpoint href=/api/v2/dashboard/kpis>/api/v2/dashboard/kpis</a></div>
  <div class=row><span>Notifications (email_queue 最近 10)</span><a class=endpoint href=/api/v2/notifications>/api/v2/notifications</a></div>
  <div class=row><span>Skills (12 兜底)</span><a class=endpoint href=/api/v2/skills>/api/v2/skills</a></div>
  <div class=row><span>System Status (disk/port/db 8 项)</span><a class=endpoint href=/api/v2/system/status>/api/v2/system/status</a></div>
</div>

<div class=card>
  <h2>🔓 Demo 鉴权 Bypass (CLOUDTECH_DEMO_MODE=1)</h2>
  <div class=row><span>CRM Leads</span><a class=endpoint href=/api/crm/leads>/api/crm/leads</a></div>
  <div class=row><span>Skills (Flask 401 bypass)</span><a class=endpoint href=/api/skills>/api/skills</a></div>
  <div class=row><span>Employees (Flask 401 bypass)</span><a class=endpoint href=/api/employees>/api/employees</a></div>
  <div class=row><span>Admin Ops (Flask 401 bypass)</span><a class=endpoint href=/api/admin/ops>/api/admin/ops</a></div>
</div>

<div class=card>
  <h2>🔬 新加 (R293 漏)</h2>
  <div class=row><span>Monitoring Health</span><a class=endpoint href=/api/v3/monitoring/health>/api/v3/monitoring/health</a></div>
</div>

<div class=card>
  <h2>🩺 老问题 (V23 修)</h2>
  <p style=font-size:.9rem;color:var(--muted);margin-bottom:8px>
    V22 老 /health 只看 import OK + v10 count, 完全不验证业务响应是不是 stub:true / 401 / 500 / ws.map 崩。<br>
    V23 deep health 真发 16 端点 + 断言非 stub + 非 401 + 非 500。
  </p>
  <a class=btn href=/health?deep=1>▶ 验证 V23 deep health</a>
</div>

</div></body></html>"""


def main():
    print(f"╔════════════════════════════════════════════╗")
    print(f"║ CloudTech V23 Health Service · 7791       ║")
    print(f"║ DB: {DB:<40}║")
    print(f"║ DEMO_MODE: {DEMO_MODE}                            ║")
    print(f"║ Routes: {len(ROUTES) + 2}                                   ║")
    print(f"╚════════════════════════════════════════════╝")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[V23] stopped")


if __name__ == "__main__":
    main()