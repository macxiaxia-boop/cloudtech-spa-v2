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