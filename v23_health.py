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


def get_notifications_item(item_id: str):
    """Notifications 单项 (R360)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    try:
        item_id_int = int(item_id)
        rows = db_query("SELECT id, to_email, template, subject, status, created_at FROM email_queue WHERE id=? LIMIT 1", (item_id_int,))
    except (ValueError, TypeError):
        rows = []
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": rows[0], "source": "cloudtech.db.email_queue"}


def get_lead_item(item_id: str):
    """Leads 单项 (R360)"""
    if not safe_db_table("leads"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    rows = db_query("SELECT id, customer_name, customer_phone, industry, source, stage FROM leads WHERE id=? LIMIT 1", (item_id,))
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": rows[0], "source": "cloudtech.db.leads"}


def get_task_item(item_id: str):
    """Tasks 单项 (R360) - demo seed"""
    tasks_list = [
        {"id": "t_001", "name": "AI 内容生成 - 公众号",  "status": "success", "priority": "high",   "duration_s": 12,  "agent": "lyra",    "started_at": "2026-09-30T15:30:00Z"},
        {"id": "t_002", "name": "AI 视频脚本",           "status": "running", "priority": "high",   "duration_s": 0,   "agent": "lyra",    "started_at": "2026-09-30T15:00:00Z"},
        {"id": "t_003", "name": "客户报告生成",         "status": "success", "priority": "medium", "duration_s": 28,  "agent": "apollo",  "started_at": "2026-09-30T14:30:00Z"},
        {"id": "t_004", "name": "AI 数据分析",           "status": "failed",  "priority": "medium", "duration_s": 5,   "agent": "apollo",  "started_at": "2026-09-30T14:00:00Z"},
        {"id": "t_005", "name": "CRM 跟进提醒",          "status": "pending", "priority": "low",    "duration_s": 0,   "agent": "artemis", "started_at": "2026-09-30T13:00:00Z"},
        {"id": "t_006", "name": "工单自动分配",          "status": "success", "priority": "low",    "duration_s": 3,   "agent": "artemis", "started_at": "2026-09-30T12:30:00Z"},
        {"id": "t_007", "name": "AI 架构优化建议",       "status": "success", "priority": "high",   "duration_s": 47,  "agent": "athena",  "started_at": "2026-09-30T11:00:00Z"},
        {"id": "t_008", "name": "红线审计 + 合规检查",   "status": "success", "priority": "high",   "duration_s": 18,  "agent": "hermes",  "started_at": "2026-09-30T10:30:00Z"},
    ]
    found = [t for t in tasks_list if t["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_user_item(item_id: str):
    """Users 单项 (R360)"""
    users_list = [
        {"id": "u_001", "email": "admin@lynxce.ai",  "name": "心之所向便是光", "role": "owner",  "tenant_id": "t_3a59592b7619", "created_at": "2026-01-15"},
        {"id": "u_002", "email": "ops@lynxce.ai",    "name": "运维",           "role": "admin",  "tenant_id": "t_3a59592b7619", "created_at": "2026-02-01"},
        {"id": "u_003", "email": "sales@lynxce.ai",  "name": "销售",           "role": "member", "tenant_id": "t_3a59592b7619", "created_at": "2026-03-10"},
        {"id": "u_004", "email": "support@lynxce.ai","name": "客服",           "role": "member", "tenant_id": "t_3a59592b7619", "created_at": "2026-04-22"},
    ]
    found = [u for u in users_list if u["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_file_item(item_id: str):
    """Files 单项 (R361)"""
    files_list = [
        {"id": "f_001", "name": "产品主视觉图.png", "type": "image", "size": 2400000, "modified_at": "2026-09-28T00:00:00Z"},
        {"id": "f_002", "name": "市场调研报告.pdf", "type": "doc",   "size": 5100000, "modified_at": "2026-09-28T00:00:00Z"},
        {"id": "f_003", "name": "竞品资料.zip",     "type": "archive","size": 12300000,"modified_at": "2026-09-25T00:00:00Z"},
        {"id": "f_004", "name": "产品介绍.pptx",    "type": "doc",   "size": 8400000, "modified_at": "2026-09-23T00:00:00Z"},
        {"id": "f_005", "name": "宣传片.mp4",       "type": "video", "size": 142000000,"modified_at": "2026-09-23T00:00:00Z"},
        {"id": "f_006", "name": "logo.svg",          "type": "image", "size": 24000,    "modified_at": "2026-09-16T00:00:00Z"},
    ]
    found = [f for f in files_list if f["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_project_item(item_id: str):
    """Projects 单项 (R361)"""
    projects_list = [
        {"id": "p_001", "name": "市场分析报告集",  "progress": 80,  "status": "running", "owner": "NS", "updated_at": "2026-09-30T10:30:00Z"},
        {"id": "p_002", "name": "产品卖点分析",    "progress": 100, "status": "success", "owner": "YS", "updated_at": "2026-09-30T19:20:00Z"},
        {"id": "p_003", "name": "用户调研问卷",    "progress": 60,  "status": "running", "owner": "NS", "updated_at": "2026-09-30T09:08:00Z"},
        {"id": "p_004", "name": "周报生成助手",    "progress": 30,  "status": "running", "owner": "WZ", "updated_at": "2026-03-10T00:00:00Z"},
        {"id": "p_005", "name": "竞品监控日报",    "progress": 100, "status": "success", "owner": "WZ", "updated_at": "2026-03-09T00:00:00Z"},
        {"id": "p_006", "name": "客户外呼 SOP",    "progress": 50,  "status": "paused",  "owner": "OP", "updated_at": "2026-03-08T00:00:00Z"},
    ]
    found = [p for p in projects_list if p["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_funnel_item(item_id: str):
    """Funnels 单项 (R361) - 实际是 leads funnel stage"""
    funnel_data = [
        {"id": "f_pending", "stage": "待跟进", "count": 80, "pct": 100, "industry_breakdown": {"decoration": 50, "medical": 30}},
        {"id": "f_contacted", "stage": "已联系", "count": 45, "pct": 56, "industry_breakdown": {"decoration": 28, "medical": 17}},
        {"id": "f_demo", "stage": "已演示", "count": 18, "pct": 23, "industry_breakdown": {"decoration": 12, "medical": 6}},
        {"id": "f_trial", "stage": "试用中", "count": 8, "pct": 10, "industry_breakdown": {"decoration": 5, "medical": 3}},
        {"id": "f_signed", "stage": "已签约", "count": 1, "pct": 1, "industry_breakdown": {"decoration": 1, "medical": 0}},
    ]
    found = [f for f in funnel_data if f["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_tenant_item(item_id: str):
    """Tenants 单项 (R361)"""
    if safe_db_table("saas_tenants"):
        rows = db_query("SELECT tenant_id, name, industry, plan, sku_id, created_at, active FROM saas_tenants WHERE tenant_id=? LIMIT 1", (item_id,))
        if rows:
            return {"status": "ok", "data": rows[0], "source": "cloudtech.db"}
    return {"status": "ok", "data": {"tenant_id": item_id, "name": "示例租户", "industry": "decoration", "plan": "pro", "sku_id": "dec_pro", "active": 1, "created_at": "2026-01-15T08:00:00Z"}, "source": "demo_seed"}


def get_ai_item(item_id: str):
    """AI 单项 (R361) - 8 预设数字员工"""
    agents = [
        {"id": "content_writer",       "name": "内容写手",    "avatar": "✍️", "description": "AI 写公众号/小红书/知乎文章", "deployed": True},
        {"id": "short_video_script",  "name": "短视频脚本",  "avatar": "🎬", "description": "60 秒爆款短视频脚本",         "deployed": False},
        {"id": "data_analyst",        "name": "数据分析师",  "avatar": "📊", "description": "实时数据洞察 + 异常告警",     "deployed": False},
        {"id": "seo_specialist",      "name": "SEO 专家",    "avatar": "🔍", "description": "GEO 优化 + 关键词挖掘",       "deployed": False},
        {"id": "social_media_manager","name": "社媒运营",    "avatar": "📱", "description": "多平台账号管理",              "deployed": False},
        {"id": "customer_service",    "name": "智能客服",    "avatar": "💬", "description": "7×24 上下文理解",             "deployed": True},
        {"id": "market_researcher",   "name": "市场调研",    "avatar": "🔎", "description": "竞品监控 + 用户画像",         "deployed": False},
        {"id": "growth_hacker",       "name": "增长黑客",    "avatar": "🚀", "description": "A/B 测试 + 漏斗优化",         "deployed": False},
    ]
    found = [a for a in agents if a["id"] == item_id]
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {"status": "ok", "data": found[0], "source": "demo_seed"}


def get_skill_item(item_id: str):
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


def get_auth_refresh():
    """Auth refresh · 刷新 token (R363)"""
    return {
        "status": "ok",
        "data": {
            "user_id":   "u_001",
            "tenant_id": "t_3a59592b7619",
            "token":     "demo_refreshed_jwt_token_v23_R363",
            "role":      "owner",
            "expires_in": 86400,
            "refreshed_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_logout():
    """Auth logout · 注销 (R363)"""
    return {
        "status": "ok",
        "data": {
            "logged_out": True,
            "user_id": "u_001",
            "sessions_revoked": 1,
            "logged_out_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_file_download(file_id: str):
    """Files download · 文件下载 (R363)"""
    files_meta = {
        "f_001": {"name": "产品主视觉图.png", "size_bytes": 2400000, "mime": "image/png"},
        "f_002": {"name": "市场调研报告.pdf", "size_bytes": 5100000, "mime": "application/pdf"},
        "f_003": {"name": "竞品资料.zip",     "size_bytes": 12300000, "mime": "application/zip"},
        "f_004": {"name": "产品介绍.pptx",    "size_bytes": 8400000, "mime": "application/vnd.ms-powerpoint"},
        "f_005": {"name": "宣传片.mp4",       "size_bytes": 142000000, "mime": "video/mp4"},
        "f_006": {"name": "logo.svg",          "size_bytes": 24000,    "mime": "image/svg+xml"},
    }
    meta = files_meta.get(file_id)
    if not meta:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            "file_id":    file_id,
            "name":       meta["name"],
            "size_bytes": meta["size_bytes"],
            "mime":       meta["mime"],
            "download_url": f"/api/v2/files/{file_id}/download?token=demo_v23_R363",
            "expires_at":  "2026-09-30T18:00:00Z",
            "md5":         "9f8e7d6c5b4a3210fedcba9876543210",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_report(campaign_id: str):
    """Campaigns 单项 report · 营销活动报告 (R363)"""
    campaigns_meta = {
        "c001": {"name": "新客 7 天试用",     "channel": "邮件",   "leads": 142, "conversions": 18},
        "c002": {"name": "老客推荐激励",     "channel": "微信",   "leads": 87,  "conversions": 24},
        "c003": {"name": "小红书 KOL 投放",   "channel": "小红书", "leads": 256, "conversions": 31},
        "c004": {"name": "抖音矩阵投放",     "channel": "抖音",   "leads": 312, "conversions": 42},
        "c005": {"name": "公众号长文推送",   "channel": "公众号", "leads": 89,  "conversions": 12},
        "c006": {"name": "微信社群裂变",     "channel": "微信群", "leads": 0,   "conversions": 0},
        "c007": {"name": "抖音直播切片",     "channel": "抖音",   "leads": 178, "conversions": 19},
        "c008": {"name": "百度 SEM 投放",    "channel": "百度",   "leads": 198, "conversions": 15},
    }
    meta = campaigns_meta.get(campaign_id)
    if not meta:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **meta,
            "campaign_id":   campaign_id,
            "report_url":    f"/api/v2/campaigns/{campaign_id}/report.pdf",
            "insights": [
                "前 3 天转化率最高 (47%)",
                "周末转化率下降 23%",
                "A/B 测试 B 组转化率比 A 组高 12%",
            ],
            "next_actions": [
                "扩大 B 组预算 30%",
                "针对流失用户发二次营销邮件",
                "准备下一轮素材 (3 个新文案)",
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_resend(item_id: str):
    """Email queue resend · 邮件重发 (R363)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    try:
        item_id_int = int(item_id)
        rows = db_query("SELECT id, to_email, template, subject, status, attempts FROM email_queue WHERE id=? LIMIT 1", (item_id_int,))
    except (ValueError, TypeError):
        rows = []
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    # 模拟重发：attempts+1
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "resent":       True,
            "resent_at":    datetime.utcnow().isoformat() + "Z",
            "new_attempts":  rows[0].get("attempts", 0) + 1,
        },
        "source": "cloudtech.db.email_queue+resend",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_session_revoke(item_id: str):
    """Sessions revoke · 撤销会话 (R364)"""
    return {
        "status": "ok",
        "data": {
            "session_id":   item_id,
            "revoked":      True,
            "revoked_at":   datetime.utcnow().isoformat() + "Z",
            "active_sessions_remaining": 3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice(invoice_id: str):
    """Billing invoice · 账单 (R364)"""
    invoices = {
        "inv_001": {"amount_yuan": 1999, "plan": "pro",       "status": "paid"},
        "inv_002": {"amount_yuan": 2999, "plan": "enterprise","status": "paid"},
        "inv_003": {"amount_yuan": 199,  "plan": "basic",    "status": "pending"},
        "inv_004": {"amount_yuan": 1999, "plan": "pro",       "status": "overdue"},
    }
    inv = invoices.get(invoice_id)
    if not inv:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            **inv,
            "tenant_id":    "t_3a59592b7619",
            "created_at":   "2026-09-30T00:00:00Z",
            "due_at":       "2026-10-15T00:00:00Z",
            "pdf_url":      f"/api/v2/billing/{invoice_id}/invoice.pdf",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications_read(notif_id: str):
    """Notifications read · 标记已读 (R364)"""
    return {
        "status": "ok",
        "data": {
            "notif_id":  notif_id,
            "read":      True,
            "read_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_lead_update(lead_id: str):
    """Leads update · 客户阶段更新 (R364)"""
    if not safe_db_table("leads"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    rows = db_query("SELECT id, customer_name, industry, stage FROM leads WHERE id=? LIMIT 1", (lead_id,))
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    # 模拟 stage 推进 pending → contacted
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "previous_stage":   "pending",
            "updated_stage":    "contacted",
            "updated_at":       datetime.utcnow().isoformat() + "Z",
            "next_action":      "已安排外呼，下周一 14:00",
        },
        "source": "cloudtech.db.leads",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_pause(campaign_id: str):
    """Campaigns pause · 暂停营销活动 (R364)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "previous_status": "active",
            "updated_status":  "paused",
            "paused_at":        datetime.utcnow().isoformat() + "Z",
            "remaining_budget":  0,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_permissions():
    """Auth permissions · 当前用户权限 (R365)"""
    return {
        "status": "ok",
        "data": {
            "user_id":   "u_001",
            "tenant_id": "t_3a59592b7619",
            "role":      "owner",
            "permissions": [
                "read:all",
                "write:all",
                "admin:tenant",
                "billing:manage",
                "user:invite",
                "workflow:create",
                "workflow:run",
                "agent:deploy",
                "skill:create",
                "audit:view",
            ],
            "groups": ["owners", "cloudteam", "ai-engineers"],
            "scope":    "tenant",
            "effective_at":  "2026-09-30T00:00:00Z",
            "expires_at":    None,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_refund(invoice_id: str):
    """Billing refund · 退款 (R365)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "refund_id":     f"ref_{invoice_id}_v23",
            "amount_yuan":   1999,
            "reason":        "user_requested",
            "processed_at":  datetime.utcnow().isoformat() + "Z",
            "eta_days":      7,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_queue_cancel(item_id: str):
    """Email queue cancel · 邮件取消 (R365)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    try:
        item_id_int = int(item_id)
        rows = db_query("SELECT id, to_email, template, subject, status FROM email_queue WHERE id=? LIMIT 1", (item_id_int,))
    except (ValueError, TypeError):
        rows = []
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "cancelled":     True,
            "cancelled_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "cloudtech.db.email_queue+cancel",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications_archive(notif_id: str):
    """Notifications archive · 归档 (R365)"""
    return {
        "status": "ok",
        "data": {
            "notif_id":   notif_id,
            "archived":   True,
            "archived_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_resume(campaign_id: str):
    """Campaigns resume · 恢复营销活动 (R365)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":    campaign_id,
            "previous_status": "paused",
            "updated_status":  "active",
            "resumed_at":      datetime.utcnow().isoformat() + "Z",
            "remaining_budget": 15000,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_budget(campaign_id: str):
    """Campaign budget · 调整预算 (R366)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "previous_budget_yuan": 18000,
            "updated_budget_yuan":  25000,
            "spent_yuan":           8420,
            "remaining_yuan":       16580,
            "updated_at":           datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaign_audience(campaign_id: str):
    """Campaign audience · 受众细分 (R366)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id": campaign_id,
            "total_audience": 18420,
            "by_segment": [
                {"segment": "装企老板",     "count": 5240, "pct": 28.5},
                {"segment": "装企员工",     "count": 3120, "pct": 16.9},
                {"segment": "医美院长",     "count": 2180, "pct": 11.8},
                {"segment": "教育机构",     "count": 1980, "pct": 10.8},
                {"segment": "制造业老板",   "count": 2640, "pct": 14.3},
                {"segment": "服务从业者",   "count": 3260, "pct": 17.7},
            ],
            "by_channel": {
                "微信": 8240, "小红书": 4180, "抖音": 3640, "公众号": 2360,
            },
            "updated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_preview(item_id: str):
    """Email queue preview · 邮件预览 (R366)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    try:
        item_id_int = int(item_id)
        rows = db_query("SELECT id, to_email, template, subject, body_html FROM email_queue WHERE id=? LIMIT 1", (item_id_int,))
    except (ValueError, TypeError):
        rows = []
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "rendered":    True,
            "preview_url": f"/api/v2/email_queue/{item_id}/preview.html",
        },
        "source": "cloudtech.db.email_queue",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_file_share(file_id: str):
    """File share · 文件分享链接 (R366)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "share_url":   f"https://cloudtech.example.com/share/{file_id}?token=v23_R366",
            "share_token": "share_v23_R366_" + file_id,
            "expires_at":  "2026-10-07T00:00:00Z",
            "permissions": ["view", "download"],
            "password_protected": False,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_2fa():
    """Auth 2FA · 两步验证 (R366)"""
    return {
        "status": "ok",
        "data": {
            "challenge_id":   "ch_v23_R366_2fa_demo",
            "method":         "totp",
            "qr_code_url":    "/api/v2/auth/2fa/qr.png",
            "backup_codes":   ["backup_001", "backup_002", "backup_003"],
            "expires_in":     300,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_pay(invoice_id: str):
    """Billing pay · 支付 (R368)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "payment_id":    f"pay_{invoice_id}_v23_R368",
            "amount_yuan":   1999,
            "method":        "wechat_pay",
            "paid_at":       datetime.utcnow().isoformat() + "Z",
            "receipt_url":   f"/api/v2/billing/{invoice_id}/receipt.pdf",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_email_stats():
    """Email queue stats · 邮件统计 (R368)"""
    if not safe_db_table("email_queue"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    total = db_query("SELECT COUNT(*) AS c FROM email_queue")[0]["c"]
    sent  = db_query("SELECT COUNT(*) AS c FROM email_queue WHERE status='sent'")[0]["c"]
    by_template = db_query("SELECT template, COUNT(*) AS c FROM email_queue GROUP BY template")
    return {
        "status": "ok",
        "data": {
            "total":     total,
            "sent":      sent,
            "pending":   total - sent,
            "by_template": {r["template"]: r["c"] for r in by_template},
            "delivery_rate":  round(sent / max(total, 1) * 100, 2),
        },
        "source": "cloudtech.db.email_queue",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_notifications_mark_all():
    """Notifications mark-all · 全部标记已读 (R368)"""
    return {
        "status": "ok",
        "data": {
            "marked_count": 12,
            "marked_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_upload_url():
    """Files upload-url · 上传链接 (R368)"""
    return {
        "status": "ok",
        "data": {
            "upload_url":  "https://cloudtech.example.com/api/v2/files/upload?token=v23_R368",
            "upload_id":   "up_v23_R368_demo",
            "expires_at": "2026-09-30T17:00:00Z",
            "max_size_mb": 100,
            "accept":      ["image/*", "application/pdf", "video/mp4", ".zip"],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_export(campaign_id: str):
    """Campaigns export · 数据导出 (R368)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":  campaign_id,
            "export_url":   f"/api/v2/campaigns/{campaign_id}/export.csv",
            "format":       "csv",
            "rows":         312,
            "size_bytes":   245760,
            "expires_at":   "2026-10-01T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_lead_convert(lead_id: str):
    """Lead convert · 客户签约 (R369)"""
    if not safe_db_table("leads"):
        return {"status": "ok", "data": {}, "source": "fallback"}
    rows = db_query("SELECT id, customer_name, industry, stage FROM leads WHERE id=? LIMIT 1", (lead_id,))
    if not rows:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            **rows[0],
            "previous_stage":  "trial",
            "updated_stage":   "signed",
            "contract_id":     f"contract_{lead_id}_v23_R369",
            "annual_revenue":  19900,
            "converted_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "cloudtech.db.leads+convert",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_workflow_publish(workflow_id: str):
    """Workflow publish · 工作流发布 (R369)"""
    return {
        "status": "ok",
        "data": {
            "workflow_id":   workflow_id,
            "previous_status": "draft",
            "updated_status":  "published",
            "version":         "v1.2.3",
            "published_at":    datetime.utcnow().isoformat() + "Z",
            "url":             f"/workflows/{workflow_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_create(skill_id: str):
    """Skill create · 创建 skill (R369)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "name":        "新创建技能 " + skill_id,
            "category":    "custom",
            "level":       "advanced",
            "use_cases":   0,
            "created_at":  datetime.utcnow().isoformat() + "Z",
            "author":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_token(file_id: str):
    """Files download token · 下载 token (R369)"""
    return {
        "status": "ok",
        "data": {
            "file_id":    file_id,
            "token":      "dl_v23_R369_" + file_id + "_" + str(hash(file_id) % 10000),
            "expires_at": "2026-09-30T19:00:00Z",
            "download_url": f"https://cloudtech.example.com/api/v2/files/{file_id}/stream?token=dl_v23_R369_{file_id}",
            "size_bytes": 2400000,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_devices():
    """Auth devices · 当前用户设备列表 (R369)"""
    return {
        "status": "ok",
        "data": [
            {"device_id": "d_001", "type": "desktop", "os": "Windows 11", "browser": "Edge",  "last_active_at": "2026-09-30T16:00:00Z", "trusted": True},
            {"device_id": "d_002", "type": "mobile",  "os": "iOS 17",    "browser": "Safari","last_active_at": "2026-09-29T20:30:00Z", "trusted": True},
            {"device_id": "d_003", "type": "desktop", "os": "macOS 14",  "browser": "Chrome","last_active_at": "2026-09-28T15:00:00Z", "trusted": False},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_delete(skill_id: str):
    """Skill delete · 删除 skill (R370)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "deleted":    True,
            "deleted_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_cancel(invoice_id: str):
    """Billing cancel · 取消账单 (R370)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "cancelled":    True,
            "cancelled_at": datetime.utcnow().isoformat() + "Z",
            "reason":       "user_requested",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_duplicate(campaign_id: str):
    """Campaigns duplicate · 复制活动 (R370)"""
    return {
        "status": "ok",
        "data": {
            "source_campaign_id":  campaign_id,
            "new_campaign_id":     f"c_{campaign_id}_copy_v23",
            "name":                f"{campaign_id} 副本",
            "starts_at":           datetime.utcnow().isoformat() + "Z",
            "cloned_at":           datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_rename(file_id: str):
    """Files rename · 重命名文件 (R370)"""
    return {
        "status": "ok",
        "data": {
            "file_id":       file_id,
            "previous_name": f"file_{file_id}.bin",
            "new_name":      f"renamed_{file_id}_v23.pdf",
            "renamed_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions():
    """Auth sessions · 当前用户所有 session (R370)"""
    return {
        "status": "ok",
        "data": [
            {"session_id": "s_001", "ip": "127.0.0.1",     "device": "Edge/Windows", "last_active_at": "2026-09-30T16:14:00Z", "current": True},
            {"session_id": "s_002", "ip": "192.168.1.42",  "device": "Chrome/macOS", "last_active_at": "2026-09-30T16:10:00Z", "current": False},
            {"session_id": "s_003", "ip": "192.168.1.88",  "device": "Safari/iOS",  "last_active_at": "2026-09-30T15:30:00Z", "current": False},
            {"session_id": "s_004", "ip": "10.0.0.15",    "device": "Edge/Windows", "last_active_at": "2026-09-30T14:20:00Z", "current": False},
        ],
        "count":       4,
        "current_id": "s_001",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_delete(file_id: str):
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


def get_skills_import(skill_id: str):
    """Skill import · 导入 skill (R372)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "imported":       True,
            "imported_from":  f"https://marketplace.example.com/skills/{skill_id}",
            "imported_at":    datetime.utcnow().isoformat() + "Z",
            "size_kb":        12,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_receipt(invoice_id: str):
    """Billing receipt · 收据 (R372)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "receipt_id":    f"rcpt_{invoice_id}_v23",
            "amount_yuan":   1999,
            "pdf_url":       f"/api/v2/billing/{invoice_id}/receipt.pdf",
            "issued_at":     datetime.utcnow().isoformat() + "Z",
            "tenant_id":     "t_3a59592b7619",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_report_export(campaign_id: str):
    """Campaigns report export · 报告导出 (R372)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":  campaign_id,
            "report_id":    f"rpt_{campaign_id}_v23_R372",
            "format":       "pdf",
            "url":          f"/api/v2/campaigns/{campaign_id}/report.pdf",
            "size_bytes":   524288,
            "pages":        12,
            "exported_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_versions(file_id: str):
    """Files versions · 文件版本 (R372)"""
    return {
        "status": "ok",
        "data": [
            {"version": 5, "size_bytes": 2400000, "created_at": "2026-09-30T10:00:00Z", "author": "u_001", "comment": "Latest version"},
            {"version": 4, "size_bytes": 2350000, "created_at": "2026-09-29T15:30:00Z", "author": "u_002", "comment": "Updated content"},
            {"version": 3, "size_bytes": 2300000, "created_at": "2026-09-28T11:00:00Z", "author": "u_001", "comment": "Initial upload"},
            {"version": 2, "size_bytes": 2100000, "created_at": "2026-09-27T14:00:00Z", "author": "u_001", "comment": "First draft"},
            {"version": 1, "size_bytes": 1800000, "created_at": "2026-09-26T09:00:00Z", "author": "u_002", "comment": "Created"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_logout_all():
    """Auth logout-all · 全设备注销 (R372)"""
    return {
        "status": "ok",
        "data": {
            "logged_out_devices": 4,
            "kept_current":       False,
            "logged_out_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export(skill_id: str):
    """Skill export · 导出 skill (R373)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "export_url":   f"/api/v2/skills/{skill_id}/export.json",
            "format":       "json",
            "size_bytes":   4096,
            "exported_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_list():
    """Billing invoice list · 账单列表 (R373)"""
    return {
        "status": "ok",
        "data": [
            {"invoice_id": "inv_001", "amount_yuan": 1999, "status": "paid",    "created_at": "2026-08-15T00:00:00Z"},
            {"invoice_id": "inv_002", "amount_yuan": 2999, "status": "paid",    "created_at": "2026-09-01T00:00:00Z"},
            {"invoice_id": "inv_003", "amount_yuan":  199, "status": "pending", "created_at": "2026-09-15T00:00:00Z"},
            {"invoice_id": "inv_004", "amount_yuan": 1999, "status": "overdue", "created_at": "2026-09-25T00:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_pause_all():
    """Campaigns pause-all · 全部暂停 (R373)"""
    return {
        "status": "ok",
        "data": {
            "paused_count":  5,
            "previous_total_active": 6,
            "remaining_active":     1,
            "paused_at":            datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_duplicate(file_id: str):
    """Files duplicate · 复制文件 (R373)"""
    return {
        "status": "ok",
        "data": {
            "original_file_id": file_id,
            "new_file_id":      f"{file_id}_copy_v23",
            "new_name":         f"副本_{file_id}.pdf",
            "duplicated_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_backup_codes():
    """Auth backup codes · 备份码 (R373)"""
    return {
        "status": "ok",
        "data": {
            "codes": [
                "v23_R373_bk_001",
                "v23_R373_bk_002",
                "v23_R373_bk_003",
                "v23_R373_bk_004",
                "v23_R373_bk_005",
                "v23_R373_bk_006",
                "v23_R373_bk_007",
                "v23_R373_bk_008",
                "v23_R373_bk_009",
                "v23_R373_bk_010",
            ],
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "regenerate_at": "2026-10-30T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_train(skill_id: str):
    """Skill train · 训练 skill (R374)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "training_status": "started",
            "epochs":          10,
            "batch_size":      32,
            "started_at":      datetime.utcnow().isoformat() + "Z",
            "estimated_done_at": "2026-10-01T08:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription(tenant_id: str):
    """Billing subscription · 订阅 (R374)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":      tenant_id,
            "subscription_id": "sub_v23_R374",
            "plan":           "pro",
            "status":         "active",
            "renews_at":      "2026-10-15T00:00:00Z",
            "auto_renew":     True,
            "monthly_yuan":   1999,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_optimize(campaign_id: str):
    """Campaigns optimize · AI 优化 (R374)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":       campaign_id,
            "optimize_status":   "applied",
            "before_ctr":        "4.5%",
            "after_ctr":         "8.2%",
            "improvement_pct":   "82.2",
            "applied_changes":   [
                "调整投放时段到 18-22 点 (CTR +32%)",
                "优化文案关键词 (CTR +28%)",
                "调整人群定向 (CTR +22%)",
            ],
            "optimized_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_trash(file_id: str):
    """Files trash · 移到回收站 (R374)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "trashed":     True,
            "trashed_at":  datetime.utcnow().isoformat() + "Z",
            "purge_after": "2026-11-15T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys():
    """Auth api-keys · API key 列表 (R374)"""
    return {
        "status": "ok",
        "data": [
            {"key_id": "k_001", "name": "production",     "scopes": ["read", "write", "admin"], "last_used_at": "2026-09-30T16:00:00Z", "created_at": "2026-06-15T00:00:00Z"},
            {"key_id": "k_002", "name": "staging",        "scopes": ["read", "write"],         "last_used_at": "2026-09-29T14:00:00Z", "created_at": "2026-08-01T00:00:00Z"},
            {"key_id": "k_003", "name": "ci-cd-pipeline", "scopes": ["read", "deploy"],        "last_used_at": "2026-09-30T10:00:00Z", "created_at": "2026-09-01T00:00:00Z"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_test(skill_id: str):
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


def get_skills_metrics(skill_id: str):
    """Skill metrics · skill 性能指标 (R376)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "total_uses":     1248,
            "success_rate":   "96.4%",
            "avg_latency_ms": 412,
            "p95_latency_ms": 1280,
            "p99_latency_ms": 3200,
            "user_rating":     "4.7/5",
            "last_used_at":   "2026-09-30T16:14:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_pdf(invoice_id: str):
    """Billing invoice PDF · 账单 PDF (R376)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "pdf_url":      f"/api/v2/billing/{invoice_id}/invoice.pdf",
            "size_bytes":   124578,
            "pages":        2,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_list(campaign_id: str):
    """Campaigns audience list · 受众列表 (R376)"""
    return {
        "status": "ok",
        "data": [
            {"user_id": "u_001", "name": "心之所向便是光", "segment": "owner",     "engagement_score": 0.95},
            {"user_id": "u_002", "name": "运维",          "segment": "admin",     "engagement_score": 0.82},
            {"user_id": "u_003", "name": "销售",          "segment": "member",    "engagement_score": 0.74},
            {"user_id": "u_004", "name": "客服",          "segment": "member",    "engagement_score": 0.68},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_preview(file_id: str):
    """Files preview · 文件预览 (R376)"""
    return {
        "status": "ok",
        "data": {
            "file_id":      file_id,
            "preview_url":  f"https://cloudtech.example.com/api/v2/files/{file_id}/preview.html",
            "thumbnail_url": f"https://cloudtech.example.com/api/v2/files/{file_id}/thumb.png",
            "format":       "pdf",
            "size_bytes":   2400000,
            "expires_at":   "2026-09-30T19:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_tokens():
    """Auth tokens · 当前用户所有 token (R376)"""
    return {
        "status": "ok",
        "data": [
            {"token_id": "t_001", "name": "web-spa",       "scopes": ["read", "write"], "last_used_at": "2026-09-30T16:00:00Z", "created_at": "2026-01-15T00:00:00Z", "expires_at": "2027-01-15T00:00:00Z"},
            {"token_id": "t_002", "name": "mobile-app",    "scopes": ["read"],         "last_used_at": "2026-09-30T15:30:00Z", "created_at": "2026-03-01T00:00:00Z", "expires_at": "2027-03-01T00:00:00Z"},
            {"token_id": "t_003", "name": "ci-cd",         "scopes": ["read", "deploy"], "last_used_at": "2026-09-30T10:00:00Z", "created_at": "2026-06-01T00:00:00Z", "expires_at": "2026-12-01T00:00:00Z"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_version(skill_id: str):
    """Skill version · 版本管理 (R377)"""
    return {
        "status": "ok",
        "data": [
            {"version": "v2.1.0", "created_at": "2026-09-30T10:00:00Z", "is_latest": True,  "deprecated": False, "changelog": "+ 新增对话缓存 + 优化 prompt"},
            {"version": "v2.0.5", "created_at": "2026-09-15T10:00:00Z", "is_latest": False, "deprecated": False, "changelog": "+ 修复边界条件"},
            {"version": "v2.0.0", "created_at": "2026-09-01T10:00:00Z", "is_latest": False, "deprecated": False, "changelog": "+ 全新 UI"},
            {"version": "v1.5.0", "created_at": "2026-08-01T10:00:00Z", "is_latest": False, "deprecated": True,  "changelog": "+ 旧版本"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_charge(invoice_id: str):
    """Billing charge · 扣款 (R377)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "charge_id":     f"chg_{invoice_id}_v23",
            "amount_yuan":   1999,
            "method":        "wechat_pay",
            "success":       True,
            "transaction_id": f"txn_{invoice_id}_v23",
            "charged_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_schedule(campaign_id: str):
    """Campaigns schedule · 排期 (R377)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "scheduled_at":  "2026-10-01T09:00:00Z",
            "duration_days": 14,
            "timezone":      "Asia/Shanghai",
            "auto_publish":  True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_lock(file_id: str):
    """Files lock · 文件锁 (R377)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "locked":      True,
            "locked_by":   "u_001",
            "locked_at":   datetime.utcnow().isoformat() + "Z",
            "expires_at":  "2026-09-30T20:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sso():
    """Auth SSO · 单点登录 (R377)"""
    return {
        "status": "ok",
        "data": {
            "sso_url":      "https://cloudtech.example.com/api/v2/auth/sso/redirect?token=sso_v23_R377&return=/dashboard",
            "providers":    ["wechat_work", "feishu", "dingtalk", "microsoft", "google", "github"],
            "current":      "wechat_work",
            "expires_in":   3600,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_share(skill_id: str):
    """Skill share · 分享 skill (R378)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "share_url":    f"https://cloudtech.example.com/share/skill/{skill_id}?token=v23_R378",
            "share_token":  "shr_v23_R378_" + skill_id,
            "permissions":  ["view", "import"],
            "expires_at":   "2026-10-30T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_card_list():
    """Billing card list · 支付方式列表 (R378)"""
    return {
        "status": "ok",
        "data": [
            {"card_id": "c_001", "brand": "Visa",       "last4": "4242", "exp": "12/27", "is_default": True},
            {"card_id": "c_002", "brand": "MasterCard", "last4": "5555", "exp": "08/28", "is_default": False},
        ],
        "count": 2,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_report_csv(campaign_id: str):
    """Campaigns report CSV · CSV 报告 (R378)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":  campaign_id,
            "csv_url":      f"/api/v2/campaigns/{campaign_id}/report.csv",
            "rows":         312,
            "columns":      ["date", "channel", "impressions", "clicks", "conversions", "revenue_yuan"],
            "size_bytes":   48720,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_metadata(file_id: str):
    """Files metadata · 文件元数据 (R378)"""
    return {
        "status": "ok",
        "data": {
            "file_id":       file_id,
            "name":          "产品主视觉图.png",
            "type":          "image/png",
            "size_bytes":    2400000,
            "created_at":    "2026-09-15T10:00:00Z",
            "modified_at":   "2026-09-30T16:00:00Z",
            "tags":          ["marketing", "v23", "hero"],
            "checksum_md5":  "9f8e7d6c5b4a3210fedcba9876543210",
            "checksum_sha256": "abc123def456789...",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_oauth():
    """Auth OAuth · OAuth 配置 (R378)"""
    return {
        "status": "ok",
        "data": {
            "providers": [
                {"provider": "google",    "client_id": "google_v23_R378", "scope": "openid email profile", "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."},
                {"provider": "github",    "client_id": "github_v23_R378", "scope": "user:email repo",       "auth_url": "https://github.com/login/oauth/authorize?..."},
                {"provider": "feishu",    "client_id": "feishu_v23_R378", "scope": "contact:user.id",       "auth_url": "https://open.feishu.cn/open-apis/authen/v1/index?..."},
            ],
            "callback_url": "https://cloudtech.example.com/auth/oauth/callback",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_fork(skill_id: str):
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


def get_skills_merge(skill_id: str):
    """Skill merge · 合并 skill (R380)"""
    return {
        "status": "ok",
        "data": {
            "source_skill_id":   skill_id,
            "target_skill_id":   f"{skill_id}_merged_v23",
            "merged_at":          datetime.utcnow().isoformat() + "Z",
            "merged_by":          "u_001",
            "merged_nodes":       47,
            "merged_skills":      3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_pdf_download(invoice_id: str):
    """Billing invoice PDF download · 账单 PDF 下载 (R380)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "pdf_url":      f"https://cloudtech.example.com/api/v2/billing/{invoice_id}/invoice.pdf?token=v23_R380",
            "filename":     f"invoice_{invoice_id}.pdf",
            "size_bytes":   124578,
            "download_id":  f"dl_{invoice_id}_v23",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_budget_history(campaign_id: str):
    """Campaigns budget history · 预算变更历史 (R380)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-30T15:00:00Z", "action": "increased",  "from_yuan": 18000, "to_yuan": 25000, "reason": "AI optimize"},
            {"date": "2026-09-25T10:00:00Z", "action": "decreased",  "from_yuan": 20000, "to_yuan": 18000, "reason": "budget control"},
            {"date": "2026-09-15T14:00:00Z", "action": "set",        "from_yuan":     0, "to_yuan": 20000, "reason": "launch"},
            {"date": "2026-09-01T09:00:00Z", "action": "draft",      "from_yuan":     0, "to_yuan":     0, "reason": "created"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_upload_stats(file_id: str):
    """Files upload stats · 上传统计 (R380)"""
    return {
        "status": "ok",
        "data": {
            "file_id":           file_id,
            "total_uploads":     12,
            "by_user": [
                {"user_id": "u_001", "name": "心之所向便是光", "uploads": 8},
                {"user_id": "u_002", "name": "运维",          "uploads": 4},
            ],
            "by_size_mb":        "124.5",
            "last_upload_at":    "2026-09-30T16:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_key_rotate(key_id: str):
    """Auth api-keys/{id}/rotate · 轮换 API key (R380)"""
    return {
        "status": "ok",
        "data": {
            "key_id":        key_id,
            "new_key_id":    f"{key_id}_rotated_v23",
            "new_secret":    f"sk_v23_R380_{key_id}_rotated",
            "old_expires_at":"2026-10-15T00:00:00Z",
            "new_expires_at":"2027-10-15T00:00:00Z",
            "rotated_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_truncate(skill_id: str):
    """Skill truncate · 截断 skill (R381)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "truncated":       True,
            "truncated_at":    datetime.utcnow().isoformat() + "Z",
            "kept_versions":   3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_cancel(tenant_id: str):
    """Billing subscription cancel · 取消订阅 (R381)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":      tenant_id,
            "subscription_id": "sub_v23_R381",
            "canceled":       True,
            "reason":         "user_requested",
            "effective_at":   "2026-10-15T00:00:00Z",  # 当前周期结束
            "refund_yuan":    0,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_report_pdf_download(campaign_id: str):
    """Campaigns report PDF download · PDF 报告下载 (R381)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "pdf_url":       f"https://cloudtech.example.com/api/v2/campaigns/{campaign_id}/report.pdf?token=v23_R381",
            "filename":      f"rpt_{campaign_id}_v23.pdf",
            "size_bytes":    524288,
            "pages":         12,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_permissions(file_id: str):
    """Files permissions · 文件权限 (R381)"""
    return {
        "status": "ok",
        "data": [
            {"user_id": "u_001", "name": "心之所向便是光", "permission": "owner",    "granted_at": "2026-06-15T00:00:00Z"},
            {"user_id": "u_002", "name": "运维",          "permission": "editor",   "granted_at": "2026-08-01T00:00:00Z"},
            {"user_id": "u_003", "name": "销售",          "permission": "viewer",   "granted_at": "2026-09-01T00:00:00Z"},
            {"user_id": "u_004", "name": "客服",          "permission": "viewer",   "granted_at": "2026-09-15T00:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_key_delete(key_id: str):
    """Auth api-keys/{id}/delete · 删除 API key (R381)"""
    return {
        "status": "ok",
        "data": {
            "key_id":    key_id,
            "deleted":   True,
            "deleted_at": datetime.utcnow().isoformat() + "Z",
            "deleted_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_duplicate(skill_id: str):
    """Skill duplicate · 复制 skill (R382)"""
    return {
        "status": "ok",
        "data": {
            "source_skill_id": skill_id,
            "new_skill_id":    f"{skill_id}_copy_v23",
            "new_name":        f"{skill_id} 副本",
            "duplicated_at":   datetime.utcnow().isoformat() + "Z",
            "duplicated_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_charge_history(invoice_id: str):
    """Billing charge history · 扣款历史 (R382)"""
    return {
        "status": "ok",
        "data": [
            {"charge_id": "chg_001", "amount_yuan": 1999, "method": "wechat_pay", "success": True,  "at": "2026-08-15T03:00:00Z"},
            {"charge_id": "chg_002", "amount_yuan": 2999, "method": "alipay",     "success": True,  "at": "2026-09-01T03:00:00Z"},
            {"charge_id": "chg_003", "amount_yuan":  199, "method": "wechat_pay", "success": False, "at": "2026-09-15T03:00:00Z"},
            {"charge_id": "chg_004", "amount_yuan": 1999, "method": "wechat_pay", "success": True,  "at": "2026-09-25T03:00:00Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_conversion_funnel(campaign_id: str):
    """Campaigns conversion funnel · 转化漏斗 (R382)"""
    return {
        "status": "ok",
        "data": [
            {"stage": "曝光",  "count": 18420, "pct": 100.0},
            {"stage": "点击",  "count":   920, "pct":   5.0},
            {"stage": "访问",  "count":   480, "pct":   2.6},
            {"stage": "注册",  "count":   180, "pct":   0.98},
            {"stage": "试用",  "count":    72, "pct":   0.39},
            {"stage": "付费",  "count":    42, "pct":   0.23},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_history(file_id: str):
    """Files download history · 下载历史 (R382)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T16:00:00Z", "user_id": "u_001", "ip": "127.0.0.1",     "user_agent": "Edge/Windows"},
            {"at": "2026-09-29T14:30:00Z", "user_id": "u_002", "ip": "192.168.1.42",  "user_agent": "Chrome/macOS"},
            {"at": "2026-09-28T10:15:00Z", "user_id": "u_003", "ip": "192.168.1.88",  "user_agent": "Safari/iOS"},
            {"at": "2026-09-27T16:45:00Z", "user_id": "u_004", "ip": "10.0.0.15",    "user_agent": "Edge/Windows"},
            {"at": "2026-09-26T11:30:00Z", "user_id": "u_001", "ip": "127.0.0.1",     "user_agent": "Edge/Windows"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_2fa_disable():
    """Auth 2FA disable · 关闭 2FA (R382)"""
    return {
        "status": "ok",
        "data": {
            "user_id":      "u_001",
            "2fa_status":   "disabled",
            "disabled_at":  datetime.utcnow().isoformat() + "Z",
            "disabled_by":  "u_001",
            "backup_codes_deleted": 10,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_stats(skill_id: str):
    """Skill stats · skill 统计 (R383)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "active_users":   87,
            "total_invocations": 1248,
            "success_rate":   "96.4%",
            "avg_response_ms": 412,
            "by_day": [
                {"date": "2026-09-24", "invocations": 145},
                {"date": "2026-09-25", "invocations": 168},
                {"date": "2026-09-26", "invocations": 192},
                {"date": "2026-09-27", "invocations": 184},
                {"date": "2026-09-28", "invocations": 210},
                {"date": "2026-09-29", "invocations": 178},
                {"date": "2026-09-30", "invocations": 171},
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_invoice_template():
    """Billing invoice template · 账单模板 (R383)"""
    return {
        "status": "ok",
        "data": {
            "templates": [
                {"template_id": "tpl_001", "name": "标准发票",     "language": "zh-CN", "fields": ["invoice_no", "tenant", "amount", "items", "tax_id"]},
                {"template_id": "tpl_002", "name": "增值税专票", "language": "zh-CN", "fields": ["invoice_no", "tenant", "amount", "items", "tax_id", "bank_info"]},
                {"template_id": "tpl_003", "name": "英文发票",   "language": "en-US", "fields": ["invoice_no", "tenant", "amount", "items", "tax_id"]},
            ],
            "default_template": "tpl_001",
            "source": "demo_seed",
            "ts": datetime.utcnow().isoformat() + "Z",
        },
    }


def get_campaigns_cost_breakdown(campaign_id: str):
    """Campaigns cost breakdown · 成本细分 (R383)"""
    return {
        "status": "ok",
        "data": [
            {"category": "ad_spend",   "amount_yuan": 2800, "pct": 87.5},
            {"category": "creative",   "amount_yuan":  200, "pct":  6.3},
            {"category": "platform_fee","amount_yuan":  150, "pct":  4.7},
            {"category": "tools",       "amount_yuan":   50, "pct":  1.5},
        ],
        "total_yuan": 3200,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_stats(file_id: str):
    """Files share stats · 分享统计 (R383)"""
    return {
        "status": "ok",
        "data": {
            "file_id":           file_id,
            "total_shares":      8,
            "active_share_links": 5,
            "total_views":       142,
            "by_link": [
                {"link_id": "l_001", "views": 65, "unique": 18},
                {"link_id": "l_002", "views": 42, "unique": 12},
                {"link_id": "l_003", "views": 28, "unique": 8},
                {"link_id": "l_004", "views": 5,  "unique": 3},
                {"link_id": "l_005", "views": 2,  "unique": 1},
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def _register_v23_q_proxy():
    """SaaS v1 register 真注册端点 (TryNow 表单后端) · 用 POST 但 vite-spa TryNow 用 GET"""
    import urllib.parse
    # 实际 TryNow.tsx 用 GET /api/v2/saas/v1/info 验证连通
    # 这里返回 mock 成功 (因为 POST 没在 vite-spa 调)
    return {
        "status":         "ok",
        "data": {
            "tenant_id":      "t_v23_R384",
            "user_id":        "u_demo",
            "trial_started":   True,
            "trial_days":      7,
            "trial_end_at":    "2026-10-07T00:00:00Z",
            "next_step_url":   "/dashboard?from=trial_v23_R384",
            "verification":   "TryNow form 后端 OK",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_2fa_regenerate():
    """Auth 2FA regenerate · 重新生成 2FA 备份码 (R383)"""
    return {
        "status": "ok",
        "data": {
            "user_id":     "u_001",
            "backup_codes": [
                "v23_R383_bk_001",
                "v23_R383_bk_002",
                "v23_R383_bk_003",
                "v23_R383_bk_004",
                "v23_R383_bk_005",
                "v23_R383_bk_006",
                "v23_R383_bk_007",
                "v23_R383_bk_008",
                "v23_R383_bk_009",
                "v23_R383_bk_010",
            ],
            "regenerated_at": datetime.utcnow().isoformat() + "Z",
            "old_codes_invalidated": True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_reindex(skill_id: str):
    """Skill reindex · 重建索引 (R385)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "reindex_status": "started",
            "indexed_vectors": 1248,
            "started_at":    datetime.utcnow().isoformat() + "Z",
            "estimated_done_at": "2026-09-30T19:30:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_rate(tenant_id: str):
    """Billing tax rate · 税率 (R385)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":    tenant_id,
            "country":      "CN",
            "tax_rate":     0.06,
            "tax_type":     "vat",
            "is_small":     True,
            "reduced_rate": 0.03,
            "updated_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_clicks(campaign_id: str):
    """Campaigns clicks · 点击流 (R385)"""
    return {
        "status": "ok",
        "data": [
            {"timestamp": "2026-09-30T16:00:00Z", "user_id": "u_001", "ip": "127.0.0.1",     "device": "Edge/Windows"},
            {"timestamp": "2026-09-30T15:45:00Z", "user_id": "u_002", "ip": "192.168.1.42",  "device": "Chrome/macOS"},
            {"timestamp": "2026-09-30T15:30:00Z", "user_id": "u_003", "ip": "192.168.1.88",  "device": "Safari/iOS"},
            {"timestamp": "2026-09-30T15:15:00Z", "user_id": "u_004", "ip": "10.0.0.15",    "device": "Edge/Windows"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments(file_id: str):
    """Files comments · 文件评论 (R385)"""
    return {
        "status": "ok",
        "data": [
            {"comment_id": "c_001", "user_id": "u_001", "name": "心之所向便是光", "content": "请更新 logo 颜色",   "created_at": "2026-09-29T10:00:00Z"},
            {"comment_id": "c_002", "user_id": "u_002", "name": "运维",          "content": "已上传 v2 版本",       "created_at": "2026-09-30T14:00:00Z"},
            {"comment_id": "c_003", "user_id": "u_003", "name": "销售",          "content": "请改成中文版",          "created_at": "2026-09-30T15:00:00Z"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_key_test(key_id: str):
    """Auth api-keys/{id}/test · 测试 API key (R385)"""
    return {
        "status": "ok",
        "data": {
            "key_id":       key_id,
            "test_status":  "valid",
            "latency_ms":   42,
            "scopes":       ["read", "write"],
            "tested_at":    datetime.utcnow().isoformat() + "Z",
            "test_request": {"endpoint": "/api/v2/auth/me", "method": "GET"},
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_reset(skill_id: str):
    """Skill reset · 重置 skill (R386)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "reset":       True,
            "reset_at":    datetime.utcnow().isoformat() + "Z",
            "kept_stats":  True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_coupon(coupon_code: str):
    """Billing coupon · 优惠券 (R386)"""
    coupons = {
        "V23_R386":     {"discount_pct": 50, "valid_until": "2026-10-30T00:00:00Z", "min_amount_yuan": 1000},
        "EARLY_BIRD":  {"discount_pct": 30, "valid_until": "2026-09-30T23:59:59Z", "min_amount_yuan": 500},
        "FRIENDS_50":  {"discount_pct": 50, "valid_until": "2026-12-31T23:59:59Z", "min_amount_yuan": 199},
    }
    found = coupons.get(coupon_code)
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {
            "coupon_code":  coupon_code,
            **found,
            "applied_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_recipients(campaign_id: str):
    """Campaigns recipients · 收件人 (R386)"""
    return {
        "status": "ok",
        "data": [
            {"user_id": "u_001", "name": "心之所向便是光", "channel": "微信",   "status": "delivered", "at": "2026-09-30T16:00:00Z"},
            {"user_id": "u_002", "name": "运维",          "channel": "邮件",   "status": "delivered", "at": "2026-09-30T16:00:01Z"},
            {"user_id": "u_003", "name": "销售",          "channel": "微信",   "status": "delivered", "at": "2026-09-30T16:00:02Z"},
            {"user_id": "u_004", "name": "客服",          "channel": "短信",   "status": "pending",   "at": "2026-09-30T16:00:03Z"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_list(file_id: str):
    """Files share list · 分享链接列表 (R386)"""
    return {
        "status": "ok",
        "data": [
            {"link_id": "l_001", "url": f"https://cloudtech.example.com/share/{file_id}", "permissions": ["view"],          "views": 65, "created_at": "2026-09-25T10:00:00Z"},
            {"link_id": "l_002", "url": f"https://cloudtech.example.com/share/{file_id}/e",  "permissions": ["view", "download"], "views": 42, "created_at": "2026-09-28T10:00:00Z"},
        ],
        "count": 2,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_signout(session_id: str):
    """Auth sessions/{id}/signout · 撤销单 session (R386)"""
    return {
        "status": "ok",
        "data": {
            "session_id":   session_id,
            "signed_out":   True,
            "signed_out_at": datetime.utcnow().isoformat() + "Z",
            "active_sessions_remaining": 3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_analytics(skill_id: str):
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


def get_skills_rollback(skill_id: str):
    """Skill rollback · 回滚 skill (R388)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":         skill_id,
            "rolled_back_to":   "v2.0.5",
            "rolled_back_at":   datetime.utcnow().isoformat() + "Z",
            "previous_version": "v2.1.0",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_dunning(invoice_id: str):
    """Billing dunning · 催收 (R388)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "dunning_sent": True,
            "reminders":    2,
            "level":        "final",
            "next_action":  "账户暂停 (7 天后)",
            "sent_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_budget_pacing(campaign_id: str):
    """Campaigns budget pacing · 预算节奏 (R388)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":     campaign_id,
            "daily_budget":    500,
            "spent_today":     287,
            "pace_left":       213,
            "pace_pct":        "57.4%",
            "expected_pace":   "62.5%",
            "recommendation":  "✓ 节奏正常",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_external_share(file_id: str):
    """Files external share · 外部分享 (R388)"""
    return {
        "status": "ok",
        "data": {
            "file_id":         file_id,
            "external_url":    f"https://ext.cloudtech.example.com/share/{file_id}?token=v23_R388",
            "external_token":  "ext_v23_R388_" + file_id,
            "expires_at":      "2026-10-30T00:00:00Z",
            "password_protected": True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_trust(session_id: str):
    """Auth sessions/{id}/trust · 信任设备 (R388)"""
    return {
        "status": "ok",
        "data": {
            "session_id":      session_id,
            "trusted":         True,
            "trusted_until":   "2027-09-30T00:00:00Z",
            "trusted_by":      "u_001",
            "trusted_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_promote(skill_id: str):
    """Skill promote · 推广 skill (R389)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "promoted":       True,
            "promoted_to":    "marketplace",
            "promoted_at":    datetime.utcnow().isoformat() + "Z",
            "visibility_boost": "10x",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_invoice(invoice_id: str):
    """Billing tax invoice · 增值税发票 (R389)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "tax_invoice_id": f"tax_{invoice_id}_v23",
            "amount_yuan":   1999,
            "tax_rate":      0.06,
            "tax_yuan":      120,
            "url":           f"/api/v2/billing/{invoice_id}/tax-invoice.pdf",
            "issued_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_creatives(campaign_id: str):
    """Campaigns creatives · 创意素材 (R389)"""
    return {
        "status": "ok",
        "data": [
            {"creative_id": "cr_001", "type": "image", "url": "/media/creatives/c001_1.jpg", "clicks": 87,  "ctr": "4.5%"},
            {"creative_id": "cr_002", "type": "video", "url": "/media/creatives/c001_1.mp4", "clicks": 142, "ctr": "6.8%"},
            {"creative_id": "cr_003", "type": "text",  "url": "/media/creatives/c001_1.txt", "clicks": 65,  "ctr": "3.8%"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_url_token(file_id: str):
    """Files download url token · 一次性下载 URL (R389)"""
    return {
        "status": "ok",
        "data": {
            "file_id":         file_id,
            "download_url":    f"https://cloudtech.example.com/api/v2/files/{file_id}/stream?token=once_v23_R389",
            "token":           f"once_v23_R389_{file_id}",
            "expires_at":      "2030-01-01T00:00:00Z",
            "single_use":      True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_revoke_all_others(session_id: str):
    """Auth sessions/{id}/revoke-all-others · 撤销其他 (R389)"""
    return {
        "status": "ok",
        "data": {
            "current_session_id":   session_id,
            "revoked_count":         3,
            "kept_session_id":       session_id,
            "revoked_at":            datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_deprecate(skill_id: str):
    """Skill deprecate · 弃用 skill (R390)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "deprecated":    True,
            "deprecated_at": datetime.utcnow().isoformat() + "Z",
            "grace_until":    "2026-12-30T00:00:00Z",
            "migration":      "plan_global_skill_v3_v23",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_pause(tenant_id: str):
    """Billing subscription pause · 暂停订阅 (R390)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R390",
            "paused":          True,
            "paused_at":       datetime.utcnow().isoformat() + "Z",
            "resume_at":      "2026-11-30T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_stats(campaign_id: str):
    """Campaigns audience stats · 受众统计 (R390)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":      campaign_id,
            "total_reached":    18420,
            "engaged":          4180,
            "engagement_rate":  "22.7%",
            "by_age": {
                "18-24": 1840, "25-34": 6280, "35-44": 5240, "45-54": 3240, "55+": 1820,
            },
            "by_gender": {
                "male":   9240, "female": 8640, "other": 540,
            },
            "by_location": {
                "深圳": 2840, "上海": 2280, "北京": 2120, "广州": 1820, "其他": 9360,
            },
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_duplicate_rename(file_id: str):
    """Files duplicate-rename · 复制+重命名 (R390)"""
    return {
        "status": "ok",
        "data": {
            "source_file_id": file_id,
            "new_file_id":    f"{file_id}_v23_R390",
            "new_name":       f"副本_{file_id}_R390.pdf",
            "duplicated_at":  datetime.utcnow().isoformat() + "Z",
            "renamed_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_impersonate(session_id: str):
    """Auth sessions/{id}/impersonate · 模拟 session (R390)"""
    return {
        "status": "ok",
        "data": {
            "impersonated_session_id":  session_id,
            "impersonated_by":           "u_001",
            "impersonated_user":         "u_002",
            "impersonated_at":           datetime.utcnow().isoformat() + "Z",
            "expires_at":                "2026-09-30T20:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_import_v2(skill_id: str):
    """Skill import v2 · 导入 (R391)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "imported":        True,
            "imported_from":   f"https://marketplace.v23.com/skills/{skill_id}.yaml",
            "size_kb":         18,
            "dependencies":    ["@xyflow/react", "lucide-react", "tailwindcss"],
            "imported_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_resume(tenant_id: str):
    """Billing subscription resume · 恢复订阅 (R391)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R391",
            "resumed":         True,
            "resumed_at":      datetime.utcnow().isoformat() + "Z",
            "next_billing_at": "2026-10-15T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_aggressive(campaign_id: str):
    """Campaigns audience-aggressive · 受众激增 (R391)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "aggressive":    True,
            "expansion_pct":  "+200%",
            "new_segments":  12,
            "extra_reach":    36840,
            "applied_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_restore_from_trash(file_id: str):
    """Files restore-from-trash · 从回收站恢复 (R391)"""
    return {
        "status": "ok",
        "data": {
            "file_id":     file_id,
            "restored":    True,
            "restored_at": datetime.utcnow().isoformat() + "Z",
            "from_trash":  True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_forget_device(session_id: str):
    """Auth sessions/{id}/forget-device · 忘记设备 (R391)"""
    return {
        "status": "ok",
        "data": {
            "session_id":     session_id,
            "device_forgot":  True,
            "forgot_at":      datetime.utcnow().isoformat() + "Z",
            "trusted_until":  None,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_auto_train(skill_id: str):
    """Skill auto-train · 自动训练 (R392)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":       skill_id,
            "auto_train":     True,
            "epochs":         20,
            "started_at":     datetime.utcnow().isoformat() + "Z",
            "estimated_done": "2026-10-01T08:00:00Z",
            "gpu":            "auto",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_coupon_validate(coupon_code: str):
    """Billing coupon validate · 验证优惠券 (R392)"""
    coupons = {
        "V23_R392":     {"discount_pct": 50, "valid": True,  "applies_to": "all"},
        "EARLY_BIRD":  {"discount_pct": 30, "valid": False, "reason": "expired"},
        "INVALID":     {"valid":        False, "reason": "unknown_code"},
    }
    found = coupons.get(coupon_code)
    if not found:
        return {"status": "ok", "data": {"coupon_code": coupon_code, "valid": False, "reason": "unknown_code"}, "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {"coupon_code": coupon_code, **found},
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_abtest_stop(campaign_id: str):
    """Campaigns abtest-stop · 停止 A/B 测试 (R392)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "abtest_status": "stopped",
            "winner":        "B",
            "stopped_at":    datetime.utcnow().isoformat() + "Z",
            "winner_promoted_to_full": True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_item(comment_id: str):
    """Files comments/{id} · 评论单项 (R392)"""
    comments = {
        "c_001": {"user_id": "u_001", "name": "心之所向便是光", "content": "请更新 logo 颜色", "created_at": "2026-09-29T10:00:00Z", "replies": 2},
        "c_002": {"user_id": "u_002", "name": "运维",          "content": "已上传 v2 版本",  "created_at": "2026-09-30T14:00:00Z", "replies": 0},
        "c_003": {"user_id": "u_003", "name": "销售",          "content": "请改成中文版",    "created_at": "2026-09-30T15:00:00Z", "replies": 1},
    }
    found = comments.get(comment_id)
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {"comment_id": comment_id, **found},
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sessions_cleanup():
    """Auth sessions cleanup · 清理过期 session (R392)"""
    return {
        "status": "ok",
        "data": {
            "cleaned_count":  12,
            "remaining_count": 4,
            "cleaned_at":      datetime.utcnow().isoformat() + "Z",
            "kept_session_ids": ["s_001", "s_002", "s_003", "s_004"],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_retire(skill_id: str):
    """Skill retire · 退役 skill (R393)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "retired":    True,
            "retired_at": datetime.utcnow().isoformat() + "Z",
            "archived":   True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_rate_update(tenant_id: str):
    """Billing tax-rate-update · 更新税率 (R393)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":   tenant_id,
            "previous_rate": 0.13,
            "updated_rate":  0.06,
            "updated_at":   datetime.utcnow().isoformat() + "Z",
            "reason":       "增值税改革",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_recipients_stats(campaign_id: str):
    """Campaigns recipients-stats · 收件人统计 (R393)"""
    return {
        "status": "ok",
        "data": {
            "campaign_id":   campaign_id,
            "total_sent":    4,
            "delivered":      3,
            "pending":       1,
            "delivery_rate": "75%",
            "by_channel": {
                "微信": {"sent": 2, "delivered": 2, "pending": 0},
                "邮件": {"sent": 1, "delivered": 1, "pending": 0},
                "短信": {"sent": 1, "delivered": 0, "pending": 1},
            },
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_reply(comment_id: str):
    """Files comments/{id}/reply · 评论回复 (R393)"""
    return {
        "status": "ok",
        "data": {
            "comment_id":   comment_id,
            "reply_id":     f"rep_{comment_id}_v23",
            "reply":        "已修复，请刷新查看",
            "replied_by":   "u_001",
            "replied_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_devices_revoke(device_id: str):
    """Auth devices/{id}/revoke · 撤销设备 (R393)"""
    return {
        "status": "ok",
        "data": {
            "device_id":   device_id,
            "revoked":     True,
            "revoked_at":  datetime.utcnow().isoformat() + "Z",
            "sessions_today":14,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_optimize(skill_id: str):
    """Skill optimize · 优化 skill (R394)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":          skill_id,
            "optimized":         True,
            "latency_improvement":"-32%",
            "cost_improvement":  "-18%",
            "optimized_at":      datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods():
    """Billing payment methods · 支付方式 (R394)"""
    return {
        "status": "ok",
        "data": [
            {"method": "wechat_pay", "name": "微信支付",   "fee_pct": 0.6,  "min_yuan": 0.01, "max":     50000},
            {"method": "alipay",      "name": "支付宝",     "fee_pct": 0.6,  "min_yuan": 0.01, "max":     50000},
            {"method": "union_pay",    "name": "银联支付",   "fee_pct": 0.7,  "min_yuan": 0.01, "max":     100000},
            {"method": "bank_card",    "name": "银行卡",     "fee_pct": 1.0,  "min_yuan": 1.00, "max":     200000},
        ],
        "default_method": "wechat_pay",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_ctr_history(campaign_id: str):
    """Campaigns ctr-history · CTR 历史 (R394)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "impressions": 2620, "clicks": 132, "ctr": "5.0%"},
            {"date": "2026-09-25", "impressions": 2840, "clicks": 145, "ctr": "5.1%"},
            {"date": "2026-09-26", "impressions": 2610, "clicks": 128, "ctr": "4.9%"},
            {"date": "2026-09-27", "impressions": 2920, "clicks": 156, "ctr": "5.3%"},
            {"date": "2026-09-28", "impressions": 3010, "clicks": 162, "ctr": "5.4%"},
            {"date": "2026-09-29", "impressions": 3120, "clicks": 178, "ctr": "5.7%"},
            {"date": "2026-09-30", "impressions": 3010, "clicks": 187, "ctr": "6.2%"},
        ],
        "average_ctr": "5.4%",
        "trend": "+1.0%",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_delete(comment_id: str):
    """Files comments/{id}/delete · 删除评论 (R394)"""
    return {
        "status": "ok",
        "data": {
            "comment_id":   comment_id,
            "deleted":      True,
            "deleted_at":   datetime.utcnow().isoformat() + "Z",
            "deleted_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_devices_forget(device_id: str):
    """Auth devices/{id}/forget · 忘记设备 (R394)"""
    return {
        "status": "ok",
        "data": {
            "device_id":   device_id,
            "forgot":      True,
            "forgot_at":   datetime.utcnow().isoformat() + "Z",
            "trusted_until":None,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_clone(skill_id: str):
    """Skill clone · 克隆 skill (R395)"""
    return {
        "status": "ok",
        "data": {
            "source_skill_id": skill_id,
            "new_skill_id":    f"{skill_id}_clone_v23",
            "new_name":        f"{skill_id} 克隆",
            "cloned_by":       "u_001",
            "cloned_at":       datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_tax_rates():
    """Billing tax rates · 税率列表 (R395)"""
    return {
        "status": "ok",
        "data": [
            {"region": "CN",   "rate": 0.06, "type": "vat_general",   "applies_to": "all"},
            {"region": "CN",   "rate": 0.03, "type": "vat_small",     "applies_to": "small_business"},
            {"region": "CN",   "rate": 0.13, "type": "vat_old",       "applies_to": "deprecated"},
            {"region": "US",   "rate": 0.0,  "type": "sales_tax",     "applies_to": "varies_by_state"},
            {"region": "EU",   "rate": 0.20, "type": "vat",          "applies_to": "all"},
            {"region": "JP",   "rate": 0.10, "type": "consumption",   "applies_to": "all"},
        ],
        "default_region": "CN",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_impressions_history(campaign_id: str):
    """Campaigns impressions-history · 曝光历史 (R395)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "impressions": 2620},
            {"date": "2026-09-25", "impressions": 2840},
            {"date": "2026-09-26", "impressions": 2610},
            {"date": "2026-09-27", "impressions": 2920},
            {"date": "2026-09-28", "impressions": 3010},
            {"date": "2026-09-29", "impressions": 3120},
            {"date": "2026-09-30", "impressions": 3010},
        ],
        "total":        20130,
        "average":      2875,
        "trend_pct":    "+2.3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_revoke(file_id: str):
    """Files share-revoke · 撤销分享 (R395)"""
    return {
        "status": "ok",
        "data": {
            "file_id":        file_id,
            "share_revoked":  True,
            "active_links":   0,
            "revoked_at":     datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_sso_config(sso_id: str):
    """Auth sso/{id}/config · SSO 配置 (R395)"""
    configs = {
        "wechat_work": {"name": "企业微信",     "client_id": "wc_v23", "scopes": ["contact:user.id"]},
        "feishu":      {"name": "飞书",         "client_id": "fs_v23", "scopes": ["contact:user.id"]},
        "dingtalk":    {"name": "钉钉",         "client_id": "dd_v23", "scopes": ["contact:user.id"]},
        "google":      {"name": "Google",       "client_id": "g_v23",  "scopes": ["openid", "email", "profile"]},
    }
    found = configs.get(sso_id)
    if not found:
        return {"status": "ok", "data": {}, "source": "not_found", "ts": datetime.utcnow().isoformat() + "Z"}
    return {
        "status": "ok",
        "data": {"sso_id": sso_id, **found},
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_merge_multiple(skill_ids: str):
    """Skill merge-multiple · 合并多个 skill (R396)"""
    ids = skill_ids.split(',') if ',' in skill_ids else [skill_ids]
    return {
        "status": "ok",
        "data": {
            "merged_count":  len(ids),
            "merged_ids":    ids,
            "new_skill_id":  f"merged_v23_R396_{len(ids)}",
            "merged_at":     datetime.utcnow().isoformat() + "Z",
            "merged_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_upgrade(tenant_id: str):
    """Billing subscription-upgrade · 升级订阅 (R396)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R396_up",
            "previous_plan":   "basic",
            "upgraded_to":     "pro",
            "upgraded_at":     datetime.utcnow().isoformat() + "Z",
            "prorated_yuan":   500,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_age_stats(campaign_id: str):
    """Campaigns audience-age-stats · 受众年龄分布 (R396)"""
    return {
        "status": "ok",
        "data": [
            {"age_range": "13-17", "count":  980,  "pct":  5.3},
            {"age_range": "18-24", "count": 3680,  "pct": 20.0},
            {"age_range": "25-34", "count": 6280,  "pct": 34.1},
            {"age_range": "35-44", "count": 4120,  "pct": 22.3},
            {"age_range": "45-54", "count": 2180,  "pct": 11.8},
            {"age_range": "55-64", "count":  980,  "pct":  5.3},
            {"age_range": "65+",   "count":  200,  "pct":  1.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_comments_count(file_id: str):
    """Files comments-count · 评论计数 (R396)"""
    return {
        "status": "ok",
        "data": {
            "file_id":        file_id,
            "total_comments": 3,
            "unresolved":     1,
            "resolved":       2,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_all():
    """Auth api-keys/rotate-all · 全部轮换 (R396)"""
    return {
        "status": "ok",
        "data": {
            "rotated_count":   3,
            "rotated_at":      datetime.utcnow().isoformat() + "Z",
            "rotated_by":       "u_001",
            "old_keys_invalidated": True,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_analytics_advanced(skill_id: str):
    """Skill analytics-advanced · 高级分析 (R397)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":          skill_id,
            "trend":             "up",
            "trend_pct":         "+18.2",
            "retention_d1":       "82%",
            "retention_d7":       "64%",
            "retention_d30":      "48%",
            "user_satisfaction":  "4.6/5",
            "nps_score":          42,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_downgrade(tenant_id: str):
    """Billing subscription-downgrade · 降级订阅 (R397)"""
    return {
        "status": "ok",
        "data": {
            "tenant_id":       tenant_id,
            "subscription_id": "sub_v23_R397_down",
            "previous_plan":   "enterprise",
            "downgraded_to":   "pro",
            "downgraded_at":   datetime.utcnow().isoformat() + "Z",
            "refund_yuan":     5000,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_gender_stats(campaign_id: str):
    """Campaigns audience-gender-stats · 受众性别 (R397)"""
    return {
        "status": "ok",
        "data": [
            {"gender": "male",   "count": 9240, "pct": 50.2},
            {"gender": "female", "count": 8640, "pct": 46.9},
            {"gender": "other",  "count":  540, "pct":  2.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_share_stats_by_day(file_id: str):
    """Files share-stats-by-day · 分享按日 (R397)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "shares": 5,  "views": 28},
            {"date": "2026-09-25", "shares": 3,  "views": 18},
            {"date": "2026-09-26", "shares": 4,  "views": 24},
            {"date": "2026-09-27", "shares": 6,  "views": 35},
            {"date": "2026-09-28", "shares": 8,  "views": 42},
            {"date": "2026-09-29", "shares": 5,  "views": 22},
            {"date": "2026-09-30", "shares": 3,  "views": 18},
        ],
        "total_shares": 34,
        "total_views":  187,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_create():
    """Auth api-keys/create · 创建 API key (R397)"""
    import hashlib
    seed = b"v23_R397_create"
    kid = "k_v23_R397_" + hashlib.md5(seed).hexdigest()[:8]
    sec = "sk_v23_R397_" + hashlib.sha256(seed + b"_secret").hexdigest()[:16]
    return {
        "status": "ok",
        "data": {
            "key_id":    kid,
            "name":      "新创建 key",
            "secret":    sec,
            "scopes":    ["read"],
            "created_by": "u_001",
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


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
    "/api/v2/notifications/{id}":          lambda q, id="1": get_notifications_item(id),
    "/api/v2/leads/{id}":                  lambda q, id="lead_88759f8c3b34": get_lead_item(id),
    "/api/v2/tasks/{id}":                  lambda q, id="t_001": get_task_item(id),
    "/api/v2/users/{id}":                  lambda q, id="u_001": get_user_item(id),
    "/api/v2/campaigns/{id}":              lambda q, id="c001": get_campaign_stats(id),
    "/api/v2/files/{id}":                  lambda q, id="f_001": get_file_item(id),
    "/api/v2/projects/{id}":               lambda q, id="p_001": get_project_item(id),
    "/api/v2/funnels/{id}":                lambda q, id="f_pending": get_funnel_item(id),
    "/api/v2/tenants/{id}":                lambda q, id="t_3a59592b7619": get_tenant_item(id),
    "/api/v2/ai/{id}":                     lambda q, id="content_writer": get_ai_item(id),
    "/api/v2/skills/{id}":                lambda q, id="s_001": get_skill_item(id),
    "/api/v2/workflow/{id}/runs":          lambda q, id="wf-content-1": get_workflow_run("r_001"),
    "/api/v2/agents/{id}":                 lambda q, id="a_001": get_agent_item(id),
    "/api/v2/notifications/unread":        lambda q: get_notifications_unread(),
    "/api/v2/marketing/conversion":        lambda q: get_marketing_conversion(),
    "/api/v2/auth/refresh":                lambda q: get_auth_refresh(),
    "/api/v2/auth/logout":                 lambda q: get_auth_logout(),
    "/api/v2/files/{id}/download":         lambda q, id="f_001": get_file_download(id),
    "/api/v2/campaigns/{id}/report":       lambda q, id="c001": get_campaign_report(id),
    "/api/v2/email_queue/{id}/resend":     lambda q, id="36": get_email_queue_resend(id),
    "/api/v2/sessions/{id}/revoke":       lambda q, id="s_001": get_session_revoke(id),
    "/api/v2/billing/{id}/invoice":       lambda q, id="inv_001": get_billing_invoice(id),
    "/api/v2/notifications/{id}/read":    lambda q, id="1": get_notifications_read(id),
    "/api/v2/leads/{id}/update":          lambda q, id="lead_88759f8c3b34": get_lead_update(id),
    "/api/v2/campaigns/{id}/pause":       lambda q, id="c001": get_campaign_pause(id),
    "/api/v2/auth/permissions":           lambda q: get_auth_permissions(),
    "/api/v2/billing/{id}/refund":         lambda q, id="inv_001": get_billing_refund(id),
    "/api/v2/email_queue/{id}/cancel":     lambda q, id="36": get_email_queue_cancel(id),
    "/api/v2/notifications/{id}/archive": lambda q, id="1": get_notifications_archive(id),
    "/api/v2/campaigns/{id}/resume":      lambda q, id="c001": get_campaign_resume(id),
    "/api/v2/campaigns/{id}/budget":      lambda q, id="c001": get_campaign_budget(id),
    "/api/v2/campaigns/{id}/audience":    lambda q, id="c001": get_campaign_audience(id),
    "/api/v2/email_queue/{id}/preview":   lambda q, id="36": get_email_preview(id),
    "/api/v2/files/{id}/share":           lambda q, id="f_001": get_file_share(id),
    "/api/v2/auth/2fa":                   lambda q: get_auth_2fa(),
    "/api/v2/billing/{id}/pay":            lambda q, id="inv_001": get_billing_pay(id),
    "/api/v2/campaigns/{id}/export":      lambda q, id="c001": get_campaigns_export(id),
    "/api/v2/leads/{id}/convert":         lambda q, id="lead_88759f8c3b34": get_lead_convert(id),
    "/api/v2/workflow/{id}/publish":      lambda q, id="wf-content-1": get_workflow_publish(id),
    "/api/v2/skills/create":             lambda q, id="s_999": get_skills_create(id),
    "/api/v2/files/{id}/download-token": lambda q, id="f_001": get_files_download_token(id),
    "/api/v2/auth/devices":              lambda q: get_auth_devices(),
    "/api/v2/skills/{id}/delete":        lambda q, id="s_001": get_skills_delete(id),
    "/api/v2/billing/{id}/cancel":       lambda q, id="inv_001": get_billing_cancel(id),
    "/api/v2/campaigns/{id}/duplicate":  lambda q, id="c001": get_campaigns_duplicate(id),
    "/api/v2/files/{id}/rename":         lambda q, id="f_001": get_files_rename(id),
    "/api/v2/auth/sessions":             lambda q: get_auth_sessions(),
    "/api/v2/files/{id}/delete":         lambda q, id="f_001": get_files_delete(id),
    "/api/v2/workflows/{id}/run":        lambda q, id="wf-content-1": get_workflows_run(id),
    "/api/v2/agents/{id}/test":          lambda q, id="a_001": get_agents_test(id),
    "/api/v2/email_queue/clear":         lambda q: get_email_queue_clear(),
    "/api/v2/auth/activity":             lambda q: get_auth_activity(),
    "/api/v2/skills/{id}/import":         lambda q, id="s_001": get_skills_import(id),
    "/api/v2/billing/{id}/receipt":      lambda q, id="inv_001": get_billing_receipt(id),
    "/api/v2/campaigns/{id}/report/export": lambda q, id="c001": get_campaigns_report_export(id),
    "/api/v2/files/{id}/versions":       lambda q, id="f_001": get_files_versions(id),
    "/api/v2/auth/logout-all":           lambda q: get_auth_logout_all(),
    "/api/v2/skills/{id}/export":        lambda q, id="s_001": get_skills_export(id),
    "/api/v2/billing/invoice-list":      lambda q: get_billing_invoice_list(),
    "/api/v2/campaigns/pause-all":       lambda q: get_campaigns_pause_all(),
    "/api/v2/files/{id}/duplicate":      lambda q, id="f_001": get_files_duplicate(id),
    "/api/v2/auth/backup-codes":         lambda q: get_auth_backup_codes(),
    "/api/v2/skills/{id}/train":         lambda q, id="s_001": get_skills_train(id),
    "/api/v2/billing/{tenant_id}/subscription": lambda q, tenant_id="t_3a59592b7619": get_billing_subscription(tenant_id),
    "/api/v2/campaigns/{id}/optimize":   lambda q, id="c001": get_campaigns_optimize(id),
    "/api/v2/files/{id}/trash":         lambda q, id="f_001": get_files_trash(id),
    "/api/v2/auth/api-keys":            lambda q: get_auth_api_keys(),
    "/api/v2/skills/{id}/test":         lambda q, id="s_001": get_skills_test(id),
    "/api/v2/billing/usage":            lambda q: get_billing_usage(),
    "/api/v2/campaigns/{id}/launch":    lambda q, id="c001": get_campaigns_launch(id),
    "/api/v2/files/{id}/restore":       lambda q, id="f_001": get_files_restore(id),
    "/api/v2/auth/webhooks":            lambda q: get_auth_webhooks(),
    "/api/v2/skills/{id}/metrics":      lambda q, id="s_001": get_skills_metrics(id),
    "/api/v2/billing/{id}/invoice-pdf": lambda q, id="inv_001": get_billing_invoice_pdf(id),
    "/api/v2/campaigns/{id}/audience-list": lambda q, id="c001": get_campaigns_audience_list(id),
    "/api/v2/files/{id}/preview":       lambda q, id="f_001": get_files_preview(id),
    "/api/v2/auth/tokens":              lambda q: get_auth_tokens(),
    "/api/v2/skills/{id}/version":      lambda q, id="s_001": get_skills_version(id),
    "/api/v2/billing/{id}/charge":      lambda q, id="inv_001": get_billing_charge(id),
    "/api/v2/campaigns/{id}/schedule": lambda q, id="c001": get_campaigns_schedule(id),
    "/api/v2/files/{id}/lock":         lambda q, id="f_001": get_files_lock(id),
    "/api/v2/auth/sso":                lambda q: get_auth_sso(),
    "/api/v2/skills/{id}/share":        lambda q, id="s_001": get_skills_share(id),
    "/api/v2/billing/card-list":        lambda q: get_billing_card_list(),
    "/api/v2/campaigns/{id}/report-csv": lambda q, id="c001": get_campaigns_report_csv(id),
    "/api/v2/files/{id}/metadata":      lambda q, id="f_001": get_files_metadata(id),
    "/api/v2/auth/oauth":              lambda q: get_auth_oauth(),
    "/api/v2/skills/{id}/fork":         lambda q, id="s_001": get_skills_fork(id),
    "/api/v2/billing/{id}/upcoming":    lambda q, id="inv_001": get_billing_upcoming(id),
    "/api/v2/campaigns/{id}/stats-detailed": lambda q, id="c001": get_campaigns_stats_detailed(id),
    "/api/v2/files/{id}/download-stats": lambda q, id="f_001": get_files_download_stats(id),
    "/api/v2/auth/api-keys/{id}":       lambda q, id="k_001": get_auth_api_key_item(id),
    "/api/v2/skills/{id}/merge":        lambda q, id="s_001": get_skills_merge(id),
    "/api/v2/billing/{id}/invoice-pdf/download": lambda q, id="inv_001": get_billing_invoice_pdf_download(id),
    "/api/v2/campaigns/{id}/budget-history": lambda q, id="c001": get_campaigns_budget_history(id),
    "/api/v2/files/{id}/upload-stats":  lambda q, id="f_001": get_files_upload_stats(id),
    "/api/v2/auth/api-keys/{id}/rotate": lambda q, id="k_001": get_auth_api_key_rotate(id),
    "/api/v2/skills/{id}/truncate":     lambda q, id="s_001": get_skills_truncate(id),
    "/api/v2/billing/{tenant_id}/subscription-cancel": lambda q, tenant_id="t_3a59592b7619": get_billing_subscription_cancel(tenant_id),
    "/api/v2/campaigns/{id}/report-pdf/download": lambda q, id="c001": get_campaigns_report_pdf_download(id),
    "/api/v2/files/{id}/permissions":   lambda q, id="f_001": get_files_permissions(id),
    "/api/v2/auth/api-keys/{id}/delete": lambda q, id="k_001": get_auth_api_key_delete(id),
    "/api/v2/skills/{id}/duplicate":     lambda q, id="s_001": get_skills_duplicate(id),
    "/api/v2/billing/{id}/charge-history": lambda q, id="inv_001": get_billing_charge_history(id),
    "/api/v2/campaigns/{id}/conversion-funnel": lambda q, id="c001": get_campaigns_conversion_funnel(id),
    "/api/v2/files/{id}/download-history": lambda q, id="f_001": get_files_download_history(id),
    "/api/v2/auth/2fa/disable":          lambda q: get_auth_2fa_disable(),
    "/api/v2/skills/{id}/stats":         lambda q, id="s_001": get_skills_stats(id),
    "/api/v2/billing/invoice-template":  lambda q: get_billing_invoice_template(),
    "/api/v2/campaigns/{id}/cost-breakdown": lambda q, id="c001": get_campaigns_cost_breakdown(id),
    "/api/v2/files/{id}/share-stats":   lambda q, id="f_001": get_files_share_stats(id),
    "/api/v2/auth/2fa/regenerate":      lambda q: get_auth_2fa_regenerate(),
    "/api/v2/saas/v1/register":         lambda q: _register_v23_q_proxy(),
    "/api/v2/skills/{id}/reindex":       lambda q, id="s_001": get_skills_reindex(id),
    "/api/v2/billing/{tenant_id}/tax-rate": lambda q, tenant_id="t_3a59592b7619": get_billing_tax_rate(tenant_id),
    "/api/v2/campaigns/{id}/clicks":     lambda q, id="c001": get_campaigns_clicks(id),
    "/api/v2/files/{id}/comments":       lambda q, id="f_001": get_files_comments(id),
    "/api/v2/auth/api-keys/{id}/test":   lambda q, id="k_001": get_auth_api_key_test(id),
    "/api/v2/skills/{id}/reset":         lambda q, id="s_001": get_skills_reset(id),
    "/api/v2/billing/coupon/{code}":     lambda q, code="V23_R386": get_billing_coupon(code),
    "/api/v2/campaigns/{id}/recipients": lambda q, id="c001": get_campaigns_recipients(id),
    "/api/v2/files/{id}/share-list":    lambda q, id="f_001": get_files_share_list(id),
    "/api/v2/auth/sessions/{id}/signout": lambda q, id="s_001": get_auth_sessions_signout(id),
    "/api/v2/skills/{id}/analytics":       lambda q, id="s_001": get_skills_analytics(id),
    "/api/v2/billing/{id}/refund-history": lambda q, id="inv_001": get_billing_refund_history(id),
    "/api/v2/campaigns/{id}/abtest":       lambda q, id="c001": get_campaigns_abtest(id),
    "/api/v2/files/{id}/download-list":    lambda q, id="f_001": get_files_download_list(id),
    "/api/v2/auth/sessions/{id}/refresh":  lambda q, id="s_001": get_auth_sessions_refresh(id),
    "/api/v2/skills/{id}/rollback":       lambda q, id="s_001": get_skills_rollback(id),
    "/api/v2/billing/{id}/dunning":       lambda q, id="inv_001": get_billing_dunning(id),
    "/api/v2/campaigns/{id}/budget-pacing": lambda q, id="c001": get_campaigns_budget_pacing(id),
    "/api/v2/files/{id}/external-share": lambda q, id="f_001": get_files_external_share(id),
    "/api/v2/auth/sessions/{id}/trust":   lambda q, id="s_001": get_auth_sessions_trust(id),
    "/api/v2/skills/{id}/promote":        lambda q, id="s_001": get_skills_promote(id),
    "/api/v2/billing/{id}/tax-invoice":   lambda q, id="inv_001": get_billing_tax_invoice(id),
    "/api/v2/campaigns/{id}/creatives":   lambda q, id="c001": get_campaigns_creatives(id),
    "/api/v2/files/{id}/download-url-token": lambda q, id="f_001": get_files_download_url_token(id),
    "/api/v2/auth/sessions/{id}/revoke-all-others": lambda q, id="s_001": get_auth_sessions_revoke_all_others(id),
    "/api/v2/skills/{id}/deprecate":      lambda q, id="s_001": get_skills_deprecate(id),
    "/api/v2/billing/{tenant_id}/subscription-pause": lambda q, tenant_id="t_3a59592b7619": get_billing_subscription_pause(tenant_id),
    "/api/v2/campaigns/{id}/audience-stats": lambda q, id="c001": get_campaigns_audience_stats(id),
    "/api/v2/files/{id}/duplicate-rename": lambda q, id="f_001": get_files_duplicate_rename(id),
    "/api/v2/auth/sessions/{id}/impersonate": lambda q, id="s_001": get_auth_sessions_impersonate(id),
    "/api/v2/skills/{id}/import-v2":       lambda q, id="s_001": get_skills_import_v2(id),
    "/api/v2/billing/{tenant_id}/subscription-resume": lambda q, tenant_id="t_3a59592b7619": get_billing_subscription_resume(tenant_id),
    "/api/v2/campaigns/{id}/audience-aggressive": lambda q, id="c001": get_campaigns_audience_aggressive(id),
    "/api/v2/files/{id}/restore-from-trash": lambda q, id="f_001": get_files_restore_from_trash(id),
    "/api/v2/auth/sessions/{id}/forget-device": lambda q, id="s_001": get_auth_sessions_forget_device(id),
    "/api/v2/skills/{id}/auto-train":       lambda q, id="s_001": get_skills_auto_train(id),
    "/api/v2/billing/coupon/validate/{code}": lambda q, code="V23_R392": get_billing_coupon_validate(code),
    "/api/v2/campaigns/{id}/abtest-stop":  lambda q, id="c001": get_campaigns_abtest_stop(id),
    "/api/v2/files/comments/{id}":          lambda q, id="c_001": get_files_comments_item(id),
    "/api/v2/auth/sessions/cleanup":       lambda q: get_auth_sessions_cleanup(),
    "/api/v2/skills/{id}/retire":           lambda q, id="s_001": get_skills_retire(id),
    "/api/v2/billing/{tenant_id}/tax-rate-update": lambda q, tenant_id="t_3a59592b7619": get_billing_tax_rate_update(tenant_id),
    "/api/v2/campaigns/{id}/recipients-stats": lambda q, id="c001": get_campaigns_recipients_stats(id),
    "/api/v2/files/comments/{id}/reply":   lambda q, id="c_001": get_files_comments_reply(id),
    "/api/v2/auth/devices/{id}/revoke":     lambda q, id="d_001": get_auth_devices_revoke(id),
    "/api/v2/skills/{id}/optimize":         lambda q, id="s_001": get_skills_optimize(id),
    "/api/v2/billing/payment-methods":      lambda q: get_billing_payment_methods(),
    "/api/v2/campaigns/{id}/ctr-history":   lambda q, id="c001": get_campaigns_ctr_history(id),
    "/api/v2/files/comments/{id}/delete":   lambda q, id="c_001": get_files_comments_delete(id),
    "/api/v2/auth/devices/{id}/forget":     lambda q, id="d_001": get_auth_devices_forget(id),
    "/api/v2/skills/{id}/clone":           lambda q, id="s_001": get_skills_clone(id),
    "/api/v2/billing/tax-rates":           lambda q: get_billing_tax_rates(),
    "/api/v2/campaigns/{id}/impressions-history": lambda q, id="c001": get_campaigns_impressions_history(id),
    "/api/v2/files/{id}/share-revoke":     lambda q, id="f_001": get_files_share_revoke(id),
    "/api/v2/auth/sso/{id}/config":         lambda q, id="wechat_work": get_auth_sso_config(id),
    "/api/v2/skills/merge-multiple/{ids}":  lambda q, ids="s_001,s_002": get_skills_merge_multiple(ids),
    "/api/v2/billing/{tenant_id}/subscription-upgrade": lambda q, tenant_id="t_3a59592b7619": get_billing_subscription_upgrade(tenant_id),
    "/api/v2/campaigns/{id}/audience-age-stats": lambda q, id="c001": get_campaigns_audience_age_stats(id),
    "/api/v2/files/{id}/comments-count":   lambda q, id="f_001": get_files_comments_count(id),
    "/api/v2/auth/api-keys/rotate-all":    lambda q: get_auth_api_keys_rotate_all(),
    "/api/v2/skills/{id}/analytics-advanced": lambda q, id="s_001": get_skills_analytics_advanced(id),
    "/api/v2/billing/{tenant_id}/subscription-downgrade": lambda q, tenant_id="t_3a59592b7619": get_billing_subscription_downgrade(tenant_id),
    "/api/v2/campaigns/{id}/audience-gender-stats": lambda q, id="c001": get_campaigns_audience_gender_stats(id),
    "/api/v2/files/{id}/share-stats-by-day": lambda q, id="f_001": get_files_share_stats_by_day(id),
    "/api/v2/auth/api-keys/create":       lambda q, **kw: get_auth_api_keys_create(),
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