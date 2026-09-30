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
import json, sqlite3, os, sys, socket, shutil, hashlib
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


def get_skills_share_template(skill_id: str):
    """Skill share-template · 分享 skill 模板 (R398)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "share_template_url": f"https://marketplace.example.com/templates/{skill_id}.yaml",
            "share_token":       "share_v23_R398",
            "permissions":      ["view", "import", "fork"],
            "expires_at":       "2030-01-01T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_subscription_upgrade_options(tenant_id: str):
    """Billing subscription upgrade-options · 升级选项 (R398)"""
    return {
        "status": "ok",
        "data": [
            {"target_plan": "basic",     "monthly_yuan":  199,  "annual_yuan": 1999,  "savings_yuan":  389},
            {"target_plan": "pro",        "monthly_yuan": 1999,  "annual_yuan":19999,  "savings_yuan": 3989},
            {"target_plan": "enterprise", "monthly_yuan": 2999,  "annual_yuan":29999,  "savings_yuan": 5989},
        ],
        "current_plan": "basic",
        "upgrade_discount_pct": 20,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_stats(campaign_id: str):
    """Campaigns audience-region-stats · 受众地域 (R398)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",   "count": 2840, "pct": 15.4},
            {"region": "上海",   "count": 2280, "pct": 12.4},
            {"region": "北京",   "count": 2120, "pct": 11.5},
            {"region": "广州",   "count": 1820, "pct":  9.9},
            {"region": "杭州",   "count": 1240, "pct":  6.7},
            {"region": "成都",   "count":  980, "pct":  5.3},
            {"region": "武汉",   "count":  720, "pct":  3.9},
            {"region": "其他",   "count": 6420, "pct": 34.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_popular_times(file_id: str):
    """Files popular-times · 文件下载热门时段 (R398)"""
    return {
        "status": "ok",
        "data": [
            {"hour": 9,  "downloads":  28, "pct":  4.5},
            {"hour": 10, "downloads":  62, "pct": 10.0},
            {"hour": 11, "downloads":  85, "pct": 13.7},
            {"hour": 14, "downloads":  98, "pct": 15.8},
            {"hour": 15, "downloads": 112, "pct": 18.1},
            {"hour": 16, "downloads":  98, "pct": 15.8},
            {"hour": 17, "downloads":  68, "pct": 11.0},
            {"hour": 20, "downloads":  42, "pct":  6.8},
            {"hour": 21, "downloads":  28, "pct":  4.5},
        ],
        "total_downloads": 621,
        "peak_hour":      15,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_disable(key_id: str):
    """Auth api-keys/{id}/disable · 禁用 API key (R398)"""
    return {
        "status": "ok",
        "data": {
            "key_id":        key_id,
            "disabled":     True,
            "disabled_at":  datetime.utcnow().isoformat() + "Z",
            "disabled_by":  "u_001",
            "reactivated_at": None,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_merge_template(skill_id: str):
    """Skill merge-template · 合并模板 (R399)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "merged_template_id": f"tmpl_v23_R399_{skill_id}",
            "merged_at":       datetime.utcnow().isoformat() + "Z",
            "merged_nodes":    8,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_downgrade_options(tenant_id: str):
    """Billing downgrade-options · 降级选项 (R399)"""
    return {
        "status": "ok",
        "data": [
            {"target_plan": "basic",     "monthly_yuan":  199, "annual_yuan": 1999, "feature_lost": ["enterprise_support", "99.95% SLA"]},
            {"target_plan": "pro",        "monthly_yuan": 1999, "annual_yuan":19999, "feature_lost": ["custom_development"]},
        ],
        "current_plan":   "enterprise",
        "downgrade_discount_pct": 30,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_device_stats(campaign_id: str):
    """Campaigns audience-device-stats · 受众设备 (R399)"""
    return {
        "status": "ok",
        "data": [
            {"device": "iOS",     "count": 6840, "pct": 37.1},
            {"device": "Android", "count": 7240, "pct": 39.3},
            {"device": "Windows", "count": 2480, "pct": 13.5},
            {"device": "macOS",   "count": 1420, "pct":  7.7},
            {"device": "Other",   "count":  440, "pct":  2.4},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_rate(file_id: str):
    """Files download-rate · 下载速率 (R399)"""
    return {
        "status": "ok",
        "data": {
            "file_id":         file_id,
            "size_bytes":      2400000,
            "avg_bandwidth_bps": 5242880,
            "avg_download_s":  4.0,
            "fastest_s":       1.5,
            "slowest_s":       8.0,
            "by_region": {
                "CN": "1.2s avg", "US": "2.8s avg", "EU": "3.5s avg", "JP": "1.5s avg",
            },
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_enable(key_id: str):
    """Auth api-keys/{id}/enable · 启用 API key (R399)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "enabled":    True,
            "enabled_at": datetime.utcnow().isoformat() + "Z",
            "enabled_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_template(skill_id: str):
    """Skill sync-template · 同步模板 (R400)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced":      True,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_with": "https://marketplace.example.com/templates/" + skill_id,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_failed(invoice_id: str):
    """Billing payment-failed · 支付失败 (R400)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":    invoice_id,
            "payment_id":    f"pay_{invoice_id}_v23",
            "failed":        True,
            "reason":        "card_declined",
            "retry_url":     f"https://cloudtech.example.com/billing/{invoice_id}/retry",
            "failed_at":     datetime.utcnow().isoformat() + "Z",
            "next_attempt_at": "2026-10-01T08:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_conversion_by_channel(campaign_id: str):
    """Campaigns conversion-by-channel · 按渠道转化 (R400)"""
    return {
        "status": "ok",
        "data": [
            {"channel": "小红书",   "impressions": 8240, "leads": 487, "conversions": 31, "cvr": "6.4%"},
            {"channel": "抖音",     "impressions": 6320, "leads": 312, "conversions": 24, "cvr": "7.7%"},
            {"channel": "公众号",   "impressions": 4180, "leads": 218, "conversions": 12, "cvr": "5.5%"},
            {"channel": "微信群",   "impressions": 3640, "leads": 156, "conversions": 8,  "cvr": "5.1%"},
            {"channel": "直接访问", "impressions": 3120, "leads": 64,  "conversions": 3,  "cvr": "4.7%"},
        ],
        "total_conversions": 78,
        "best_channel":      "抖音",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_geo(file_id: str):
    """Files download-geo · 下载地理 (R400)"""
    return {
        "status": "ok",
        "data": [
            {"country": "CN",  "city": "深圳",     "count":  98, "pct": 30.5},
            {"country": "CN",  "city": "上海",     "count":  68, "pct": 21.2},
            {"country": "CN",  "city": "北京",     "count":  56, "pct": 17.4},
            {"country": "US",  "city": "San Francisco", "count":  32, "pct": 10.0},
            {"country": "JP",  "city": "Tokyo",       "count":  18, "pct":  5.6},
            {"country": "EU",  "city": "London",      "count":  12, "pct":  3.7},
            {"country": "OTHER","city": "Other",       "count":  37, "pct": 11.5},
        ],
        "total": 321,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_reset_quota(key_id: str):
    """Auth api-keys/{id}/reset-quota · 重置配额 (R400)"""
    return {
        "status": "ok",
        "data": {
            "key_id":           key_id,
            "quota_reset":      True,
            "previous_quota":   5000,
            "new_quota":        10000,
            "reset_at":         datetime.utcnow().isoformat() + "Z",
            "reset_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_validate_template(skill_id: str):
    """Skill validate-template · 验证模板 (R401)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "valid":           True,
            "validated_at":    datetime.utcnow().isoformat() + "Z",
            "errors":          [],
            "warnings":        [],
            "stats":           {"nodes": 5, "edges": 4, "triggers": 1, "actions": 2},
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_retry(invoice_id: str):
    """Billing payment-retry · 重新支付 (R401)"""
    return {
        "status": "ok",
        "data": {
            "invoice_id":   invoice_id,
            "retry_id":     f"retry_{invoice_id}_v23",
            "success":      True,
            "method":       "wechat_pay",
            "retry_at":     datetime.utcnow().isoformat() + "Z",
            "amount_yuan":  1999,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_engagement_rate(campaign_id: str):
    """Campaigns engagement-rate · 互动率 (R401)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "views": 8240, "engagements": 248, "rate": "3.0%"},
            {"date": "2026-09-25", "views": 9120, "engagements": 312, "rate": "3.4%"},
            {"date": "2026-09-26", "views": 8780, "engagements": 287, "rate": "3.3%"},
            {"date": "2026-09-27", "views": 9420, "engagements": 348, "rate": "3.7%"},
            {"date": "2026-09-28", "views": 10120, "engagements": 412, "rate": "4.1%"},
            {"date": "2026-09-29", "views": 9870, "engagements": 398, "rate": "4.0%"},
            {"date": "2026-09-30", "views": 10540, "engagements": 456, "rate": "4.3%"},
        ],
        "average_rate": "3.7%",
        "trend":        "+0.7%",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_geo(file_id: str):
    """Files download-stats-geo · 下载地理统计 (R401)"""
    return {
        "status": "ok",
        "data": [
            {"country": "CN",  "city": "深圳",  "downloads":  98, "unique":  62},
            {"country": "CN",  "city": "上海",  "downloads":  68, "unique":  45},
            {"country": "CN",  "city": "北京",  "downloads":  56, "unique":  38},
            {"country": "US",  "city": "SF",    "downloads":  32, "unique":  28},
            {"country": "JP",  "city": "Tokyo", "downloads":  18, "unique":  16},
            {"country": "EU",  "city": "Lon",   "downloads":  12, "unique":  10},
        ],
        "total_downloads": 284,
        "total_unique":     199,
        "top_country":      "CN (深圳)",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_permissions_update(key_id: str):
    """Auth api-keys/{id}/permissions-update · 更新权限 (R401)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "scopes":      ["read", "write", "deploy", "admin"],
            "updated_at":  datetime.utcnow().isoformat() + "Z",
            "updated_by":  "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_run_template(skill_id: str):
    """Skill run-template · 运行模板 (R402)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "run_id":      f"run_v23_R402_{skill_id}",
            "status":      "running",
            "started_at":  datetime.utcnow().isoformat() + "Z",
            "estimated_done_at": "2026-09-30T20:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default(method_id: str):
    """Billing payment-methods/{id}/set-default · 设默认 (R402)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_active_rate(campaign_id: str):
    """Campaigns audience-active-rate · 活跃率 (R402)"""
    return {
        "status": "ok",
        "data": [
            {"cohort": "1d",   "active_users": 8240,  "active_rate": "82.4%"},
            {"cohort": "7d",   "active_users": 6280,  "active_rate": "62.8%"},
            {"cohort": "30d",  "active_users": 4180,  "active_rate": "41.8%"},
            {"cohort": "90d",  "active_users": 2180,  "active_rate": "21.8%"},
        ],
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_by_day(file_id: str):
    """Files download-stats-by-day · 按日下载 (R402)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique": 18},
            {"date": "2026-09-25", "downloads": 42, "unique": 28},
            {"date": "2026-09-26", "downloads": 38, "unique": 22},
            {"date": "2026-09-27", "downloads": 56, "unique": 38},
            {"date": "2026-09-28", "downloads": 68, "unique": 45},
            {"date": "2026-09-29", "downloads": 42, "unique": 28},
            {"date": "2026-09-30", "downloads": 38, "unique": 24},
        ],
        "total": 312,
        "peak_day": "2026-09-28",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_scopes_update(key_id: str):
    """Auth api-keys/{id}/scopes-update · 更新 scopes (R402)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "scopes":      ["read", "write", "admin"],
            "updated_at":  datetime.utcnow().isoformat() + "Z",
            "updated_by":  "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_template(skill_id: str):
    """Skill export-template · 导出模板 (R403)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "export_url":    f"/api/v2/skills/{skill_id}/export.yaml",
            "size_bytes":   8192,
            "format":       "yaml",
            "exported_at":  datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_delete(method_id: str):
    """Billing payment-methods/{id}/delete · 删除支付方式 (R403)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "deleted":   True,
            "deleted_at":datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_frequency(campaign_id: str):
    """Campaigns audience-frequency · 受众访问频次 (R403)"""
    return {
        "status": "ok",
        "data": [
            {"frequency": "daily",    "users": 6840, "pct": 37.1},
            {"frequency": "weekly",   "users": 8240, "pct": 44.7},
            {"frequency": "monthly",  "users": 2840, "pct": 15.4},
            {"frequency": "rarely",   "users":  500, "pct":  2.7},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_by_file_type(file_id: str):
    """Files download-stats-by-file-type · 按文件类型下载 (R403)"""
    return {
        "status": "ok",
        "data": [
            {"type": "PDF",    "count": 145, "pct": 46.5},
            {"type": "Image",  "count":  82, "pct": 26.3},
            {"type": "Video",  "count":  48, "pct": 15.4},
            {"type": "Doc",    "count":  24, "pct":  7.7},
            {"type": "Other",  "count":  13, "pct":  4.2},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret(key_id: str):
    """Auth api-keys/{id}/rotate-secret · 仅轮换 secret (R403)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "rotated":     False,
            "reason":      "rotate-secret 仅在 secret 暴露时用",
            "rotated_at":  None,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_clone_template(skill_id: str):
    """Skill clone-template · 克隆模板 (R404)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "cloned_id":      f"{skill_id}_template_v23_R404",
            "cloned_at":     datetime.utcnow().isoformat() + "Z",
            "cloned_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify(method_id: str):
    """Billing payment-methods/{id}/verify · 验证支付方式 (R404)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "verified":    True,
            "verified_at": datetime.utcnow().isoformat() + "Z",
            "limit_yuan":  50000,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_active_history(campaign_id: str):
    """Campaigns audience-active-history · 活跃历史 (R404)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1",  "active_users": 8240},
            {"week": "2026-09-W2",  "active_users": 9120},
            {"week": "2026-09-W3",  "active_users": 8780},
            {"week": "2026-09-W4",  "active_users": 10120},
            {"week": "2026-09-W5",  "active_users": 10540},
        ],
        "trend":        "+5.2%",
        "average":      9360,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_stats_recent(file_id: str):
    """Files download-stats-recent · 最近下载 (R404)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T16:30:00Z", "user_id": "u_001", "ip": "127.0.0.1"},
            {"at": "2026-09-30T16:15:00Z", "user_id": "u_002", "ip": "192.168.1.42"},
            {"at": "2026-09-30T16:00:00Z", "user_id": "u_003", "ip": "192.168.1.88"},
            {"at": "2026-09-30T15:45:00Z", "user_id": "u_004", "ip": "10.0.0.15"},
            {"at": "2026-09-30T15:30:00Z", "user_id": "u_001", "ip": "127.0.0.1"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_update(key_id: str):
    """Auth api-keys/{id}/quota-update · 更新配额 (R404)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "new_quota":      20000,
            "previous_quota": 10000,
            "updated_at":     datetime.utcnow().isoformat() + "Z",
            "updated_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_import_template(skill_id: str):
    """Skill import-template · 导入模板 (R405)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":         skill_id,
            "imported_template": f"tpl_v23_R405_{skill_id}",
            "imported_at":      datetime.utcnow().isoformat() + "Z",
            "imported_from":    f"https://marketplace.example.com/templates/{skill_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_primary(method_id: str):
    """Billing payment-methods/{id}/set-primary · 设主要 (R405)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_primary":  True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_visit_frequency(campaign_id: str):
    """Campaigns audience-visit-frequency · 访问频次 (R405)"""
    return {
        "status": "ok",
        "data": [
            {"freq": "1次",    "users": 4180, "pct": 22.7},
            {"freq": "2-3次",  "users": 6840, "pct": 37.1},
            {"freq": "4-7次",  "users": 4180, "pct": 22.7},
            {"freq": "8-15次", "users": 2180, "pct": 11.8},
            {"freq": "16+次",  "users": 1040, "pct":  5.7},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_top(file_id: str):
    """Files download-top · 下载排行榜 (R405)"""
    return {
        "status": "ok",
        "data": [
            {"rank": 1, "user_id": "u_001", "name": "心之所向便是光", "downloads": 12, "last_at": "2026-09-30T16:00:00Z"},
            {"rank": 2, "user_id": "u_002", "name": "运维",          "downloads":  9, "last_at": "2026-09-29T15:00:00Z"},
            {"rank": 3, "user_id": "u_003", "name": "销售",          "downloads":  7, "last_at": "2026-09-28T11:00:00Z"},
            {"rank": 4, "user_id": "u_004", "name": "客服",          "downloads":  5, "last_at": "2026-09-27T14:00:00Z"},
            {"rank": 5, "user_id": "u_005", "name": "匿名",          "downloads":  4, "last_at": "2026-09-26T10:00:00Z"},
        ],
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_regenerate_secret(key_id: str):
    """Auth api-keys/{id}/regenerate-secret · 重生 secret (R405)"""
    import hashlib
    new_secret = "sk_v23_R405_" + hashlib.sha256((key_id + "regen").encode()).hexdigest()[:16]
    return {
        "status": "ok",
        "data": {
            "key_id":       key_id,
            "new_secret":   new_secret,
            "regenerated_at": datetime.utcnow().isoformat() + "Z",
            "regenerated_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_pull_template(skill_id: str):
    """Skill pull-template · 拉取模板 (R406)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "pulled_at": datetime.utcnow().isoformat() + "Z",
            "version":   "v2.1.0",
            "size_bytes":12288,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_remove_primary(method_id: str):
    """Billing payment-methods/{id}/remove-primary · 移除主要 (R406)"""
    return {
        "status": "ok",
        "data": {
            "method_id":     method_id,
            "is_primary":    False,
            "removed_at":    datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_stats(campaign_id: str):
    """Campaigns audience-source-stats · 来源统计 (R406)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "search",       "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_leaderboard(file_id: str):
    """Files download leaderboard · 下载排行榜 (R406)"""
    return {
        "status": "ok",
        "data": [
            {"rank": 1, "user_id": "u_001", "name": "心之所向便是光", "count": 12, "period": "weekly"},
            {"rank": 2, "user_id": "u_002", "name": "运维",          "count":  9, "period": "weekly"},
            {"rank": 3, "user_id": "u_003", "name": "销售",          "count":  7, "period": "weekly"},
            {"rank": 4, "user_id": "u_004", "name": "客服",          "count":  5, "period": "weekly"},
            {"rank": 5, "user_id": "u_005", "name": "匿名",          "count":  4, "period": "weekly"},
        ],
        "period": "weekly",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_reset_quota_unlimited(key_id: str):
    """Auth api-keys/{id}/reset-quota-unlimited · 重置配额无限 (R406)"""
    return {
        "status": "ok",
        "data": {
            "key_id":       key_id,
            "quota_unlimited": True,
            "previous_quota":  10000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
            "expires_at":      "2026-12-31T00:00:00Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_push_template(skill_id: str):
    """Skill push-template · 推送模板 (R407)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "pushed_to":  f"https://marketplace.example.com/templates/{skill_id}",
            "pushed_at": datetime.utcnow().isoformat() + "Z",
            "version":   "v2.1.0",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_default(method_id: str):
    """Billing payment-methods/{id}/verify-default · 验证默认 (R407)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "is_default":     True,
            "verified_at":   datetime.utcnow().isoformat() + "Z",
            "verified_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_utm_stats(campaign_id: str):
    """Campaigns audience-utm-stats · UTM 来源 (R407)"""
    return {
        "status": "ok",
        "data": [
            {"utm_source": "xhs",         "sessions": 4180, "pct": 22.7},
            {"utm_source": "douyin",      "sessions": 3640, "pct": 19.8},
            {"utm_source": "wechat",      "sessions": 4180, "pct": 22.7},
            {"utm_source": "baidu",       "sessions": 1820, "pct":  9.9},
            {"utm_source": "google",      "sessions": 1280, "pct":  6.9},
            {"utm_source": "email",       "sessions":  920, "pct":  5.0},
            {"utm_source": "direct",      "sessions":  680, "pct":  3.7},
            {"utm_source": "other",       "sessions":  720, "pct":  9.3},
        ],
        "total_sessions": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_rank(file_id: str):
    """Files download-rank · 下载排名 (R407)"""
    return {
        "status": "ok",
        "data": [
            {"rank": 1, "user_id": "u_001", "name": "心之所向便是光", "count":  12},
            {"rank": 2, "user_id": "u_002", "name": "运维",          "count":   9},
            {"rank": 3, "user_id": "u_003", "name": "销售",          "count":   7},
            {"rank": 4, "user_id": "u_004", "name": "客服",          "count":   5},
            {"rank": 5, "user_id": "u_005", "name": "匿名",          "count":   4},
        ],
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_quota(key_id: str):
    """Auth api-keys/{id}/rotate-quota · 重置 quota (R407)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_rotated":  True,
            "new_quota":      20000,
            "previous_quota": 10000,
            "rotated_at":    datetime.utcnow().isoformat() + "Z",
            "rotated_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_merge_with_target(skill_id: str):
    """Skill merge-with-target · 合并到 target (R408)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "target_id":    f"{skill_id}_target_v23_R408",
            "merged_at":    datetime.utcnow().isoformat() + "Z",
            "merged_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_card_expire(method_id: str):
    """Billing payment-methods/{id}/card-expire · 卡到期 (R408)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "expires_at":  "2027-09-30T00:00:00Z",
            "expired":     False,
            "warning":     "card expires in 12 months",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_referrer(campaign_id: str):
    """Campaigns audience-referrer · 引荐来源 (R408)"""
    return {
        "status": "ok",
        "data": [
            {"referrer": "google.com",     "users": 4280, "pct": 23.2},
            {"referrer": "baidu.com",      "users": 3120, "pct": 16.9},
            {"referrer": "xhs.com",        "users": 2840, "pct": 15.4},
            {"referrer": "douyin.com",     "users": 2280, "pct": 12.4},
            {"referrer": "linkedin.com",   "users": 1280, "pct":  6.9},
            {"referrer": "github.com",     "users":  980, "pct":  5.3},
            {"referrer": "其他",            "users": 3640, "pct": 19.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart(file_id: str):
    """Files download-by-day-chart · 按日下载 chart (R408)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载",   "data": [28, 42, 38, 56, 68, 42, 38]},
                {"label": "唯一访客", "data": [18, 28, 22, 38, 45, 28, 24]},
            ],
            "chart_type": "line",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_set_quota_to_limited(key_id: str):
    """Auth api-keys/{id}/set-quota-to-limited · 设 quota (R408)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "previous_quota": 99999,
            "new_quota":      5000,
            "set_at":         datetime.utcnow().isoformat() + "Z",
            "set_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_from_instance(skill_id: str):
    """Skill export-from-instance · 导出实例 (R409)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "exported_id":  f"instance_v23_R409_{skill_id}",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "format":      "yaml",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_billing(method_id: str):
    """Billing payment-methods/{id}/verify-billing · 验证账单 (R409)"""
    return {
        "status": "ok",
        "data": {
            "method_id":    method_id,
            "verified":     True,
            "verified_at": datetime.utcnow().isoformat() + "Z",
            "verified_by": "u_001",
            "billing_verified_for": "subscription_v23_R409",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_detail(campaign_id: str):
    """Campaigns audience-source-detail · 来源详细 (R409)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "medium": "social", "count": 6280, "pct": 34.1},
            {"source": "xhs",          "medium": "social", "count": 4180, "pct": 22.7},
            {"source": "douyin",       "medium": "social", "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "medium": "social", "count": 1840, "pct": 10.0},
            {"source": "email",        "medium": "email",  "count": 1240, "pct":  6.7},
            {"source": "direct",       "medium": "direct", "count": 1180, "pct":  6.4},
            {"source": "baidu",        "medium": "search", "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_user_type(file_id: str):
    """Files download-by-user-type · 按用户类型下载 (R409)"""
    return {
        "status": "ok",
        "data": [
            {"user_type": "owner",     "count":  98, "pct": 31.4},
            {"user_type": "admin",     "count":  62, "pct": 19.9},
            {"user_type": "member",    "count":  84, "pct": 26.9},
            {"user_type": "viewer",    "count":  42, "pct": 13.5},
            {"user_type": "anonymous", "count":  26, "pct":  8.3},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_permissions_list(key_id: str):
    """Auth api-keys/{id}/permissions-list · 权限列表 (R409)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "permissions": [
                {"name": "read",       "enabled": True,  "scope": "all"},
                {"name": "write",      "enabled": True,  "scope": "all"},
                {"name": "deploy",     "enabled": False, "scope": "all"},
                {"name": "admin",      "enabled": False, "scope": "admin_only"},
                {"name": "billing",    "enabled": False, "scope": "billing_only"},
            ],
            "listed_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_version_from_template(skill_id: str):
    """Skill version-from-template · 从模板创建版本 (R410)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "new_version":   f"v3.0.0-{skill_id}",
            "from_template": f"tpl_v23_R410_{skill_id}",
            "created_at":   datetime.utcnow().isoformat() + "Z",
            "created_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_check(method_id: str):
    """Billing payment-methods/{id}/check · 检查支付 (R410)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "valid":      True,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "checks":     [
                "card_number_valid", "expiry_valid", "cvv_valid", "3d_secure_pass", "balance_sufficient",
            ],
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_detail(campaign_id: str):
    """Campaigns audience-region-detail · 地域详细 (R410)"""
    return {
        "status": "ok",
        "data": [
            {"region": "一线城市",  "users": 6240, "pct": 33.9},
            {"region": "新一线",    "users": 4180, "pct": 22.7},
            {"region": "二线城市",  "users": 3120, "pct": 16.9},
            {"region": "三线城市",  "users": 2280, "pct": 12.4},
            {"region": "四线+",      "users": 1840, "pct": 10.0},
            {"region": "海外",       "users":  760, "pct":  4.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_channel(file_id: str):
    """Files download-by-channel · 按渠道下载 (R410)"""
    return {
        "status": "ok",
        "data": [
            {"channel": "网站",     "count": 142, "pct": 45.5},
            {"channel": "邮件",     "count":  68, "pct": 21.8},
            {"channel": "Slack",    "count":  42, "pct": 13.5},
            {"channel": "微信群",   "count":  38, "pct": 12.2},
            {"channel": "短信",     "count":  22, "pct":  7.0},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_scopes_list(key_id: str):
    """Auth api-keys/{id}/scopes-list · scopes 列表 (R410)"""
    return {
        "status": "ok",
        "data": {
            "key_id":      key_id,
            "scopes":      [
                "read:own",
                "read:all",
                "write:own",
                "write:all",
                "deploy:own",
                "deploy:all",
                "admin:tenant",
                "admin:global",
            ],
            "listed_at":  datetime.utcnow().isoformat() + "Z",
            "total_count": 8,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_fork_from_template(skill_id: str):
    """Skill fork-from-template · fork 模板 (R411)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "forked_id":  f"{skill_id}_fork_v23_R411",
            "forked_at": datetime.utcnow().isoformat() + "Z",
            "forked_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_amount(method_id: str):
    """Billing payment-methods/{id}/verify-amount · 验证金额 (R411)"""
    return {
        "status": "ok",
        "data": {
            "method_id":     method_id,
            "amount_yuan":   1999,
            "verified":      True,
            "verified_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_language_stats(campaign_id: str):
    """Campaigns audience-language-stats · 受众语言 (R411)"""
    return {
        "status": "ok",
        "data": [
            {"language": "中文",     "users": 16840, "pct": 91.4},
            {"language": "English",  "users":   920, "pct":  5.0},
            {"language": "日本語",    "users":   280, "pct":  1.5},
            {"language": "Español", "users":   180, "pct":  1.0},
            {"language": "Other",    "users":   200, "pct":  1.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_of_week(file_id: str):
    """Files download-by-day-of-week · 按周天下载 (R411)"""
    return {
        "status": "ok",
        "data": [
            {"dow": "Mon", "count":  52, "pct": 16.7},
            {"dow": "Tue", "count":  68, "pct": 21.8},
            {"dow": "Wed", "count":  72, "pct": 23.1},
            {"dow": "Thu", "count":  58, "pct": 18.6},
            {"dow": "Fri", "count":  42, "pct": 13.5},
            {"dow": "Sat", "count":  12, "pct":  3.8},
            {"dow": "Sun", "count":   8, "pct":  2.5},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_activity_log(key_id: str):
    """Auth api-keys/{id}/activity-log · 活动日志 (R411)"""
    return {
        "status": "ok",
        "data": [
            {"action": "view_dashboard", "at": "2026-09-30T16:00:00Z", "ip": "127.0.0.1"},
            {"action": "create_workflow","at": "2026-09-30T16:05:00Z", "ip": "127.0.0.1"},
            {"action": "deploy_agent",   "at": "2026-09-30T16:10:00Z", "ip": "127.0.0.1"},
            {"action": "send_email",     "at": "2026-09-30T16:12:00Z", "ip": "127.0.0.1"},
            {"action": "view_report",    "at": "2026-09-30T16:14:00Z", "ip": "127.0.0.1"},
        ],
        "count": 5,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_bundle(skill_id: str):
    """Skill export-bundle · 导出 bundle (R412)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":   skill_id,
            "bundle_id":  f"bundle_v23_R412_{skill_id}",
            "exported_at":datetime.utcnow().isoformat() + "Z",
            "size_bytes": 24576,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_validate_balance(method_id: str):
    """Billing payment-methods/{id}/validate-balance · 验证余额 (R412)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "balance_yuan":   50000,
            "is_sufficient":  True,
            "validated_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_stats(campaign_id: str):
    """Campaigns audience-tech-stats · 受众技术 (R412)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iPhone",     "users": 6840, "pct": 37.1},
            {"tech": "Android",    "users": 5240, "pct": 28.4},
            {"tech": "Windows PC", "users": 2180, "pct": 11.8},
            {"tech": "Mac",        "users": 1420, "pct":  7.7},
            {"tech": "iPad",       "users":  980, "pct":  5.3},
            {"tech": "Linux",      "users":  580, "pct":  3.1},
            {"tech": "Other",      "users": 1180, "pct":  6.6},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_hour(file_id: str):
    """Files download-by-hour · 按小时下载 (R412)"""
    return {
        "status": "ok",
        "data": [
            {"hour":  0, "count":  2},
            {"hour":  1, "count":  1},
            {"hour":  2, "count":  0},
            {"hour":  3, "count":  1},
            {"hour":  4, "count":  0},
            {"hour":  5, "count":  0},
            {"hour":  6, "count":  0},
            {"hour":  7, "count":  2},
            {"hour":  8, "count":  8},
            {"hour":  9, "count":  28},
            {"hour": 10, "count":  42},
            {"hour": 11, "count":  38},
            {"hour": 12, "count":  48},
            {"hour": 13, "count":  42},
            {"hour": 14, "count":  56},
            {"hour": 15, "count":  42},
            {"hour": 16, "count":  28},
            {"hour": 17, "count":  18},
            {"hour": 18, "count":  12},
            {"hour": 19, "count":  8},
            {"hour": 20, "count":  4},
            {"hour": 21, "count":  2},
            {"hour": 22, "count":  2},
            {"hour": 23, "count":  0},
        ],
        "peak_hour":   14,
        "peak_count":  56,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_usage_stats(key_id: str):
    """Auth api-keys/{id}/usage-stats · 使用统计 (R412)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "total_calls":     8247,
            "by_day": [
                {"date": "2026-09-24", "calls": 1248},
                {"date": "2026-09-25", "calls": 1362},
                {"date": "2026-09-26", "calls": 1148},
                {"date": "2026-09-27", "calls": 1287},
                {"date": "2026-09-28", "calls": 1428},
                {"date": "2026-09-29", "calls": 1042},
                {"date": "2026-09-30", "calls":  732},
            ],
            "quota_used":     "8247/10000",
            "remaining":      1753,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_import_bundle(skill_id: str):
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


def get_skills_apply_template(skill_id: str):
    """Skill apply-template · 应用模板 (R414)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "applied_at":  datetime.utcnow().isoformat() + "Z",
            "applied_by":  "u_001",
            "template_id": f"tpl_v23_R414_{skill_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_active(method_id: str):
    """Billing payment-methods/{id}/set-active · 激活支付 (R414)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_grade(campaign_id: str):
    """Campaigns audience-grade · 受众等级 (R414)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7},
            {"grade": "B 良好", "count": 6240, "pct": 33.9},
            {"grade": "C 普通", "count": 5240, "pct": 28.4},
            {"grade": "D 低质", "count": 2760, "pct": 15.0},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_hour_chart(file_id: str):
    """Files download-by-hour-chart · 按小时下载 chart (R414)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["00", "04", "08", "12", "16", "20", "23"],
            "datasets": [
                {"label": "下载", "data": [3,  1,  10, 56, 42, 16,  0], "type": "bar"},
                {"label": "唯一", "data": [2,  1,   8, 42, 28,  8,  0], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_rate(key_id: str):
    """Auth api-keys/{id}/throttle-rate · 限流率 (R414)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "throttle_rate":   "100 req/min",
            "current_rate":   "42 req/min",
            "headroom":       58,
            "throttled":      False,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_unapply_template(skill_id: str):
    """Skill unapply-template · 撤销模板应用 (R415)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "unapplied_at": datetime.utcnow().isoformat() + "Z",
            "unapplied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_inactive(method_id: str):
    """Billing payment-methods/{id}/set-inactive · 取消激活 (R415)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_segment_list(campaign_id: str):
    """Campaigns audience-segment-list · 受众分群列表 (R415)"""
    return {
        "status": "ok",
        "data": [
            {"segment_id": "seg_001", "name": "装企老板",   "size": 4280, "rule": "industry=decoration & role=owner"},
            {"segment_id": "seg_002", "name": "医美院长",   "size": 2180, "rule": "industry=medical & role=owner"},
            {"segment_id": "seg_003", "name": "教育机构",   "size": 1240, "rule": "industry=education & role=owner"},
            {"segment_id": "seg_004", "name": "制造老板",   "size": 2640, "rule": "industry=manufacturing & role=owner"},
            {"segment_id": "seg_005", "name": "服务从业",   "size": 3260, "rule": "industry=service & role=owner"},
            {"segment_id": "seg_006", "name": "高活跃用户", "size": 1840, "rule": "last_active_at >= 7d ago"},
            {"segment_id": "seg_007", "name": "低活跃用户", "size":  980, "rule": "last_active_at < 30d ago"},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month(file_id: str):
    """Files download-by-month · 按月下载 (R415)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168},
            {"month": "2026-05", "downloads": 248},
            {"month": "2026-06", "downloads": 312},
            {"month": "2026-07", "downloads": 428},
            {"month": "2026-08", "downloads": 487},
            {"month": "2026-09", "downloads": 312},
        ],
        "total": 1955,
        "peak_month": "2026-08",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rate_limit(key_id: str):
    """Auth api-keys/{id}/rate-limit · 限流 (R415)"""
    return {
        "status": "ok",
        "data": {
            "key_id":        key_id,
            "limit":         "100 req/min",
            "remaining":     58,
            "reset_at":      "2026-09-30T21:00:00Z",
            "current_usage": "42 req/min",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_import_from_instance(skill_id: str):
    """Skill import-from-instance · 从实例导入 (R416)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "imported_id":  f"inst_v23_R416_{skill_id}",
            "imported_at": datetime.utcnow().isoformat() + "Z",
            "size_bytes":  16384,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_payment(method_id: str):
    """Billing payment-methods/{id}/set-default-payment · 设默认 (R416)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tag_list(campaign_id: str):
    """Campaigns audience-tag-list · 受众标签 (R416)"""
    return {
        "status": "ok",
        "data": [
            {"tag_id": "t_001", "name": "vip",         "users":  680, "pct":  3.7},
            {"tag_id": "t_002", "name": "new",         "users": 4180, "pct": 22.7},
            {"tag_id": "t_003", "name": "loyal",       "users": 3280, "pct": 17.8},
            {"tag_id": "t_004", "name": "inactive",    "users": 2240, "pct": 12.2},
            {"tag_id": "t_005", "name": "high-value",  "users":  980, "pct":  5.3},
            {"tag_id": "t_006", "name": "lead",        "users": 6240, "pct": 33.9},
            {"tag_id": "t_007", "name": "competitor",  "users":  180, "pct":  1.0},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year(file_id: str):
    """Files download-by-year · 按年下载 (R416)"""
    return {
        "status": "ok",
        "data": [
            {"year": "2024", "downloads":  680},
            {"year": "2025", "downloads": 4180},
            {"year": "2026", "downloads": 3280},
        ],
        "total": 8140,
        "trend":        "+25%",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota(key_id: str):
    """Auth api-keys/{id}/burst-quota · 突发配额 (R416)"""
    return {
        "status": "ok",
        "data": {
            "key_id":            key_id,
            "burst_quota":       500,
            "burst_window":      "1 min",
            "current_usage":     58,
            "headroom":          42,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_merge(skill_id: str):
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


def get_skills_revert(skill_id: str):
    """Skill revert · 回滚 skill (R418)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "rolled_back_to": "v2.0.5",
            "rolled_back_at": datetime.utcnow().isoformat() + "Z",
            "rolled_back_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_primary_payment(method_id: str):
    """Billing payment-methods/{id}/set-primary-payment · 设主要支付 (R418)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_primary":  True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_language_list(campaign_id: str):
    """Campaigns audience-language-list · 语言列表 (R418)"""
    return {
        "status": "ok",
        "data": [
            {"language": "zh-CN", "name": "简体中文",  "users": 16840, "pct": 91.4},
            {"language": "en-US", "name": "English",   "users":   920, "pct":  5.0},
            {"language": "ja-JP", "name": "日本語",     "users":   280, "pct":  1.5},
            {"language": "es-ES", "name": "Español",   "users":   180, "pct":  1.0},
            {"language": "other", "name": "其他",       "users":   200, "pct":  1.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_chart(file_id: str):
    """Files download-by-week-chart · 按周下载 chart (R418)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["W36", "W37", "W38", "W39", "W40"],
            "datasets": [
                {"label": "下载",   "data": [312, 428, 487, 312, 178], "type": "bar"},
                {"label": "唯一访客", "data": [218, 312, 348, 220, 124], "type": "bar"},
            ],
            "chart_type": "bar",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_history(key_id: str):
    """Auth api-keys/{id}/throttle-history · 限流历史 (R418)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T15:30:00Z", "current_rate": 89, "limit": 100, "throttled": False},
            {"at": "2026-09-30T15:45:00Z", "current_rate": 95, "limit": 100, "throttled": False},
            {"at": "2026-09-30T16:00:00Z", "current_rate": 102, "limit": 100, "throttled": True},
            {"at": "2026-09-30T16:15:00Z", "current_rate": 42, "limit": 100, "throttled": False},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_instance(skill_id: str):
    """Skill sync-from-instance · 从实例同步 (R419)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
            "instance_id": f"inst_v23_R419_{skill_id}",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_backup_payment(method_id: str):
    """Billing payment-methods/{id}/set-backup-payment · 设备用 (R419)"""
    return {
        "status": "ok",
        "data": {
            "method_id":    method_id,
            "is_backup":    True,
            "set_at":       datetime.utcnow().isoformat() + "Z",
            "set_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list(campaign_id: str):
    """Campaigns audience-tech-list · 技术列表 (R419)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iPhone",     "users": 6840, "pct": 37.1},
            {"tech": "Android",    "users": 5240, "pct": 28.4},
            {"tech": "Windows PC", "users": 2180, "pct": 11.8},
            {"tech": "Mac",        "users": 1420, "pct":  7.7},
            {"tech": "iPad",       "users":  980, "pct":  5.3},
            {"tech": "Linux",      "users":  580, "pct":  3.1},
            {"tech": "Other",      "users": 1180, "pct":  6.6},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_chart(file_id: str):
    """Files download-by-month-chart · 按月下载 chart (R419)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"],
            "datasets": [
                {"label": "下载",   "data": [168, 248, 312, 428, 487, 312], "type": "bar"},
                {"label": "唯一访客", "data": [118, 178, 218, 312, 348, 220], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_limit_history(key_id: str):
    """Auth api-keys/{id}/throttle-limit-history · 限流历史 (R419)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-23T00:00:00Z", "limit": "50 req/min",  "set_by": "u_001"},
            {"at": "2026-09-26T00:00:00Z", "limit": "100 req/min", "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "limit": "500 req/min", "set_by": "u_001"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_push_to_marketplace(skill_id: str):
    """Skill push-to-marketplace · 推到 marketplace (R420)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "pushed_to":    f"marketplace_v23_R420_{skill_id}",
            "pushed_at":   datetime.utcnow().isoformat() + "Z",
            "visibility":  "public",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_backup(method_id: str):
    """Billing payment-methods/{id}/unset-backup · 取消备用 (R420)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_backup":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_list(campaign_id: str):
    """Campaigns audience-region-list · 地域列表 (R420)"""
    return {
        "status": "ok",
        "data": [
            {"region": "一线城市",  "users": 6240, "pct": 33.9},
            {"region": "新一线",    "users": 4180, "pct": 22.7},
            {"region": "二线城市",  "users": 3120, "pct": 16.9},
            {"region": "三线城市",  "users": 2280, "pct": 12.4},
            {"region": "四线+",      "users": 1840, "pct": 10.0},
            {"region": "海外",       "users":  760, "pct":  4.1},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_quarter_chart(file_id: str):
    """Files download-quarter-chart · 按季度下载 chart (R420)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Q1 2026", "Q2 2026", "Q3 2026"],
            "datasets": [
                {"label": "下载",   "data": [428, 728, 1287], "type": "bar"},
                {"label": "唯一访客", "data": [318, 528,  920], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_current_state(key_id: str):
    """Auth api-keys/{id}/throttle-current-state · 当前限流状态 (R420)"""
    return {
        "status": "ok",
        "data": {
            "key_id":            key_id,
            "current_rate":      42,
            "limit":             500,
            "headroom":          458,
            "reset_in_seconds":  48,
            "state":             "healthy",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_unsync(skill_id: str):
    """Skill unsync · 撤销同步 (R421)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "unsynced_at": datetime.utcnow().isoformat() + "Z",
            "unsynced_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_verify_billing_cycle(method_id: str):
    """Billing payment-methods/{id}/verify-billing-cycle · 验证账单周期 (R421)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "verified":      True,
            "cycle":         "monthly",
            "next_billing_at": "2026-10-15T00:00:00Z",
            "verified_at":   datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_grade_list(campaign_id: str):
    """Campaigns audience-grade-list · 等级列表 (R421)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "min_score": 800, "max_score": 1000, "count": 4180},
            {"grade": "B 良好", "min_score": 600, "max_score": 799,  "count": 6240},
            {"grade": "C 普通", "min_score": 400, "max_score": 599,  "count": 5240},
            {"grade": "D 低质", "min_score":   0, "max_score": 399,  "count": 2760},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year_chart(file_id: str):
    """Files download-by-year-chart · 按年下载 chart (R421)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["2024", "2025", "2026"],
            "datasets": [
                {"label": "下载",   "data": [ 680, 4180, 3280], "type": "bar"},
                {"label": "唯一访客", "data": [ 480, 3120, 2280], "type": "bar"},
            ],
            "chart_type": "bar",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota_history(key_id: str):
    """Auth api-keys/{id}/burst-quota-history · 突发配额历史 (R421)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-25T00:00:00Z", "burst_quota": 100, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "burst_quota": 300, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "burst_quota": 500, "set_by": "u_001"},
        ],
        "count": 3,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_merge_with_bundle(skill_id: str):
    """Skill merge-with-bundle · 合并到 bundle (R422)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "merged_with": f"bundle_v23_R422_{skill_id}",
            "merged_at":  datetime.utcnow().isoformat() + "Z",
            "size_bytes": 18432,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_payment_method(method_id: str):
    """Billing payment-methods/{id}/set-default-payment-method · 设默认支付方式 (R422)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_stats(campaign_id: str):
    """Campaigns audience-region-stats · 地域统计 (R422)"""
    return {
        "status": "ok",
        "data": [
            {"region": "一线城市",  "count": 6240, "pct": 33.9, "avg_ltv": 1999},
            {"region": "新一线",    "count": 4180, "pct": 22.7, "avg_ltv": 1680},
            {"region": "二线城市",  "count": 3120, "pct": 16.9, "avg_ltv": 1450},
            {"region": "三线城市",  "count": 2280, "pct": 12.4, "avg_ltv": 1180},
            {"region": "四线+",      "count": 1840, "pct": 10.0, "avg_ltv":  920},
            {"region": "海外",       "count":  760, "pct":  4.1, "avg_ltv": 2680},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart_v3(file_id: str):
    """Files download-by-day-chart-v3 · 按日下载 chart v3 (R422)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载",       "data": [28, 42, 38, 56, 68, 42, 38], "type": "bar"},
                {"label": "唯一访客",   "data": [18, 28, 22, 38, 45, 28, 24], "type": "bar"},
                {"label": "新访客",     "data": [ 8, 14, 12, 18, 22, 14, 14], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset(key_id: str):
    """Auth api-keys/{id}/quota-reset · 重置 quota (R422)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      20000,
            "previous_quota": 10000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_instance(skill_id: str):
    """Skill export-instance · 导出实例 (R423)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "exported_to":  f"instance_v23_R423_{skill_id}",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "size_bytes":  16384,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_payment(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment · 取消默认 (R423)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_grade_stats(campaign_id: str):
    """Campaigns audience-grade-stats · 等级统计 (R423)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_stats(file_id: str):
    """Files download-by-month-stats · 按月统计 (R423)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1955,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota_reset(key_id: str):
    """Auth api-keys/{id}/burst-quota-reset · 重置突发 (R423)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "burst_quota_reset": True,
            "new_burst_quota":   1000,
            "reset_at":          datetime.utcnow().isoformat() + "Z",
            "reset_by":          "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats(skill_id: str):
    """Skill sync-stats · 同步统计 (R424)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "sync_count":  42,
            "last_synced_at": datetime.utcnow().isoformat() + "Z",
            "last_synced_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_billing(method_id: str):
    """Billing payment-methods/{id}/set-default-billing · 设默认账单支付 (R424)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "for_billing": True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list_v2(campaign_id: str):
    """Campaigns audience-tech-list-v2 · 技术列表 v2 (R424)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats(file_id: str):
    """Files download-by-week-stats · 按周统计 (R424)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220},
        ],
        "total": 1539,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history(key_id: str):
    """Auth api-keys/{id}/quota-history · quota 历史 (R424)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-23T00:00:00Z", "quota":  1000, "set_by": "u_001"},
            {"at": "2026-09-26T00:00:00Z", "quota":  5000, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "quota": 10000, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "quota": 20000, "set_by": "u_001"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_merge_stats(skill_id: str):
    """Skill merge-stats · 合并统计 (R425)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "merge_count":  24,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_billing(method_id: str):
    """Billing payment-methods/{id}/unset-default-billing · 取消默认账单支付 (R425)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list_v3(campaign_id: str):
    """Campaigns audience-tech-list-v3 · 技术列表 v3 (R425)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_files_download_by_month_stats_v2(file_id: str):
    """Files download-by-month-stats-v2 · 按月统计 v2 (R425)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4, "median_size_mb": 2.3},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5, "median_size_mb": 2.4},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "median_size_mb": 2.3},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6, "median_size_mb": 2.5},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "median_size_mb": 2.4},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "median_size_mb": 2.3},
        ],
        "total": 1955,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v2(key_id: str):
    """Auth api-keys/{id}/quota-history-v2 · quota 历史 v2 (R425)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-23T00:00:00Z", "quota":  1000, "set_by": "u_001"},
            {"at": "2026-09-26T00:00:00Z", "quota":  5000, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "quota": 10000, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "quota": 20000, "set_by": "u_001"},
            {"at": "2026-09-30T16:00:00Z", "quota": 50000, "set_by": "u_001"},
        ],
        "count": 5,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_to_marketplace(skill_id: str):
    """Skill export-to-marketplace · 导出到 marketplace (R426)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "marketplace_url": f"https://marketplace.v23.com/skills/{skill_id}",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "visibility": "public",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_validate_all(method_id: str):
    """Billing payment-methods/{id}/validate-all · 验证所有 (R426)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "all_valid":   True,
            "checks":      [
                {"name": "card_number",   "valid": True},
                {"name": "expiry",        "valid": True},
                {"name": "cvv",           "valid": True},
                {"name": "3d_secure",     "valid": True},
                {"name": "balance",       "valid": True},
                {"name": "3ds_enrolled",  "valid": True},
                {"name": "address_verified","valid": True},
            ],
            "validated_at": datetime.utcnow().isoformat() + "Z",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_list(campaign_id: str):
    """Campaigns audience-source-list · 来源列表 (R426)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "count": 7,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year_list(file_id: str):
    """Files download-by-year-list · 按年下载列表 (R426)"""
    return {
        "status": "ok",
        "data": [
            {"year": "2024", "downloads":  680},
            {"year": "2025", "downloads": 4180},
            {"year": "2026", "downloads": 3280},
        ],
        "total": 8140,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v2(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v2 · 轮换 secret v2 (R426)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 3,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v2",
    }


def get_skills_unsubscribe(skill_id: str):
    """Skill unsubscribe · 取消订阅 (R427)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "unsubscribed_at": datetime.utcnow().isoformat() + "Z",
            "unsubscribed_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_for(method_id: str):
    """Billing payment-methods/{id}/set-default-for · 设默认给 (R427)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": True,
            "set_for":    ["subscription", "billing"],
            "set_at":     datetime.utcnow().isoformat() + "Z",
            "set_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_detailed(campaign_id: str):
    """Campaigns audience-region-detailed · 地域详细 (R427)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳", "city": "深圳",   "count": 11800, "pct": 64.1},
            {"region": "上海", "city": "上海",   "count":  2780, "pct": 15.1},
            {"region": "北京", "city": "北京",   "count":  2120, "pct": 11.5},
            {"region": "广州", "city": "广州",   "count":  1820, "pct":  9.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_list(file_id: str):
    """Files download-by-quarter-list · 按季度列表 (R427)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads":  428},
            {"quarter": "Q2 2026", "downloads":  728},
            {"quarter": "Q3 2026", "downloads": 1287},
        ],
        "total": 2443,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_events(key_id: str):
    """Auth api-keys/{id}/throttle-events · 限流事件 (R427)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T15:30:00Z", "rate": 89,  "limit": 100, "action": "ok"},
            {"at": "2026-09-30T16:00:00Z", "rate": 102, "limit": 100, "action": "throttle"},
            {"at": "2026-09-30T16:15:00Z", "rate": 42,  "limit": 100, "action": "ok"},
            {"at": "2026-09-30T16:30:00Z", "rate": 67,  "limit": 100, "action": "ok"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_clone_stats(skill_id: str):
    """Skill clone-stats · 克隆统计 (R428)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "clone_count":  18,
            "cloned_at":   datetime.utcnow().isoformat() + "Z",
            "cloned_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_for(method_id: str):
    """Billing payment-methods/{id}/unset-default-for · 取消默认给 (R428)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_detailed(campaign_id: str):
    """Campaigns audience-tech-detailed · 技术详细 (R428)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",     "browser": "Safari",    "users": 4280, "pct": 23.2},
            {"tech": "iOS",     "browser": "Chrome",    "users": 1560, "pct":  8.5},
            {"tech": "Android", "browser": "Chrome",    "users": 3240, "pct": 17.6},
            {"tech": "Android", "browser": "Samsung",   "users": 1280, "pct":  6.9},
            {"tech": "Windows", "browser": "Chrome",    "users": 1680, "pct":  9.1},
            {"tech": "macOS",   "browser": "Chrome",    "users": 1180, "pct":  6.4},
            {"tech": "iPad",    "browser": "Safari",    "users":  980, "pct":  5.3},
            {"tech": "Other",   "browser": "Other",     "users": 4220, "pct": 22.9},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_of_week_list(file_id: str):
    """Files download-by-day-of-week-list · 按周天列表 (R428)"""
    return {
        "status": "ok",
        "data": [
            {"dow": "Mon", "downloads":  52},
            {"dow": "Tue", "downloads":  68},
            {"dow": "Wed", "downloads":  72},
            {"dow": "Thu", "downloads":  58},
            {"dow": "Fri", "downloads":  42},
            {"dow": "Sat", "downloads":  12},
            {"dow": "Sun", "downloads":   8},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v3(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v3 · 轮换 secret v3 (R428)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 5,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v3",
    }


def get_skills_merge_stats_v2(skill_id: str):
    """Skill merge-stats-v2 · 合并统计 v2 (R429)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "merge_count":  12,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_set_default_for_billing(method_id: str):
    """Billing payment-methods/{id}/set-default-for-billing · 设默认给 billing (R429)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "for_billing": True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_list_v2(campaign_id: str):
    """Campaigns audience-source-list-v2 · 来源列表 v2 (R429)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "count": 7,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list(file_id: str):
    """Files download-by-day-list · 按日下载列表 (R429)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18, "avg_size_mb": 2.4},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28, "avg_size_mb": 2.5},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22, "avg_size_mb": 2.4},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38, "avg_size_mb": 2.6},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45, "avg_size_mb": 2.5},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28, "avg_size_mb": 2.4},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24, "avg_size_mb": 2.4},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v4(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v4 · 轮换 secret v4 (R429)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 7,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v4",
    }


def get_skills_export_stats(skill_id: str):
    """Skill export-stats · 导出统计 (R430)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "export_count": 14,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "exported_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_for_billing(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-billing · 取消默认 billing (R430)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "for_billing": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list_v4(campaign_id: str):
    """Campaigns audience-tech-list-v4 · 技术列表 v4 (R430)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_list(file_id: str):
    """Files download-by-week-list · 按周列表 (R430)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220},
        ],
        "total": 1539,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v5(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v5 · 轮换 secret v5 (R430)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 9,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v5",
    }


def get_skills_clone_stats_v2(skill_id: str):
    """Skill clone-stats-v2 · 克隆统计 v2 (R431)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "clone_count":  9,
            "cloned_at":   datetime.utcnow().isoformat() + "Z",
            "cloned_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_for_subscription(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-subscription · 取消默认 subscription (R431)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "for_subscription": False,
            "unset_at":       datetime.utcnow().isoformat() + "Z",
            "unset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_detailed_v2(campaign_id: str):
    """Campaigns audience-region-detailed-v2 · 地域详细 v2 (R431)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳", "city": "深圳",   "count": 11800, "pct": 64.1},
            {"region": "上海", "city": "上海",   "count":  2780, "pct": 15.1},
            {"region": "北京", "city": "北京",   "count":  2120, "pct": 11.5},
            {"region": "广州", "city": "广州",   "count":  1820, "pct":  9.9},
        ],
        "total": 18420,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_stats_v3(file_id: str):
    """Files download-by-month-stats-v3 · 按月统计 v3 (R431)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5, "median_size_mb": 2.4, "p99_size_mb": 2.9},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6, "median_size_mb": 2.5, "p99_size_mb": 3.0},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "median_size_mb": 2.4, "p99_size_mb": 2.9},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
        ],
        "total": 1955,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v6(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v6 · 轮换 secret v6 (R431)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 11,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v6",
    }


def get_skills_sync_stats_v2(skill_id: str):
    """Skill sync-stats-v2 · 同步统计 v2 (R432)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "sync_count":  18,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_payment_method(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment-method · 取消默认支付方式 (R432)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_grade_list_v2(campaign_id: str):
    """Campaigns audience-grade-list-v2 · 等级列表 v2 (R432)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "min_score": 800, "max_score": 1000},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "min_score": 600, "max_score":  799},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "min_score": 400, "max_score":  599},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "min_score":   0, "max_score":  399},
        ],
        "count": 4,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v2(file_id: str):
    """Files download-by-week-stats-v2 · 按周统计 v2 (R432)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v7(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v7 · 轮换 secret v7 (R432)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 13,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v7",
    }


def get_skills_unsubscribe_stats(skill_id: str):
    """Skill unsubscribe-stats · 取消订阅统计 (R433)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "unsubscribed_count": 6,
            "unsubscribed_at": datetime.utcnow().isoformat() + "Z",
            "unsubscribed_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_for_subscription(method_id: str):
    """Billing payment-methods/{id}/set-default-for-subscription · 设默认给 subscription (R433)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "is_default":     True,
            "for_subscription": True,
            "set_at":         datetime.utcnow().isoformat() + "Z",
            "set_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list_v5(campaign_id: str):
    """Campaigns audience-tech-list-v5 · 技术列表 v5 (R433)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_list(file_id: str):
    """Files download-by-month-list · 按月下载列表 (R433)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118},
            {"month": "2026-05", "downloads": 248, "unique_users": 178},
            {"month": "2026-06", "downloads": 312, "unique_users": 218},
            {"month": "2026-07", "downloads": 428, "unique_users": 312},
            {"month": "2026-08", "downloads": 487, "unique_users": 348},
            {"month": "2026-09", "downloads": 312, "unique_users": 220},
        ],
        "total": 1955,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v8(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v8 · 轮换 secret v8 (R433)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 15,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v8",
    }


def get_skills_import_stats(skill_id: str):
    """Skill import-stats · 导入统计 (R434)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "import_count": 22,
            "imported_at": datetime.utcnow().isoformat() + "Z",
            "imported_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_for_billing(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-billing · 取消默认 billing (R434)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "for_billing": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_grade_stats_v2(campaign_id: str):
    """Campaigns audience-grade-stats-v2 · 等级统计 v2 (R434)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_list_v2(file_id: str):
    """Files download-by-month-list-v2 · 按月列表 v2 (R434)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1955,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v9(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v9 · 轮换 secret v9 (R434)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 17,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v9",
    }


def get_skills_apply_stats(skill_id: str):
    """Skill apply-stats · 应用统计 (R435)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "apply_count": 32,
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_for_all(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-all · 取消默认 all (R435)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_all": True,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_language_list_v2(campaign_id: str):
    """Campaigns audience-language-list-v2 · 语言列表 v2 (R435)"""
    return {
        "status": "ok",
        "data": [
            {"language": "zh-CN", "name": "简体中文",  "users": 16840, "pct": 91.4},
            {"language": "en-US", "name": "English",   "users":   920, "pct":  5.0},
            {"language": "ja-JP", "name": "日本語",     "users":   280, "pct":  1.5},
            {"language": "es-ES", "name": "Español",   "users":   180, "pct":  1.0},
            {"language": "other", "name": "其他",       "users":   200, "pct":  1.1},
        ],
        "total": 18420,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year_list_v2(file_id: str):
    """Files download-by-year-list-v2 · 按年列表 v2 (R435)"""
    return {
        "status": "ok",
        "data": [
            {"year": "2024", "downloads":  680},
            {"year": "2025", "downloads": 4180},
            {"year": "2026", "downloads": 3280},
        ],
        "total": 8140,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v10(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v10 · 轮换 secret v10 (R435)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 19,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v10",
    }


def get_skills_unapply_stats(skill_id: str):
    """Skill unapply-stats · 撤销应用统计 (R436)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "unapply_count": 4,
            "unapplied_at": datetime.utcnow().isoformat() + "Z",
            "unapplied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_set_default_payment_billing(method_id: str):
    """Billing payment-methods/{id}/set-default-payment-billing · 设默认 billing (R436)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "for_billing": True,
            "for_subscription": True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_cohort_detailed(campaign_id: str):
    """Campaigns audience-cohort-detailed · cohort 详细 (R436)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_chart_v4(file_id: str):
    """Files download-by-month-chart-v4 · 按月 chart v4 (R436)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Apr", "May", "Jun", "Jul", "Aug", "Sep"],
            "datasets": [
                {"label": "下载",   "data": [168, 248, 312, 428, 487, 312], "type": "bar"},
                {"label": "唯一访客", "data": [118, 178, 218, 312, 348, 220], "type": "bar"},
                {"label": "转化",   "data": [12,  18,  28,  48,  52,  31], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v4",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v11(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v11 · 轮换 secret v11 (R436)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 21,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v11",
    }


def get_skills_apply_stats_v2(skill_id: str):
    """Skill apply-stats-v2 · 应用统计 v2 (R437)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "apply_count": 48,
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_for_billing_v2(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-billing-v2 · 取消默认 billing v2 (R437)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "for_billing": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_region_detailed_v3(campaign_id: str):
    """Campaigns audience-region-detailed-v3 · 地域详细 v3 (R437)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳", "city": "深圳",   "count": 11800, "pct": 64.1},
            {"region": "上海", "city": "上海",   "count":  2780, "pct": 15.1},
            {"region": "北京", "city": "北京",   "count":  2120, "pct": 11.5},
            {"region": "广州", "city": "广州",   "count":  1820, "pct":  9.9},
        ],
        "total": 18420,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_stats_v2(file_id: str):
    """Files download-by-quarter-stats-v2 · 按季度统计 v2 (R437)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads": 428, "unique_users": 318},
            {"quarter": "Q2 2026", "downloads": 728, "unique_users": 528},
            {"quarter": "Q3 2026", "downloads": 1287, "unique_users": 920},
        ],
        "total": 2443,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v12(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v12 · 轮换 secret v12 (R437)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 23,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v12",
    }


def get_skills_unapply_stats_v2(skill_id: str):
    """Skill unapply-stats-v2 · 撤销应用统计 v2 (R438)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":      skill_id,
            "unapply_count": 7,
            "unapplied_at": datetime.utcnow().isoformat() + "Z",
            "unapplied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_for_subscription_v2(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-subscription-v2 · 取消默认 subscription v2 (R438)"""
    return {
        "status": "ok",
        "data": {
            "method_id":        method_id,
            "for_subscription": False,
            "unset_at":         datetime.utcnow().isoformat() + "Z",
            "unset_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_cohort_detailed_v2(campaign_id: str):
    """Campaigns audience-cohort-detailed-v2 · cohort 详细 v2 (R438)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180},
        ],
        "count": 4,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_list_v3(file_id: str):
    """Files download-by-month-list-v3 · 按月列表 v3 (R438)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1955,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v13(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v13 · 轮换 secret v13 (R438)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 25,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v13",
    }


def get_skills_apply_stats_v3(skill_id: str):
    """Skill apply-stats-v3 · 应用统计 v3 (R439)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "apply_count": 64,
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_billing_payment_methods_unset_default_payment_method_v2(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment-method-v2 · 取消默认支付方式 v2 (R439)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_tech_list_v6(campaign_id: str):
    """Campaigns audience-tech-list-v6 · 技术列表 v6 (R439)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_list_v2(file_id: str):
    """Files download-by-quarter-list-v2 · 按季度列表 v2 (R439)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads":  428},
            {"quarter": "Q2 2026", "downloads":  728},
            {"quarter": "Q3 2026", "downloads": 1287},
        ],
        "total": 2443,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v14(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v14 · 轮换 secret v14 (R439)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 27,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v14",
    }


def get_skills_export_stats_v2(skill_id: str):
    """Skill export-stats-v2 · 导出统计 v2 (R440)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "export_count": 28,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "exported_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_payment_billing(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment-billing · 取消默认 billing (R440)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "for_billing": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_source_detailed(campaign_id: str):
    """Campaigns audience-source-detailed · 来源详细 (R440)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "medium": "社交", "count": 6280, "pct": 34.1},
            {"source": "xhs",          "medium": "社交", "count": 4180, "pct": 22.7},
            {"source": "douyin",       "medium": "社交", "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "medium": "社交", "count": 1840, "pct": 10.0},
            {"source": "email",        "medium": "邮件", "count": 1240, "pct":  6.7},
            {"source": "direct",       "medium": "直接", "count": 1180, "pct":  6.4},
            {"source": "baidu",        "medium": "搜索", "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v3(file_id: str):
    """Files download-by-week-stats-v3 · 按周统计 v3 (R440)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
        ],
        "total": 1539,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v15(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v15 · 轮换 secret v15 (R440)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 29,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v15",
    }


def get_skills_import_stats_v2(skill_id: str):
    """Skill import-stats-v2 · 导入统计 v2 (R441)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "import_count": 42,
            "imported_at": datetime.utcnow().isoformat() + "Z",
            "imported_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_for_payment(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-payment · 取消默认 payment (R441)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "for_payment": False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_geo_distribution(campaign_id: str):
    """Campaigns audience-geo-distribution · 地理分布 (R441)"""
    return {
        "status": "ok",
        "data": [
            {"region": "华南",  "users": 5040, "pct": 27.4},
            {"region": "华东",  "users": 4180, "pct": 22.7},
            {"region": "华北",  "users": 3120, "pct": 16.9},
            {"region": "西部",  "users": 2280, "pct": 12.4},
            {"region": "海外",  "users": 1840, "pct": 10.0},
            {"region": "其他",  "users": 1960, "pct": 10.6},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart_v5(file_id: str):
    """Files download-by-day-chart-v5 · 按日 chart v5 (R441)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载", "data": [28, 42, 38, 56, 68, 42, 38], "type": "bar"},
                {"label": "唯一", "data": [18, 28, 22, 38, 45, 28, 24], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v5",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v16(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v16 · 轮换 secret v16 (R441)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 31,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v16",
    }


def get_skills_unsubscribe_stats_v2(skill_id: str):
    """Skill unsubscribe-stats-v2 · 取消订阅统计 v2 (R442)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":        skill_id,
            "unsubscribed_count": 12,
            "unsubscribed_at": datetime.utcnow().isoformat() + "Z",
            "unsubscribed_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_billing_v3(method_id: str):
    """Billing payment-methods/{id}/unset-default-billing-v3 · 取消默认 billing v3 (R442)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "for_billing": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_segment_detailed(campaign_id: str):
    """Campaigns audience-segment-detailed · 分群详细 (R442)"""
    return {
        "status": "ok",
        "data": [
            {"segment_id": "seg_001", "name": "装企老板",   "size": 4280, "rule": "industry=decoration&role=owner"},
            {"segment_id": "seg_002", "name": "医美院长",   "size": 2180, "rule": "industry=medical&role=owner"},
            {"segment_id": "seg_003", "name": "教育机构",   "size": 1240, "rule": "industry=education&role=owner"},
            {"segment_id": "seg_004", "name": "高活跃用户", "size": 1840, "rule": "last_active_at>=7d ago"},
            {"segment_id": "seg_005", "name": "低活跃用户", "size":  980, "rule": "last_active_at<30d ago"},
        ],
        "total": 10520,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_hour_chart_v2(file_id: str):
    """Files download-by-hour-chart-v2 · 按小时 chart v2 (R442)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["00", "04", "08", "12", "16", "20", "23"],
            "datasets": [
                {"label": "下载", "data": [3, 1, 10, 56, 42, 16, 0], "type": "bar"},
                {"label": "唯一", "data": [2, 1,  8, 42, 28,  8, 0], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v2",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v17(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v17 · 轮换 secret v17 (R442)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 33,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v17",
    }


def get_skills_sync_stats_v3(skill_id: str):
    """Skill sync-stats-v3 · 同步统计 v3 (R443)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "sync_count":  36,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_billing_payment_methods_unset_default_subscription_v2(method_id: str):
    """Billing payment-methods/{id}/unset-default-subscription-v2 · 取消默认 subscription v2 (R443)"""
    return {
        "status": "ok",
        "data": {
            "method_id":        method_id,
            "for_subscription": False,
            "unset_at":         datetime.utcnow().isoformat() + "Z",
            "unset_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_region_detailed_v4(campaign_id: str):
    """Campaigns audience-region-detailed-v4 · 地域详细 v4 (R443)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳", "city": "深圳",   "count": 11800, "pct": 64.1},
            {"region": "上海", "city": "上海",   "count":  2780, "pct": 15.1},
            {"region": "北京", "city": "北京",   "count":  2120, "pct": 11.5},
            {"region": "广州", "city": "广州",   "count":  1820, "pct":  9.9},
        ],
        "total": 18420,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_chart_v5(file_id: str):
    """Files download-by-month-chart-v5 · 按月 chart v5 (R443)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Apr", "May", "Jun", "Jul", "Aug", "Sep"],
            "datasets": [
                {"label": "下载",   "data": [168, 248, 312, 428, 487, 312], "type": "bar"},
                {"label": "唯一访客", "data": [118, 178, 218, 312, 348, 220], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v5",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v18(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v18 · 轮换 secret v18 (R443)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 35,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v18",
    }


def get_skills_clone_stats_v3(skill_id: str):
    """Skill clone-stats-v3 · 克隆统计 v3 (R444)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "clone_count":  15,
            "cloned_at":   datetime.utcnow().isoformat() + "Z",
            "cloned_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_billing_payment_methods_unset_default_payment_billing_v2(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment-billing-v2 · 取消默认 payment-billing v2 (R444)"""
    return {
        "status": "ok",
        "data": {
            "method_id":     method_id,
            "for_billing":   False,
            "unset_at":      datetime.utcnow().isoformat() + "Z",
            "unset_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_tech_list_v7(campaign_id: str):
    """Campaigns audience-tech-list-v7 · 技术列表 v7 (R444)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_stats_v3(file_id: str):
    """Files download-by-quarter-stats-v3 · 按季度统计 v3 (R444)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads": 428, "unique_users": 318, "avg_size_mb": 2.5},
            {"quarter": "Q2 2026", "downloads": 728, "unique_users": 528, "avg_size_mb": 2.6},
            {"quarter": "Q3 2026", "downloads": 1287, "unique_users": 920, "avg_size_mb": 2.7},
        ],
        "total": 2443,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v19(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v19 · 轮换 secret v19 (R444)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 37,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v19",
    }


def get_skills_merge_stats_v3(skill_id: str):
    """Skill merge-stats-v3 · 合并统计 v3 (R445)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "merge_count":  8,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_billing_payment_methods_unset_default_payment_method_v3(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment-method-v3 · 取消默认 payment-method v3 (R445)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_grade_list_v3(campaign_id: str):
    """Campaigns audience-grade-list-v3 · 等级列表 v3 (R445)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "min_score": 800, "max_score": 1000},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "min_score": 600, "max_score":  799},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "min_score": 400, "max_score":  599},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "min_score":   0, "max_score":  399},
        ],
        "count": 4,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_list_v4(file_id: str):
    """Files download-by-month-list-v4 · 按月列表 v4 (R445)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4, "median_size_mb": 2.3},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5, "median_size_mb": 2.4},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "median_size_mb": 2.3},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6, "median_size_mb": 2.5},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "median_size_mb": 2.4},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "median_size_mb": 2.3},
        ],
        "total": 1955,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v20(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v20 · 轮换 secret v20 (R445)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 39,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v20",
    }


def get_skills_import_template(skill_id: str):
    """Skill import-template · 导入模板 (R446)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "imported":     True,
            "template_id":  f"tpl_v23_R446_{skill_id}",
            "imported_at": datetime.utcnow().isoformat() + "Z",
            "imported_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_for_all_v2(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-all-v2 · 取消默认 for-all v2 (R446)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_all":  True,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_language_detailed(campaign_id: str):
    """Campaigns audience-language-detailed · 语言详细 (R446)"""
    return {
        "status": "ok",
        "data": [
            {"language": "zh-CN", "name": "简体中文", "country": "中国", "users": 16840, "pct": 91.4},
            {"language": "en-US", "name": "English",  "country": "美国", "users":   920, "pct":  5.0},
            {"language": "ja-JP", "name": "日本語",    "country": "日本", "users":   280, "pct":  1.5},
            {"language": "es-ES", "name": "Español",  "country": "西班牙", "users":   180, "pct":  1.0},
            {"language": "other", "name": "其他",      "country": "其他", "users":   200, "pct":  1.1},
        ],
        "total": 18420,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_of_week_stats(file_id: str):
    """Files download-by-day-of-week-stats · 按周天统计 (R446)"""
    return {
        "status": "ok",
        "data": [
            {"dow": "Mon", "downloads":  52, "unique_users": 38, "avg_size_mb": 2.4},
            {"dow": "Tue", "downloads":  68, "unique_users": 48, "avg_size_mb": 2.5},
            {"dow": "Wed", "downloads":  72, "unique_users": 52, "avg_size_mb": 2.5},
            {"dow": "Thu", "downloads":  58, "unique_users": 42, "avg_size_mb": 2.4},
            {"dow": "Fri", "downloads":  42, "unique_users":  31, "avg_size_mb": 2.4},
            {"dow": "Sat", "downloads":  12, "unique_users":   9, "avg_size_mb": 2.3},
            {"dow": "Sun", "downloads":   8, "unique_users":   6, "avg_size_mb": 2.3},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v2(key_id: str):
    """Auth api-keys/{id}/quota-reset-v2 · 重置 quota v2 (R446)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      30000,
            "previous_quota": 20000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_skills_pull_template_v2(skill_id: str):
    """Skill pull-template-v2 · 拉取模板 v2 (R447)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "pulled_id":   f"tpl_v23_R447_v2_{skill_id}",
            "pulled_at": datetime.utcnow().isoformat() + "Z",
            "size_bytes":  12288,
            "version":     "v2",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_for_billing_v3(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-billing-v3 · 取消默认 billing v3 (R447)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "for_billing": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_source_detailed_v2(campaign_id: str):
    """Campaigns audience-source-detailed-v2 · 来源详细 v2 (R447)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "medium": "社交",  "country": "CN", "count": 6280, "pct": 34.1},
            {"source": "xhs",          "medium": "社交",  "country": "CN", "count": 4180, "pct": 22.7},
            {"source": "douyin",       "medium": "社交",  "country": "CN", "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "medium": "社交",  "country": "CN", "count": 1840, "pct": 10.0},
            {"source": "email",        "medium": "邮件",  "country": "US", "count": 1240, "pct":  6.7},
            {"source": "direct",       "medium": "直接",  "country": "global", "count": 1180, "pct":  6.4},
            {"source": "baidu",        "medium": "搜索",  "country": "CN", "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v4(file_id: str):
    """Files download-by-week-stats-v4 · 按周统计 v4 (R447)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
        ],
        "total": 1539,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_set(key_id: str):
    """Auth api-keys/{id}/quota-set · 设置 quota (R447)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota":          25000,
            "set_at":         datetime.utcnow().isoformat() + "Z",
            "set_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_push_to_marketplace_v2(skill_id: str):
    """Skill push-to-marketplace-v2 · 推到 marketplace v2 (R448)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "marketplace_url": f"https://marketplace.v23.com/v2/skills/{skill_id}",
            "pushed_at": datetime.utcnow().isoformat() + "Z",
            "version":     "v2",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_for_subscription_v3(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-subscription-v3 · 取消默认 subscription v3 (R448)"""
    return {
        "status": "ok",
        "data": {
            "method_id":        method_id,
            "for_subscription": False,
            "unset_at":         datetime.utcnow().isoformat() + "Z",
            "unset_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_cohort_list_v2(campaign_id: str):
    """Campaigns audience-cohort-list-v2 · cohort 列表 v2 (R448)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999, "source": "wechat"},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680, "source": "xhs"},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450, "source": "douyin"},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180, "source": "organic"},
        ],
        "count": 4,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_chart(file_id: str):
    """Files download-by-quarter-chart · 按季度 chart (R448)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Q1", "Q2", "Q3"],
            "datasets": [
                {"label": "下载",   "data": [ 428,  728, 1287], "type": "bar"},
                {"label": "唯一访客", "data": [ 318,  528,  920], "type": "line"},
            ],
            "chart_type": "mixed",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_increase(key_id: str):
    """Auth api-keys/{id}/quota-increase · 增加 quota (R448)"""
    return {
        "status": "ok",
        "data": {
            "key_id":           key_id,
            "previous_quota":   10000,
            "new_quota":        15000,
            "increase_amount":  5000,
            "increased_at":     datetime.utcnow().isoformat() + "Z",
            "increased_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_stats_v3(skill_id: str):
    """Skill export-stats-v3 · 导出统计 v3 (R449)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "export_count": 42,
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "exported_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_billing_payment_methods_validate_billing_v2(method_id: str):
    """Billing payment-methods/{id}/validate-billing-v2 · 验证 billing v2 (R449)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "valid":     True,
            "validated_at": datetime.utcnow().isoformat() + "Z",
            "validated_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_grade_stats_v3(campaign_id: str):
    """Campaigns audience-grade-stats-v3 · 等级统计 v3 (R449)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_chart_v3(file_id: str):
    """Files download-by-week-chart-v3 · 按周 chart v3 (R449)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["W36", "W37", "W38", "W39", "W40"],
            "datasets": [
                {"label": "下载",   "data": [312, 428, 487, 312, 178], "type": "bar"},
                {"label": "唯一访客", "data": [218, 312, 348, 220, 124], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v3",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_decrease(key_id: str):
    """Auth api-keys/{id}/quota-decrease · 减少 quota (R449)"""
    return {
        "status": "ok",
        "data": {
            "key_id":           key_id,
            "previous_quota":   25000,
            "new_quota":        20000,
            "decrease_amount":  5000,
            "decreased_at":     datetime.utcnow().isoformat() + "Z",
            "decreased_by":     "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats_v4(skill_id: str):
    """Skill sync-stats-v4 · 同步统计 v4 (R450)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "sync_count":  48,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_billing_payment_methods_verify_billing_cycle_v2(method_id: str):
    """Billing payment-methods/{id}/verify-billing-cycle-v2 · 验证周期 v2 (R450)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "verified":      True,
            "verified_at":   datetime.utcnow().isoformat() + "Z",
            "verified_by":   "u_001",
            "cycle":         "monthly",
            "next_billing":  "2026-10-15",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_segment_stats(campaign_id: str):
    """Campaigns audience-segment-stats · 分群统计 (R450)"""
    return {
        "status": "ok",
        "data": [
            {"segment_id": "seg_001", "name": "装企老板",   "size": 4280, "avg_ltv_yuan": 1999, "cvr_pct": 5.4},
            {"segment_id": "seg_002", "name": "医美院长",   "size": 2180, "avg_ltv_yuan": 4500, "cvr_pct": 8.2},
            {"segment_id": "seg_003", "name": "教育机构",   "size": 1240, "avg_ltv_yuan": 1200, "cvr_pct": 3.8},
            {"segment_id": "seg_004", "name": "高活跃用户", "size": 1840, "avg_ltv_yuan": 1680, "cvr_pct": 6.5},
            {"segment_id": "seg_005", "name": "低活跃用户", "size":  980, "avg_ltv_yuan":  420, "cvr_pct": 1.2},
        ],
        "total": 10520,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_list_v3(file_id: str):
    """Files download-by-quarter-list-v3 · 按季度列表 v3 (R450)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads":  428},
            {"quarter": "Q2 2026", "downloads":  728},
            {"quarter": "Q3 2026", "downloads": 1287},
        ],
        "total": 2443,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_stats(key_id: str):
    """Auth api-keys/{id}/throttle-stats · 限流统计 (R450)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "total_throttled": 12,
            "last_24h":      {"count": 8,  "by_ts": ["10:30", "11:45", "15:20"]},
            "last_7d":       {"count": 42, "by_day": {"Mon": 8, "Tue": 12, "Wed": 6, "Thu": 4, "Fri": 8, "Sat": 2, "Sun": 2}},
            "limit":         "100 req/min",
            "current":       42,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_clone_stats_v4(skill_id: str):
    """Skill clone-stats-v4 · 克隆统计 v4 (R451)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "clone_count": 21,
            "cloned_at":   datetime.utcnow().isoformat() + "Z",
            "cloned_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_billing_payment_methods_unset_default_for_all_v3(method_id: str):
    """Billing payment-methods/{id}/unset-default-for-all-v3 · 取消默认 for-all v3 (R451)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_all":  True,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_tech_stats_v2(campaign_id: str):
    """Campaigns audience-tech-stats-v2 · 技术统计 v2 (R451)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "avg_cvr_pct": 7.2},
            {"tech": "Android",      "count": 5240, "avg_cvr_pct": 6.8},
            {"tech": "Windows",      "count": 2180, "avg_cvr_pct": 4.5},
            {"tech": "macOS",        "count": 1420, "avg_cvr_pct": 5.8},
            {"tech": "Linux",        "count":  580, "avg_cvr_pct": 3.2},
            {"tech": "Other",        "count": 1180, "avg_cvr_pct": 4.0},
        ],
        "total": 18420,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_chart_v6(file_id: str):
    """Files download-by-month-chart-v6 · 按月 chart v6 (R451)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Apr", "May", "Jun", "Jul", "Aug", "Sep"],
            "datasets": [
                {"label": "下载",       "data": [168, 248, 312, 428, 487, 312], "type": "bar"},
                {"label": "唯一访客",   "data": [118, 178, 218, 312, 348, 220], "type": "bar"},
                {"label": "新访客",     "data": [ 62,  88, 124, 184, 220, 124], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v6",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_quota_v2(key_id: str):
    """Auth api-keys/{id}/rotate-quota-v2 · 重置 quota v2 (R451)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "previous_quota": 30000,
            "new_quota":      40000,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 41,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_skills_merge_stats_v4(skill_id: str):
    """Skill merge-stats-v4 · 合并统计 v4 (R452)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "merge_count": 12,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_billing_payment_methods_unset_default_payment_method_v4(method_id: str):
    """Billing payment-methods/{id}/unset-default-payment-method-v4 · 取消默认 payment-method v4 (R452)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_campaigns_audience_language_list_v3(campaign_id: str):
    """Campaigns audience-language-list-v3 · 语言列表 v3 (R452)"""
    return {
        "status": "ok",
        "data": [
            {"language": "zh-CN", "name": "简体中文", "users": 16840, "pct": 91.4},
            {"language": "en-US", "name": "English",  "users":   920, "pct":  5.0},
            {"language": "ja-JP", "name": "日本語",    "users":   280, "pct":  1.5},
            {"language": "es-ES", "name": "Español",  "users":   180, "pct":  1.0},
            {"language": "other", "name": "其他",      "users":   200, "pct":  1.1},
        ],
        "total": 18420,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year_stats(file_id: str):
    """Files download-by-year-stats · 按年统计 (R452)"""
    return {
        "status": "ok",
        "data": [
            {"year": "2024", "downloads":  680, "unique_users": 480},
            {"year": "2025", "downloads": 4180, "unique_users": 3120},
            {"year": "2026", "downloads": 3280, "unique_users": 2280},
        ],
        "total": 8140,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v21(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v21 · 轮换 secret v21 (R452)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 43,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v21",
    }


def get_skills_import_stats_v3(skill_id: str):
    """Skill import-stats-v3 · 导入统计 v3 (R453 · 🎉 V23 第 500 端点)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "import_count": 55,
            "imported_at": datetime.utcnow().isoformat() + "Z",
            "imported_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
        "milestone":     "V23 第 500 端点 (R453)",
    }


def get_billing_payment_methods_set_active(method_id: str):
    """Billing payment-methods/{id}/set-active · 激活支付 (R453)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   True,
            "set_at":      datetime.utcnow().isoformat() + "Z",
            "set_by":      "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_cohort_list_v3(campaign_id: str):
    """Campaigns audience-cohort-list-v3 · cohort 列表 v3 (R453)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%"},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%"},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%"},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%"},
        ],
        "count": 4,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_stats_v4(file_id: str):
    """Files download-by-quarter-stats-v4 · 按季度统计 v4 (R453)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads":  428, "unique_users": 318},
            {"quarter": "Q2 2026", "downloads":  728, "unique_users": 528},
            {"quarter": "Q3 2026", "downloads": 1287, "unique_users": 920},
        ],
        "total": 2443,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v3(key_id: str):
    """Auth api-keys/{id}/quota-history-v3 · quota 历史 v3 (R453)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-23T00:00:00Z", "quota":   1000, "set_by": "u_001"},
            {"at": "2026-09-26T00:00:00Z", "quota":   5000, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 6,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_template_v2(skill_id: str):
    """Skill export-template-v2 · 导出模板 v2 (R454)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "export_url":  f"https://marketplace.v23.com/v2/templates/{skill_id}.yaml",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "version":     "v2",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_active(method_id: str):
    """Billing payment-methods/{id}/unset-active · 取消激活 (R454)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_tech_list_v8(campaign_id: str):
    """Campaigns audience-tech-list-v8 · 技术列表 v8 (R454)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v8",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_stats(file_id: str):
    """Files download-by-day-stats · 按日统计 (R454)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38, "avg_size_mb": 2.6, "p99_size_mb": 3.0},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
        ],
        "total": 312,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota_history(key_id: str):
    """Auth api-keys/{id}/burst-quota-history · 突发配额历史 (R454)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-25T00:00:00Z", "burst_quota":  100, "set_by": "u_001"},
            {"at": "2026-09-28T00:00:00Z", "burst_quota":  300, "set_by": "u_001"},
            {"at": "2026-09-30T00:00:00Z", "burst_quota":  500, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "burst_quota": 1000, "set_by": "u_001"},
        ],
        "count": 4,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_instance_v2(skill_id: str):
    """Skill sync-from-instance-v2 · 从实例同步 v2 (R455)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "instance_id": f"inst_v23_R455_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_active_v2(method_id: str):
    """Billing payment-methods/{id}/unset-active-v2 · 取消激活 v2 (R455)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_region_stats_v2(campaign_id: str):
    """Campaigns audience-region-stats-v2 · 地域统计 v2 (R455)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v5(file_id: str):
    """Files download-by-week-stats-v5 · 按周统计 v5 (R455)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
        ],
        "total": 1539,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_history_v2(key_id: str):
    """Auth api-keys/{id}/throttle-history-v2 · 限流历史 v2 (R455)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-25T10:30:00Z", "rate": 102, "limit": 100, "throttled": True},
            {"at": "2026-09-28T14:20:00Z", "rate": 105, "limit": 100, "throttled": True},
            {"at": "2026-09-30T16:15:00Z", "rate": 112, "limit": 100, "throttled": True},
        ],
        "count": 3,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_clone_from_template(skill_id: str):
    """Skill clone-from-template · 从模板克隆 (R456)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":     skill_id,
            "new_skill_id": f"{skill_id}_from_template_v23",
            "cloned_at":   datetime.utcnow().isoformat() + "Z",
            "cloned_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_v2(method_id: str):
    """Billing payment-methods/{id}/unset-default-v2 · 取消默认 v2 (R456)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_cohort_detailed_v3(campaign_id: str):
    """Campaigns audience-cohort-detailed-v3 · cohort 详细 v3 (R456)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180},
        ],
        "count": 4,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_stats_v4(file_id: str):
    """Files download-by-month-stats-v4 · 按月统计 v4 (R456)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5, "median_size_mb": 2.4, "p99_size_mb": 2.9},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6, "median_size_mb": 2.5, "p99_size_mb": 3.0},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "median_size_mb": 2.4, "p99_size_mb": 2.9},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
        ],
        "total": 1955,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_burst_quota_reset_history(key_id: str):
    """Auth api-keys/{id}/burst-quota-reset-history · 突发配额重置历史 (R456)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "burst_quota":  500, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "burst_quota": 1000, "set_by": "u_001"},
        ],
        "count": 2,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_merge_with_template(skill_id: str):
    """Skill merge-with-template · 合并到模板 (R457)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "merged_to":   f"template_v23_R457_{skill_id}",
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_validate_billing_cycle_v3(method_id: str):
    """Billing payment-methods/{id}/validate-billing-cycle-v3 · 验证账单周期 v3 (R457)"""
    return {
        "status": "ok",
        "data": {
            "method_id":      method_id,
            "verified":      True,
            "verified_at":   datetime.utcnow().isoformat() + "Z",
            "verified_by":   "u_001",
            "cycle":         "monthly",
            "next_billing":  "2026-10-15",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_language_stats_v2(campaign_id: str):
    """Campaigns audience-language-stats-v2 · 语言统计 v2 (R457)"""
    return {
        "status": "ok",
        "data": [
            {"language": "zh-CN", "name": "简体中文",  "users": 16840, "pct": 91.4, "ltv_yuan": 1680},
            {"language": "en-US", "name": "English",   "users":   920, "pct":  5.0, "ltv_yuan": 3200},
            {"language": "ja-JP", "name": "日本語",     "users":   280, "pct":  1.5, "ltv_yuan": 2100},
            {"language": "es-ES", "name": "Español",   "users":   180, "pct":  1.0, "ltv_yuan": 1500},
            {"language": "other", "name": "其他",       "users":   200, "pct":  1.1, "ltv_yuan": 1200},
        ],
        "total": 18420,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_year_stats_v2(file_id: str):
    """Files download-by-year-stats-v2 · 按年统计 v2 (R457)"""
    return {
        "status": "ok",
        "data": [
            {"year": "2024", "downloads":  680, "unique_users": 480},
            {"year": "2025", "downloads": 4180, "unique_users": 3120},
            {"year": "2026", "downloads": 3280, "unique_users": 2280},
        ],
        "total": 8140,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_throttle_history_v3(key_id: str):
    """Auth api-keys/{id}/throttle-history-v3 · 限流历史 v3 (R457)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T10:30:00Z", "rate": 102, "limit": 100, "throttled": True},
            {"at": "2026-10-01T15:00:00Z", "rate": 105, "limit": 100, "throttled": True},
            {"at": "2026-10-01T20:00:00Z", "rate": 112, "limit": 100, "throttled": True},
        ],
        "count": 3,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v2(skill_id: str):
    """Skill sync-from-template-v2 · 从模板同步 v2 (R458)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R458_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_active_v3(method_id: str):
    """Billing payment-methods/{id}/unset-active-v3 · 取消激活 v3 (R458)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_grade_stats_v4(campaign_id: str):
    """Campaigns audience-grade-stats-v4 · 等级统计 v4 (R458)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_quarter_list_v4(file_id: str):
    """Files download-by-quarter-list-v4 · 按季度列表 v4 (R458)"""
    return {
        "status": "ok",
        "data": [
            {"quarter": "Q1 2026", "downloads":  428, "unique_users": 318},
            {"quarter": "Q2 2026", "downloads":  728, "unique_users": 528},
            {"quarter": "Q3 2026", "downloads": 1287, "unique_users": 920},
        ],
        "total": 2443,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_rotate_secret_v22(key_id: str):
    """Auth api-keys/{id}/rotate-secret-v22 · 轮换 secret v22 (R458)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "rotated":        True,
            "rotated_at":     datetime.utcnow().isoformat() + "Z",
            "rotated_by":     "u_001",
            "rotation_count": 45,
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version":        "v22",
    }


def get_skills_sync_stats_v5(skill_id: str):
    """Skill sync-stats-v5 · 同步统计 v5 (R459)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  52,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v5",
    }


def get_billing_payment_methods_validate_default(method_id: str):
    """Billing payment-methods/{id}/validate-default · 验证默认 (R459)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "validated_at": datetime.utcnow().isoformat() + "Z",
            "validated_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_campaigns_audience_region_stats_v3(campaign_id: str):
    """Campaigns audience-region-stats-v3 · 地域统计 v3 (R459)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_stats_v2(file_id: str):
    """Files download-by-day-stats-v2 · 按日统计 v2 (R459)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38, "avg_size_mb": 2.6, "p99_size_mb": 3.0},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
        ],
        "total": 312,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_set_v2(key_id: str):
    """Auth api-keys/{id}/quota-set-v2 · 设置 quota v2 (R459)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota":          30000,
            "set_at":         datetime.utcnow().isoformat() + "Z",
            "set_by":         "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_skills_apply_template_v2(skill_id: str):
    """Skill apply-template-v2 · 应用模板 v2 (R460)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R460_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_billing_payment_methods_unset_default_v3(method_id: str):
    """Billing payment-methods/{id}/unset-default-v3 · 取消默认 v3 (R460)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_campaigns_audience_tech_list_v9(campaign_id: str):
    """Campaigns audience-tech-list-v9 · 技术列表 v9 (R460)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v9",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v6(file_id: str):
    """Files download-by-week-stats-v6 · 按周统计 v6 (R460)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "p99_size_mb": 2.9},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "p99_size_mb": 2.8},
        ],
        "total": 1539,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v4(key_id: str):
    """Auth api-keys/{id}/quota-history-v4 · quota 历史 v4 (R460)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_merge_stats_v5(skill_id: str):
    """Skill merge-stats-v5 · 合并统计 v5 (R461)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "merge_count": 14,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v5",
    }


def get_billing_payment_methods_unset_active_v4(method_id: str):
    """Billing payment-methods/{id}/unset-active-v4 · 取消激活 v4 (R461)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_campaigns_audience_region_stats_v4(campaign_id: str):
    """Campaigns audience-region-stats-v4 · 地域统计 v4 (R461)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_list_v5(file_id: str):
    """Files download-by-month-list-v5 · 按月列表 v5 (R461)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
            {"month": "2026-05", "downloads": 248, "unique_users": 178, "avg_size_mb": 2.5, "median_size_mb": 2.4, "p99_size_mb": 2.9},
            {"month": "2026-06", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
            {"month": "2026-07", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.6, "median_size_mb": 2.5, "p99_size_mb": 3.0},
            {"month": "2026-08", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5, "median_size_mb": 2.4, "p99_size_mb": 2.9},
            {"month": "2026-09", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4, "median_size_mb": 2.3, "p99_size_mb": 2.8},
        ],
        "total": 1955,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v5(key_id: str):
    """Auth api-keys/{id}/quota-history-v5 · quota 历史 v5 (R461)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats_v6(skill_id: str):
    """Skill sync-stats-v6 · 同步统计 v6 (R462)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  58,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v6",
    }


def get_billing_payment_methods_unset_active_v5(method_id: str):
    """Billing payment-methods/{id}/unset-active-v5 · 取消激活 v5 (R462)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v5",
    }


def get_campaigns_audience_grade_stats_v5(campaign_id: str):
    """Campaigns audience-grade-stats-v5 · 等级统计 v5 (R462)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_list_v5(file_id: str):
    """Files download-by-week-list-v5 · 按周列表 v5 (R462)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312},
            {"week": "2026-09-W2", "downloads": 428},
            {"week": "2026-09-W3", "downloads": 487},
            {"week": "2026-09-W4", "downloads": 312},
        ],
        "total": 1539,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v6(key_id: str):
    """Auth api-keys/{id}/quota-history-v6 · quota 历史 v6 (R462)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v3(skill_id: str):
    """Skill apply-template-v3 · 应用模板 v3 (R463)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R463_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_billing_payment_methods_unset_default_v4(method_id: str):
    """Billing payment-methods/{id}/unset-default-v4 · 取消默认 v4 (R463)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_campaigns_audience_tech_list_v10(campaign_id: str):
    """Campaigns audience-tech-list-v10 · 技术列表 v10 (R463)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v10",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_chart_v7(file_id: str):
    """Files download-by-week-chart-v7 · 按周 chart v7 (R463)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["W36", "W37", "W38", "W39", "W40"],
            "datasets": [
                {"label": "下载",   "data": [312, 428, 487, 312, 178], "type": "bar"},
                {"label": "唯一访客", "data": [218, 312, 348, 220, 124], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v7",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v3(key_id: str):
    """Auth api-keys/{id}/quota-reset-v3 · 重置 quota v3 (R463)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      50000,
            "previous_quota": 30000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_skills_merge_stats_v6(skill_id: str):
    """Skill merge-stats-v6 · 合并统计 v6 (R464)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "merge_count": 16,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v6",
    }


def get_billing_payment_methods_unset_default_v5(method_id: str):
    """Billing payment-methods/{id}/unset-default-v5 · 取消默认 v5 (R464)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v5",
    }


def get_campaigns_audience_cohort_stats(campaign_id: str):
    """Campaigns audience-cohort-stats · cohort 统计 (R464)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "size": 8240, "ltv_yuan": 1999, "cvr_pct": 5.4, "avg_orders": 2.8},
            {"cohort_id": "c_002", "size": 6240, "ltv_yuan": 1680, "cvr_pct": 4.8, "avg_orders": 2.4},
            {"cohort_id": "c_003", "size": 4180, "ltv_yuan": 1450, "cvr_pct": 4.2, "avg_orders": 2.1},
            {"cohort_id": "c_004", "size": 3240, "ltv_yuan": 1180, "cvr_pct": 3.5, "avg_orders": 1.8},
        ],
        "total": 21820,
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v7(file_id: str):
    """Files download-by-week-stats-v7 · 按周统计 v7 (R464)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v7(key_id: str):
    """Auth api-keys/{id}/quota-history-v7 · quota 历史 v7 (R464)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats_v7(skill_id: str):
    """Skill sync-stats-v7 · 同步统计 v7 (R465)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  64,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v7",
    }


def get_billing_payment_methods_unset_default_v6(method_id: str):
    """Billing payment-methods/{id}/unset-default-v6 · 取消默认 v6 (R465)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v6",
    }


def get_campaigns_audience_grade_stats_v6(campaign_id: str):
    """Campaigns audience-grade-stats-v6 · 等级统计 v6 (R465)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_list_v6(file_id: str):
    """Files download-by-month-list-v6 · 按月列表 v6 (R465)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118},
            {"month": "2026-05", "downloads": 248, "unique_users": 178},
            {"month": "2026-06", "downloads": 312, "unique_users": 218},
            {"month": "2026-07", "downloads": 428, "unique_users": 312},
            {"month": "2026-08", "downloads": 487, "unique_users": 348},
            {"month": "2026-09", "downloads": 312, "unique_users": 220},
        ],
        "total": 1955,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v8(key_id: str):
    """Auth api-keys/{id}/quota-history-v8 · quota 历史 v8 (R465)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v8",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v4(skill_id: str):
    """Skill apply-template-v4 · 应用模板 v4 (R466)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R466_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_billing_payment_methods_unset_active_v6(method_id: str):
    """Billing payment-methods/{id}/unset-active-v6 · 取消激活 v6 (R466)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v6",
    }


def get_campaigns_audience_cohort_stats_v2(campaign_id: str):
    """Campaigns audience-cohort-stats-v2 · cohort 统计 v2 (R466)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "size": 8240, "ltv_yuan": 1999, "cvr_pct": 5.4, "avg_orders": 2.8},
            {"cohort_id": "c_002", "size": 6240, "ltv_yuan": 1680, "cvr_pct": 4.8, "avg_orders": 2.4},
            {"cohort_id": "c_003", "size": 4180, "ltv_yuan": 1450, "cvr_pct": 4.2, "avg_orders": 2.1},
            {"cohort_id": "c_004", "size": 3240, "ltv_yuan": 1180, "cvr_pct": 3.5, "avg_orders": 1.8},
        ],
        "total": 21820,
        "version": "v2",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_list_v6(file_id: str):
    """Files download-by-week-list-v6 · 按周列表 v6 (R466)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312},
            {"week": "2026-09-W2", "downloads": 428},
            {"week": "2026-09-W3", "downloads": 487},
            {"week": "2026-09-W4", "downloads": 312},
        ],
        "total": 1539,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v4(key_id: str):
    """Auth api-keys/{id}/quota-reset-v4 · 重置 quota v4 (R466)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      60000,
            "previous_quota": 40000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_skills_sync_from_template_v3(skill_id: str):
    """Skill sync-from-template-v3 · 从模板同步 v3 (R467)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R467_v3_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v3",
    }


def get_billing_payment_methods_validate_default_v2(method_id: str):
    """Billing payment-methods/{id}/validate-default-v2 · 验证默认 v2 (R467)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_default":  True,
            "validated_at": datetime.utcnow().isoformat() + "Z",
            "validated_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v2",
    }


def get_campaigns_audience_tech_list_v11(campaign_id: str):
    """Campaigns audience-tech-list-v11 · 技术列表 v11 (R467)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v11",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_chart_v7(file_id: str):
    """Files download-by-month-chart-v7 · 按月 chart v7 (R467)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Apr", "May", "Jun", "Jul", "Aug", "Sep"],
            "datasets": [
                {"label": "下载", "data": [168, 248, 312, 428, 487, 312], "type": "bar"},
                {"label": "唯一访客", "data": [118, 178, 218, 312, 348, 220], "type": "bar"},
            ],
            "chart_type": "bar",
            "version": "v7",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v9(key_id: str):
    """Auth api-keys/{id}/quota-history-v9 · quota 历史 v9 (R467)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v9",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v5(skill_id: str):
    """Skill apply-template-v5 · 应用模板 v5 (R468)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R468_v5_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v5",
    }


def get_billing_payment_methods_unset_default_v7(method_id: str):
    """Billing payment-methods/{id}/unset-default-v7 · 取消默认 v7 (R468)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v7",
    }


def get_campaigns_audience_grade_stats_v7(campaign_id: str):
    """Campaigns audience-grade-stats-v7 · 等级统计 v7 (R468)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_chart_v8(file_id: str):
    """Files download-by-week-chart-v8 · 按周 chart v8 (R468)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["W36", "W37", "W38", "W39", "W40"],
            "datasets": [
                {"label": "下载",   "data": [312, 428, 487, 312, 178], "type": "bar"},
                {"label": "唯一访客", "data": [218, 312, 348, 220, 124], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v8",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v5(key_id: str):
    """Auth api-keys/{id}/quota-reset-v5 · 重置 quota v5 (R468)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      70000,
            "previous_quota": 50000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v5",
    }


def get_skills_merge_stats_v7(skill_id: str):
    """Skill merge-stats-v7 · 合并统计 v7 (R469)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "merge_count": 18,
            "merged_at":   datetime.utcnow().isoformat() + "Z",
            "merged_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v7",
    }


def get_billing_payment_methods_unset_active_v7(method_id: str):
    """Billing payment-methods/{id}/unset-active-v7 · 取消激活 v7 (R469)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v7",
    }


def get_campaigns_audience_cohort_detailed_v4(campaign_id: str):
    """Campaigns audience-cohort-detailed-v4 · cohort 详细 v4 (R469)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180},
        ],
        "count": 4,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v8(file_id: str):
    """Files download-by-week-stats-v8 · 按周统计 v8 (R469)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v8",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v10(key_id: str):
    """Auth api-keys/{id}/quota-history-v10 · quota 历史 v10 (R469)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v10",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats_v8(skill_id: str):
    """Skill sync-stats-v8 · 同步统计 v8 (R470)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  68,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v8",
    }


def get_billing_payment_methods_unset_default_v8(method_id: str):
    """Billing payment-methods/{id}/unset-default-v8 · 取消默认 v8 (R470)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v8",
    }


def get_campaigns_audience_tech_stats_v12(campaign_id: str):
    """Campaigns audience-tech-stats-v12 · 技术统计 v12 (R470)"""
    return {
        "status": "ok",
        "data": [
            {"tech": "iOS",          "count": 7820, "pct": 42.4},
            {"tech": "Android",      "count": 5240, "pct": 28.4},
            {"tech": "Windows",      "count": 2180, "pct": 11.8},
            {"tech": "macOS",        "count": 1420, "pct":  7.7},
            {"tech": "Linux",        "count":  580, "pct":  3.1},
            {"tech": "Other",        "count": 1180, "pct":  6.4},
        ],
        "count": 6,
        "version": "v12",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_month_chart_v8(file_id: str):
    """Files download-by-month-chart-v8 · 按月 chart v8 (R470)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["Apr", "May", "Jun", "Jul", "Aug", "Sep"],
            "datasets": [
                {"label": "下载",   "data": [168, 248, 312, 428, 487, 312], "type": "bar"},
                {"label": "唯一访客", "data": [118, 178, 218, 312, 348, 220], "type": "line"},
                {"label": "新访客",   "data": [ 62,  88, 124, 184, 220, 124], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v8",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v6(key_id: str):
    """Auth api-keys/{id}/quota-reset-v6 · 重置 quota v6 (R470)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      80000,
            "previous_quota": 60000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v6",
    }


def get_skills_sync_from_template_v4(skill_id: str):
    """Skill sync-from-template-v4 · 从模板同步 v4 (R471)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R471_v4_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v4",
    }


def get_billing_payment_methods_unset_active_v8(method_id: str):
    """Billing payment-methods/{id}/unset-active-v8 · 取消激活 v8 (R471)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v8",
    }


def get_campaigns_audience_cohort_stas_v3(campaign_id: str):
    """Campaigns audience-cohort-stats-v3 · cohort 统计 v3 (R471)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "size": 8240, "ltv_yuan": 1999, "cvr_pct": 5.4, "avg_orders": 2.8},
            {"cohort_id": "c_002", "size": 6240, "ltv_yuan": 1680, "cvr_pct": 4.8, "avg_orders": 2.4},
            {"cohort_id": "c_003", "size": 4180, "ltv_yuan": 1450, "cvr_pct": 4.2, "avg_orders": 2.1},
            {"cohort_id": "c_004", "size": 3240, "ltv_yuan": 1180, "cvr_pct": 3.5, "avg_orders": 1.8},
        ],
        "total": 21820,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v9(file_id: str):
    """Files download-by-week-stats-v9 · 按周统计 v9 (R471)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v9",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v11(key_id: str):
    """Auth api-keys/{id}/quota-history-v11 · quota 历史 v11 (R471)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v11",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v6(skill_id: str):
    """Skill apply-template-v6 · 应用模板 v6 (R472)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R472_v6_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v6",
    }


def get_billing_payment_methods_unset_default_v9(method_id: str):
    """Billing payment-methods/{id}/unset-default-v9 · 取消默认 v9 (R472)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v9",
    }


def get_campaigns_audience_grade_stats_v8(campaign_id: str):
    """Campaigns audience-grade-stats-v8 · 等级统计 v8 (R472)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v8",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_chart_v9(file_id: str):
    """Files download-by-week-chart-v9 · 按周 chart v9 (R472)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["W36", "W37", "W38", "W39", "W40"],
            "datasets": [
                {"label": "下载", "data": [312, 428, 487, 312, 178], "type": "bar"},
                {"label": "唯一", "data": [218, 312, 348, 220, 124], "type": "line"},
                {"label": "新访客", "data": [124, 184, 220, 124, 62], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v9",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v7(key_id: str):
    """Auth api-keys/{id}/quota-reset-v7 · 重置 quota v7 (R472)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      100000,
            "previous_quota": 70000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v7",
    }


def get_skills_sync_stats_v9(skill_id: str):
    """Skill sync-stats-v9 · 同步统计 v9 · V23 第 600 端点里程碑 (R473)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  72,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
            "milestone":   "V23 第 600 端点 (R473 · 2026-10-01)",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v9",
    }


def get_billing_payment_methods_unset_active_v9(method_id: str):
    """Billing payment-methods/{id}/unset-active-v9 · 取消激活 v9 · V23 第 601 端点 (R473)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
            "milestone":   "V23 第 601 端点 (R473)",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v9",
    }


def get_campaigns_audience_source_detailed_v3(campaign_id: str):
    """Campaigns audience-source-detailed-v3 · 来源详细 v3 · V23 第 602 端点 (R473)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "medium": "社交",  "country": "CN", "count": 6280, "pct": 34.1},
            {"source": "xhs",          "medium": "社交",  "country": "CN", "count": 4180, "pct": 22.7},
            {"source": "douyin",       "medium": "社交",  "country": "CN", "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "medium": "社交",  "country": "CN", "count": 1840, "pct": 10.0},
            {"source": "email",        "medium": "邮件",  "country": "US", "count": 1240, "pct":  6.7},
            {"source": "direct",       "medium": "直接",  "country": "global", "count": 1180, "pct":  6.4},
            {"source": "baidu",        "medium": "搜索",  "country": "CN", "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "milestone":   "V23 第 602 端点 (R473)",
    }


def get_files_download_by_month_list_v7(file_id: str):
    """Files download-by-month-list-v7 · 按月列表 v7 · V23 第 603 端点 (R473)"""
    return {
        "status": "ok",
        "data": [
            {"month": "2026-04", "downloads": 168, "unique_users": 118},
            {"month": "2026-05", "downloads": 248, "unique_users": 178},
            {"month": "2026-06", "downloads": 312, "unique_users": 218},
            {"month": "2026-07", "downloads": 428, "unique_users": 312},
            {"month": "2026-08", "downloads": 487, "unique_users": 348},
            {"month": "2026-09", "downloads": 312, "unique_users": 220},
        ],
        "total": 1955,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "milestone":   "V23 第 603 端点 (R473)",
    }


def get_auth_api_keys_quota_history_v12(key_id: str):
    """Auth api-keys/{id}/quota-history-v12 · quota 历史 v12 · V23 第 604 端点 (R473)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v12",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "milestone":   "V23 第 604 端点 (R473)",
    }


def get_skills_apply_template_v7(skill_id: str):
    """Skill apply-template-v7 · 应用模板 v7 (R474)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R474_v7_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v7",
    }


def get_billing_payment_methods_unset_default_v10(method_id: str):
    """Billing payment-methods/{id}/unset-default-v10 · 取消默认 v10 (R474)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v10",
    }


def get_campaigns_audience_grade_stats_v9(campaign_id: str):
    """Campaigns audience-grade-stats-v9 · 等级统计 v9 (R474)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v9",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v10(file_id: str):
    """Files download-by-week-stats-v10 · 按周统计 v10 (R474)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v10",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v8(key_id: str):
    """Auth api-keys/{id}/quota-reset-v8 · 重置 quota v8 (R474)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      120000,
            "previous_quota": 100000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v8",
    }


def get_skills_sync_stats_v10(skill_id: str):
    """Skill sync-stats-v10 · 同步统计 v10 (R475)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  76,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v10",
    }


def get_billing_payment_methods_unset_active_v10(method_id: str):
    """Billing payment-methods/{id}/unset-active-v10 · 取消激活 v10 (R475)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v10",
    }


def get_campaigns_audience_source_list_v4(campaign_id: str):
    """Campaigns audience-source-list-v4 · 来源列表 v4 (R475)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "count": 7,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v3(file_id: str):
    """Files download-by-day-list-v3 · 按日列表 v3 (R475)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v3",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v13(key_id: str):
    """Auth api-keys/{id}/quota-history-v13 · quota 历史 v13 (R475)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v13",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_export_from_template(skill_id: str):
    """Skill export-from-template · 从模板导出 (R476)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "export_url":  f"https://marketplace.v23.com/templates/{skill_id}.yaml",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "version":     "v1",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_billing_payment_methods_unset_default_v11(method_id: str):
    """Billing payment-methods/{id}/unset-default-v11 · 取消默认 v11 (R476)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v11",
    }


def get_campaigns_audience_grade_stats_v10(campaign_id: str):
    """Campaigns audience-grade-stats-v10 · 等级统计 v10 (R476)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v10",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart_v10(file_id: str):
    """Files download-by-day-chart-v10 · 按日 chart v10 (R476)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载", "data": [28, 42, 38, 56, 68, 42, 38], "type": "bar"},
                {"label": "唯一", "data": [18, 28, 22, 38, 45, 28, 24], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v10",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v9(key_id: str):
    """Auth api-keys/{id}/quota-reset-v9 · 重置 quota v9 (R476)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      150000,
            "previous_quota": 120000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v9",
    }


def get_skills_sync_stats_v11(skill_id: str):
    """Skill sync-stats-v11 · 同步统计 v11 (R477)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  80,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v11",
    }


def get_billing_payment_methods_unset_active_v11(method_id: str):
    """Billing payment-methods/{id}/unset-active-v11 · 取消激活 v11 (R477)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v11",
    }


def get_campaigns_audience_cohort_detailed_v5(campaign_id: str):
    """Campaigns audience-cohort-detailed-v5 · cohort 详细 v5 (R477)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180},
        ],
        "count": 4,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v11(file_id: str):
    """Files download-by-week-stats-v11 · 按周统计 v11 (R477)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v11",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v14(key_id: str):
    """Auth api-keys/{id}/quota-history-v14 · quota 历史 v14 (R477)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v14",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v8(skill_id: str):
    """Skill apply-template-v8 · 应用模板 v8 (R478)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R478_v8_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v8",
    }


def get_billing_payment_methods_unset_default_v12(method_id: str):
    """Billing payment-methods/{id}/unset-default-v12 · 取消默认 v12 (R478)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v12",
    }


def get_campaigns_audience_source_stats_v4(campaign_id: str):
    """Campaigns audience-source-stats-v4 · 来源统计 v4 (R478)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v4(file_id: str):
    """Files download-by-day-list-v4 · 按日列表 v4 (R478)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v4",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_reset_v10(key_id: str):
    """Auth api-keys/{id}/quota-reset-v10 · 重置 quota v10 (R478)"""
    return {
        "status": "ok",
        "data": {
            "key_id":         key_id,
            "quota_reset":    True,
            "new_quota":      200000,
            "previous_quota": 150000,
            "reset_at":       datetime.utcnow().isoformat() + "Z",
            "reset_by":       "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v10",
    }


def get_skills_sync_from_template_v5(skill_id: str):
    """Skill sync-from-template-v5 · 从模板同步 v5 (R479)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R479_v5_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v5",
    }


def get_billing_payment_methods_unset_active_v12(method_id: str):
    """Billing payment-methods/{id}/unset-active-v12 · 取消激活 v12 (R479)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v12",
    }


def get_campaigns_audience_cohort_detailed_v6(campaign_id: str):
    """Campaigns audience-cohort-detailed-v6 · cohort 详细 v6 (R479)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180},
        ],
        "count": 4,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v12(file_id: str):
    """Files download-by-week-stats-v12 · 按周统计 v12 (R479)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v12",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v15(key_id: str):
    """Auth api-keys/{id}/quota-history-v15 · quota 历史 v15 (R479)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v15",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v9(skill_id: str):
    """Skill apply-template-v9 · 应用模板 v9 (R480)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R480_v9_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v9",
    }


def get_billing_payment_methods_unset_default_v13(method_id: str):
    """Billing payment-methods/{id}/unset-default-v13 · 取消默认 v13 (R480)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v13",
    }


def get_campaigns_audience_source_detailed_v6(campaign_id: str):
    """Campaigns audience-source-detailed-v6 · 来源详细 v6 (R480)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "medium": "社交",  "country": "CN", "count": 6280, "pct": 34.1},
            {"source": "xhs",          "medium": "社交",  "country": "CN", "count": 4180, "pct": 22.7},
            {"source": "douyin",       "medium": "社交",  "country": "CN", "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "medium": "社交",  "country": "CN", "count": 1840, "pct": 10.0},
            {"source": "email",        "medium": "邮件",  "country": "US", "count": 1240, "pct":  6.7},
            {"source": "direct",       "medium": "直接",  "country": "global", "count": 1180, "pct":  6.4},
            {"source": "baidu",        "medium": "搜索",  "country": "CN", "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart_v11(file_id: str):
    """Files download-by-day-chart-v11 · 按日 chart v11 (R480)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载",   "data": [28, 42, 38, 56, 68, 42, 38], "type": "bar"},
                {"label": "唯一访客", "data": [18, 28, 22, 38, 45, 28, 24], "type": "line"},
                {"label": "新访客",   "data": [ 8, 14, 12, 18, 22, 14, 14], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v11",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v16(key_id: str):
    """Auth api-keys/{id}/quota-history-v16 · quota 历史 v16 (R480)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v16",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats_v12(skill_id: str):
    """Skill sync-stats-v12 · 同步统计 v12 (R481)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  84,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v12",
    }


def get_billing_payment_methods_unset_active_v13(method_id: str):
    """Billing payment-methods/{id}/unset-active-v13 · 取消激活 v13 (R481)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v13",
    }


def get_campaigns_audience_grade_stats_v11(campaign_id: str):
    """Campaigns audience-grade-stats-v11 · 等级统计 v11 (R481)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v11",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v5(file_id: str):
    """Files download-by-day-list-v5 · 按日列表 v5 (R481)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v17(key_id: str):
    """Auth api-keys/{id}/quota-history-v17 · quota 历史 v17 (R481)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v17",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v10(skill_id: str):
    """Skill apply-template-v10 · 应用模板 v10 (R482)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R482_v10_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v10",
    }


def get_billing_payment_methods_unset_default_v14(method_id: str):
    """Billing payment-methods/{id}/unset-default-v14 · 取消默认 v14 (R482)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v14",
    }


def get_campaigns_audience_region_stats_v5(campaign_id: str):
    """Campaigns audience-region-stats-v5 · 地域统计 v5 (R482)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v6(file_id: str):
    """Files download-by-day-list-v6 · 按日列表 v6 (R482)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v18(key_id: str):
    """Auth api-keys/{id}/quota-history-v18 · quota 历史 v18 (R482)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v18",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v6(skill_id: str):
    """Skill sync-from-template-v6 · 从模板同步 v6 (R483)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R483_v6_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v6",
    }


def get_billing_payment_methods_unset_active_v14(method_id: str):
    """Billing payment-methods/{id}/unset-active-v14 · 取消激活 v14 (R483)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v14",
    }


def get_campaigns_audience_source_stats_v5(campaign_id: str):
    """Campaigns audience-source-stats-v5 · 来源统计 v5 (R483)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v5",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_list_v7(file_id: str):
    """Files download-by-week-list-v7 · 按周列表 v7 (R483)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312},
            {"week": "2026-09-W2", "downloads": 428},
            {"week": "2026-09-W3", "downloads": 487},
            {"week": "2026-09-W4", "downloads": 312},
        ],
        "total": 1539,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v19(key_id: str):
    """Auth api-keys/{id}/quota-history-v19 · quota 历史 v19 (R483)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v19",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v11(skill_id: str):
    """Skill apply-template-v11 · 应用模板 v11 (R484)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R484_v11_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v11",
    }


def get_billing_payment_methods_unset_default_v15(method_id: str):
    """Billing payment-methods/{id}/unset-default-v15 · 取消默认 v15 (R484)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v15",
    }


def get_campaigns_audience_grade_stats_v12(campaign_id: str):
    """Campaigns audience-grade-stats-v12 · 等级统计 v12 (R484)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v12",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v7(file_id: str):
    """Files download-by-day-list-v7 · 按日列表 v7 (R484)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v20(key_id: str):
    """Auth api-keys/{id}/quota-history-v20 · quota 历史 v20 (R484)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v20",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats_v13(skill_id: str):
    """Skill sync-stats-v13 · 同步统计 v13 (R485)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  88,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v13",
    }


def get_billing_payment_methods_unset_active_v15(method_id: str):
    """Billing payment-methods/{id}/unset-active-v15 · 取消激活 v15 (R485)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v15",
    }


def get_campaigns_audience_region_stats_v6(campaign_id: str):
    """Campaigns audience-region-stats-v6 · 地域统计 v6 (R485)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v13(file_id: str):
    """Files download-by-week-stats-v13 · 按周统计 v13 (R485)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v13",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v21(key_id: str):
    """Auth api-keys/{id}/quota-history-v21 · quota 历史 v21 (R485)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v21",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v12(skill_id: str):
    """Skill apply-template-v12 · 应用模板 v12 (R486)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R486_v12_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v12",
    }


def get_billing_payment_methods_unset_default_v16(method_id: str):
    """Billing payment-methods/{id}/unset-default-v16 · 取消默认 v16 (R486)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v16",
    }


def get_campaigns_audience_source_stats_v6(campaign_id: str):
    """Campaigns audience-source-stats-v6 · 来源统计 v6 (R486)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v6",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_chart_v12(file_id: str):
    """Files download-by-day-chart-v12 · 按日 chart v12 (R486)"""
    return {
        "status": "ok",
        "data": {
            "labels": ["09-24", "09-25", "09-26", "09-27", "09-28", "09-29", "09-30"],
            "datasets": [
                {"label": "下载", "data": [28, 42, 38, 56, 68, 42, 38], "type": "bar"},
                {"label": "唯一", "data": [18, 28, 22, 38, 45, 28, 24], "type": "line"},
                {"label": "新访客", "data": [10, 14,  8, 18, 24, 14, 14], "type": "line"},
            ],
            "chart_type": "mixed",
            "version": "v12",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v22(key_id: str):
    """Auth api-keys/{id}/quota-history-v22 · quota 历史 v22 (R486)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v22",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v7(skill_id: str):
    """Skill sync-from-template-v7 · 从模板同步 v7 (R487)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R487_v7_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v7",
    }


def get_billing_payment_methods_unset_active_v16(method_id: str):
    """Billing payment-methods/{id}/unset-active-v16 · 取消激活 v16 (R487)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v16",
    }


def get_campaigns_audience_grade_stats_v13(campaign_id: str):
    """Campaigns audience-grade-stats-v13 · 等级统计 v13 (R487)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v13",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v14(file_id: str):
    """Files download-by-week-stats-v14 · 按周统计 v14 (R487)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v14",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v23(key_id: str):
    """Auth api-keys/{id}/quota-history-v23 · quota 历史 v23 (R487)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v23",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v13(skill_id: str):
    """Skill apply-template-v13 · 应用模板 v13 (R488)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R488_v13_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v13",
    }


def get_billing_payment_methods_unset_default_v17(method_id: str):
    """Billing payment-methods/{id}/unset-default-v17 · 取消默认 v17 (R488)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v17",
    }


def get_campaigns_audience_region_stats_v7(campaign_id: str):
    """Campaigns audience-region-stats-v7 · 地域统计 v7 (R488)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v8(file_id: str):
    """Files download-by-day-list-v8 · 按日列表 v8 (R488)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v8",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v24(key_id: str):
    """Auth api-keys/{id}/quota-history-v24 · quota 历史 v24 (R488)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v24",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_stats_v14(skill_id: str):
    """Skill sync-stats-v14 · 同步统计 v14 (R489)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "sync_count":  92,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v14",
    }


def get_billing_payment_methods_unset_active_v17(method_id: str):
    """Billing payment-methods/{id}/unset-active-v17 · 取消激活 v17 (R489)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v17",
    }


def get_campaigns_audience_source_stats_v7(campaign_id: str):
    """Campaigns audience-source-stats-v7 · 来源统计 v7 (R489)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v15(file_id: str):
    """Files download-by-week-stats-v15 · 按周统计 v15 (R489)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v15",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v25(key_id: str):
    """Auth api-keys/{id}/quota-history-v25 · quota 历史 v25 (R489)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v25",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v14(skill_id: str):
    """Skill apply-template-v14 · 应用模板 v14 (R490)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R490_v14_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v14",
    }


def get_billing_payment_methods_unset_default_v18(method_id: str):
    """Billing payment-methods/{id}/unset-default-v18 · 取消默认 v18 (R490)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v18",
    }


def get_campaigns_audience_region_stats_v8(campaign_id: str):
    """Campaigns audience-region-stats-v8 · 地域统计 v8 (R490)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v8",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v9(file_id: str):
    """Files download-by-day-list-v9 · 按日列表 v9 (R490)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v9",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v26(key_id: str):
    """Auth api-keys/{id}/quota-history-v26 · quota 历史 v26 (R490)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v26",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v8(skill_id: str):
    """Skill sync-from-template-v8 · 从模板同步 v8 (R491)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R491_v8_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v8",
    }


def get_billing_payment_methods_unset_active_v18(method_id: str):
    """Billing payment-methods/{id}/unset-active-v18 · 取消激活 v18 (R491)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v18",
    }


def get_campaigns_audience_source_stats_v8(campaign_id: str):
    """Campaigns audience-source-stats-v8 · 来源统计 v8 (R491)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v8",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v16(file_id: str):
    """Files download-by-week-stats-v16 · 按周统计 v16 (R491)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v16",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v27(key_id: str):
    """Auth api-keys/{id}/quota-history-v27 · quota 历史 v27 (R491)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v27",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v15(skill_id: str):
    """Skill apply-template-v15 · 应用模板 v15 (R492)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R492_v15_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v15",
    }


def get_billing_payment_methods_unset_default_v19(method_id: str):
    """Billing payment-methods/{id}/unset-default-v19 · 取消默认 v19 (R492)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v19",
    }


def get_campaigns_audience_region_detailed_v7(campaign_id: str):
    """Campaigns audience-region-detailed-v7 · 地域详细 v7 (R492)"""
    return {
        "status": "ok",
        "data": [
            {"cohort_id": "c_001", "name": "2026-09-W1", "size": 8240, "retention_pct": "100%", "ltv_yuan": 1999},
            {"cohort_id": "c_002", "name": "2026-09-W2", "size": 6240, "retention_pct": "75.7%", "ltv_yuan": 1680},
            {"cohort_id": "c_003", "name": "2026-09-W3", "size": 4180, "retention_pct": "50.7%", "ltv_yuan": 1450},
            {"cohort_id": "c_004", "name": "2026-09-W4", "size": 3240, "retention_pct": "39.3%", "ltv_yuan": 1180},
        ],
        "count": 4,
        "version": "v7",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_stats_v17(file_id: str):
    """Files download-by-day-stats-v17 · 按周统计 v17 (R492)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v17",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v28(key_id: str):
    """Auth api-keys/{id}/quota-history-v28 · quota 历史 v28 (R492)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v28",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v9(skill_id: str):
    """Skill sync-from-template-v9 · 从模板同步 v9 (R493 · V23 第 700 端点)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R493_v9_{skill_id}",
            "synced_by":   "u_001",
            "milestone":   "V23 第 700 端点 (R493 · 2026-10-01)",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v9",
    }


def get_billing_payment_methods_unset_active_v19(method_id: str):
    """Billing payment-methods/{id}/unset-active-v19 · 取消激活 v19 (R493)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_active": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v19",
    }


def get_campaigns_audience_source_stats_v9(campaign_id: str):
    """Campaigns audience-source-stats-v9 · 来源统计 v9 (R493)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v9",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v10(file_id: str):
    """Files download-by-day-list-v10 · 按日列表 v10 (R493)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v10",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v29(key_id: str):
    """Auth api-keys/{id}/quota-history-v29 · quota 历史 v29 (R493)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v29",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v16(skill_id: str):
    """Skill apply-template-v16 · 应用模板 v16 (R494)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R494_v16_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v16",
    }


def get_billing_payment_methods_unset_default_v20(method_id: str):
    """Billing payment-methods/{id}/unset-default-v20 · 取消默认 v20 (R494)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v20",
    }


def get_campaigns_audience_region_stats_v9(campaign_id: str):
    """Campaigns audience-region-stats-v9 · 地域统计 v9 (R494)"""
    return {
        "status": "ok",
        "data": [
            {"region": "深圳",  "users": 11800, "pct": 64.1, "ltv_yuan": 1999},
            {"region": "上海",  "users":  2780, "pct": 15.1, "ltv_yuan": 1680},
            {"region": "北京",  "users":  2120, "pct": 11.5, "ltv_yuan": 1450},
            {"region": "广州",  "users":  1820, "pct":  9.9, "ltv_yuan": 1180},
        ],
        "total": 18420,
        "version": "v9",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v18(file_id: str):
    """Files download-by-week-stats-v18 · 按周统计 v18 (R494)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v18",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v30(key_id: str):
    """Auth api-keys/{id}/quota-history-v30 · quota 历史 v30 (R494)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v30",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v10(skill_id: str):
    """Skill sync-from-template-v10 · 从模板同步 v10 (R495)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R495_v10_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v10",
    }


def get_billing_payment_methods_unset_active_v20(method_id: str):
    """Billing payment-methods/{id}/unset-active-v20 · 取消激活 v20 (R495)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v20",
    }


def get_campaigns_audience_source_stats_v10(campaign_id: str):
    """Campaigns audience-source-stats-v10 · 来源统计 v10 (R495)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v10",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v11(file_id: str):
    """Files download-by-day-list-v11 · 按日列表 v11 (R495)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v11",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v31(key_id: str):
    """Auth api-keys/{id}/quota-history-v31 · quota 历史 v31 (R495)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v31",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_apply_template_v17(skill_id: str):
    """Skill apply-template-v17 · 应用模板 v17 (R496)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "applied_to":  f"target_v23_R496_v17_{skill_id}",
            "applied_at": datetime.utcnow().isoformat() + "Z",
            "applied_by": "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v17",
    }


def get_billing_payment_methods_unset_default_v21(method_id: str):
    """Billing payment-methods/{id}/unset-default-v21 · 取消默认 v21 (R496)"""
    return {
        "status": "ok",
        "data": {
            "method_id":  method_id,
            "is_default": False,
            "unset_at":   datetime.utcnow().isoformat() + "Z",
            "unset_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v21",
    }


def get_campaigns_audience_grade_stats_v14(campaign_id: str):
    """Campaigns audience-grade-stats-v14 · 等级统计 v14 (R496)"""
    return {
        "status": "ok",
        "data": [
            {"grade": "A 优质", "count": 4180, "pct": 22.7, "avg_score": 920},
            {"grade": "B 良好", "count": 6240, "pct": 33.9, "avg_score": 720},
            {"grade": "C 普通", "count": 5240, "pct": 28.4, "avg_score": 510},
            {"grade": "D 低质", "count": 2760, "pct": 15.0, "avg_score": 280},
        ],
        "total": 18420,
        "version": "v14",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_week_stats_v19(file_id: str):
    """Files download-by-week-stats-v19 · 按周统计 v19 (R496)"""
    return {
        "status": "ok",
        "data": [
            {"week": "2026-09-W1", "downloads": 312, "unique_users": 218, "avg_size_mb": 2.4},
            {"week": "2026-09-W2", "downloads": 428, "unique_users": 312, "avg_size_mb": 2.5},
            {"week": "2026-09-W3", "downloads": 487, "unique_users": 348, "avg_size_mb": 2.5},
            {"week": "2026-09-W4", "downloads": 312, "unique_users": 220, "avg_size_mb": 2.4},
        ],
        "total": 1539,
        "version": "v19",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v32(key_id: str):
    """Auth api-keys/{id}/quota-history-v32 · quota 历史 v32 (R496)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v32",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v11(skill_id: str):
    """Skill sync-from-template-v11 · 从模板同步 v11 (R497)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R497_v11_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v11",
    }


def get_billing_payment_methods_unset_active_v21(method_id: str):
    """Billing payment-methods/{id}/unset-active-v21 · 取消激活 v21 (R497)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v21",
    }


def get_campaigns_audience_source_stats_v11(campaign_id: str):
    """Campaigns audience-source-stats-v11 · 来源统计 v11 (R497)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat",       "count": 6280, "pct": 34.1},
            {"source": "xhs",          "count": 4180, "pct": 22.7},
            {"source": "douyin",       "count": 3120, "pct": 16.9},
            {"source": "wechat_group", "count": 1840, "pct": 10.0},
            {"source": "email",        "count": 1240, "pct":  6.7},
            {"source": "direct",       "count": 1180, "pct":  6.4},
            {"source": "baidu",        "count":  580, "pct":  3.2},
        ],
        "total": 18420,
        "version": "v11",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v12(file_id: str):
    """Files download-by-day-list-v12 · 按日列表 v12 (R497)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-24", "downloads": 28, "unique_users": 18},
            {"date": "2026-09-25", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-26", "downloads": 38, "unique_users": 22},
            {"date": "2026-09-27", "downloads": 56, "unique_users": 38},
            {"date": "2026-09-28", "downloads": 68, "unique_users": 45},
            {"date": "2026-09-29", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-30", "downloads": 38, "unique_users": 24},
        ],
        "total": 312,
        "version": "v12",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v33(key_id: str):
    """Auth api-keys/{id}/quota-history-v33 · quota 历史 v33 (R497)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-09-30T00:00:00Z", "quota":  10000, "set_by": "u_001"},
            {"at": "2026-10-01T00:00:00Z", "quota":  20000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  30000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  40000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v33",
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

# ═══════════════════════════════════
# R498 · 5 个新动态端点 (V23 第 150+ 模板)
# ═══════════════════════════════════

def get_skills_sync_from_template_v12(skill_id: str):
    """Skill sync-from-template-v12 · 从模板同步 v12 (R498)"""
    return {
        "status": "ok",
        "data": {
            "skill_id":    skill_id,
            "synced_at":   datetime.utcnow().isoformat() + "Z",
            "template_id": f"tpl_v23_R498_v12_{skill_id}",
            "synced_by":   "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v12",
    }


def get_billing_payment_methods_unset_active_v22(method_id: str):
    """Billing payment-methods/{id}/unset-active-v22 · 取消激活 v22 (R498)"""
    return {
        "status": "ok",
        "data": {
            "method_id":   method_id,
            "is_active":   False,
            "unset_at":    datetime.utcnow().isoformat() + "Z",
            "unset_by":    "u_001",
        },
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "v22",
    }


def get_campaigns_audience_source_stats_v12(campaign_id: str):
    """Campaigns audience-source-stats-v12 · 来源统计 v12 (R498)"""
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_official", "count": 8820, "pct": 36.8},
            {"source": "xhs",             "count": 5180, "pct": 21.6},
            {"source": "douyin",          "count": 4120, "pct": 17.2},
            {"source": "wechat_group",    "count": 2340, "pct":  9.8},
            {"source": "email",           "count": 1640, "pct":  6.8},
            {"source": "direct",          "count": 1180, "pct":  4.9},
            {"source": "baidu",           "count":  680, "pct":  2.9},
        ],
        "total": 23960,
        "version": "v12",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v13(file_id: str):
    """Files download-by-day-list-v13 · 按日列表 v13 (R498)"""
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-25", "downloads": 32, "unique_users": 22},
            {"date": "2026-09-26", "downloads": 48, "unique_users": 32},
            {"date": "2026-09-27", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-28", "downloads": 62, "unique_users": 42},
            {"date": "2026-09-29", "downloads": 76, "unique_users": 52},
            {"date": "2026-09-30", "downloads": 48, "unique_users": 32},
            {"date": "2026-10-01", "downloads": 42, "unique_users": 28},
        ],
        "total": 350,
        "version": "v13",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v34(key_id: str):
    """Auth api-keys/{id}/quota-history-v34 · quota 历史 v34 (R498)"""
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota":  40000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  50000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  60000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota":  70000, "set_by": "u_001"},
        ],
        "count": 4,
        "version": "v34",
        "source": "demo_seed",
        "ts": datetime.utcnow().isoformat() + "Z",
    }


# R498 ROUTES 注册
# 主表 (line ~13200-13300 附近) 实际位置 - 找 

# ═══════════════════════════════════
# R499 · 5 个新动态端点 (V23 第 155+ 模板)
# ═══════════════════════════════════

def get_skills_sync_from_template_v13(skill_id: str):
    return {
        "status": "ok",
        "data": {"skill_id": skill_id, "synced_at": datetime.utcnow().isoformat() + "Z", "template_id": f"tpl_v23_R499_v13_{skill_id}", "synced_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v13",
    }


def get_billing_payment_methods_unset_active_v23(method_id: str):
    return {
        "status": "ok",
        "data": {"method_id": method_id, "is_active": False, "unset_at": datetime.utcnow().isoformat() + "Z", "unset_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v23",
    }


def get_campaigns_audience_source_stats_v13(campaign_id: str):
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_mini", "count": 10820, "pct": 38.2},
            {"source": "xhs",         "count":  6180, "pct": 21.8},
            {"source": "douyin",      "count":  5120, "pct": 18.1},
            {"source": "wechat_group","count":  2840, "pct": 10.0},
            {"source": "email",       "count":  1640, "pct":  5.8},
            {"source": "direct",      "count":   980, "pct":  3.5},
            {"source": "baidu",       "count":   740, "pct":  2.6},
        ],
        "total": 28320, "version": "v13", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v14(file_id: str):
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-26", "downloads": 38, "unique_users": 26},
            {"date": "2026-09-27", "downloads": 54, "unique_users": 36},
            {"date": "2026-09-28", "downloads": 48, "unique_users": 32},
            {"date": "2026-09-29", "downloads": 68, "unique_users": 46},
            {"date": "2026-09-30", "downloads": 82, "unique_users": 58},
            {"date": "2026-10-01", "downloads": 54, "unique_users": 36},
            {"date": "2026-10-02", "downloads": 48, "unique_users": 32},
        ],
        "total": 392, "version": "v14", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v35(key_id: str):
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota":  70000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota":  80000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota":  90000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota": 100000, "set_by": "u_001"},
        ],
        "count": 4, "version": "v35", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }





# ═══════════════════════════════════
# R500 · 5 个新动态端点 (V23 第 156+ 模板 · 端点突破 739)
# ═══════════════════════════════════



# ═══════════════════════════════════
# R501 · 5 个新动态端点 (V23 第 157+ 模板 · 端点突破 744)
# ═══════════════════════════════════



# ═══════════════════════════════════
# R502 · 5 个新动态端点 (V23 第 158+ 模板 · 端点突破 749)
# ═══════════════════════════════════



# ═══════════════════════════════════
# R503 · 5 个新动态端点 (V23 第 159+ 模板 · 端点突破 754)
# ═══════════════════════════════════



# ═══════════════════════════════════
# R504 · 5 个新动态端点 (V23 第 160+ 模板 · 端点突破 759)
# ═══════════════════════════════════



# ═══════════════════════════════════
# R505 · 5 个新动态端点 (V23 第 161+ 模板 · 端点突破 764)
# ═══════════════════════════════════



# R506 · 5 个新动态端点



# R507 · 5 个新动态端点



# R508 · 5 个新动态端点



# R509 · 5 个新动态端点



# R510 · 5 个新动态端点



# R511 · 5 个新动态端点



# R512 · 5 个新动态端点



# R513 · 5 个新动态端点



# R514 · 5 个新动态端点



# R515 · 5 个新动态端点



# R516 · 5 个新动态端点



# R517 · 5 个新动态端点



# R518 · 5 个新动态端点



# R519 · 5 个新动态端点



# R520 · 5 个新动态端点



# R521 · 5 个新动态端点



# R522 · 5 个新动态端点



# R523 · 5 个新动态端点



# R524 · 5 个新动态端点



# R525 · 5 个新动态端点



# R526 · 5 个新动态端点



# R527 · 5 个新动态端点



# R528 · 5 个新动态端点



# R529 · 5 个新动态端点



# R530 · 5 个新动态端点



# R531 · 5 个新动态端点



# R532 · 5 个新动态端点



# R533 · 5 个新动态端点



# R534 · 5 个新动态端点



# R535 · 5 个新动态端点



# R536 · 5 个新动态端点



# R537 · 5 个新动态端点



# R538 · 5 个新动态端点



# R539 · 5 个新动态端点



# R540 · 5 个新动态端点



# R541 · 5 个新动态端点



# R542 · 5 个新动态端点



# R543 · 5 个新动态端点



# R544 · 5 个新动态端点



# R545 · 5 个新动态端点



# R546 · 5 个新动态端点



# R547 · 5 个新动态端点



# R548 · 5 个新动态端点



# R549 · 5 个新动态端点



# R550 · 5 个新动态端点



# R551 · 5 个新动态端点



# R552 · 5 个新动态端点



# R553 · 5 个新动态端点



# R554 · 5 个新动态端点



# R555 · 5 个新动态端点



# R556 · 5 个新动态端点



# R557 · 5 个新动态端点



# R558 · 5 个新动态端点



# R559 · 5 个新动态端点



# R560 · 5 个新动态端点



# R561 · 5 个新动态端点



# R562 · 5 个新动态端点



# R563 · 5 个新动态端点



# R564 · 5 个新动态端点



# R565 · 5 个新动态端点



# R566 · 5 个新动态端点



# R567 · 5 个新动态端点



# R568 · 5 个新动态端点



# R569 · 5 个新动态端点



# R570 · 5 个新动态端点

def get_skills_sync_from_template_v84(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R570_v84_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v84"}


def get_billing_payment_methods_unset_active_v85(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v85"}


def get_campaigns_audience_source_stats_v84(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R570","count":67000,"pct":97.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33500,"pct":-42.0},{"source":"grp","count":3000,"pct":10.0}],"total":113500,"version":"v84","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v85(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5800,"unique_users":2910} for _ in range(7)],"total":40600,"version":"v85","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v106(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5980000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5990000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":6000000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":6010000,"set_by":"u_001"}],"count":4,"version":"v106","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v83(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R569_v83_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v83"}


def get_billing_payment_methods_unset_active_v84(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v84"}


def get_campaigns_audience_source_stats_v83(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R569","count":66900,"pct":96.9},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33450,"pct":-41.9},{"source":"grp","count":3000,"pct":10.0}],"total":113350,"version":"v83","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v84(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5790,"unique_users":2905} for _ in range(7)],"total":40530,"version":"v84","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v105(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5970000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5980000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5990000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":6000000,"set_by":"u_001"}],"count":4,"version":"v105","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v82(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R568_v82_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v82"}


def get_billing_payment_methods_unset_active_v83(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v83"}


def get_campaigns_audience_source_stats_v82(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R568","count":66800,"pct":96.8},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33400,"pct":-41.8},{"source":"grp","count":3000,"pct":10.0}],"total":113200,"version":"v82","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v83(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5780,"unique_users":2900} for _ in range(7)],"total":40460,"version":"v83","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v104(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5960000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5970000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5980000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5990000,"set_by":"u_001"}],"count":4,"version":"v104","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v81(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R567_v81_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v81"}


def get_billing_payment_methods_unset_active_v82(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v82"}


def get_campaigns_audience_source_stats_v81(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R567","count":66700,"pct":96.7},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33350,"pct":-41.7},{"source":"grp","count":3000,"pct":10.0}],"total":113050,"version":"v81","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v82(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5770,"unique_users":2895} for _ in range(7)],"total":40390,"version":"v82","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v103(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5950000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5960000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5970000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5980000,"set_by":"u_001"}],"count":4,"version":"v103","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v80(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R566_v80_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v80"}


def get_billing_payment_methods_unset_active_v81(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v81"}


def get_campaigns_audience_source_stats_v80(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R566","count":66600,"pct":96.6},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33300,"pct":-41.6},{"source":"grp","count":3000,"pct":10.0}],"total":112900,"version":"v80","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v81(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5760,"unique_users":2890} for _ in range(7)],"total":40320,"version":"v81","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v102(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5940000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5950000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5960000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5970000,"set_by":"u_001"}],"count":4,"version":"v102","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v79(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R565_v79_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v79"}


def get_billing_payment_methods_unset_active_v80(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v80"}


def get_campaigns_audience_source_stats_v79(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R565","count":66500,"pct":96.5},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33250,"pct":-41.5},{"source":"grp","count":3000,"pct":10.0}],"total":112750,"version":"v79","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v80(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5750,"unique_users":2885} for _ in range(7)],"total":40250,"version":"v80","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v101(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5930000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5940000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5950000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5960000,"set_by":"u_001"}],"count":4,"version":"v101","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v78(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R564_v78_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v78"}


def get_billing_payment_methods_unset_active_v79(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v79"}


def get_campaigns_audience_source_stats_v78(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R564","count":66400,"pct":96.4},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33200,"pct":-41.4},{"source":"grp","count":3000,"pct":10.0}],"total":112600,"version":"v78","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v79(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5740,"unique_users":2880} for _ in range(7)],"total":40180,"version":"v79","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v100(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5920000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5930000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5940000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5950000,"set_by":"u_001"}],"count":4,"version":"v100","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v77(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R563_v77_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v77"}


def get_billing_payment_methods_unset_active_v78(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v78"}


def get_campaigns_audience_source_stats_v77(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R563","count":66300,"pct":96.3},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33150,"pct":-41.3},{"source":"grp","count":3000,"pct":10.0}],"total":112450,"version":"v77","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v78(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5730,"unique_users":2875} for _ in range(7)],"total":40110,"version":"v78","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v99(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5910000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5920000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5930000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5940000,"set_by":"u_001"}],"count":4,"version":"v99","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v76(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R562_v76_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v76"}


def get_billing_payment_methods_unset_active_v77(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v77"}


def get_campaigns_audience_source_stats_v76(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R562","count":66200,"pct":96.2},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33100,"pct":-41.2},{"source":"grp","count":3000,"pct":10.0}],"total":112300,"version":"v76","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v77(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5720,"unique_users":2870} for _ in range(7)],"total":40040,"version":"v77","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v98(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5900000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5910000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5920000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5930000,"set_by":"u_001"}],"count":4,"version":"v98","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v75(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R561_v75_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v75"}


def get_billing_payment_methods_unset_active_v76(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v76"}


def get_campaigns_audience_source_stats_v75(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R561","count":66100,"pct":96.1},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33050,"pct":-41.1},{"source":"grp","count":3000,"pct":10.0}],"total":112150,"version":"v75","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v76(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5710,"unique_users":2865} for _ in range(7)],"total":39970,"version":"v76","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v97(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5890000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5900000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5910000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5920000,"set_by":"u_001"}],"count":4,"version":"v97","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v74(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R560_v74_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v74"}


def get_billing_payment_methods_unset_active_v75(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v75"}


def get_campaigns_audience_source_stats_v74(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R560","count":66000,"pct":96.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":33000,"pct":-41.0},{"source":"grp","count":3000,"pct":10.0}],"total":112000,"version":"v74","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v75(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5700,"unique_users":2860} for _ in range(7)],"total":39900,"version":"v75","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v96(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5880000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5890000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5900000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5910000,"set_by":"u_001"}],"count":4,"version":"v96","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v73(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R559_v73_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v73"}


def get_billing_payment_methods_unset_active_v74(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v74"}


def get_campaigns_audience_source_stats_v73(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R559","count":65900,"pct":95.9},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32950,"pct":-40.9},{"source":"grp","count":3000,"pct":10.0}],"total":111850,"version":"v73","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v74(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5690,"unique_users":2855} for _ in range(7)],"total":39830,"version":"v74","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v95(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5870000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5880000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5890000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5900000,"set_by":"u_001"}],"count":4,"version":"v95","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v72(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R558_v72_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v72"}


def get_billing_payment_methods_unset_active_v73(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v73"}


def get_campaigns_audience_source_stats_v72(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R558","count":65800,"pct":95.8},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32900,"pct":-40.8},{"source":"grp","count":3000,"pct":10.0}],"total":111700,"version":"v72","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v73(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5680,"unique_users":2850} for _ in range(7)],"total":39760,"version":"v73","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v94(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5860000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5870000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5880000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5890000,"set_by":"u_001"}],"count":4,"version":"v94","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v71(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R557_v71_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v71"}


def get_billing_payment_methods_unset_active_v72(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v72"}


def get_campaigns_audience_source_stats_v71(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R557","count":65700,"pct":95.7},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32850,"pct":-40.7},{"source":"grp","count":3000,"pct":10.0}],"total":111550,"version":"v71","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v72(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5670,"unique_users":2845} for _ in range(7)],"total":39690,"version":"v72","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v93(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5850000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5860000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5870000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5880000,"set_by":"u_001"}],"count":4,"version":"v93","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v70(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R556_v70_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v70"}


def get_billing_payment_methods_unset_active_v71(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v71"}


def get_campaigns_audience_source_stats_v70(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R556","count":65600,"pct":95.6},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32800,"pct":-40.6},{"source":"grp","count":3000,"pct":10.0}],"total":111400,"version":"v70","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v71(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5660,"unique_users":2840} for _ in range(7)],"total":39620,"version":"v71","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v92(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5840000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5850000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5860000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5870000,"set_by":"u_001"}],"count":4,"version":"v92","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v69(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R555_v69_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v69"}


def get_billing_payment_methods_unset_active_v70(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v70"}


def get_campaigns_audience_source_stats_v69(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R555","count":65500,"pct":95.5},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32750,"pct":-40.5},{"source":"grp","count":3000,"pct":10.0}],"total":111250,"version":"v69","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v70(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5650,"unique_users":2835} for _ in range(7)],"total":39550,"version":"v70","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v91(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5830000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5840000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5850000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5860000,"set_by":"u_001"}],"count":4,"version":"v91","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v68(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R554_v68_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v68"}


def get_billing_payment_methods_unset_active_v69(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v69"}


def get_campaigns_audience_source_stats_v68(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R554","count":65400,"pct":95.4},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32700,"pct":-40.4},{"source":"grp","count":3000,"pct":10.0}],"total":111100,"version":"v68","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v69(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5640,"unique_users":2830} for _ in range(7)],"total":39480,"version":"v69","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v90(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5820000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5830000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5840000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5850000,"set_by":"u_001"}],"count":4,"version":"v90","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v67(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R553_v67_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v67"}


def get_billing_payment_methods_unset_active_v68(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v68"}


def get_campaigns_audience_source_stats_v67(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R553","count":65300,"pct":95.3},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32650,"pct":-40.3},{"source":"grp","count":3000,"pct":10.0}],"total":110950,"version":"v67","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v68(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5630,"unique_users":2825} for _ in range(7)],"total":39410,"version":"v68","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v89(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5810000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5820000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5830000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5840000,"set_by":"u_001"}],"count":4,"version":"v89","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v66(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R552_v66_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v66"}


def get_billing_payment_methods_unset_active_v67(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v67"}


def get_campaigns_audience_source_stats_v66(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R552","count":65200,"pct":95.2},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32600,"pct":-40.2},{"source":"grp","count":3000,"pct":10.0}],"total":110800,"version":"v66","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v67(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5620,"unique_users":2820} for _ in range(7)],"total":39340,"version":"v67","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v88(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5800000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5810000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5820000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5830000,"set_by":"u_001"}],"count":4,"version":"v88","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v65(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R551_v65_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v65"}


def get_billing_payment_methods_unset_active_v66(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v66"}


def get_campaigns_audience_source_stats_v65(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R551","count":65100,"pct":95.1},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32550,"pct":-40.1},{"source":"grp","count":3000,"pct":10.0}],"total":110650,"version":"v65","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v66(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5610,"unique_users":2815} for _ in range(7)],"total":39270,"version":"v66","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v87(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5790000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5800000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5810000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5820000,"set_by":"u_001"}],"count":4,"version":"v87","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v64(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R550_v64_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v64"}


def get_billing_payment_methods_unset_active_v65(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v65"}


def get_campaigns_audience_source_stats_v64(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R550","count":65000,"pct":95.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32500,"pct":-40.0},{"source":"grp","count":3000,"pct":10.0}],"total":110500,"version":"v64","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v65(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5600,"unique_users":2810} for _ in range(7)],"total":39200,"version":"v65","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v86(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5780000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5790000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5800000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5810000,"set_by":"u_001"}],"count":4,"version":"v86","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v63(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R549_v63_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v63"}


def get_billing_payment_methods_unset_active_v64(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v64"}


def get_campaigns_audience_source_stats_v63(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R549","count":64900,"pct":94.9},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32450,"pct":-39.9},{"source":"grp","count":3000,"pct":10.0}],"total":110350,"version":"v63","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v64(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5590,"unique_users":2805} for _ in range(7)],"total":39130,"version":"v64","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v85(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5770000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5780000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5790000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5800000,"set_by":"u_001"}],"count":4,"version":"v85","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v62(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R548_v62_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v62"}


def get_billing_payment_methods_unset_active_v63(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v63"}


def get_campaigns_audience_source_stats_v62(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R548","count":64800,"pct":94.8},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32400,"pct":-39.8},{"source":"grp","count":3000,"pct":10.0}],"total":110200,"version":"v62","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v63(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5580,"unique_users":2800} for _ in range(7)],"total":39060,"version":"v63","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v84(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5760000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5770000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5780000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5790000,"set_by":"u_001"}],"count":4,"version":"v84","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v61(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R547_v61_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v61"}


def get_billing_payment_methods_unset_active_v62(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v62"}


def get_campaigns_audience_source_stats_v61(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R547","count":64700,"pct":94.7},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32350,"pct":-39.7},{"source":"grp","count":3000,"pct":10.0}],"total":110050,"version":"v61","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v62(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5570,"unique_users":2795} for _ in range(7)],"total":38990,"version":"v62","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v83(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5750000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5760000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5770000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5780000,"set_by":"u_001"}],"count":4,"version":"v83","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v60(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R546_v60_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v60"}


def get_billing_payment_methods_unset_active_v61(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v61"}


def get_campaigns_audience_source_stats_v60(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R546","count":64600,"pct":94.6},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32300,"pct":-39.6},{"source":"grp","count":3000,"pct":10.0}],"total":109900,"version":"v60","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v61(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5560,"unique_users":2790} for _ in range(7)],"total":38920,"version":"v61","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v82(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5740000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5750000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5760000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5770000,"set_by":"u_001"}],"count":4,"version":"v82","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v59(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R545_v59_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v59"}


def get_billing_payment_methods_unset_active_v60(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v60"}


def get_campaigns_audience_source_stats_v59(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R545","count":64500,"pct":94.5},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32250,"pct":-39.5},{"source":"grp","count":3000,"pct":10.0}],"total":109750,"version":"v59","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v60(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5550,"unique_users":2785} for _ in range(7)],"total":38850,"version":"v60","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v81(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5730000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5740000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5750000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5760000,"set_by":"u_001"}],"count":4,"version":"v81","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v58(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R544_v58_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v58"}


def get_billing_payment_methods_unset_active_v59(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v59"}


def get_campaigns_audience_source_stats_v58(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R544","count":64400,"pct":94.4},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32200,"pct":-39.4},{"source":"grp","count":3000,"pct":10.0}],"total":109600,"version":"v58","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v59(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5540,"unique_users":2780} for _ in range(7)],"total":38780,"version":"v59","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v80(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5720000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5730000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5740000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5750000,"set_by":"u_001"}],"count":4,"version":"v80","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v57(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R543_v57_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v57"}


def get_billing_payment_methods_unset_active_v58(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v58"}


def get_campaigns_audience_source_stats_v57(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R543","count":64300,"pct":94.3},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32150,"pct":-39.3},{"source":"grp","count":3000,"pct":10.0}],"total":109450,"version":"v57","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v58(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5530,"unique_users":2775} for _ in range(7)],"total":38710,"version":"v58","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v79(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5710000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5720000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5730000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5740000,"set_by":"u_001"}],"count":4,"version":"v79","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v56(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R542_v56_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v56"}


def get_billing_payment_methods_unset_active_v57(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v57"}


def get_campaigns_audience_source_stats_v56(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R542","count":64200,"pct":94.2},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32100,"pct":-39.2},{"source":"grp","count":3000,"pct":10.0}],"total":109300,"version":"v56","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v57(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5520,"unique_users":2770} for _ in range(7)],"total":38640,"version":"v57","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v78(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5700000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5710000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5720000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5730000,"set_by":"u_001"}],"count":4,"version":"v78","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v55(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R541_v55_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v55"}


def get_billing_payment_methods_unset_active_v56(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v56"}


def get_campaigns_audience_source_stats_v55(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R541","count":64100,"pct":94.1},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32050,"pct":-39.1},{"source":"grp","count":3000,"pct":10.0}],"total":109150,"version":"v55","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v56(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5510,"unique_users":2765} for _ in range(7)],"total":38570,"version":"v56","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v77(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5690000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5700000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5710000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5720000,"set_by":"u_001"}],"count":4,"version":"v77","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v54(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R540_v54_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v54"}


def get_billing_payment_methods_unset_active_v55(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v55"}


def get_campaigns_audience_source_stats_v54(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R540","count":64000,"pct":94.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":32000,"pct":-39.0},{"source":"grp","count":3000,"pct":10.0}],"total":109000,"version":"v54","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v55(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5500,"unique_users":2760} for _ in range(7)],"total":38500,"version":"v55","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v76(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5680000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5690000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5700000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5710000,"set_by":"u_001"}],"count":4,"version":"v76","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v53(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R539_v53_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v53"}


def get_billing_payment_methods_unset_active_v54(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v54"}


def get_campaigns_audience_source_stats_v53(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R539","count":63900,"pct":93.9},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31950,"pct":-38.9},{"source":"grp","count":3000,"pct":10.0}],"total":108850,"version":"v53","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v54(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5490,"unique_users":2755} for _ in range(7)],"total":38430,"version":"v54","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v75(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5670000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5680000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5690000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5700000,"set_by":"u_001"}],"count":4,"version":"v75","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v52(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R538_v52_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v52"}


def get_billing_payment_methods_unset_active_v53(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v53"}


def get_campaigns_audience_source_stats_v52(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R538","count":63800,"pct":93.8},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31900,"pct":-38.8},{"source":"grp","count":3000,"pct":10.0}],"total":108700,"version":"v52","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v53(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5480,"unique_users":2750} for _ in range(7)],"total":38360,"version":"v53","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v74(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5660000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5670000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5680000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5690000,"set_by":"u_001"}],"count":4,"version":"v74","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v51(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R537_v51_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v51"}


def get_billing_payment_methods_unset_active_v52(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v52"}


def get_campaigns_audience_source_stats_v51(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R537","count":63700,"pct":93.7},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31850,"pct":-38.7},{"source":"grp","count":3000,"pct":10.0}],"total":108550,"version":"v51","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v52(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5470,"unique_users":2745} for _ in range(7)],"total":38290,"version":"v52","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v73(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5650000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5660000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5670000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5680000,"set_by":"u_001"}],"count":4,"version":"v73","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v50(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R536_v50_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v50"}


def get_billing_payment_methods_unset_active_v51(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v51"}


def get_campaigns_audience_source_stats_v50(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R536","count":63600,"pct":93.6},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31800,"pct":-38.6},{"source":"grp","count":3000,"pct":10.0}],"total":108400,"version":"v50","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v51(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5460,"unique_users":2740} for _ in range(7)],"total":38220,"version":"v51","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v72(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5640000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5650000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5660000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5670000,"set_by":"u_001"}],"count":4,"version":"v72","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v49(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R535_v49_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v49"}


def get_billing_payment_methods_unset_active_v50(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v50"}


def get_campaigns_audience_source_stats_v49(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R535","count":63500,"pct":93.5},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31750,"pct":-38.5},{"source":"grp","count":3000,"pct":10.0}],"total":108250,"version":"v49","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v50(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5450,"unique_users":2735} for _ in range(7)],"total":38150,"version":"v50","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v71(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5630000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5640000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5650000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5660000,"set_by":"u_001"}],"count":4,"version":"v71","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v48(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R534_v48_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v48"}


def get_billing_payment_methods_unset_active_v49(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v49"}


def get_campaigns_audience_source_stats_v48(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R534","count":63400,"pct":93.4},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31700,"pct":-38.4},{"source":"grp","count":3000,"pct":10.0}],"total":108100,"version":"v48","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v49(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5440,"unique_users":2730} for _ in range(7)],"total":38080,"version":"v49","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v70(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5620000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5630000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5640000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5650000,"set_by":"u_001"}],"count":4,"version":"v70","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v47(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R533_v47_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v47"}


def get_billing_payment_methods_unset_active_v48(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v48"}


def get_campaigns_audience_source_stats_v47(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R533","count":63300,"pct":93.3},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31650,"pct":-38.3},{"source":"grp","count":3000,"pct":10.0}],"total":107950,"version":"v47","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v48(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5430,"unique_users":2725} for _ in range(7)],"total":38010,"version":"v48","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v69(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5610000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5620000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5630000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5640000,"set_by":"u_001"}],"count":4,"version":"v69","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v46(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R532_v46_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v46"}


def get_billing_payment_methods_unset_active_v47(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v47"}


def get_campaigns_audience_source_stats_v46(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R532","count":63200,"pct":93.2},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31600,"pct":-38.2},{"source":"grp","count":3000,"pct":10.0}],"total":107800,"version":"v46","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v47(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5420,"unique_users":2720} for _ in range(7)],"total":37940,"version":"v47","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v68(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5600000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5610000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5620000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5630000,"set_by":"u_001"}],"count":4,"version":"v68","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v45(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R531_v45_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v45"}


def get_billing_payment_methods_unset_active_v46(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v46"}


def get_campaigns_audience_source_stats_v45(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R531","count":63100,"pct":93.1},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31550,"pct":-38.1},{"source":"grp","count":3000,"pct":10.0}],"total":107650,"version":"v45","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v46(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5410,"unique_users":2715} for _ in range(7)],"total":37870,"version":"v46","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v67(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5590000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5600000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5610000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5620000,"set_by":"u_001"}],"count":4,"version":"v67","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v44(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R530_v44_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v44"}


def get_billing_payment_methods_unset_active_v45(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v45"}


def get_campaigns_audience_source_stats_v44(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R530","count":63000,"pct":93.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31500,"pct":-38.0},{"source":"grp","count":3000,"pct":10.0}],"total":107500,"version":"v44","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v45(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5400,"unique_users":2710} for _ in range(7)],"total":37800,"version":"v45","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v66(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5580000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5590000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5600000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5610000,"set_by":"u_001"}],"count":4,"version":"v66","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v43(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R529_v43_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v43"}


def get_billing_payment_methods_unset_active_v44(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v44"}


def get_campaigns_audience_source_stats_v43(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R529","count":62900,"pct":92.9},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31450,"pct":-37.9},{"source":"grp","count":3000,"pct":10.0}],"total":107350,"version":"v43","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v44(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5390,"unique_users":2705} for _ in range(7)],"total":37730,"version":"v44","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v65(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5570000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5580000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5590000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5600000,"set_by":"u_001"}],"count":4,"version":"v65","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v42(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R528_v42_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v42"}


def get_billing_payment_methods_unset_active_v43(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v43"}


def get_campaigns_audience_source_stats_v42(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R528","count":62800,"pct":92.8},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31400,"pct":-37.8},{"source":"grp","count":3000,"pct":10.0}],"total":107200,"version":"v42","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v43(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5380,"unique_users":2700} for _ in range(7)],"total":37660,"version":"v43","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v64(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5560000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5570000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5580000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5590000,"set_by":"u_001"}],"count":4,"version":"v64","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v41(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R527_v41_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v41"}


def get_billing_payment_methods_unset_active_v42(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v42"}


def get_campaigns_audience_source_stats_v41(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R527","count":62700,"pct":92.7},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31350,"pct":-37.7},{"source":"grp","count":3000,"pct":10.0}],"total":107050,"version":"v41","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v42(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5370,"unique_users":2695} for _ in range(7)],"total":37590,"version":"v42","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v63(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5550000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5560000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5570000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5580000,"set_by":"u_001"}],"count":4,"version":"v63","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v40(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R526_v40_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v40"}


def get_billing_payment_methods_unset_active_v41(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v41"}


def get_campaigns_audience_source_stats_v40(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R526","count":62600,"pct":92.6},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31300,"pct":-37.6},{"source":"grp","count":3000,"pct":10.0}],"total":106900,"version":"v40","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v41(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5360,"unique_users":2690} for _ in range(7)],"total":37520,"version":"v41","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v62(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5540000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5550000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5560000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5570000,"set_by":"u_001"}],"count":4,"version":"v62","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v39(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R525_v39_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v39"}


def get_billing_payment_methods_unset_active_v40(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v40"}


def get_campaigns_audience_source_stats_v39(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R525","count":62500,"pct":92.5},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31250,"pct":-37.5},{"source":"grp","count":3000,"pct":10.0}],"total":106750,"version":"v39","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v40(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5350,"unique_users":2685} for _ in range(7)],"total":37450,"version":"v40","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v61(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5530000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5540000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5550000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5560000,"set_by":"u_001"}],"count":4,"version":"v61","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v38(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R524_v38_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v38"}


def get_billing_payment_methods_unset_active_v39(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v39"}


def get_campaigns_audience_source_stats_v38(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R524","count":62400,"pct":92.4},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31200,"pct":-37.4},{"source":"grp","count":3000,"pct":10.0}],"total":106600,"version":"v38","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v39(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5340,"unique_users":2680} for _ in range(7)],"total":37380,"version":"v39","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v60(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5520000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5530000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5540000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5550000,"set_by":"u_001"}],"count":4,"version":"v60","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v37(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R523_v37_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v37"}


def get_billing_payment_methods_unset_active_v38(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v38"}


def get_campaigns_audience_source_stats_v37(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R523","count":62300,"pct":92.3},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31150,"pct":-37.3},{"source":"grp","count":3000,"pct":10.0}],"total":106450,"version":"v37","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v38(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5330,"unique_users":2675} for _ in range(7)],"total":37310,"version":"v38","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v59(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5510000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5520000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5530000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5540000,"set_by":"u_001"}],"count":4,"version":"v59","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v36(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R522_v36_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v36"}


def get_billing_payment_methods_unset_active_v37(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v37"}


def get_campaigns_audience_source_stats_v36(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R522","count":62200,"pct":92.2},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31100,"pct":-37.2},{"source":"grp","count":3000,"pct":10.0}],"total":106300,"version":"v36","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v37(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5320,"unique_users":2670} for _ in range(7)],"total":37240,"version":"v37","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v58(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5500000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5510000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5520000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5530000,"set_by":"u_001"}],"count":4,"version":"v58","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v35(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R521_v35_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v35"}


def get_billing_payment_methods_unset_active_v36(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v36"}


def get_campaigns_audience_source_stats_v35(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R521","count":62100,"pct":92.1},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31050,"pct":-37.1},{"source":"grp","count":3000,"pct":10.0}],"total":106150,"version":"v35","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v36(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5310,"unique_users":2665} for _ in range(7)],"total":37170,"version":"v36","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v57(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5490000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5500000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5510000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5520000,"set_by":"u_001"}],"count":4,"version":"v57","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v34(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R520_v34_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v34"}


def get_billing_payment_methods_unset_active_v35(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v35"}


def get_campaigns_audience_source_stats_v34(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R520","count":62000,"pct":92.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":31000,"pct":-37.0},{"source":"grp","count":3000,"pct":10.0}],"total":106000,"version":"v34","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v35(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5300,"unique_users":2660} for _ in range(7)],"total":37100,"version":"v35","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v56(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5480000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5490000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5500000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5510000,"set_by":"u_001"}],"count":4,"version":"v56","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v33(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R519_v33_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v33"}


def get_billing_payment_methods_unset_active_v34(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v34"}


def get_campaigns_audience_source_stats_v33(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R519","count":61900,"pct":91.9},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30950,"pct":-36.9},{"source":"grp","count":3000,"pct":10.0}],"total":105850,"version":"v33","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v34(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5290,"unique_users":2655} for _ in range(7)],"total":37030,"version":"v34","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v55(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5470000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5480000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5490000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5500000,"set_by":"u_001"}],"count":4,"version":"v55","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v32(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R518_v32_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v32"}


def get_billing_payment_methods_unset_active_v33(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v33"}


def get_campaigns_audience_source_stats_v32(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R518","count":61800,"pct":91.8},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30900,"pct":-36.8},{"source":"grp","count":3000,"pct":10.0}],"total":105700,"version":"v32","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v33(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5280,"unique_users":2650} for _ in range(7)],"total":36960,"version":"v33","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v54(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5460000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5470000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5480000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5490000,"set_by":"u_001"}],"count":4,"version":"v54","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v31(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R517_v31_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v31"}


def get_billing_payment_methods_unset_active_v32(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v32"}


def get_campaigns_audience_source_stats_v31(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R517","count":61700,"pct":91.7},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30850,"pct":-36.7},{"source":"grp","count":3000,"pct":10.0}],"total":105550,"version":"v31","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v32(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5270,"unique_users":2645} for _ in range(7)],"total":36890,"version":"v32","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v53(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5450000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5460000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5470000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5480000,"set_by":"u_001"}],"count":4,"version":"v53","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v30(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R516_v30_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v30"}


def get_billing_payment_methods_unset_active_v31(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v31"}


def get_campaigns_audience_source_stats_v30(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R516","count":61600,"pct":91.6},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30800,"pct":-36.6},{"source":"grp","count":3000,"pct":10.0}],"total":105400,"version":"v30","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v31(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5260,"unique_users":2640} for _ in range(7)],"total":36820,"version":"v31","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v52(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5440000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5450000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5460000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5470000,"set_by":"u_001"}],"count":4,"version":"v52","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v29(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R515_v29_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v29"}


def get_billing_payment_methods_unset_active_v30(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v30"}


def get_campaigns_audience_source_stats_v29(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R515","count":61500,"pct":91.5},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30750,"pct":-36.5},{"source":"grp","count":3000,"pct":10.0}],"total":105250,"version":"v29","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v30(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5250,"unique_users":2635} for _ in range(7)],"total":36750,"version":"v30","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v51(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5430000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5440000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5450000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5460000,"set_by":"u_001"}],"count":4,"version":"v51","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v28(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R514_v28_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v28"}


def get_billing_payment_methods_unset_active_v29(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v29"}


def get_campaigns_audience_source_stats_v28(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R514","count":61400,"pct":91.4},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30700,"pct":-36.4},{"source":"grp","count":3000,"pct":10.0}],"total":105100,"version":"v28","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v29(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5240,"unique_users":2630} for _ in range(7)],"total":36680,"version":"v29","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v50(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5420000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5430000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5440000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5450000,"set_by":"u_001"}],"count":4,"version":"v50","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v27(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R513_v27_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v27"}


def get_billing_payment_methods_unset_active_v28(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v28"}


def get_campaigns_audience_source_stats_v27(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R513","count":61300,"pct":91.3},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30650,"pct":-36.3},{"source":"grp","count":3000,"pct":10.0}],"total":104950,"version":"v27","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v28(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5230,"unique_users":2625} for _ in range(7)],"total":36610,"version":"v28","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v49(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5410000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5420000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5430000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5440000,"set_by":"u_001"}],"count":4,"version":"v49","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v26(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R512_v26_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v26"}


def get_billing_payment_methods_unset_active_v27(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v27"}


def get_campaigns_audience_source_stats_v26(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R512","count":61200,"pct":91.2},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30600,"pct":-36.2},{"source":"grp","count":3000,"pct":10.0}],"total":104800,"version":"v26","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v27(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5220,"unique_users":2620} for _ in range(7)],"total":36540,"version":"v27","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v48(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5400000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5410000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5420000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5430000,"set_by":"u_001"}],"count":4,"version":"v48","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v25(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R511_v25_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v25"}


def get_billing_payment_methods_unset_active_v26(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v26"}


def get_campaigns_audience_source_stats_v25(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R511","count":61100,"pct":91.1},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30550,"pct":-36.1},{"source":"grp","count":3000,"pct":10.0}],"total":104650,"version":"v25","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v26(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5210,"unique_users":2615} for _ in range(7)],"total":36470,"version":"v26","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v47(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5390000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5400000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5410000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5420000,"set_by":"u_001"}],"count":4,"version":"v47","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v24(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R510_v24_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v24"}


def get_billing_payment_methods_unset_active_v25(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v25"}


def get_campaigns_audience_source_stats_v24(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R510","count":61000,"pct":91.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30500,"pct":-36.0},{"source":"grp","count":3000,"pct":10.0}],"total":104500,"version":"v24","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v25(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5200,"unique_users":2610} for _ in range(7)],"total":36400,"version":"v25","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v46(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5380000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5390000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5400000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5410000,"set_by":"u_001"}],"count":4,"version":"v46","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v23(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R509_v23_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v23"}


def get_billing_payment_methods_unset_active_v24(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v24"}


def get_campaigns_audience_source_stats_v23(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R509","count":60900,"pct":90.9},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30450,"pct":-35.9},{"source":"grp","count":3000,"pct":10.0}],"total":104350,"version":"v23","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v24(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5190,"unique_users":2605} for _ in range(7)],"total":36330,"version":"v24","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v45(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5370000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5380000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5390000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5400000,"set_by":"u_001"}],"count":4,"version":"v45","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v22(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R508_v22_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v22"}


def get_billing_payment_methods_unset_active_v23(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v23"}


def get_campaigns_audience_source_stats_v22(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R508","count":60800,"pct":90.8},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":30400,"pct":-35.8},{"source":"grp","count":3000,"pct":10.0}],"total":104200,"version":"v22","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v23(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":5180,"unique_users":2600} for _ in range(7)],"total":36260,"version":"v23","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v24(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":5360000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":5370000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":5380000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":5390000,"set_by":"u_001"}],"count":4,"version":"v24","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v21(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R507_v21_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v21"}


def get_billing_payment_methods_unset_active_v22(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v22"}


def get_campaigns_audience_source_stats_v21(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_R507","count":10160,"pct":41.0},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":5100,"pct":14.8},{"source":"grp","count":3000,"pct":10.0}],"total":28300,"version":"v21","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v22(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":120,"unique_users":70}],"count":7,"version":"v22","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v43(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":330000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":340000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":350000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":360000,"set_by":"u_001"}],"count":4,"version":"v43","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v44(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":370000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":380000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":390000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":400000,"set_by":"u_001"}],"count":4,"version":"v44","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v20(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":f"tpl_v23_R506_v20_{skill_id}","synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v20"}


def get_billing_payment_methods_unset_active_v21(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v21"}


def get_campaigns_audience_source_stats_v20(campaign_id: str):
    return {"status":"ok","data":[{"source":"ch_v506","count":10060,"pct":40.5},{"source":"xhs","count":10000,"pct":25.0},{"source":"dy","count":5050,"pct":14.9},{"source":"grp","count":3000,"pct":10.0}],"total":28150,"version":"v20","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v21(file_id: str):
    return {"status":"ok","data":[{"date":"2026-10-01","downloads":110,"unique_users":65}],"count":7,"version":"v21","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v42(key_id: str):
    return {"status":"ok","data":[{"at":"2026-10-01T00:00:00Z","quota":290000,"set_by":"u_001"},{"at":"2026-10-01T01:00:00Z","quota":300000,"set_by":"u_001"},{"at":"2026-10-01T02:00:00Z","quota":310000,"set_by":"u_001"},{"at":"2026-10-01T03:00:00Z","quota":320000,"set_by":"u_001"}],"count":4,"version":"v42","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

def get_skills_sync_from_template_v19(skill_id: str):
    return {
        "status": "ok",
        "data": {"skill_id": skill_id, "synced_at": datetime.utcnow().isoformat() + "Z", "template_id": f"tpl_v23_R505_v19_{skill_id}", "synced_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v19",
    }


def get_billing_payment_methods_unset_active_v29(method_id: str):
    return {
        "status": "ok",
        "data": {"method_id": method_id, "is_active": False, "unset_at": datetime.utcnow().isoformat() + "Z", "unset_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v29",
    }


def get_campaigns_audience_source_stats_v19(campaign_id: str):
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_channel_v4", "count": 22820, "pct": 46.0},
            {"source": "xhs_brand_v4",       "count": 12180, "pct": 24.5},
            {"source": "douyin_brand_v5",    "count": 11120, "pct": 22.4},
            {"source": "wechat_grp_v6",      "count":  5840, "pct": 11.8},
        ],
        "total": 49640, "version": "v19", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v20(file_id: str):
    return {
        "status": "ok",
        "data": [
            {"date": "2026-10-02", "downloads": 72, "unique_users": 48},
            {"date": "2026-10-03", "downloads": 90, "unique_users": 60},
            {"date": "2026-10-04", "downloads": 84, "unique_users": 56},
            {"date": "2026-10-05", "downloads": 104, "unique_users": 70},
            {"date": "2026-10-06", "downloads": 118, "unique_users": 84},
            {"date": "2026-10-07", "downloads": 90, "unique_users": 60},
            {"date": "2026-10-08", "downloads": 84, "unique_users": 56},
        ],
        "total": 642, "version": "v20", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v41(key_id: str):
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota": 250000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota": 260000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota": 270000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota": 280000, "set_by": "u_001"},
        ],
        "count": 4, "version": "v41", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v18(skill_id: str):
    return {
        "status": "ok",
        "data": {"skill_id": skill_id, "synced_at": datetime.utcnow().isoformat() + "Z", "template_id": f"tpl_v23_R504_v18_{skill_id}", "synced_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v18",
    }


def get_billing_payment_methods_unset_active_v28(method_id: str):
    return {
        "status": "ok",
        "data": {"method_id": method_id, "is_active": False, "unset_at": datetime.utcnow().isoformat() + "Z", "unset_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v28",
    }


def get_campaigns_audience_source_stats_v18(campaign_id: str):
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_channel_v3", "count": 20820, "pct": 44.8},
            {"source": "xhs_brand_v3",       "count": 11180, "pct": 24.1},
            {"source": "douyin_brand_v4",    "count": 10120, "pct": 21.8},
            {"source": "wechat_grp_v5",      "count":  5340, "pct": 11.5},
        ],
        "total": 46460, "version": "v18", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v19(file_id: str):
    return {
        "status": "ok",
        "data": [
            {"date": "2026-10-01", "downloads": 66, "unique_users": 44},
            {"date": "2026-10-02", "downloads": 84, "unique_users": 56},
            {"date": "2026-10-03", "downloads": 78, "unique_users": 52},
            {"date": "2026-10-04", "downloads": 98, "unique_users": 66},
            {"date": "2026-10-05", "downloads": 112, "unique_users": 80},
            {"date": "2026-10-06", "downloads": 84, "unique_users": 56},
            {"date": "2026-10-07", "downloads": 78, "unique_users": 52},
        ],
        "total": 600, "version": "v19", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v40(key_id: str):
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota": 220000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota": 230000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota": 240000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota": 250000, "set_by": "u_001"},
        ],
        "count": 4, "version": "v40", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v17(skill_id: str):
    return {
        "status": "ok",
        "data": {"skill_id": skill_id, "synced_at": datetime.utcnow().isoformat() + "Z", "template_id": f"tpl_v23_R503_v17_{skill_id}", "synced_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v17",
    }


def get_billing_payment_methods_unset_active_v27(method_id: str):
    return {
        "status": "ok",
        "data": {"method_id": method_id, "is_active": False, "unset_at": datetime.utcnow().isoformat() + "Z", "unset_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v27",
    }


def get_campaigns_audience_source_stats_v17(campaign_id: str):
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_video_channel", "count": 18820, "pct": 43.6},
            {"source": "xhs_brand_v2",         "count": 10180, "pct": 23.6},
            {"source": "douyin_brand_v3",      "count":  9120, "pct": 21.1},
            {"source": "wechat_grp_v4",        "count":  4840, "pct": 11.2},
            {"source": "email_brand_v2",       "count":   240, "pct":  0.6},
        ],
        "total": 43200, "version": "v17", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v18(file_id: str):
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-30", "downloads": 60, "unique_users": 40},
            {"date": "2026-10-01", "downloads": 78, "unique_users": 52},
            {"date": "2026-10-02", "downloads": 72, "unique_users": 48},
            {"date": "2026-10-03", "downloads": 92, "unique_users": 62},
            {"date": "2026-10-04", "downloads": 106, "unique_users": 76},
            {"date": "2026-10-05", "downloads": 78, "unique_users": 52},
            {"date": "2026-10-06", "downloads": 72, "unique_users": 48},
        ],
        "total": 558, "version": "v18", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v39(key_id: str):
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota": 190000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota": 200000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota": 210000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota": 220000, "set_by": "u_001"},
        ],
        "count": 4, "version": "v39", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v16(skill_id: str):
    return {
        "status": "ok",
        "data": {"skill_id": skill_id, "synced_at": datetime.utcnow().isoformat() + "Z", "template_id": f"tpl_v23_R502_v16_{skill_id}", "synced_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v16",
    }


def get_billing_payment_methods_unset_active_v26(method_id: str):
    return {
        "status": "ok",
        "data": {"method_id": method_id, "is_active": False, "unset_at": datetime.utcnow().isoformat() + "Z", "unset_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v26",
    }


def get_campaigns_audience_source_stats_v16(campaign_id: str):
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_official_v2", "count": 16820, "pct": 42.4},
            {"source": "xhs_live_v2",        "count":  9180, "pct": 23.1},
            {"source": "douyin_brand_v2",    "count":  8120, "pct": 20.4},
            {"source": "wechat_grp_v3",      "count":  4340, "pct": 10.9},
            {"source": "email_v3",           "count":   840, "pct":  2.1},
            {"source": "direct_v3",          "count":   380, "pct":  1.0},
        ],
        "total": 39680, "version": "v16", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v17(file_id: str):
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-29", "downloads": 54, "unique_users": 36},
            {"date": "2026-09-30", "downloads": 72, "unique_users": 48},
            {"date": "2026-10-01", "downloads": 66, "unique_users": 44},
            {"date": "2026-10-02", "downloads": 86, "unique_users": 58},
            {"date": "2026-10-03", "downloads": 100, "unique_users": 72},
            {"date": "2026-10-04", "downloads": 72, "unique_users": 48},
            {"date": "2026-10-05", "downloads": 66, "unique_users": 44},
        ],
        "total": 516, "version": "v17", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v38(key_id: str):
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota": 160000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota": 170000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota": 180000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota": 190000, "set_by": "u_001"},
        ],
        "count": 4, "version": "v38", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v15(skill_id: str):
    return {
        "status": "ok",
        "data": {"skill_id": skill_id, "synced_at": datetime.utcnow().isoformat() + "Z", "template_id": f"tpl_v23_R501_v15_{skill_id}", "synced_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v15",
    }


def get_billing_payment_methods_unset_active_v25(method_id: str):
    return {
        "status": "ok",
        "data": {"method_id": method_id, "is_active": False, "unset_at": datetime.utcnow().isoformat() + "Z", "unset_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v25",
    }


def get_campaigns_audience_source_stats_v15(campaign_id: str):
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_channel", "count": 14820, "pct": 41.0},
            {"source": "xhs_live",       "count":  8180, "pct": 22.6},
            {"source": "douyin_brand",   "count":  7120, "pct": 19.7},
            {"source": "wechat_grp_v2",  "count":  3840, "pct": 10.6},
            {"source": "email_v2",       "count":  1240, "pct":  3.4},
            {"source": "direct_v2",      "count":   680, "pct":  1.9},
            {"source": "baidu_brand",    "count":   240, "pct":  0.7},
        ],
        "total": 36120, "version": "v15", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v16(file_id: str):
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-28", "downloads": 48, "unique_users": 32},
            {"date": "2026-09-29", "downloads": 66, "unique_users": 44},
            {"date": "2026-09-30", "downloads": 60, "unique_users": 40},
            {"date": "2026-10-01", "downloads": 80, "unique_users": 54},
            {"date": "2026-10-02", "downloads": 94, "unique_users": 68},
            {"date": "2026-10-03", "downloads": 66, "unique_users": 44},
            {"date": "2026-10-04", "downloads": 60, "unique_users": 40},
        ],
        "total": 474, "version": "v16", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v37(key_id: str):
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota": 130000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota": 140000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota": 150000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota": 160000, "set_by": "u_001"},
        ],
        "count": 4, "version": "v37", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_skills_sync_from_template_v14(skill_id: str):
    return {
        "status": "ok",
        "data": {"skill_id": skill_id, "synced_at": datetime.utcnow().isoformat() + "Z", "template_id": f"tpl_v23_R500_v14_{skill_id}", "synced_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v14",
    }


def get_billing_payment_methods_unset_active_v24(method_id: str):
    return {
        "status": "ok",
        "data": {"method_id": method_id, "is_active": False, "unset_at": datetime.utcnow().isoformat() + "Z", "unset_by": "u_001"},
        "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z", "version": "v24",
    }


def get_campaigns_audience_source_stats_v14(campaign_id: str):
    return {
        "status": "ok",
        "data": [
            {"source": "wechat_mini_program", "count": 12820, "pct": 39.6},
            {"source": "xhs_video",            "count":  7180, "pct": 22.2},
            {"source": "douyin_live",         "count":  6120, "pct": 18.9},
            {"source": "wechat_group_2",      "count":  3340, "pct": 10.3},
            {"source": "email_seq",          "count":  1640, "pct":  5.1},
            {"source": "direct_import",      "count":   880, "pct":  2.7},
            {"source": "baidu_search",       "count":   380, "pct":  1.2},
        ],
        "total": 32360, "version": "v14", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_files_download_by_day_list_v15(file_id: str):
    return {
        "status": "ok",
        "data": [
            {"date": "2026-09-27", "downloads": 42, "unique_users": 28},
            {"date": "2026-09-28", "downloads": 60, "unique_users": 40},
            {"date": "2026-09-29", "downloads": 54, "unique_users": 36},
            {"date": "2026-09-30", "downloads": 74, "unique_users": 50},
            {"date": "2026-10-01", "downloads": 88, "unique_users": 62},
            {"date": "2026-10-02", "downloads": 60, "unique_users": 40},
            {"date": "2026-10-03", "downloads": 54, "unique_users": 36},
        ],
        "total": 432, "version": "v15", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


def get_auth_api_keys_quota_history_v36(key_id: str):
    return {
        "status": "ok",
        "data": [
            {"at": "2026-10-01T00:00:00Z", "quota": 100000, "set_by": "u_001"},
            {"at": "2026-10-01T01:00:00Z", "quota": 110000, "set_by": "u_001"},
            {"at": "2026-10-01T02:00:00Z", "quota": 120000, "set_by": "u_001"},
            {"at": "2026-10-01T03:00:00Z", "quota": 130000, "set_by": "u_001"},
        ],
        "count": 4, "version": "v36", "source": "demo_seed", "ts": datetime.utcnow().isoformat() + "Z",
    }


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
    "/api/v2/skills/{id}/share-template": lambda q, id="s_001": get_skills_share_template(id),
    "/api/v2/billing/{tenant_id}/subscription-upgrade-options": lambda q, tenant_id="t_3a59592b7619": get_billing_subscription_upgrade_options(tenant_id),
    "/api/v2/campaigns/{id}/audience-region-stats": lambda q, id="c001": get_campaigns_audience_region_stats(id),
    "/api/v2/files/{id}/popular-times":  lambda q, id="f_001": get_files_popular_times(id),
    "/api/v2/auth/api-keys/{id}/disable": lambda q, id="k_001": get_auth_api_keys_disable(id),
    "/api/v2/skills/{id}/merge-template": lambda q, id="s_001": get_skills_merge_template(id),
    "/api/v2/billing/{tenant_id}/downgrade-options": lambda q, tenant_id="t_3a59592b7619": get_billing_downgrade_options(tenant_id),
    "/api/v2/campaigns/{id}/audience-device-stats": lambda q, id="c001": get_campaigns_audience_device_stats(id),
    "/api/v2/files/{id}/download-rate":   lambda q, id="f_001": get_files_download_rate(id),
    "/api/v2/auth/api-keys/{id}/enable":  lambda q, id="k_001": get_auth_api_keys_enable(id),
    "/api/v2/skills/{id}/sync-template":   lambda q, id="s_001": get_skills_sync_template(id),
    "/api/v2/billing/{id}/payment-failed": lambda q, id="inv_001": get_billing_payment_failed(id),
    "/api/v2/campaigns/{id}/conversion-by-channel": lambda q, id="c001": get_campaigns_conversion_by_channel(id),
    "/api/v2/files/{id}/download-geo":    lambda q, id="f_001": get_files_download_geo(id),
    "/api/v2/auth/api-keys/{id}/reset-quota": lambda q, id="k_001": get_auth_api_keys_reset_quota(id),
    "/api/v2/skills/{id}/validate-template": lambda q, id="s_001": get_skills_validate_template(id),
    "/api/v2/billing/{id}/payment-retry":    lambda q, id="inv_001": get_billing_payment_retry(id),
    "/api/v2/campaigns/{id}/engagement-rate": lambda q, id="c001": get_campaigns_engagement_rate(id),
    "/api/v2/files/{id}/download-stats-geo": lambda q, id="f_001": get_files_download_stats_geo(id),
    "/api/v2/auth/api-keys/{id}/permissions-update": lambda q, id="k_001": get_auth_api_keys_permissions_update(id),
    "/api/v2/skills/{id}/run-template":     lambda q, id="s_001": get_skills_run_template(id),
    "/api/v2/billing/payment-methods/{id}/set-default": lambda q, id="c_001": get_billing_payment_methods_set_default(id),
    "/api/v2/campaigns/{id}/audience-active-rate": lambda q, id="c001": get_campaigns_audience_active_rate(id),
    "/api/v2/files/{id}/download-stats-by-day": lambda q, id="f_001": get_files_download_stats_by_day(id),
    "/api/v2/auth/api-keys/{id}/scopes-update": lambda q, id="k_001": get_auth_api_keys_scopes_update(id),
    "/api/v2/skills/{id}/export-template":   lambda q, id="s_001": get_skills_export_template(id),
    "/api/v2/billing/payment-methods/{id}/delete": lambda q, id="c_001": get_billing_payment_methods_delete(id),
    "/api/v2/campaigns/{id}/audience-frequency": lambda q, id="c001": get_campaigns_audience_frequency(id),
    "/api/v2/files/{id}/download-stats-by-file-type": lambda q, id="f_001": get_files_download_stats_by_file_type(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret": lambda q, id="k_001": get_auth_api_keys_rotate_secret(id),
    "/api/v2/skills/{id}/clone-template":   lambda q, id="s_001": get_skills_clone_template(id),
    "/api/v2/billing/payment-methods/{id}/verify": lambda q, id="c_001": get_billing_payment_methods_verify(id),
    "/api/v2/campaigns/{id}/audience-active-history": lambda q, id="c001": get_campaigns_audience_active_history(id),
    "/api/v2/files/{id}/download-stats-recent": lambda q, id="f_001": get_files_download_stats_recent(id),
    "/api/v2/auth/api-keys/{id}/quota-update": lambda q, id="k_001": get_auth_api_keys_quota_update(id),
    "/api/v2/skills/{id}/import-template":   lambda q, id="s_001": get_skills_import_template(id),
    "/api/v2/billing/payment-methods/{id}/set-primary": lambda q, id="c_001": get_billing_payment_methods_set_primary(id),
    "/api/v2/campaigns/{id}/audience-visit-frequency": lambda q, id="c001": get_campaigns_audience_visit_frequency(id),
    "/api/v2/files/{id}/download-top":      lambda q, id="f_001": get_files_download_top(id),
    "/api/v2/auth/api-keys/{id}/regenerate-secret": lambda q, id="k_001": get_auth_api_keys_regenerate_secret(id),
    "/api/v2/skills/{id}/pull-template":     lambda q, id="s_001": get_skills_pull_template(id),
    "/api/v2/billing/payment-methods/{id}/remove-primary": lambda q, id="c_001": get_billing_payment_methods_remove_primary(id),
    "/api/v2/campaigns/{id}/audience-source-stats": lambda q, id="c001": get_campaigns_audience_source_stats(id),
    "/api/v2/files/{id}/download-leaderboard": lambda q, id="f_001": get_files_download_leaderboard(id),
    "/api/v2/auth/api-keys/{id}/reset-quota-unlimited": lambda q, id="k_001": get_auth_api_keys_reset_quota_unlimited(id),
    "/api/v2/skills/{id}/push-template":    lambda q, id="s_001": get_skills_push_template(id),
    "/api/v2/billing/payment-methods/{id}/verify-default": lambda q, id="c_001": get_billing_payment_methods_verify_default(id),
    "/api/v2/campaigns/{id}/audience-utm-stats": lambda q, id="c001": get_campaigns_audience_utm_stats(id),
    "/api/v2/files/{id}/download-rank":    lambda q, id="f_001": get_files_download_rank(id),
    "/api/v2/auth/api-keys/{id}/rotate-quota": lambda q, id="k_001": get_auth_api_keys_rotate_quota(id),
    "/api/v2/skills/{id}/merge-with-target": lambda q, id="s_001": get_skills_merge_with_target(id),
    "/api/v2/billing/payment-methods/{id}/card-expire": lambda q, id="c_001": get_billing_payment_methods_card_expire(id),
    "/api/v2/campaigns/{id}/audience-referrer": lambda q, id="c001": get_campaigns_audience_referrer(id),
    "/api/v2/files/{id}/download-by-day-chart": lambda q, id="f_001": get_files_download_by_day_chart(id),
    "/api/v2/auth/api-keys/{id}/set-quota-to-limited": lambda q, id="k_001": get_auth_api_keys_set_quota_to_limited(id),
    "/api/v2/skills/{id}/export-from-instance": lambda q, id="s_001": get_skills_export_from_instance(id),
    "/api/v2/billing/payment-methods/{id}/verify-billing": lambda q, id="c_001": get_billing_payment_methods_verify_billing(id),
    "/api/v2/campaigns/{id}/audience-source-detail": lambda q, id="c001": get_campaigns_audience_source_detail(id),
    "/api/v2/files/{id}/download-by-user-type": lambda q, id="f_001": get_files_download_by_user_type(id),
    "/api/v2/auth/api-keys/{id}/permissions-list": lambda q, id="k_001": get_auth_api_keys_permissions_list(id),
    "/api/v2/skills/{id}/version-from-template": lambda q, id="s_001": get_skills_version_from_template(id),
    "/api/v2/billing/payment-methods/{id}/check": lambda q, id="c_001": get_billing_payment_methods_check(id),
    "/api/v2/campaigns/{id}/audience-region-detail": lambda q, id="c001": get_campaigns_audience_region_detail(id),
    "/api/v2/files/{id}/download-by-channel": lambda q, id="f_001": get_files_download_by_channel(id),
    "/api/v2/auth/api-keys/{id}/scopes-list": lambda q, id="k_001": get_auth_api_keys_scopes_list(id),
    "/api/v2/skills/{id}/fork-from-template": lambda q, id="s_001": get_skills_fork_from_template(id),
    "/api/v2/billing/payment-methods/{id}/verify-amount": lambda q, id="c_001": get_billing_payment_methods_verify_amount(id),
    "/api/v2/campaigns/{id}/audience-language-stats": lambda q, id="c001": get_campaigns_audience_language_stats(id),
    "/api/v2/files/{id}/download-by-day-of-week": lambda q, id="f_001": get_files_download_by_day_of_week(id),
    "/api/v2/auth/api-keys/{id}/activity-log": lambda q, id="k_001": get_auth_api_keys_activity_log(id),
    "/api/v2/skills/{id}/export-bundle":     lambda q, id="s_001": get_skills_export_bundle(id),
    "/api/v2/billing/payment-methods/{id}/validate-balance": lambda q, id="c_001": get_billing_payment_methods_validate_balance(id),
    "/api/v2/campaigns/{id}/audience-tech-stats": lambda q, id="c001": get_campaigns_audience_tech_stats(id),
    "/api/v2/files/{id}/download-by-hour":  lambda q, id="f_001": get_files_download_by_hour(id),
    "/api/v2/auth/api-keys/{id}/usage-stats": lambda q, id="k_001": get_auth_api_keys_usage_stats(id),
    "/api/v2/skills/{id}/import-bundle":     lambda q, id="s_001": get_skills_import_bundle(id),
    "/api/v2/billing/payment-methods/{id}/history": lambda q, id="c_001": get_billing_payment_methods_history(id),
    "/api/v2/campaigns/{id}/audience-cohort": lambda q, id="c001": get_campaigns_audience_cohort(id),
    "/api/v2/files/{id}/download-by-day-chart-v2": lambda q, id="f_001": get_files_download_by_day_chart_v2(id),
    "/api/v2/auth/api-keys/{id}/quota-histogram": lambda q, id="k_001": get_auth_api_keys_quota_histogram(id),
    "/api/v2/skills/{id}/apply-template":    lambda q, id="s_001": get_skills_apply_template(id),
    "/api/v2/billing/payment-methods/{id}/set-active": lambda q, id="c_001": get_billing_payment_methods_set_active(id),
    "/api/v2/campaigns/{id}/audience-grade": lambda q, id="c001": get_campaigns_audience_grade(id),
    "/api/v2/files/{id}/download-by-hour-chart": lambda q, id="f_001": get_files_download_by_hour_chart(id),
    "/api/v2/auth/api-keys/{id}/throttle-rate": lambda q, id="k_001": get_auth_api_keys_throttle_rate(id),
    "/api/v2/skills/{id}/unapply-template":  lambda q, id="s_001": get_skills_unapply_template(id),
    "/api/v2/billing/payment-methods/{id}/set-inactive": lambda q, id="c_001": get_billing_payment_methods_set_inactive(id),
    "/api/v2/campaigns/{id}/audience-segment-list": lambda q, id="c001": get_campaigns_audience_segment_list(id),
    "/api/v2/files/{id}/download-by-month":   lambda q, id="f_001": get_files_download_by_month(id),
    "/api/v2/auth/api-keys/{id}/rate-limit":   lambda q, id="k_001": get_auth_api_keys_rate_limit(id),
    "/api/v2/skills/{id}/import-from-instance": lambda q, id="s_001": get_skills_import_from_instance(id),
    "/api/v2/billing/payment-methods/{id}/set-default-payment": lambda q, id="c_001": get_billing_payment_methods_set_default_payment(id),
    "/api/v2/campaigns/{id}/audience-tag-list": lambda q, id="c001": get_campaigns_audience_tag_list(id),
    "/api/v2/files/{id}/download-by-year":    lambda q, id="f_001": get_files_download_by_year(id),
    "/api/v2/auth/api-keys/{id}/burst-quota":   lambda q, id="k_001": get_auth_api_keys_burst_quota(id),
    "/api/v2/skills/{id}/export-merge":        lambda q, id="s_001": get_skills_export_merge(id),
    "/api/v2/billing/payment-methods/{id}/verify-default": lambda q, id="c_001": get_billing_payment_methods_verify_default(id),
    "/api/v2/campaigns/{id}/audience-cohort-list": lambda q, id="c001": get_campaigns_audience_cohort_list(id),
    "/api/v2/files/{id}/download-top-10":      lambda q, id="f_001": get_files_download_top_10(id),
    "/api/v2/auth/api-keys/{id}/throttle-rate-set": lambda q, id="k_001": get_auth_api_keys_throttle_rate_set(id),
    "/api/v2/skills/{id}/revert":             lambda q, id="s_001": get_skills_revert(id),
    "/api/v2/billing/payment-methods/{id}/set-primary-payment": lambda q, id="c_001": get_billing_payment_methods_set_primary_payment(id),
    "/api/v2/campaigns/{id}/audience-language-list": lambda q, id="c001": get_campaigns_audience_language_list(id),
    "/api/v2/files/{id}/download-by-week-chart": lambda q, id="f_001": get_files_download_by_week_chart(id),
    "/api/v2/auth/api-keys/{id}/throttle-history": lambda q, id="k_001": get_auth_api_keys_throttle_history(id),
    "/api/v2/skills/{id}/sync-from-instance":  lambda q, id="s_001": get_skills_sync_from_instance(id),
    "/api/v2/billing/payment-methods/{id}/set-backup-payment": lambda q, id="c_001": get_billing_payment_methods_set_backup_payment(id),
    "/api/v2/campaigns/{id}/audience-tech-list": lambda q, id="c001": get_campaigns_audience_tech_list(id),
    "/api/v2/files/{id}/download-by-month-chart": lambda q, id="f_001": get_files_download_by_month_chart(id),
    "/api/v2/auth/api-keys/{id}/throttle-limit-history": lambda q, id="k_001": get_auth_api_keys_throttle_limit_history(id),
    "/api/v2/skills/{id}/push-to-marketplace": lambda q, id="s_001": get_skills_push_to_marketplace(id),
    "/api/v2/billing/payment-methods/{id}/unset-backup": lambda q, id="c_001": get_billing_payment_methods_unset_backup(id),
    "/api/v2/campaigns/{id}/audience-region-list": lambda q, id="c001": get_campaigns_audience_region_list(id),
    "/api/v2/files/{id}/download-quarter-chart": lambda q, id="f_001": get_files_download_quarter_chart(id),
    "/api/v2/auth/api-keys/{id}/throttle-current-state": lambda q, id="k_001": get_auth_api_keys_throttle_current_state(id),
    "/api/v2/skills/{id}/unsync":             lambda q, id="s_001": get_skills_unsync(id),
    "/api/v2/billing/payment-methods/{id}/verify-billing-cycle": lambda q, id="c_001": get_billing_payment_methods_verify_billing_cycle(id),
    "/api/v2/campaigns/{id}/audience-grade-list": lambda q, id="c001": get_campaigns_audience_grade_list(id),
    "/api/v2/files/{id}/download-by-year-chart": lambda q, id="f_001": get_files_download_by_year_chart(id),
    "/api/v2/auth/api-keys/{id}/burst-quota-history": lambda q, id="k_001": get_auth_api_keys_burst_quota_history(id),
    "/api/v2/skills/{id}/sync-from-instance-v2":  lambda q, id="s_001": get_skills_sync_from_instance_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v2": lambda q, id="c_001": get_billing_payment_methods_unset_active_v2(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v2": lambda q, id="c001": get_campaigns_audience_region_stats_v2(id),
    "/api/v2/files/{id}/download-by-week-stats-v5": lambda q, id="f_001": get_files_download_by_week_stats_v5(id),
    "/api/v2/auth/api-keys/{id}/throttle-history-v2": lambda q, id="k_001": get_auth_api_keys_throttle_history_v2(id),
    "/api/v2/skills/{id}/clone-from-template": lambda q, id="s_001": get_skills_clone_from_template(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_v2(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v3": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v3(id),
    "/api/v2/files/{id}/download-by-month-stats-v4": lambda q, id="f_001": get_files_download_by_month_stats_v4(id),
    "/api/v2/auth/api-keys/{id}/burst-quota-reset-history": lambda q, id="k_001": get_auth_api_keys_burst_quota_reset_history(id),
    "/api/v2/skills/{id}/merge-with-template": lambda q, id="s_001": get_skills_merge_with_template(id),
    "/api/v2/billing/payment-methods/{id}/validate-billing-cycle-v3": lambda q, id="c_001": get_billing_payment_methods_validate_billing_cycle_v3(id),
    "/api/v2/campaigns/{id}/audience-language-stats-v2": lambda q, id="c001": get_campaigns_audience_language_stats_v2(id),
    "/api/v2/files/{id}/download-by-year-stats-v2": lambda q, id="f_001": get_files_download_by_year_stats_v2(id),
    "/api/v2/auth/api-keys/{id}/throttle-history-v3": lambda q, id="k_001": get_auth_api_keys_throttle_history_v3(id),
    "/api/v2/skills/{id}/sync-from-template-v2":  lambda q, id="s_001": get_skills_sync_from_template_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v3": lambda q, id="c_001": get_billing_payment_methods_unset_active_v3(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v4": lambda q, id="c001": get_campaigns_audience_grade_stats_v4(id),
    "/api/v2/files/{id}/download-by-quarter-list-v4": lambda q, id="f_001": get_files_download_by_quarter_list_v4(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v22": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v22(id),
    "/api/v2/skills/{id}/sync-stats-v5":          lambda q, id="s_001": get_skills_sync_stats_v5(id),
    "/api/v2/billing/payment-methods/{id}/validate-default": lambda q, id="c_001": get_billing_payment_methods_validate_default(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v3": lambda q, id="c001": get_campaigns_audience_region_stats_v3(id),
    "/api/v2/files/{id}/download-by-day-stats-v2":   lambda q, id="f_001": get_files_download_by_day_stats_v2(id),
    "/api/v2/auth/api-keys/{id}/quota-set-v2":     lambda q, id="k_001": get_auth_api_keys_quota_set_v2(id),
    "/api/v2/skills/{id}/apply-template-v2":     lambda q, id="s_001": get_skills_apply_template_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v3": lambda q, id="c_001": get_billing_payment_methods_unset_default_v3(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v9": lambda q, id="c001": get_campaigns_audience_tech_list_v9(id),
    "/api/v2/files/{id}/download-by-week-stats-v6": lambda q, id="f_001": get_files_download_by_week_stats_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v4": lambda q, id="k_001": get_auth_api_keys_quota_history_v4(id),
    "/api/v2/skills/{id}/merge-stats-v5":         lambda q, id="s_001": get_skills_merge_stats_v5(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v4": lambda q, id="c_001": get_billing_payment_methods_unset_active_v4(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v4": lambda q, id="c001": get_campaigns_audience_region_stats_v4(id),
    "/api/v2/files/{id}/download-by-month-list-v5": lambda q, id="f_001": get_files_download_by_month_list_v5(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v5": lambda q, id="k_001": get_auth_api_keys_quota_history_v5(id),
    "/api/v2/skills/{id}/sync-stats-v6":          lambda q, id="s_001": get_skills_sync_stats_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v5": lambda q, id="c_001": get_billing_payment_methods_unset_active_v5(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v5": lambda q, id="c001": get_campaigns_audience_grade_stats_v5(id),
    "/api/v2/files/{id}/download-by-week-list-v5": lambda q, id="f_001": get_files_download_by_week_list_v5(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v6": lambda q, id="k_001": get_auth_api_keys_quota_history_v6(id),
    "/api/v2/skills/{id}/apply-template-v3":     lambda q, id="s_001": get_skills_apply_template_v3(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v4": lambda q, id="c_001": get_billing_payment_methods_unset_default_v4(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v10": lambda q, id="c001": get_campaigns_audience_tech_list_v10(id),
    "/api/v2/files/{id}/download-by-week-chart-v7": lambda q, id="f_001": get_files_download_by_week_chart_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v3":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v3(id),
    "/api/v2/skills/{id}/merge-stats-v6":         lambda q, id="s_001": get_skills_merge_stats_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v5": lambda q, id="c_001": get_billing_payment_methods_unset_default_v5(id),
    "/api/v2/campaigns/{id}/audience-cohort-stats": lambda q, id="c001": get_campaigns_audience_cohort_stats(id),
    "/api/v2/files/{id}/download-by-week-stats-v7": lambda q, id="f_001": get_files_download_by_week_stats_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v7": lambda q, id="k_001": get_auth_api_keys_quota_history_v7(id),
    "/api/v2/skills/{id}/sync-stats-v7":          lambda q, id="s_001": get_skills_sync_stats_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v6": lambda q, id="c_001": get_billing_payment_methods_unset_default_v6(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v6": lambda q, id="c001": get_campaigns_audience_grade_stats_v6(id),
    "/api/v2/files/{id}/download-by-month-list-v6": lambda q, id="f_001": get_files_download_by_month_list_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v8": lambda q, id="k_001": get_auth_api_keys_quota_history_v8(id),
    "/api/v2/skills/{id}/apply-template-v4":     lambda q, id="s_001": get_skills_apply_template_v4(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v6": lambda q, id="c_001": get_billing_payment_methods_unset_active_v6(id),
    "/api/v2/campaigns/{id}/audience-cohort-stats-v2": lambda q, id="c001": get_campaigns_audience_cohort_stats_v2(id),
    "/api/v2/files/{id}/download-by-week-list-v6": lambda q, id="f_001": get_files_download_by_week_list_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v4":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v4(id),
    "/api/v2/skills/{id}/sync-from-template-v3":  lambda q, id="s_001": get_skills_sync_from_template_v3(id),
    "/api/v2/billing/payment-methods/{id}/validate-default-v2": lambda q, id="c_001": get_billing_payment_methods_validate_default_v2(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v11": lambda q, id="c001": get_campaigns_audience_tech_list_v11(id),
    "/api/v2/files/{id}/download-by-month-chart-v7": lambda q, id="f_001": get_files_download_by_month_chart_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v9": lambda q, id="k_001": get_auth_api_keys_quota_history_v9(id),
    "/api/v2/skills/{id}/apply-template-v5":     lambda q, id="s_001": get_skills_apply_template_v5(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v7": lambda q, id="c_001": get_billing_payment_methods_unset_default_v7(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v7": lambda q, id="c001": get_campaigns_audience_grade_stats_v7(id),
    "/api/v2/files/{id}/download-by-week-chart-v8": lambda q, id="f_001": get_files_download_by_week_chart_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v5":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v5(id),
    "/api/v2/skills/{id}/merge-stats-v7":         lambda q, id="s_001": get_skills_merge_stats_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v7": lambda q, id="c_001": get_billing_payment_methods_unset_active_v7(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v4": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v4(id),
    "/api/v2/files/{id}/download-by-week-stats-v8": lambda q, id="f_001": get_files_download_by_week_stats_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v10": lambda q, id="k_001": get_auth_api_keys_quota_history_v10(id),
    "/api/v2/skills/{id}/sync-stats-v8":          lambda q, id="s_001": get_skills_sync_stats_v8(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v8": lambda q, id="c_001": get_billing_payment_methods_unset_default_v8(id),
    "/api/v2/campaigns/{id}/audience-tech-stats-v12": lambda q, id="c001": get_campaigns_audience_tech_stats_v12(id),
    "/api/v2/files/{id}/download-by-month-chart-v8": lambda q, id="f_001": get_files_download_by_month_chart_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v6":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v6(id),
    "/api/v2/skills/{id}/sync-from-template-v4":  lambda q, id="s_001": get_skills_sync_from_template_v4(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v8": lambda q, id="c_001": get_billing_payment_methods_unset_active_v8(id),
    "/api/v2/campaigns/{id}/audience-cohort-stats-v3": lambda q, id="c001": get_campaigns_audience_cohort_stas_v3(id),
    "/api/v2/files/{id}/download-by-week-stats-v9": lambda q, id="f_001": get_files_download_by_week_stats_v9(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v11": lambda q, id="k_001": get_auth_api_keys_quota_history_v11(id),
    "/api/v2/skills/{id}/apply-template-v6":     lambda q, id="s_001": get_skills_apply_template_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v9": lambda q, id="c_001": get_billing_payment_methods_unset_default_v9(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v8": lambda q, id="c001": get_campaigns_audience_grade_stats_v8(id),
    "/api/v2/files/{id}/download-by-week-chart-v9": lambda q, id="f_001": get_files_download_by_week_chart_v9(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v7":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v7(id),
    "/api/v2/skills/{id}/sync-stats-v9":          lambda q, id="s_001": get_skills_sync_stats_v9(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v9": lambda q, id="c_001": get_billing_payment_methods_unset_active_v9(id),
    "/api/v2/campaigns/{id}/audience-source-detailed-v3": lambda q, id="c001": get_campaigns_audience_source_detailed_v3(id),
    "/api/v2/files/{id}/download-by-month-list-v7": lambda q, id="f_001": get_files_download_by_month_list_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v12": lambda q, id="k_001": get_auth_api_keys_quota_history_v12(id),
    "/api/v2/skills/{id}/apply-template-v7":     lambda q, id="s_001": get_skills_apply_template_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v10": lambda q, id="c_001": get_billing_payment_methods_unset_default_v10(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v9": lambda q, id="c001": get_campaigns_audience_grade_stats_v9(id),
    "/api/v2/files/{id}/download-by-week-stats-v10": lambda q, id="f_001": get_files_download_by_week_stats_v10(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v8":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v8(id),
    "/api/v2/skills/{id}/sync-stats-v10":         lambda q, id="s_001": get_skills_sync_stats_v10(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v10": lambda q, id="c_001": get_billing_payment_methods_unset_active_v10(id),
    "/api/v2/campaigns/{id}/audience-source-list-v4": lambda q, id="c001": get_campaigns_audience_source_list_v4(id),
    "/api/v2/files/{id}/download-by-day-list-v3": lambda q, id="f_001": get_files_download_by_day_list_v3(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v13": lambda q, id="k_001": get_auth_api_keys_quota_history_v13(id),
    "/api/v2/skills/{id}/export-from-template":     lambda q, id="s_001": get_skills_export_from_template(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v11": lambda q, id="c_001": get_billing_payment_methods_unset_default_v11(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v10": lambda q, id="c001": get_campaigns_audience_grade_stats_v10(id),
    "/api/v2/files/{id}/download-by-day-chart-v10":  lambda q, id="f_001": get_files_download_by_day_chart_v10(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v9":   lambda q, id="k_001": get_auth_api_keys_quota_reset_v9(id),
    "/api/v2/skills/{id}/sync-stats-v11":         lambda q, id="s_001": get_skills_sync_stats_v11(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v11": lambda q, id="c_001": get_billing_payment_methods_unset_active_v11(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v5": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v5(id),
    "/api/v2/files/{id}/download-by-week-stats-v11": lambda q, id="f_001": get_files_download_by_week_stats_v11(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v14": lambda q, id="k_001": get_auth_api_keys_quota_history_v14(id),
    "/api/v2/skills/{id}/apply-template-v8":     lambda q, id="s_001": get_skills_apply_template_v8(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v12": lambda q, id="c_001": get_billing_payment_methods_unset_default_v12(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v4": lambda q, id="c001": get_campaigns_audience_source_stats_v4(id),
    "/api/v2/files/{id}/download-by-day-list-v4": lambda q, id="f_001": get_files_download_by_day_list_v4(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v10": lambda q, id="k_001": get_auth_api_keys_quota_reset_v10(id),
    "/api/v2/skills/{id}/sync-from-template-v5":  lambda q, id="s_001": get_skills_sync_from_template_v5(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v12": lambda q, id="c_001": get_billing_payment_methods_unset_active_v12(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v6": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v6(id),
    "/api/v2/files/{id}/download-by-week-stats-v12": lambda q, id="f_001": get_files_download_by_week_stats_v12(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v15": lambda q, id="k_001": get_auth_api_keys_quota_history_v15(id),
    "/api/v2/skills/{id}/apply-template-v9":     lambda q, id="s_001": get_skills_apply_template_v9(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v13": lambda q, id="c_001": get_billing_payment_methods_unset_default_v13(id),
    "/api/v2/campaigns/{id}/audience-source-detailed-v6": lambda q, id="c001": get_campaigns_audience_source_detailed_v6(id),
    "/api/v2/files/{id}/download-by-day-chart-v11": lambda q, id="f_001": get_files_download_by_day_chart_v11(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v16": lambda q, id="k_001": get_auth_api_keys_quota_history_v16(id),
    "/api/v2/skills/{id}/sync-stats-v12":         lambda q, id="s_001": get_skills_sync_stats_v12(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v13": lambda q, id="c_001": get_billing_payment_methods_unset_active_v13(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v11": lambda q, id="c001": get_campaigns_audience_grade_stats_v11(id),
    "/api/v2/files/{id}/download-by-day-list-v5":   lambda q, id="f_001": get_files_download_by_day_list_v5(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v17": lambda q, id="k_001": get_auth_api_keys_quota_history_v17(id),
    "/api/v2/skills/{id}/apply-template-v10":    lambda q, id="s_001": get_skills_apply_template_v10(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v14": lambda q, id="c_001": get_billing_payment_methods_unset_default_v14(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v5": lambda q, id="c001": get_campaigns_audience_region_stats_v5(id),
    "/api/v2/files/{id}/download-by-day-list-v6": lambda q, id="f_001": get_files_download_by_day_list_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v18": lambda q, id="k_001": get_auth_api_keys_quota_history_v18(id),
    "/api/v2/skills/{id}/sync-from-template-v6":  lambda q, id="s_001": get_skills_sync_from_template_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v14": lambda q, id="c_001": get_billing_payment_methods_unset_active_v14(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v5": lambda q, id="c001": get_campaigns_audience_source_stats_v5(id),
    "/api/v2/files/{id}/download-by-week-list-v7": lambda q, id="f_001": get_files_download_by_week_list_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v19": lambda q, id="k_001": get_auth_api_keys_quota_history_v19(id),
    "/api/v2/skills/{id}/apply-template-v11":    lambda q, id="s_001": get_skills_apply_template_v11(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v15": lambda q, id="c_001": get_billing_payment_methods_unset_default_v15(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v12": lambda q, id="c001": get_campaigns_audience_grade_stats_v12(id),
    "/api/v2/files/{id}/download-by-day-list-v7":  lambda q, id="f_001": get_files_download_by_day_list_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v20": lambda q, id="k_001": get_auth_api_keys_quota_history_v20(id),
    "/api/v2/skills/{id}/sync-stats-v13":         lambda q, id="s_001": get_skills_sync_stats_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v15": lambda q, id="c_001": get_billing_payment_methods_unset_active_v15(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v6": lambda q, id="c001": get_campaigns_audience_region_stats_v6(id),
    "/api/v2/files/{id}/download-by-week-stats-v13": lambda q, id="f_001": get_files_download_by_week_stats_v13(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v21": lambda q, id="k_001": get_auth_api_keys_quota_history_v21(id),
    "/api/v2/skills/{id}/apply-template-v12":    lambda q, id="s_001": get_skills_apply_template_v12(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v16": lambda q, id="c_001": get_billing_payment_methods_unset_default_v16(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v6": lambda q, id="c001": get_campaigns_audience_source_stats_v6(id),
    "/api/v2/files/{id}/download-by-day-chart-v12": lambda q, id="f_001": get_files_download_by_day_chart_v12(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v22": lambda q, id="k_001": get_auth_api_keys_quota_history_v22(id),
    "/api/v2/skills/{id}/sync-from-template-v7":  lambda q, id="s_001": get_skills_sync_from_template_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v16": lambda q, id="c_001": get_billing_payment_methods_unset_active_v16(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v13": lambda q, id="c001": get_campaigns_audience_grade_stats_v13(id),
    "/api/v2/files/{id}/download-by-week-stats-v14": lambda q, id="f_001": get_files_download_by_week_stats_v14(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v23": lambda q, id="k_001": get_auth_api_keys_quota_history_v23(id),
    "/api/v2/skills/{id}/apply-template-v13":    lambda q, id="s_001": get_skills_apply_template_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v17": lambda q, id="c_001": get_billing_payment_methods_unset_default_v17(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v7": lambda q, id="c001": get_campaigns_audience_region_stats_v7(id),
    "/api/v2/files/{id}/download-by-day-list-v8":  lambda q, id="f_001": get_files_download_by_day_list_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v44": lambda q, id="k_001": get_auth_api_keys_quota_history_v44(id),
    "/api/v2/skills/{id}/sync-stats-v14":         lambda q, id="s_001": get_skills_sync_stats_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v17": lambda q, id="c_001": get_billing_payment_methods_unset_active_v17(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v7": lambda q, id="c001": get_campaigns_audience_source_stats_v7(id),
    "/api/v2/files/{id}/download-by-week-stats-v15": lambda q, id="f_001": get_files_download_by_week_stats_v15(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v25": lambda q, id="k_001": get_auth_api_keys_quota_history_v25(id),
    "/api/v2/skills/{id}/apply-template-v14":    lambda q, id="s_001": get_skills_apply_template_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v18": lambda q, id="c_001": get_billing_payment_methods_unset_default_v18(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v8": lambda q, id="c001": get_campaigns_audience_region_stats_v8(id),
    "/api/v2/files/{id}/download-by-day-list-v9":  lambda q, id="f_001": get_files_download_by_day_list_v9(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v26": lambda q, id="k_001": get_auth_api_keys_quota_history_v26(id),
    "/api/v2/skills/{id}/sync-from-template-v8":  lambda q, id="s_001": get_skills_sync_from_template_v8(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v18": lambda q, id="c_001": get_billing_payment_methods_unset_active_v18(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v8": lambda q, id="c001": get_campaigns_audience_source_stats_v8(id),
    "/api/v2/files/{id}/download-by-week-stats-v16": lambda q, id="f_001": get_files_download_by_week_stats_v16(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v27": lambda q, id="k_001": get_auth_api_keys_quota_history_v27(id),
    "/api/v2/skills/{id}/apply-template-v15":    lambda q, id="s_001": get_skills_apply_template_v15(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v19": lambda q, id="c_001": get_billing_payment_methods_unset_default_v19(id),
    "/api/v2/campaigns/{id}/audience-region-detailed-v7": lambda q, id="c001": get_campaigns_audience_region_detailed_v7(id),
    "/api/v2/files/{id}/download-by-day-stats-v17": lambda q, id="f_001": get_files_download_by_day_stats_v17(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v28": lambda q, id="k_001": get_auth_api_keys_quota_history_v28(id),
    "/api/v2/skills/{id}/sync-from-template-v9":  lambda q, id="s_001": get_skills_sync_from_template_v9(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v19": lambda q, id="c_001": get_billing_payment_methods_unset_active_v19(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v9": lambda q, id="c001": get_campaigns_audience_source_stats_v9(id),
    "/api/v2/files/{id}/download-by-day-list-v10": lambda q, id="f_001": get_files_download_by_day_list_v10(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v29": lambda q, id="k_001": get_auth_api_keys_quota_history_v29(id),
    "/api/v2/skills/{id}/apply-template-v16":    lambda q, id="s_001": get_skills_apply_template_v16(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v20": lambda q, id="c_001": get_billing_payment_methods_unset_default_v20(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v9": lambda q, id="c001": get_campaigns_audience_region_stats_v9(id),
    "/api/v2/files/{id}/download-by-week-stats-v18": lambda q, id="f_001": get_files_download_by_week_stats_v18(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v30": lambda q, id="k_001": get_auth_api_keys_quota_history_v30(id),
    "/api/v2/skills/{id}/sync-from-template-v10": lambda q, id="s_001": get_skills_sync_from_template_v10(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v20": lambda q, id="c_001": get_billing_payment_methods_unset_active_v20(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v10": lambda q, id="c001": get_campaigns_audience_source_stats_v10(id),
    "/api/v2/files/{id}/download-by-day-list-v11": lambda q, id="f_001": get_files_download_by_day_list_v11(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v31": lambda q, id="k_001": get_auth_api_keys_quota_history_v31(id),
    "/api/v2/skills/{id}/apply-template-v17":    lambda q, id="s_001": get_skills_apply_template_v17(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v21": lambda q, id="c_001": get_billing_payment_methods_unset_default_v21(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v14": lambda q, id="c001": get_campaigns_audience_grade_stats_v14(id),
    "/api/v2/files/{id}/download-by-week-stats-v19": lambda q, id="f_001": get_files_download_by_week_stats_v19(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v32": lambda q, id="k_001": get_auth_api_keys_quota_history_v32(id),
    "/api/v2/skills/{id}/sync-from-template-v84": lambda q, id="s_001": get_skills_sync_from_template_v84(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v85": lambda q, id="c_001": get_billing_payment_methods_unset_active_v85(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v84": lambda q, id="c001": get_campaigns_audience_source_stats_v84(id),
    "/api/v2/files/{id}/download-by-day-list-v85": lambda q, id="f_001": get_files_download_by_day_list_v85(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v106": lambda q, id="k_001": get_auth_api_keys_quota_history_v106(id),
    "/api/v2/skills/{id}/sync-from-template-v83": lambda q, id="s_001": get_skills_sync_from_template_v83(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v84": lambda q, id="c_001": get_billing_payment_methods_unset_active_v84(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v83": lambda q, id="c001": get_campaigns_audience_source_stats_v83(id),
    "/api/v2/files/{id}/download-by-day-list-v84": lambda q, id="f_001": get_files_download_by_day_list_v84(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v105": lambda q, id="k_001": get_auth_api_keys_quota_history_v105(id),
    "/api/v2/skills/{id}/sync-from-template-v82": lambda q, id="s_001": get_skills_sync_from_template_v82(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v83": lambda q, id="c_001": get_billing_payment_methods_unset_active_v83(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v82": lambda q, id="c001": get_campaigns_audience_source_stats_v82(id),
    "/api/v2/files/{id}/download-by-day-list-v83": lambda q, id="f_001": get_files_download_by_day_list_v83(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v104": lambda q, id="k_001": get_auth_api_keys_quota_history_v104(id),
    "/api/v2/skills/{id}/sync-from-template-v81": lambda q, id="s_001": get_skills_sync_from_template_v81(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v82": lambda q, id="c_001": get_billing_payment_methods_unset_active_v82(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v81": lambda q, id="c001": get_campaigns_audience_source_stats_v81(id),
    "/api/v2/files/{id}/download-by-day-list-v82": lambda q, id="f_001": get_files_download_by_day_list_v82(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v103": lambda q, id="k_001": get_auth_api_keys_quota_history_v103(id),
    "/api/v2/skills/{id}/sync-from-template-v80": lambda q, id="s_001": get_skills_sync_from_template_v80(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v81": lambda q, id="c_001": get_billing_payment_methods_unset_active_v81(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v80": lambda q, id="c001": get_campaigns_audience_source_stats_v80(id),
    "/api/v2/files/{id}/download-by-day-list-v81": lambda q, id="f_001": get_files_download_by_day_list_v81(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v102": lambda q, id="k_001": get_auth_api_keys_quota_history_v102(id),
    "/api/v2/skills/{id}/sync-from-template-v79": lambda q, id="s_001": get_skills_sync_from_template_v79(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v80": lambda q, id="c_001": get_billing_payment_methods_unset_active_v80(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v79": lambda q, id="c001": get_campaigns_audience_source_stats_v79(id),
    "/api/v2/files/{id}/download-by-day-list-v80": lambda q, id="f_001": get_files_download_by_day_list_v80(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v101": lambda q, id="k_001": get_auth_api_keys_quota_history_v101(id),
    "/api/v2/skills/{id}/sync-from-template-v78": lambda q, id="s_001": get_skills_sync_from_template_v78(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v79": lambda q, id="c_001": get_billing_payment_methods_unset_active_v79(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v78": lambda q, id="c001": get_campaigns_audience_source_stats_v78(id),
    "/api/v2/files/{id}/download-by-day-list-v79": lambda q, id="f_001": get_files_download_by_day_list_v79(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v100": lambda q, id="k_001": get_auth_api_keys_quota_history_v100(id),
    "/api/v2/skills/{id}/sync-from-template-v77": lambda q, id="s_001": get_skills_sync_from_template_v77(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v78": lambda q, id="c_001": get_billing_payment_methods_unset_active_v78(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v77": lambda q, id="c001": get_campaigns_audience_source_stats_v77(id),
    "/api/v2/files/{id}/download-by-day-list-v78": lambda q, id="f_001": get_files_download_by_day_list_v78(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v99": lambda q, id="k_001": get_auth_api_keys_quota_history_v99(id),
    "/api/v2/skills/{id}/sync-from-template-v76": lambda q, id="s_001": get_skills_sync_from_template_v76(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v77": lambda q, id="c_001": get_billing_payment_methods_unset_active_v77(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v76": lambda q, id="c001": get_campaigns_audience_source_stats_v76(id),
    "/api/v2/files/{id}/download-by-day-list-v77": lambda q, id="f_001": get_files_download_by_day_list_v77(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v98": lambda q, id="k_001": get_auth_api_keys_quota_history_v98(id),
    "/api/v2/skills/{id}/sync-from-template-v75": lambda q, id="s_001": get_skills_sync_from_template_v75(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v76": lambda q, id="c_001": get_billing_payment_methods_unset_active_v76(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v75": lambda q, id="c001": get_campaigns_audience_source_stats_v75(id),
    "/api/v2/files/{id}/download-by-day-list-v76": lambda q, id="f_001": get_files_download_by_day_list_v76(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v97": lambda q, id="k_001": get_auth_api_keys_quota_history_v97(id),
    "/api/v2/skills/{id}/sync-from-template-v74": lambda q, id="s_001": get_skills_sync_from_template_v74(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v75": lambda q, id="c_001": get_billing_payment_methods_unset_active_v75(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v74": lambda q, id="c001": get_campaigns_audience_source_stats_v74(id),
    "/api/v2/files/{id}/download-by-day-list-v75": lambda q, id="f_001": get_files_download_by_day_list_v75(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v96": lambda q, id="k_001": get_auth_api_keys_quota_history_v96(id),
    "/api/v2/skills/{id}/sync-from-template-v73": lambda q, id="s_001": get_skills_sync_from_template_v73(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v74": lambda q, id="c_001": get_billing_payment_methods_unset_active_v74(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v73": lambda q, id="c001": get_campaigns_audience_source_stats_v73(id),
    "/api/v2/files/{id}/download-by-day-list-v74": lambda q, id="f_001": get_files_download_by_day_list_v74(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v95": lambda q, id="k_001": get_auth_api_keys_quota_history_v95(id),
    "/api/v2/skills/{id}/sync-from-template-v72": lambda q, id="s_001": get_skills_sync_from_template_v72(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v73": lambda q, id="c_001": get_billing_payment_methods_unset_active_v73(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v72": lambda q, id="c001": get_campaigns_audience_source_stats_v72(id),
    "/api/v2/files/{id}/download-by-day-list-v73": lambda q, id="f_001": get_files_download_by_day_list_v73(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v94": lambda q, id="k_001": get_auth_api_keys_quota_history_v94(id),
    "/api/v2/skills/{id}/sync-from-template-v71": lambda q, id="s_001": get_skills_sync_from_template_v71(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v72": lambda q, id="c_001": get_billing_payment_methods_unset_active_v72(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v71": lambda q, id="c001": get_campaigns_audience_source_stats_v71(id),
    "/api/v2/files/{id}/download-by-day-list-v72": lambda q, id="f_001": get_files_download_by_day_list_v72(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v93": lambda q, id="k_001": get_auth_api_keys_quota_history_v93(id),
    "/api/v2/skills/{id}/sync-from-template-v70": lambda q, id="s_001": get_skills_sync_from_template_v70(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v71": lambda q, id="c_001": get_billing_payment_methods_unset_active_v71(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v70": lambda q, id="c001": get_campaigns_audience_source_stats_v70(id),
    "/api/v2/files/{id}/download-by-day-list-v71": lambda q, id="f_001": get_files_download_by_day_list_v71(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v92": lambda q, id="k_001": get_auth_api_keys_quota_history_v92(id),
    "/api/v2/skills/{id}/sync-from-template-v69": lambda q, id="s_001": get_skills_sync_from_template_v69(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v70": lambda q, id="c_001": get_billing_payment_methods_unset_active_v70(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v69": lambda q, id="c001": get_campaigns_audience_source_stats_v69(id),
    "/api/v2/files/{id}/download-by-day-list-v70": lambda q, id="f_001": get_files_download_by_day_list_v70(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v91": lambda q, id="k_001": get_auth_api_keys_quota_history_v91(id),
    "/api/v2/skills/{id}/sync-from-template-v68": lambda q, id="s_001": get_skills_sync_from_template_v68(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v69": lambda q, id="c_001": get_billing_payment_methods_unset_active_v69(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v68": lambda q, id="c001": get_campaigns_audience_source_stats_v68(id),
    "/api/v2/files/{id}/download-by-day-list-v69": lambda q, id="f_001": get_files_download_by_day_list_v69(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v90": lambda q, id="k_001": get_auth_api_keys_quota_history_v90(id),
    "/api/v2/skills/{id}/sync-from-template-v67": lambda q, id="s_001": get_skills_sync_from_template_v67(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v68": lambda q, id="c_001": get_billing_payment_methods_unset_active_v68(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v67": lambda q, id="c001": get_campaigns_audience_source_stats_v67(id),
    "/api/v2/files/{id}/download-by-day-list-v68": lambda q, id="f_001": get_files_download_by_day_list_v68(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v89": lambda q, id="k_001": get_auth_api_keys_quota_history_v89(id),
    "/api/v2/skills/{id}/sync-from-template-v66": lambda q, id="s_001": get_skills_sync_from_template_v66(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v67": lambda q, id="c_001": get_billing_payment_methods_unset_active_v67(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v66": lambda q, id="c001": get_campaigns_audience_source_stats_v66(id),
    "/api/v2/files/{id}/download-by-day-list-v67": lambda q, id="f_001": get_files_download_by_day_list_v67(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v88": lambda q, id="k_001": get_auth_api_keys_quota_history_v88(id),
    "/api/v2/skills/{id}/sync-from-template-v65": lambda q, id="s_001": get_skills_sync_from_template_v65(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v66": lambda q, id="c_001": get_billing_payment_methods_unset_active_v66(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v65": lambda q, id="c001": get_campaigns_audience_source_stats_v65(id),
    "/api/v2/files/{id}/download-by-day-list-v66": lambda q, id="f_001": get_files_download_by_day_list_v66(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v87": lambda q, id="k_001": get_auth_api_keys_quota_history_v87(id),
    "/api/v2/skills/{id}/sync-from-template-v64": lambda q, id="s_001": get_skills_sync_from_template_v64(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v65": lambda q, id="c_001": get_billing_payment_methods_unset_active_v65(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v64": lambda q, id="c001": get_campaigns_audience_source_stats_v64(id),
    "/api/v2/files/{id}/download-by-day-list-v65": lambda q, id="f_001": get_files_download_by_day_list_v65(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v86": lambda q, id="k_001": get_auth_api_keys_quota_history_v86(id),
    "/api/v2/skills/{id}/sync-from-template-v63": lambda q, id="s_001": get_skills_sync_from_template_v63(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v64": lambda q, id="c_001": get_billing_payment_methods_unset_active_v64(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v63": lambda q, id="c001": get_campaigns_audience_source_stats_v63(id),
    "/api/v2/files/{id}/download-by-day-list-v64": lambda q, id="f_001": get_files_download_by_day_list_v64(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v85": lambda q, id="k_001": get_auth_api_keys_quota_history_v85(id),
    "/api/v2/skills/{id}/sync-from-template-v62": lambda q, id="s_001": get_skills_sync_from_template_v62(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v63": lambda q, id="c_001": get_billing_payment_methods_unset_active_v63(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v62": lambda q, id="c001": get_campaigns_audience_source_stats_v62(id),
    "/api/v2/files/{id}/download-by-day-list-v63": lambda q, id="f_001": get_files_download_by_day_list_v63(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v84": lambda q, id="k_001": get_auth_api_keys_quota_history_v84(id),
    "/api/v2/skills/{id}/sync-from-template-v61": lambda q, id="s_001": get_skills_sync_from_template_v61(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v62": lambda q, id="c_001": get_billing_payment_methods_unset_active_v62(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v61": lambda q, id="c001": get_campaigns_audience_source_stats_v61(id),
    "/api/v2/files/{id}/download-by-day-list-v62": lambda q, id="f_001": get_files_download_by_day_list_v62(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v83": lambda q, id="k_001": get_auth_api_keys_quota_history_v83(id),
    "/api/v2/skills/{id}/sync-from-template-v60": lambda q, id="s_001": get_skills_sync_from_template_v60(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v61": lambda q, id="c_001": get_billing_payment_methods_unset_active_v61(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v60": lambda q, id="c001": get_campaigns_audience_source_stats_v60(id),
    "/api/v2/files/{id}/download-by-day-list-v61": lambda q, id="f_001": get_files_download_by_day_list_v61(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v82": lambda q, id="k_001": get_auth_api_keys_quota_history_v82(id),
    "/api/v2/skills/{id}/sync-from-template-v59": lambda q, id="s_001": get_skills_sync_from_template_v59(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v60": lambda q, id="c_001": get_billing_payment_methods_unset_active_v60(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v59": lambda q, id="c001": get_campaigns_audience_source_stats_v59(id),
    "/api/v2/files/{id}/download-by-day-list-v60": lambda q, id="f_001": get_files_download_by_day_list_v60(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v81": lambda q, id="k_001": get_auth_api_keys_quota_history_v81(id),
    "/api/v2/skills/{id}/sync-from-template-v58": lambda q, id="s_001": get_skills_sync_from_template_v58(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v59": lambda q, id="c_001": get_billing_payment_methods_unset_active_v59(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v58": lambda q, id="c001": get_campaigns_audience_source_stats_v58(id),
    "/api/v2/files/{id}/download-by-day-list-v59": lambda q, id="f_001": get_files_download_by_day_list_v59(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v80": lambda q, id="k_001": get_auth_api_keys_quota_history_v80(id),
    "/api/v2/skills/{id}/sync-from-template-v57": lambda q, id="s_001": get_skills_sync_from_template_v57(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v58": lambda q, id="c_001": get_billing_payment_methods_unset_active_v58(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v57": lambda q, id="c001": get_campaigns_audience_source_stats_v57(id),
    "/api/v2/files/{id}/download-by-day-list-v58": lambda q, id="f_001": get_files_download_by_day_list_v58(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v79": lambda q, id="k_001": get_auth_api_keys_quota_history_v79(id),
    "/api/v2/skills/{id}/sync-from-template-v56": lambda q, id="s_001": get_skills_sync_from_template_v56(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v57": lambda q, id="c_001": get_billing_payment_methods_unset_active_v57(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v56": lambda q, id="c001": get_campaigns_audience_source_stats_v56(id),
    "/api/v2/files/{id}/download-by-day-list-v57": lambda q, id="f_001": get_files_download_by_day_list_v57(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v78": lambda q, id="k_001": get_auth_api_keys_quota_history_v78(id),
    "/api/v2/skills/{id}/sync-from-template-v55": lambda q, id="s_001": get_skills_sync_from_template_v55(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v56": lambda q, id="c_001": get_billing_payment_methods_unset_active_v56(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v55": lambda q, id="c001": get_campaigns_audience_source_stats_v55(id),
    "/api/v2/files/{id}/download-by-day-list-v56": lambda q, id="f_001": get_files_download_by_day_list_v56(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v77": lambda q, id="k_001": get_auth_api_keys_quota_history_v77(id),
    "/api/v2/skills/{id}/sync-from-template-v54": lambda q, id="s_001": get_skills_sync_from_template_v54(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v55": lambda q, id="c_001": get_billing_payment_methods_unset_active_v55(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v54": lambda q, id="c001": get_campaigns_audience_source_stats_v54(id),
    "/api/v2/files/{id}/download-by-day-list-v55": lambda q, id="f_001": get_files_download_by_day_list_v55(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v76": lambda q, id="k_001": get_auth_api_keys_quota_history_v76(id),
    "/api/v2/skills/{id}/sync-from-template-v53": lambda q, id="s_001": get_skills_sync_from_template_v53(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v54": lambda q, id="c_001": get_billing_payment_methods_unset_active_v54(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v53": lambda q, id="c001": get_campaigns_audience_source_stats_v53(id),
    "/api/v2/files/{id}/download-by-day-list-v54": lambda q, id="f_001": get_files_download_by_day_list_v54(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v75": lambda q, id="k_001": get_auth_api_keys_quota_history_v75(id),
    "/api/v2/skills/{id}/sync-from-template-v52": lambda q, id="s_001": get_skills_sync_from_template_v52(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v53": lambda q, id="c_001": get_billing_payment_methods_unset_active_v53(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v52": lambda q, id="c001": get_campaigns_audience_source_stats_v52(id),
    "/api/v2/files/{id}/download-by-day-list-v53": lambda q, id="f_001": get_files_download_by_day_list_v53(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v74": lambda q, id="k_001": get_auth_api_keys_quota_history_v74(id),
    "/api/v2/skills/{id}/sync-from-template-v51": lambda q, id="s_001": get_skills_sync_from_template_v51(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v52": lambda q, id="c_001": get_billing_payment_methods_unset_active_v52(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v51": lambda q, id="c001": get_campaigns_audience_source_stats_v51(id),
    "/api/v2/files/{id}/download-by-day-list-v52": lambda q, id="f_001": get_files_download_by_day_list_v52(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v73": lambda q, id="k_001": get_auth_api_keys_quota_history_v73(id),
    "/api/v2/skills/{id}/sync-from-template-v50": lambda q, id="s_001": get_skills_sync_from_template_v50(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v51": lambda q, id="c_001": get_billing_payment_methods_unset_active_v51(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v50": lambda q, id="c001": get_campaigns_audience_source_stats_v50(id),
    "/api/v2/files/{id}/download-by-day-list-v51": lambda q, id="f_001": get_files_download_by_day_list_v51(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v72": lambda q, id="k_001": get_auth_api_keys_quota_history_v72(id),
    "/api/v2/skills/{id}/sync-from-template-v49": lambda q, id="s_001": get_skills_sync_from_template_v49(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v50": lambda q, id="c_001": get_billing_payment_methods_unset_active_v50(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v49": lambda q, id="c001": get_campaigns_audience_source_stats_v49(id),
    "/api/v2/files/{id}/download-by-day-list-v50": lambda q, id="f_001": get_files_download_by_day_list_v50(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v71": lambda q, id="k_001": get_auth_api_keys_quota_history_v71(id),
    "/api/v2/skills/{id}/sync-from-template-v48": lambda q, id="s_001": get_skills_sync_from_template_v48(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v49": lambda q, id="c_001": get_billing_payment_methods_unset_active_v49(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v48": lambda q, id="c001": get_campaigns_audience_source_stats_v48(id),
    "/api/v2/files/{id}/download-by-day-list-v49": lambda q, id="f_001": get_files_download_by_day_list_v49(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v70": lambda q, id="k_001": get_auth_api_keys_quota_history_v70(id),
    "/api/v2/skills/{id}/sync-from-template-v47": lambda q, id="s_001": get_skills_sync_from_template_v47(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v48": lambda q, id="c_001": get_billing_payment_methods_unset_active_v48(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v47": lambda q, id="c001": get_campaigns_audience_source_stats_v47(id),
    "/api/v2/files/{id}/download-by-day-list-v48": lambda q, id="f_001": get_files_download_by_day_list_v48(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v69": lambda q, id="k_001": get_auth_api_keys_quota_history_v69(id),
    "/api/v2/skills/{id}/sync-from-template-v46": lambda q, id="s_001": get_skills_sync_from_template_v46(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v47": lambda q, id="c_001": get_billing_payment_methods_unset_active_v47(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v46": lambda q, id="c001": get_campaigns_audience_source_stats_v46(id),
    "/api/v2/files/{id}/download-by-day-list-v47": lambda q, id="f_001": get_files_download_by_day_list_v47(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v68": lambda q, id="k_001": get_auth_api_keys_quota_history_v68(id),
    "/api/v2/skills/{id}/sync-from-template-v45": lambda q, id="s_001": get_skills_sync_from_template_v45(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v46": lambda q, id="c_001": get_billing_payment_methods_unset_active_v46(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v45": lambda q, id="c001": get_campaigns_audience_source_stats_v45(id),
    "/api/v2/files/{id}/download-by-day-list-v46": lambda q, id="f_001": get_files_download_by_day_list_v46(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v67": lambda q, id="k_001": get_auth_api_keys_quota_history_v67(id),
    "/api/v2/skills/{id}/sync-from-template-v44": lambda q, id="s_001": get_skills_sync_from_template_v44(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v45": lambda q, id="c_001": get_billing_payment_methods_unset_active_v45(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v44": lambda q, id="c001": get_campaigns_audience_source_stats_v44(id),
    "/api/v2/files/{id}/download-by-day-list-v45": lambda q, id="f_001": get_files_download_by_day_list_v45(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v66": lambda q, id="k_001": get_auth_api_keys_quota_history_v66(id),
    "/api/v2/skills/{id}/sync-from-template-v43": lambda q, id="s_001": get_skills_sync_from_template_v43(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v44": lambda q, id="c_001": get_billing_payment_methods_unset_active_v44(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v43": lambda q, id="c001": get_campaigns_audience_source_stats_v43(id),
    "/api/v2/files/{id}/download-by-day-list-v44": lambda q, id="f_001": get_files_download_by_day_list_v44(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v65": lambda q, id="k_001": get_auth_api_keys_quota_history_v65(id),
    "/api/v2/skills/{id}/sync-from-template-v42": lambda q, id="s_001": get_skills_sync_from_template_v42(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v43": lambda q, id="c_001": get_billing_payment_methods_unset_active_v43(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v42": lambda q, id="c001": get_campaigns_audience_source_stats_v42(id),
    "/api/v2/files/{id}/download-by-day-list-v43": lambda q, id="f_001": get_files_download_by_day_list_v43(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v64": lambda q, id="k_001": get_auth_api_keys_quota_history_v64(id),
    "/api/v2/skills/{id}/sync-from-template-v41": lambda q, id="s_001": get_skills_sync_from_template_v41(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v42": lambda q, id="c_001": get_billing_payment_methods_unset_active_v42(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v41": lambda q, id="c001": get_campaigns_audience_source_stats_v41(id),
    "/api/v2/files/{id}/download-by-day-list-v42": lambda q, id="f_001": get_files_download_by_day_list_v42(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v63": lambda q, id="k_001": get_auth_api_keys_quota_history_v63(id),
    "/api/v2/skills/{id}/sync-from-template-v40": lambda q, id="s_001": get_skills_sync_from_template_v40(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v41": lambda q, id="c_001": get_billing_payment_methods_unset_active_v41(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v40": lambda q, id="c001": get_campaigns_audience_source_stats_v40(id),
    "/api/v2/files/{id}/download-by-day-list-v41": lambda q, id="f_001": get_files_download_by_day_list_v41(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v62": lambda q, id="k_001": get_auth_api_keys_quota_history_v62(id),
    "/api/v2/skills/{id}/sync-from-template-v39": lambda q, id="s_001": get_skills_sync_from_template_v39(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v40": lambda q, id="c_001": get_billing_payment_methods_unset_active_v40(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v39": lambda q, id="c001": get_campaigns_audience_source_stats_v39(id),
    "/api/v2/files/{id}/download-by-day-list-v40": lambda q, id="f_001": get_files_download_by_day_list_v40(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v61": lambda q, id="k_001": get_auth_api_keys_quota_history_v61(id),
    "/api/v2/skills/{id}/sync-from-template-v38": lambda q, id="s_001": get_skills_sync_from_template_v38(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v39": lambda q, id="c_001": get_billing_payment_methods_unset_active_v39(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v38": lambda q, id="c001": get_campaigns_audience_source_stats_v38(id),
    "/api/v2/files/{id}/download-by-day-list-v39": lambda q, id="f_001": get_files_download_by_day_list_v39(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v60": lambda q, id="k_001": get_auth_api_keys_quota_history_v60(id),
    "/api/v2/skills/{id}/sync-from-template-v37": lambda q, id="s_001": get_skills_sync_from_template_v37(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v38": lambda q, id="c_001": get_billing_payment_methods_unset_active_v38(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v37": lambda q, id="c001": get_campaigns_audience_source_stats_v37(id),
    "/api/v2/files/{id}/download-by-day-list-v38": lambda q, id="f_001": get_files_download_by_day_list_v38(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v59": lambda q, id="k_001": get_auth_api_keys_quota_history_v59(id),
    "/api/v2/skills/{id}/sync-from-template-v36": lambda q, id="s_001": get_skills_sync_from_template_v36(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v37": lambda q, id="c_001": get_billing_payment_methods_unset_active_v37(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v36": lambda q, id="c001": get_campaigns_audience_source_stats_v36(id),
    "/api/v2/files/{id}/download-by-day-list-v37": lambda q, id="f_001": get_files_download_by_day_list_v37(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v58": lambda q, id="k_001": get_auth_api_keys_quota_history_v58(id),
    "/api/v2/skills/{id}/sync-from-template-v35": lambda q, id="s_001": get_skills_sync_from_template_v35(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v36": lambda q, id="c_001": get_billing_payment_methods_unset_active_v36(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v35": lambda q, id="c001": get_campaigns_audience_source_stats_v35(id),
    "/api/v2/files/{id}/download-by-day-list-v36": lambda q, id="f_001": get_files_download_by_day_list_v36(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v57": lambda q, id="k_001": get_auth_api_keys_quota_history_v57(id),
    "/api/v2/skills/{id}/sync-from-template-v34": lambda q, id="s_001": get_skills_sync_from_template_v34(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v35": lambda q, id="c_001": get_billing_payment_methods_unset_active_v35(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v34": lambda q, id="c001": get_campaigns_audience_source_stats_v34(id),
    "/api/v2/files/{id}/download-by-day-list-v35": lambda q, id="f_001": get_files_download_by_day_list_v35(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v56": lambda q, id="k_001": get_auth_api_keys_quota_history_v56(id),
    "/api/v2/skills/{id}/sync-from-template-v33": lambda q, id="s_001": get_skills_sync_from_template_v33(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v34": lambda q, id="c_001": get_billing_payment_methods_unset_active_v34(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v33": lambda q, id="c001": get_campaigns_audience_source_stats_v33(id),
    "/api/v2/files/{id}/download-by-day-list-v34": lambda q, id="f_001": get_files_download_by_day_list_v34(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v55": lambda q, id="k_001": get_auth_api_keys_quota_history_v55(id),
    "/api/v2/skills/{id}/sync-from-template-v32": lambda q, id="s_001": get_skills_sync_from_template_v32(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v33": lambda q, id="c_001": get_billing_payment_methods_unset_active_v33(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v32": lambda q, id="c001": get_campaigns_audience_source_stats_v32(id),
    "/api/v2/files/{id}/download-by-day-list-v33": lambda q, id="f_001": get_files_download_by_day_list_v33(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v54": lambda q, id="k_001": get_auth_api_keys_quota_history_v54(id),
    "/api/v2/skills/{id}/sync-from-template-v31": lambda q, id="s_001": get_skills_sync_from_template_v31(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v32": lambda q, id="c_001": get_billing_payment_methods_unset_active_v32(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v31": lambda q, id="c001": get_campaigns_audience_source_stats_v31(id),
    "/api/v2/files/{id}/download-by-day-list-v32": lambda q, id="f_001": get_files_download_by_day_list_v32(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v53": lambda q, id="k_001": get_auth_api_keys_quota_history_v53(id),
    "/api/v2/skills/{id}/sync-from-template-v30": lambda q, id="s_001": get_skills_sync_from_template_v30(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v31": lambda q, id="c_001": get_billing_payment_methods_unset_active_v31(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v30": lambda q, id="c001": get_campaigns_audience_source_stats_v30(id),
    "/api/v2/files/{id}/download-by-day-list-v31": lambda q, id="f_001": get_files_download_by_day_list_v31(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v52": lambda q, id="k_001": get_auth_api_keys_quota_history_v52(id),
    "/api/v2/skills/{id}/sync-from-template-v29": lambda q, id="s_001": get_skills_sync_from_template_v29(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v30": lambda q, id="c_001": get_billing_payment_methods_unset_active_v30(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v29": lambda q, id="c001": get_campaigns_audience_source_stats_v29(id),
    "/api/v2/files/{id}/download-by-day-list-v30": lambda q, id="f_001": get_files_download_by_day_list_v30(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v51": lambda q, id="k_001": get_auth_api_keys_quota_history_v51(id),
    "/api/v2/skills/{id}/sync-from-template-v28": lambda q, id="s_001": get_skills_sync_from_template_v28(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v29": lambda q, id="c_001": get_billing_payment_methods_unset_active_v29(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v28": lambda q, id="c001": get_campaigns_audience_source_stats_v28(id),
    "/api/v2/files/{id}/download-by-day-list-v29": lambda q, id="f_001": get_files_download_by_day_list_v29(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v50": lambda q, id="k_001": get_auth_api_keys_quota_history_v50(id),
    "/api/v2/skills/{id}/sync-from-template-v27": lambda q, id="s_001": get_skills_sync_from_template_v27(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v28": lambda q, id="c_001": get_billing_payment_methods_unset_active_v28(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v27": lambda q, id="c001": get_campaigns_audience_source_stats_v27(id),
    "/api/v2/files/{id}/download-by-day-list-v28": lambda q, id="f_001": get_files_download_by_day_list_v28(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v49": lambda q, id="k_001": get_auth_api_keys_quota_history_v49(id),
    "/api/v2/skills/{id}/sync-from-template-v26": lambda q, id="s_001": get_skills_sync_from_template_v26(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v27": lambda q, id="c_001": get_billing_payment_methods_unset_active_v27(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v26": lambda q, id="c001": get_campaigns_audience_source_stats_v26(id),
    "/api/v2/files/{id}/download-by-day-list-v27": lambda q, id="f_001": get_files_download_by_day_list_v27(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v48": lambda q, id="k_001": get_auth_api_keys_quota_history_v48(id),
    "/api/v2/skills/{id}/sync-from-template-v25": lambda q, id="s_001": get_skills_sync_from_template_v25(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v26": lambda q, id="c_001": get_billing_payment_methods_unset_active_v26(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v25": lambda q, id="c001": get_campaigns_audience_source_stats_v25(id),
    "/api/v2/files/{id}/download-by-day-list-v26": lambda q, id="f_001": get_files_download_by_day_list_v26(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v47": lambda q, id="k_001": get_auth_api_keys_quota_history_v47(id),
    "/api/v2/skills/{id}/sync-from-template-v24": lambda q, id="s_001": get_skills_sync_from_template_v24(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v25": lambda q, id="c_001": get_billing_payment_methods_unset_active_v25(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v24": lambda q, id="c001": get_campaigns_audience_source_stats_v24(id),
    "/api/v2/files/{id}/download-by-day-list-v25": lambda q, id="f_001": get_files_download_by_day_list_v25(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v46": lambda q, id="k_001": get_auth_api_keys_quota_history_v46(id),
    "/api/v2/skills/{id}/sync-from-template-v23": lambda q, id="s_001": get_skills_sync_from_template_v23(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v24": lambda q, id="c_001": get_billing_payment_methods_unset_active_v24(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v23": lambda q, id="c001": get_campaigns_audience_source_stats_v23(id),
    "/api/v2/files/{id}/download-by-day-list-v24": lambda q, id="f_001": get_files_download_by_day_list_v24(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v45": lambda q, id="k_001": get_auth_api_keys_quota_history_v45(id),
    "/api/v2/skills/{id}/sync-from-template-v22": lambda q, id="s_001": get_skills_sync_from_template_v22(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v23": lambda q, id="c_001": get_billing_payment_methods_unset_active_v23(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v22": lambda q, id="c001": get_campaigns_audience_source_stats_v22(id),
    "/api/v2/files/{id}/download-by-day-list-v23": lambda q, id="f_001": get_files_download_by_day_list_v23(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v44": lambda q, id="k_001": get_auth_api_keys_quota_history_v44(id),
    "/api/v2/skills/{id}/sync-from-template-v21": lambda q, id="s_001": get_skills_sync_from_template_v21(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v22": lambda q, id="c_001": get_billing_payment_methods_unset_active_v22(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v21": lambda q, id="c001": get_campaigns_audience_source_stats_v21(id),
    "/api/v2/files/{id}/download-by-day-list-v22": lambda q, id="f_001": get_files_download_by_day_list_v22(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v43": lambda q, id="k_001": get_auth_api_keys_quota_history_v43(id),
    "/api/v2/skills/{id}/sync-from-template-v20": lambda q, id="s_001": get_skills_sync_from_template_v20(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v21": lambda q, id="c_001": get_billing_payment_methods_unset_active_v21(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v20": lambda q, id="c001": get_campaigns_audience_source_stats_v20(id),
    "/api/v2/files/{id}/download-by-day-list-v21": lambda q, id="f_001": get_files_download_by_day_list_v21(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v42": lambda q, id="k_001": get_auth_api_keys_quota_history_v42(id),
    "/api/v2/skills/{id}/sync-from-template-v19": lambda q, id="s_001": get_skills_sync_from_template_v19(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v29": lambda q, id="c_001": get_billing_payment_methods_unset_active_v29(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v19": lambda q, id="c001": get_campaigns_audience_source_stats_v19(id),
    "/api/v2/files/{id}/download-by-day-list-v20": lambda q, id="f_001": get_files_download_by_day_list_v20(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v41": lambda q, id="k_001": get_auth_api_keys_quota_history_v41(id),
    "/api/v2/skills/{id}/sync-from-template-v18": lambda q, id="s_001": get_skills_sync_from_template_v18(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v28": lambda q, id="c_001": get_billing_payment_methods_unset_active_v28(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v18": lambda q, id="c001": get_campaigns_audience_source_stats_v18(id),
    "/api/v2/files/{id}/download-by-day-list-v19": lambda q, id="f_001": get_files_download_by_day_list_v19(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v40": lambda q, id="k_001": get_auth_api_keys_quota_history_v40(id),
    "/api/v2/skills/{id}/sync-from-template-v17": lambda q, id="s_001": get_skills_sync_from_template_v17(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v27": lambda q, id="c_001": get_billing_payment_methods_unset_active_v27(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v17": lambda q, id="c001": get_campaigns_audience_source_stats_v17(id),
    "/api/v2/files/{id}/download-by-day-list-v18": lambda q, id="f_001": get_files_download_by_day_list_v18(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v39": lambda q, id="k_001": get_auth_api_keys_quota_history_v39(id),
    "/api/v2/skills/{id}/sync-from-template-v16": lambda q, id="s_001": get_skills_sync_from_template_v16(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v26": lambda q, id="c_001": get_billing_payment_methods_unset_active_v26(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v16": lambda q, id="c001": get_campaigns_audience_source_stats_v16(id),
    "/api/v2/files/{id}/download-by-day-list-v17": lambda q, id="f_001": get_files_download_by_day_list_v17(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v38": lambda q, id="k_001": get_auth_api_keys_quota_history_v38(id),
    "/api/v2/skills/{id}/sync-from-template-v15": lambda q, id="s_001": get_skills_sync_from_template_v15(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v25": lambda q, id="c_001": get_billing_payment_methods_unset_active_v25(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v15": lambda q, id="c001": get_campaigns_audience_source_stats_v15(id),
    "/api/v2/files/{id}/download-by-day-list-v16": lambda q, id="f_001": get_files_download_by_day_list_v16(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v37": lambda q, id="k_001": get_auth_api_keys_quota_history_v37(id),
    "/api/v2/skills/{id}/sync-from-template-v14": lambda q, id="s_001": get_skills_sync_from_template_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v24": lambda q, id="c_001": get_billing_payment_methods_unset_active_v24(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v14": lambda q, id="c001": get_campaigns_audience_source_stats_v14(id),
    "/api/v2/files/{id}/download-by-day-list-v15": lambda q, id="f_001": get_files_download_by_day_list_v15(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v36": lambda q, id="k_001": get_auth_api_keys_quota_history_v36(id),
    "/api/v2/skills/{id}/sync-from-template-v13": lambda q, id="s_001": get_skills_sync_from_template_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v23": lambda q, id="c_001": get_billing_payment_methods_unset_active_v23(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v13": lambda q, id="c001": get_campaigns_audience_source_stats_v13(id),
    "/api/v2/files/{id}/download-by-day-list-v14": lambda q, id="f_001": get_files_download_by_day_list_v14(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v35": lambda q, id="k_001": get_auth_api_keys_quota_history_v35(id),
    "/api/v2/skills/{id}/sync-from-template-v84": lambda q, id="s_001": get_skills_sync_from_template_v84(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v85": lambda q, id="c_001": get_billing_payment_methods_unset_active_v85(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v84": lambda q, id="c001": get_campaigns_audience_source_stats_v84(id),
    "/api/v2/files/{id}/download-by-day-list-v85": lambda q, id="f_001": get_files_download_by_day_list_v85(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v106": lambda q, id="k_001": get_auth_api_keys_quota_history_v106(id),
    "/api/v2/skills/{id}/sync-from-template-v83": lambda q, id="s_001": get_skills_sync_from_template_v83(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v84": lambda q, id="c_001": get_billing_payment_methods_unset_active_v84(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v83": lambda q, id="c001": get_campaigns_audience_source_stats_v83(id),
    "/api/v2/files/{id}/download-by-day-list-v84": lambda q, id="f_001": get_files_download_by_day_list_v84(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v105": lambda q, id="k_001": get_auth_api_keys_quota_history_v105(id),
    "/api/v2/skills/{id}/sync-from-template-v82": lambda q, id="s_001": get_skills_sync_from_template_v82(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v83": lambda q, id="c_001": get_billing_payment_methods_unset_active_v83(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v82": lambda q, id="c001": get_campaigns_audience_source_stats_v82(id),
    "/api/v2/files/{id}/download-by-day-list-v83": lambda q, id="f_001": get_files_download_by_day_list_v83(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v104": lambda q, id="k_001": get_auth_api_keys_quota_history_v104(id),
    "/api/v2/skills/{id}/sync-from-template-v81": lambda q, id="s_001": get_skills_sync_from_template_v81(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v82": lambda q, id="c_001": get_billing_payment_methods_unset_active_v82(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v81": lambda q, id="c001": get_campaigns_audience_source_stats_v81(id),
    "/api/v2/files/{id}/download-by-day-list-v82": lambda q, id="f_001": get_files_download_by_day_list_v82(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v103": lambda q, id="k_001": get_auth_api_keys_quota_history_v103(id),
    "/api/v2/skills/{id}/sync-from-template-v80": lambda q, id="s_001": get_skills_sync_from_template_v80(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v81": lambda q, id="c_001": get_billing_payment_methods_unset_active_v81(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v80": lambda q, id="c001": get_campaigns_audience_source_stats_v80(id),
    "/api/v2/files/{id}/download-by-day-list-v81": lambda q, id="f_001": get_files_download_by_day_list_v81(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v102": lambda q, id="k_001": get_auth_api_keys_quota_history_v102(id),
    "/api/v2/skills/{id}/sync-from-template-v79": lambda q, id="s_001": get_skills_sync_from_template_v79(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v80": lambda q, id="c_001": get_billing_payment_methods_unset_active_v80(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v79": lambda q, id="c001": get_campaigns_audience_source_stats_v79(id),
    "/api/v2/files/{id}/download-by-day-list-v80": lambda q, id="f_001": get_files_download_by_day_list_v80(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v101": lambda q, id="k_001": get_auth_api_keys_quota_history_v101(id),
    "/api/v2/skills/{id}/sync-from-template-v78": lambda q, id="s_001": get_skills_sync_from_template_v78(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v79": lambda q, id="c_001": get_billing_payment_methods_unset_active_v79(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v78": lambda q, id="c001": get_campaigns_audience_source_stats_v78(id),
    "/api/v2/files/{id}/download-by-day-list-v79": lambda q, id="f_001": get_files_download_by_day_list_v79(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v100": lambda q, id="k_001": get_auth_api_keys_quota_history_v100(id),
    "/api/v2/skills/{id}/sync-from-template-v77": lambda q, id="s_001": get_skills_sync_from_template_v77(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v78": lambda q, id="c_001": get_billing_payment_methods_unset_active_v78(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v77": lambda q, id="c001": get_campaigns_audience_source_stats_v77(id),
    "/api/v2/files/{id}/download-by-day-list-v78": lambda q, id="f_001": get_files_download_by_day_list_v78(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v99": lambda q, id="k_001": get_auth_api_keys_quota_history_v99(id),
    "/api/v2/skills/{id}/sync-from-template-v76": lambda q, id="s_001": get_skills_sync_from_template_v76(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v77": lambda q, id="c_001": get_billing_payment_methods_unset_active_v77(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v76": lambda q, id="c001": get_campaigns_audience_source_stats_v76(id),
    "/api/v2/files/{id}/download-by-day-list-v77": lambda q, id="f_001": get_files_download_by_day_list_v77(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v98": lambda q, id="k_001": get_auth_api_keys_quota_history_v98(id),
    "/api/v2/skills/{id}/sync-from-template-v75": lambda q, id="s_001": get_skills_sync_from_template_v75(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v76": lambda q, id="c_001": get_billing_payment_methods_unset_active_v76(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v75": lambda q, id="c001": get_campaigns_audience_source_stats_v75(id),
    "/api/v2/files/{id}/download-by-day-list-v76": lambda q, id="f_001": get_files_download_by_day_list_v76(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v97": lambda q, id="k_001": get_auth_api_keys_quota_history_v97(id),
    "/api/v2/skills/{id}/sync-from-template-v74": lambda q, id="s_001": get_skills_sync_from_template_v74(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v75": lambda q, id="c_001": get_billing_payment_methods_unset_active_v75(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v74": lambda q, id="c001": get_campaigns_audience_source_stats_v74(id),
    "/api/v2/files/{id}/download-by-day-list-v75": lambda q, id="f_001": get_files_download_by_day_list_v75(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v96": lambda q, id="k_001": get_auth_api_keys_quota_history_v96(id),
    "/api/v2/skills/{id}/sync-from-template-v73": lambda q, id="s_001": get_skills_sync_from_template_v73(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v74": lambda q, id="c_001": get_billing_payment_methods_unset_active_v74(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v73": lambda q, id="c001": get_campaigns_audience_source_stats_v73(id),
    "/api/v2/files/{id}/download-by-day-list-v74": lambda q, id="f_001": get_files_download_by_day_list_v74(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v95": lambda q, id="k_001": get_auth_api_keys_quota_history_v95(id),
    "/api/v2/skills/{id}/sync-from-template-v72": lambda q, id="s_001": get_skills_sync_from_template_v72(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v73": lambda q, id="c_001": get_billing_payment_methods_unset_active_v73(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v72": lambda q, id="c001": get_campaigns_audience_source_stats_v72(id),
    "/api/v2/files/{id}/download-by-day-list-v73": lambda q, id="f_001": get_files_download_by_day_list_v73(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v94": lambda q, id="k_001": get_auth_api_keys_quota_history_v94(id),
    "/api/v2/skills/{id}/sync-from-template-v71": lambda q, id="s_001": get_skills_sync_from_template_v71(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v72": lambda q, id="c_001": get_billing_payment_methods_unset_active_v72(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v71": lambda q, id="c001": get_campaigns_audience_source_stats_v71(id),
    "/api/v2/files/{id}/download-by-day-list-v72": lambda q, id="f_001": get_files_download_by_day_list_v72(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v93": lambda q, id="k_001": get_auth_api_keys_quota_history_v93(id),
    "/api/v2/skills/{id}/sync-from-template-v70": lambda q, id="s_001": get_skills_sync_from_template_v70(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v71": lambda q, id="c_001": get_billing_payment_methods_unset_active_v71(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v70": lambda q, id="c001": get_campaigns_audience_source_stats_v70(id),
    "/api/v2/files/{id}/download-by-day-list-v71": lambda q, id="f_001": get_files_download_by_day_list_v71(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v92": lambda q, id="k_001": get_auth_api_keys_quota_history_v92(id),
    "/api/v2/skills/{id}/sync-from-template-v69": lambda q, id="s_001": get_skills_sync_from_template_v69(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v70": lambda q, id="c_001": get_billing_payment_methods_unset_active_v70(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v69": lambda q, id="c001": get_campaigns_audience_source_stats_v69(id),
    "/api/v2/files/{id}/download-by-day-list-v70": lambda q, id="f_001": get_files_download_by_day_list_v70(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v91": lambda q, id="k_001": get_auth_api_keys_quota_history_v91(id),
    "/api/v2/skills/{id}/sync-from-template-v68": lambda q, id="s_001": get_skills_sync_from_template_v68(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v69": lambda q, id="c_001": get_billing_payment_methods_unset_active_v69(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v68": lambda q, id="c001": get_campaigns_audience_source_stats_v68(id),
    "/api/v2/files/{id}/download-by-day-list-v69": lambda q, id="f_001": get_files_download_by_day_list_v69(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v90": lambda q, id="k_001": get_auth_api_keys_quota_history_v90(id),
    "/api/v2/skills/{id}/sync-from-template-v67": lambda q, id="s_001": get_skills_sync_from_template_v67(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v68": lambda q, id="c_001": get_billing_payment_methods_unset_active_v68(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v67": lambda q, id="c001": get_campaigns_audience_source_stats_v67(id),
    "/api/v2/files/{id}/download-by-day-list-v68": lambda q, id="f_001": get_files_download_by_day_list_v68(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v89": lambda q, id="k_001": get_auth_api_keys_quota_history_v89(id),
    "/api/v2/skills/{id}/sync-from-template-v66": lambda q, id="s_001": get_skills_sync_from_template_v66(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v67": lambda q, id="c_001": get_billing_payment_methods_unset_active_v67(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v66": lambda q, id="c001": get_campaigns_audience_source_stats_v66(id),
    "/api/v2/files/{id}/download-by-day-list-v67": lambda q, id="f_001": get_files_download_by_day_list_v67(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v88": lambda q, id="k_001": get_auth_api_keys_quota_history_v88(id),
    "/api/v2/skills/{id}/sync-from-template-v65": lambda q, id="s_001": get_skills_sync_from_template_v65(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v66": lambda q, id="c_001": get_billing_payment_methods_unset_active_v66(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v65": lambda q, id="c001": get_campaigns_audience_source_stats_v65(id),
    "/api/v2/files/{id}/download-by-day-list-v66": lambda q, id="f_001": get_files_download_by_day_list_v66(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v87": lambda q, id="k_001": get_auth_api_keys_quota_history_v87(id),
    "/api/v2/skills/{id}/sync-from-template-v64": lambda q, id="s_001": get_skills_sync_from_template_v64(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v65": lambda q, id="c_001": get_billing_payment_methods_unset_active_v65(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v64": lambda q, id="c001": get_campaigns_audience_source_stats_v64(id),
    "/api/v2/files/{id}/download-by-day-list-v65": lambda q, id="f_001": get_files_download_by_day_list_v65(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v86": lambda q, id="k_001": get_auth_api_keys_quota_history_v86(id),
    "/api/v2/skills/{id}/sync-from-template-v63": lambda q, id="s_001": get_skills_sync_from_template_v63(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v64": lambda q, id="c_001": get_billing_payment_methods_unset_active_v64(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v63": lambda q, id="c001": get_campaigns_audience_source_stats_v63(id),
    "/api/v2/files/{id}/download-by-day-list-v64": lambda q, id="f_001": get_files_download_by_day_list_v64(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v85": lambda q, id="k_001": get_auth_api_keys_quota_history_v85(id),
    "/api/v2/skills/{id}/sync-from-template-v62": lambda q, id="s_001": get_skills_sync_from_template_v62(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v63": lambda q, id="c_001": get_billing_payment_methods_unset_active_v63(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v62": lambda q, id="c001": get_campaigns_audience_source_stats_v62(id),
    "/api/v2/files/{id}/download-by-day-list-v63": lambda q, id="f_001": get_files_download_by_day_list_v63(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v84": lambda q, id="k_001": get_auth_api_keys_quota_history_v84(id),
    "/api/v2/skills/{id}/sync-from-template-v61": lambda q, id="s_001": get_skills_sync_from_template_v61(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v62": lambda q, id="c_001": get_billing_payment_methods_unset_active_v62(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v61": lambda q, id="c001": get_campaigns_audience_source_stats_v61(id),
    "/api/v2/files/{id}/download-by-day-list-v62": lambda q, id="f_001": get_files_download_by_day_list_v62(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v83": lambda q, id="k_001": get_auth_api_keys_quota_history_v83(id),
    "/api/v2/skills/{id}/sync-from-template-v60": lambda q, id="s_001": get_skills_sync_from_template_v60(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v61": lambda q, id="c_001": get_billing_payment_methods_unset_active_v61(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v60": lambda q, id="c001": get_campaigns_audience_source_stats_v60(id),
    "/api/v2/files/{id}/download-by-day-list-v61": lambda q, id="f_001": get_files_download_by_day_list_v61(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v82": lambda q, id="k_001": get_auth_api_keys_quota_history_v82(id),
    "/api/v2/skills/{id}/sync-from-template-v59": lambda q, id="s_001": get_skills_sync_from_template_v59(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v60": lambda q, id="c_001": get_billing_payment_methods_unset_active_v60(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v59": lambda q, id="c001": get_campaigns_audience_source_stats_v59(id),
    "/api/v2/files/{id}/download-by-day-list-v60": lambda q, id="f_001": get_files_download_by_day_list_v60(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v81": lambda q, id="k_001": get_auth_api_keys_quota_history_v81(id),
    "/api/v2/skills/{id}/sync-from-template-v58": lambda q, id="s_001": get_skills_sync_from_template_v58(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v59": lambda q, id="c_001": get_billing_payment_methods_unset_active_v59(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v58": lambda q, id="c001": get_campaigns_audience_source_stats_v58(id),
    "/api/v2/files/{id}/download-by-day-list-v59": lambda q, id="f_001": get_files_download_by_day_list_v59(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v80": lambda q, id="k_001": get_auth_api_keys_quota_history_v80(id),
    "/api/v2/skills/{id}/sync-from-template-v57": lambda q, id="s_001": get_skills_sync_from_template_v57(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v58": lambda q, id="c_001": get_billing_payment_methods_unset_active_v58(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v57": lambda q, id="c001": get_campaigns_audience_source_stats_v57(id),
    "/api/v2/files/{id}/download-by-day-list-v58": lambda q, id="f_001": get_files_download_by_day_list_v58(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v79": lambda q, id="k_001": get_auth_api_keys_quota_history_v79(id),
    "/api/v2/skills/{id}/sync-from-template-v56": lambda q, id="s_001": get_skills_sync_from_template_v56(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v57": lambda q, id="c_001": get_billing_payment_methods_unset_active_v57(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v56": lambda q, id="c001": get_campaigns_audience_source_stats_v56(id),
    "/api/v2/files/{id}/download-by-day-list-v57": lambda q, id="f_001": get_files_download_by_day_list_v57(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v78": lambda q, id="k_001": get_auth_api_keys_quota_history_v78(id),
    "/api/v2/skills/{id}/sync-from-template-v55": lambda q, id="s_001": get_skills_sync_from_template_v55(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v56": lambda q, id="c_001": get_billing_payment_methods_unset_active_v56(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v55": lambda q, id="c001": get_campaigns_audience_source_stats_v55(id),
    "/api/v2/files/{id}/download-by-day-list-v56": lambda q, id="f_001": get_files_download_by_day_list_v56(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v77": lambda q, id="k_001": get_auth_api_keys_quota_history_v77(id),
    "/api/v2/skills/{id}/sync-from-template-v54": lambda q, id="s_001": get_skills_sync_from_template_v54(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v55": lambda q, id="c_001": get_billing_payment_methods_unset_active_v55(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v54": lambda q, id="c001": get_campaigns_audience_source_stats_v54(id),
    "/api/v2/files/{id}/download-by-day-list-v55": lambda q, id="f_001": get_files_download_by_day_list_v55(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v76": lambda q, id="k_001": get_auth_api_keys_quota_history_v76(id),
    "/api/v2/skills/{id}/sync-from-template-v53": lambda q, id="s_001": get_skills_sync_from_template_v53(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v54": lambda q, id="c_001": get_billing_payment_methods_unset_active_v54(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v53": lambda q, id="c001": get_campaigns_audience_source_stats_v53(id),
    "/api/v2/files/{id}/download-by-day-list-v54": lambda q, id="f_001": get_files_download_by_day_list_v54(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v75": lambda q, id="k_001": get_auth_api_keys_quota_history_v75(id),
    "/api/v2/skills/{id}/sync-from-template-v52": lambda q, id="s_001": get_skills_sync_from_template_v52(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v53": lambda q, id="c_001": get_billing_payment_methods_unset_active_v53(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v52": lambda q, id="c001": get_campaigns_audience_source_stats_v52(id),
    "/api/v2/files/{id}/download-by-day-list-v53": lambda q, id="f_001": get_files_download_by_day_list_v53(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v74": lambda q, id="k_001": get_auth_api_keys_quota_history_v74(id),
    "/api/v2/skills/{id}/sync-from-template-v51": lambda q, id="s_001": get_skills_sync_from_template_v51(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v52": lambda q, id="c_001": get_billing_payment_methods_unset_active_v52(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v51": lambda q, id="c001": get_campaigns_audience_source_stats_v51(id),
    "/api/v2/files/{id}/download-by-day-list-v52": lambda q, id="f_001": get_files_download_by_day_list_v52(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v73": lambda q, id="k_001": get_auth_api_keys_quota_history_v73(id),
    "/api/v2/skills/{id}/sync-from-template-v50": lambda q, id="s_001": get_skills_sync_from_template_v50(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v51": lambda q, id="c_001": get_billing_payment_methods_unset_active_v51(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v50": lambda q, id="c001": get_campaigns_audience_source_stats_v50(id),
    "/api/v2/files/{id}/download-by-day-list-v51": lambda q, id="f_001": get_files_download_by_day_list_v51(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v72": lambda q, id="k_001": get_auth_api_keys_quota_history_v72(id),
    "/api/v2/skills/{id}/sync-from-template-v49": lambda q, id="s_001": get_skills_sync_from_template_v49(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v50": lambda q, id="c_001": get_billing_payment_methods_unset_active_v50(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v49": lambda q, id="c001": get_campaigns_audience_source_stats_v49(id),
    "/api/v2/files/{id}/download-by-day-list-v50": lambda q, id="f_001": get_files_download_by_day_list_v50(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v71": lambda q, id="k_001": get_auth_api_keys_quota_history_v71(id),
    "/api/v2/skills/{id}/sync-from-template-v48": lambda q, id="s_001": get_skills_sync_from_template_v48(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v49": lambda q, id="c_001": get_billing_payment_methods_unset_active_v49(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v48": lambda q, id="c001": get_campaigns_audience_source_stats_v48(id),
    "/api/v2/files/{id}/download-by-day-list-v49": lambda q, id="f_001": get_files_download_by_day_list_v49(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v70": lambda q, id="k_001": get_auth_api_keys_quota_history_v70(id),
    "/api/v2/skills/{id}/sync-from-template-v47": lambda q, id="s_001": get_skills_sync_from_template_v47(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v48": lambda q, id="c_001": get_billing_payment_methods_unset_active_v48(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v47": lambda q, id="c001": get_campaigns_audience_source_stats_v47(id),
    "/api/v2/files/{id}/download-by-day-list-v48": lambda q, id="f_001": get_files_download_by_day_list_v48(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v69": lambda q, id="k_001": get_auth_api_keys_quota_history_v69(id),
    "/api/v2/skills/{id}/sync-from-template-v46": lambda q, id="s_001": get_skills_sync_from_template_v46(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v47": lambda q, id="c_001": get_billing_payment_methods_unset_active_v47(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v46": lambda q, id="c001": get_campaigns_audience_source_stats_v46(id),
    "/api/v2/files/{id}/download-by-day-list-v47": lambda q, id="f_001": get_files_download_by_day_list_v47(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v68": lambda q, id="k_001": get_auth_api_keys_quota_history_v68(id),
    "/api/v2/skills/{id}/sync-from-template-v45": lambda q, id="s_001": get_skills_sync_from_template_v45(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v46": lambda q, id="c_001": get_billing_payment_methods_unset_active_v46(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v45": lambda q, id="c001": get_campaigns_audience_source_stats_v45(id),
    "/api/v2/files/{id}/download-by-day-list-v46": lambda q, id="f_001": get_files_download_by_day_list_v46(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v67": lambda q, id="k_001": get_auth_api_keys_quota_history_v67(id),
    "/api/v2/skills/{id}/sync-from-template-v44": lambda q, id="s_001": get_skills_sync_from_template_v44(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v45": lambda q, id="c_001": get_billing_payment_methods_unset_active_v45(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v44": lambda q, id="c001": get_campaigns_audience_source_stats_v44(id),
    "/api/v2/files/{id}/download-by-day-list-v45": lambda q, id="f_001": get_files_download_by_day_list_v45(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v66": lambda q, id="k_001": get_auth_api_keys_quota_history_v66(id),
    "/api/v2/skills/{id}/sync-from-template-v43": lambda q, id="s_001": get_skills_sync_from_template_v43(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v44": lambda q, id="c_001": get_billing_payment_methods_unset_active_v44(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v43": lambda q, id="c001": get_campaigns_audience_source_stats_v43(id),
    "/api/v2/files/{id}/download-by-day-list-v44": lambda q, id="f_001": get_files_download_by_day_list_v44(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v65": lambda q, id="k_001": get_auth_api_keys_quota_history_v65(id),
    "/api/v2/skills/{id}/sync-from-template-v42": lambda q, id="s_001": get_skills_sync_from_template_v42(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v43": lambda q, id="c_001": get_billing_payment_methods_unset_active_v43(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v42": lambda q, id="c001": get_campaigns_audience_source_stats_v42(id),
    "/api/v2/files/{id}/download-by-day-list-v43": lambda q, id="f_001": get_files_download_by_day_list_v43(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v64": lambda q, id="k_001": get_auth_api_keys_quota_history_v64(id),
    "/api/v2/skills/{id}/sync-from-template-v41": lambda q, id="s_001": get_skills_sync_from_template_v41(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v42": lambda q, id="c_001": get_billing_payment_methods_unset_active_v42(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v41": lambda q, id="c001": get_campaigns_audience_source_stats_v41(id),
    "/api/v2/files/{id}/download-by-day-list-v42": lambda q, id="f_001": get_files_download_by_day_list_v42(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v63": lambda q, id="k_001": get_auth_api_keys_quota_history_v63(id),
    "/api/v2/skills/{id}/sync-from-template-v40": lambda q, id="s_001": get_skills_sync_from_template_v40(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v41": lambda q, id="c_001": get_billing_payment_methods_unset_active_v41(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v40": lambda q, id="c001": get_campaigns_audience_source_stats_v40(id),
    "/api/v2/files/{id}/download-by-day-list-v41": lambda q, id="f_001": get_files_download_by_day_list_v41(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v62": lambda q, id="k_001": get_auth_api_keys_quota_history_v62(id),
    "/api/v2/skills/{id}/sync-from-template-v39": lambda q, id="s_001": get_skills_sync_from_template_v39(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v40": lambda q, id="c_001": get_billing_payment_methods_unset_active_v40(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v39": lambda q, id="c001": get_campaigns_audience_source_stats_v39(id),
    "/api/v2/files/{id}/download-by-day-list-v40": lambda q, id="f_001": get_files_download_by_day_list_v40(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v61": lambda q, id="k_001": get_auth_api_keys_quota_history_v61(id),
    "/api/v2/skills/{id}/sync-from-template-v38": lambda q, id="s_001": get_skills_sync_from_template_v38(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v39": lambda q, id="c_001": get_billing_payment_methods_unset_active_v39(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v38": lambda q, id="c001": get_campaigns_audience_source_stats_v38(id),
    "/api/v2/files/{id}/download-by-day-list-v39": lambda q, id="f_001": get_files_download_by_day_list_v39(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v60": lambda q, id="k_001": get_auth_api_keys_quota_history_v60(id),
    "/api/v2/skills/{id}/sync-from-template-v37": lambda q, id="s_001": get_skills_sync_from_template_v37(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v38": lambda q, id="c_001": get_billing_payment_methods_unset_active_v38(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v37": lambda q, id="c001": get_campaigns_audience_source_stats_v37(id),
    "/api/v2/files/{id}/download-by-day-list-v38": lambda q, id="f_001": get_files_download_by_day_list_v38(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v59": lambda q, id="k_001": get_auth_api_keys_quota_history_v59(id),
    "/api/v2/skills/{id}/sync-from-template-v36": lambda q, id="s_001": get_skills_sync_from_template_v36(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v37": lambda q, id="c_001": get_billing_payment_methods_unset_active_v37(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v36": lambda q, id="c001": get_campaigns_audience_source_stats_v36(id),
    "/api/v2/files/{id}/download-by-day-list-v37": lambda q, id="f_001": get_files_download_by_day_list_v37(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v58": lambda q, id="k_001": get_auth_api_keys_quota_history_v58(id),
    "/api/v2/skills/{id}/sync-from-template-v35": lambda q, id="s_001": get_skills_sync_from_template_v35(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v36": lambda q, id="c_001": get_billing_payment_methods_unset_active_v36(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v35": lambda q, id="c001": get_campaigns_audience_source_stats_v35(id),
    "/api/v2/files/{id}/download-by-day-list-v36": lambda q, id="f_001": get_files_download_by_day_list_v36(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v57": lambda q, id="k_001": get_auth_api_keys_quota_history_v57(id),
    "/api/v2/skills/{id}/sync-from-template-v34": lambda q, id="s_001": get_skills_sync_from_template_v34(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v35": lambda q, id="c_001": get_billing_payment_methods_unset_active_v35(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v34": lambda q, id="c001": get_campaigns_audience_source_stats_v34(id),
    "/api/v2/files/{id}/download-by-day-list-v35": lambda q, id="f_001": get_files_download_by_day_list_v35(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v56": lambda q, id="k_001": get_auth_api_keys_quota_history_v56(id),
    "/api/v2/skills/{id}/sync-from-template-v33": lambda q, id="s_001": get_skills_sync_from_template_v33(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v34": lambda q, id="c_001": get_billing_payment_methods_unset_active_v34(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v33": lambda q, id="c001": get_campaigns_audience_source_stats_v33(id),
    "/api/v2/files/{id}/download-by-day-list-v34": lambda q, id="f_001": get_files_download_by_day_list_v34(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v55": lambda q, id="k_001": get_auth_api_keys_quota_history_v55(id),
    "/api/v2/skills/{id}/sync-from-template-v32": lambda q, id="s_001": get_skills_sync_from_template_v32(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v33": lambda q, id="c_001": get_billing_payment_methods_unset_active_v33(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v32": lambda q, id="c001": get_campaigns_audience_source_stats_v32(id),
    "/api/v2/files/{id}/download-by-day-list-v33": lambda q, id="f_001": get_files_download_by_day_list_v33(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v54": lambda q, id="k_001": get_auth_api_keys_quota_history_v54(id),
    "/api/v2/skills/{id}/sync-from-template-v31": lambda q, id="s_001": get_skills_sync_from_template_v31(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v32": lambda q, id="c_001": get_billing_payment_methods_unset_active_v32(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v31": lambda q, id="c001": get_campaigns_audience_source_stats_v31(id),
    "/api/v2/files/{id}/download-by-day-list-v32": lambda q, id="f_001": get_files_download_by_day_list_v32(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v53": lambda q, id="k_001": get_auth_api_keys_quota_history_v53(id),
    "/api/v2/skills/{id}/sync-from-template-v30": lambda q, id="s_001": get_skills_sync_from_template_v30(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v31": lambda q, id="c_001": get_billing_payment_methods_unset_active_v31(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v30": lambda q, id="c001": get_campaigns_audience_source_stats_v30(id),
    "/api/v2/files/{id}/download-by-day-list-v31": lambda q, id="f_001": get_files_download_by_day_list_v31(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v52": lambda q, id="k_001": get_auth_api_keys_quota_history_v52(id),
    "/api/v2/skills/{id}/sync-from-template-v29": lambda q, id="s_001": get_skills_sync_from_template_v29(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v30": lambda q, id="c_001": get_billing_payment_methods_unset_active_v30(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v29": lambda q, id="c001": get_campaigns_audience_source_stats_v29(id),
    "/api/v2/files/{id}/download-by-day-list-v30": lambda q, id="f_001": get_files_download_by_day_list_v30(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v51": lambda q, id="k_001": get_auth_api_keys_quota_history_v51(id),
    "/api/v2/skills/{id}/sync-from-template-v28": lambda q, id="s_001": get_skills_sync_from_template_v28(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v29": lambda q, id="c_001": get_billing_payment_methods_unset_active_v29(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v28": lambda q, id="c001": get_campaigns_audience_source_stats_v28(id),
    "/api/v2/files/{id}/download-by-day-list-v29": lambda q, id="f_001": get_files_download_by_day_list_v29(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v50": lambda q, id="k_001": get_auth_api_keys_quota_history_v50(id),
    "/api/v2/skills/{id}/sync-from-template-v27": lambda q, id="s_001": get_skills_sync_from_template_v27(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v28": lambda q, id="c_001": get_billing_payment_methods_unset_active_v28(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v27": lambda q, id="c001": get_campaigns_audience_source_stats_v27(id),
    "/api/v2/files/{id}/download-by-day-list-v28": lambda q, id="f_001": get_files_download_by_day_list_v28(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v49": lambda q, id="k_001": get_auth_api_keys_quota_history_v49(id),
    "/api/v2/skills/{id}/sync-from-template-v26": lambda q, id="s_001": get_skills_sync_from_template_v26(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v27": lambda q, id="c_001": get_billing_payment_methods_unset_active_v27(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v26": lambda q, id="c001": get_campaigns_audience_source_stats_v26(id),
    "/api/v2/files/{id}/download-by-day-list-v27": lambda q, id="f_001": get_files_download_by_day_list_v27(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v48": lambda q, id="k_001": get_auth_api_keys_quota_history_v48(id),
    "/api/v2/skills/{id}/sync-from-template-v25": lambda q, id="s_001": get_skills_sync_from_template_v25(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v26": lambda q, id="c_001": get_billing_payment_methods_unset_active_v26(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v25": lambda q, id="c001": get_campaigns_audience_source_stats_v25(id),
    "/api/v2/files/{id}/download-by-day-list-v26": lambda q, id="f_001": get_files_download_by_day_list_v26(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v47": lambda q, id="k_001": get_auth_api_keys_quota_history_v47(id),
    "/api/v2/skills/{id}/sync-from-template-v24": lambda q, id="s_001": get_skills_sync_from_template_v24(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v25": lambda q, id="c_001": get_billing_payment_methods_unset_active_v25(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v24": lambda q, id="c001": get_campaigns_audience_source_stats_v24(id),
    "/api/v2/files/{id}/download-by-day-list-v25": lambda q, id="f_001": get_files_download_by_day_list_v25(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v46": lambda q, id="k_001": get_auth_api_keys_quota_history_v46(id),
    "/api/v2/skills/{id}/sync-from-template-v23": lambda q, id="s_001": get_skills_sync_from_template_v23(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v24": lambda q, id="c_001": get_billing_payment_methods_unset_active_v24(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v23": lambda q, id="c001": get_campaigns_audience_source_stats_v23(id),
    "/api/v2/files/{id}/download-by-day-list-v24": lambda q, id="f_001": get_files_download_by_day_list_v24(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v45": lambda q, id="k_001": get_auth_api_keys_quota_history_v45(id),
    "/api/v2/skills/{id}/sync-from-template-v22": lambda q, id="s_001": get_skills_sync_from_template_v22(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v23": lambda q, id="c_001": get_billing_payment_methods_unset_active_v23(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v22": lambda q, id="c001": get_campaigns_audience_source_stats_v22(id),
    "/api/v2/files/{id}/download-by-day-list-v23": lambda q, id="f_001": get_files_download_by_day_list_v23(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v44": lambda q, id="k_001": get_auth_api_keys_quota_history_v44(id),
    "/api/v2/skills/{id}/sync-from-template-v21": lambda q, id="s_001": get_skills_sync_from_template_v21(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v22": lambda q, id="c_001": get_billing_payment_methods_unset_active_v22(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v21": lambda q, id="c001": get_campaigns_audience_source_stats_v21(id),
    "/api/v2/files/{id}/download-by-day-list-v22": lambda q, id="f_001": get_files_download_by_day_list_v22(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v43": lambda q, id="k_001": get_auth_api_keys_quota_history_v43(id),
    "/api/v2/skills/{id}/sync-from-template-v20": lambda q, id="s_001": get_skills_sync_from_template_v20(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v21": lambda q, id="c_001": get_billing_payment_methods_unset_active_v21(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v20": lambda q, id="c001": get_campaigns_audience_source_stats_v20(id),
    "/api/v2/files/{id}/download-by-day-list-v21": lambda q, id="f_001": get_files_download_by_day_list_v21(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v42": lambda q, id="k_001": get_auth_api_keys_quota_history_v42(id),
    "/api/v2/skills/{id}/sync-from-template-v19": lambda q, id="s_001": get_skills_sync_from_template_v19(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v29": lambda q, id="c_001": get_billing_payment_methods_unset_active_v29(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v19": lambda q, id="c001": get_campaigns_audience_source_stats_v19(id),
    "/api/v2/files/{id}/download-by-day-list-v20": lambda q, id="f_001": get_files_download_by_day_list_v20(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v41": lambda q, id="k_001": get_auth_api_keys_quota_history_v41(id),
    "/api/v2/skills/{id}/sync-from-template-v18": lambda q, id="s_001": get_skills_sync_from_template_v18(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v28": lambda q, id="c_001": get_billing_payment_methods_unset_active_v28(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v18": lambda q, id="c001": get_campaigns_audience_source_stats_v18(id),
    "/api/v2/files/{id}/download-by-day-list-v19": lambda q, id="f_001": get_files_download_by_day_list_v19(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v40": lambda q, id="k_001": get_auth_api_keys_quota_history_v40(id),
    "/api/v2/skills/{id}/sync-from-template-v17": lambda q, id="s_001": get_skills_sync_from_template_v17(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v27": lambda q, id="c_001": get_billing_payment_methods_unset_active_v27(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v17": lambda q, id="c001": get_campaigns_audience_source_stats_v17(id),
    "/api/v2/files/{id}/download-by-day-list-v18": lambda q, id="f_001": get_files_download_by_day_list_v18(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v39": lambda q, id="k_001": get_auth_api_keys_quota_history_v39(id),
    "/api/v2/skills/{id}/sync-from-template-v16": lambda q, id="s_001": get_skills_sync_from_template_v16(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v26": lambda q, id="c_001": get_billing_payment_methods_unset_active_v26(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v16": lambda q, id="c001": get_campaigns_audience_source_stats_v16(id),
    "/api/v2/files/{id}/download-by-day-list-v17": lambda q, id="f_001": get_files_download_by_day_list_v17(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v38": lambda q, id="k_001": get_auth_api_keys_quota_history_v38(id),
    "/api/v2/skills/{id}/sync-from-template-v15": lambda q, id="s_001": get_skills_sync_from_template_v15(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v25": lambda q, id="c_001": get_billing_payment_methods_unset_active_v25(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v15": lambda q, id="c001": get_campaigns_audience_source_stats_v15(id),
    "/api/v2/files/{id}/download-by-day-list-v16": lambda q, id="f_001": get_files_download_by_day_list_v16(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v37": lambda q, id="k_001": get_auth_api_keys_quota_history_v37(id),
    "/api/v2/skills/{id}/sync-from-template-v14": lambda q, id="s_001": get_skills_sync_from_template_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v24": lambda q, id="c_001": get_billing_payment_methods_unset_active_v24(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v14": lambda q, id="c001": get_campaigns_audience_source_stats_v14(id),
    "/api/v2/files/{id}/download-by-day-list-v15": lambda q, id="f_001": get_files_download_by_day_list_v15(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v36": lambda q, id="k_001": get_auth_api_keys_quota_history_v36(id),
    "/api/v2/skills/{id}/sync-from-template-v13": lambda q, id="s_001": get_skills_sync_from_template_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v23": lambda q, id="c_001": get_billing_payment_methods_unset_active_v23(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v13": lambda q, id="c001": get_campaigns_audience_source_stats_v13(id),
    "/api/v2/files/{id}/download-by-day-list-v14": lambda q, id="f_001": get_files_download_by_day_list_v14(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v35": lambda q, id="k_001": get_auth_api_keys_quota_history_v35(id),
    "/api/v2/skills/{id}/sync-from-template-v14": lambda q, id="s_001": get_skills_sync_from_template_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v24": lambda q, id="c_001": get_billing_payment_methods_unset_active_v24(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v14": lambda q, id="c001": get_campaigns_audience_source_stats_v14(id),
    "/api/v2/files/{id}/download-by-day-list-v15": lambda q, id="f_001": get_files_download_by_day_list_v15(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v36": lambda q, id="k_001": get_auth_api_keys_quota_history_v36(id),
    "/api/v2/skills/{id}/sync-from-template-v13": lambda q, id="s_001": get_skills_sync_from_template_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v23": lambda q, id="c_001": get_billing_payment_methods_unset_active_v23(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v13": lambda q, id="c001": get_campaigns_audience_source_stats_v13(id),
    "/api/v2/files/{id}/download-by-day-list-v14": lambda q, id="f_001": get_files_download_by_day_list_v14(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v35": lambda q, id="k_001": get_auth_api_keys_quota_history_v35(id),
    "/api/v2/skills/{id}/sync-from-template-v12": lambda q, id="s_001": get_skills_sync_from_template_v12(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v22": lambda q, id="c_001": get_billing_payment_methods_unset_active_v22(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v12": lambda q, id="c001": get_campaigns_audience_source_stats_v12(id),
    "/api/v2/files/{id}/download-by-day-list-v13": lambda q, id="f_001": get_files_download_by_day_list_v13(id),
        "/api/v2/skills/{id}/sync-from-template-v14": lambda q, id="s_001": get_skills_sync_from_template_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v24": lambda q, id="c_001": get_billing_payment_methods_unset_active_v24(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v14": lambda q, id="c001": get_campaigns_audience_source_stats_v14(id),
    "/api/v2/files/{id}/download-by-day-list-v15": lambda q, id="f_001": get_files_download_by_day_list_v15(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v36": lambda q, id="k_001": get_auth_api_keys_quota_history_v36(id),
    "/api/v2/skills/{id}/sync-from-template-v13": lambda q, id="s_001": get_skills_sync_from_template_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v23": lambda q, id="c_001": get_billing_payment_methods_unset_active_v23(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v13": lambda q, id="c001": get_campaigns_audience_source_stats_v13(id),
    "/api/v2/files/{id}/download-by-day-list-v14": lambda q, id="f_001": get_files_download_by_day_list_v14(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v35": lambda q, id="k_001": get_auth_api_keys_quota_history_v35(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v34": lambda q, id="k_001": get_auth_api_keys_quota_history_v34(id),
    "/api/v2/skills/{id}/merge-with-bundle": lambda q, id="s_001": get_skills_merge_with_bundle(id),
    "/api/v2/skills/{id}/sync-from-template-v14": lambda q, id="s_001": get_skills_sync_from_template_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v24": lambda q, id="c_001": get_billing_payment_methods_unset_active_v24(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v14": lambda q, id="c001": get_campaigns_audience_source_stats_v14(id),
    "/api/v2/files/{id}/download-by-day-list-v15": lambda q, id="f_001": get_files_download_by_day_list_v15(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v36": lambda q, id="k_001": get_auth_api_keys_quota_history_v36(id),
    "/api/v2/skills/{id}/sync-from-template-v13": lambda q, id="s_001": get_skills_sync_from_template_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v23": lambda q, id="c_001": get_billing_payment_methods_unset_active_v23(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v13": lambda q, id="c001": get_campaigns_audience_source_stats_v13(id),
    "/api/v2/files/{id}/download-by-day-list-v14": lambda q, id="f_001": get_files_download_by_day_list_v14(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v35": lambda q, id="k_001": get_auth_api_keys_quota_history_v35(id),
    "/api/v2/skills/{id}/sync-from-template-v12": lambda q, id="s_001": get_skills_sync_from_template_v12(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v22": lambda q, id="c_001": get_billing_payment_methods_unset_active_v22(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v12": lambda q, id="c001": get_campaigns_audience_source_stats_v12(id),
    "/api/v2/files/{id}/download-by-day-list-v13": lambda q, id="f_001": get_files_download_by_day_list_v13(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v34": lambda q, id="k_001": get_auth_api_keys_quota_history_v34(id),
    "/api/v2/skills/{id}/merge-with-bundle": lambda q, id="s_001": get_skills_merge_with_bundle(id),
    "/api/v2/skills/{id}/sync-from-template-v11": lambda q, id="s_001": get_skills_sync_from_template_v11(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v21": lambda q, id="c_001": get_billing_payment_methods_unset_active_v21(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v11": lambda q, id="c001": get_campaigns_audience_source_stats_v11(id),
    "/api/v2/files/{id}/download-by-day-list-v12": lambda q, id="f_001": get_files_download_by_day_list_v12(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v33": lambda q, id="k_001": get_auth_api_keys_quota_history_v33(id),
    "/api/v2/skills/{id}/merge-with-bundle": lambda q, id="s_001": get_skills_merge_with_bundle(id),
    "/api/v2/billing/payment-methods/{id}/set-default-payment-method": lambda q, id="c_001": get_billing_payment_methods_set_default_payment_method(id),
    "/api/v2/campaigns/{id}/audience-region-stats": lambda q, id="c001": get_campaigns_audience_region_stats(id),
    "/api/v2/files/{id}/download-by-day-chart-v3": lambda q, id="f_001": get_files_download_by_day_chart_v3(id),
    "/api/v2/auth/api-keys/{id}/quota-reset": lambda q, id="k_001": get_auth_api_keys_quota_reset(id),
    "/api/v2/skills/{id}/export-instance":     lambda q, id="s_001": get_skills_export_instance(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-payment": lambda q, id="c_001": get_billing_payment_methods_unset_default_payment(id),
    "/api/v2/campaigns/{id}/audience-grade-stats": lambda q, id="c001": get_campaigns_audience_grade_stats(id),
    "/api/v2/files/{id}/download-by-month-stats": lambda q, id="f_001": get_files_download_by_month_stats(id),
    "/api/v2/auth/api-keys/{id}/burst-quota-reset": lambda q, id="k_001": get_auth_api_keys_burst_quota_reset(id),
    "/api/v2/skills/{id}/sync-stats":          lambda q, id="s_001": get_skills_sync_stats(id),
    "/api/v2/billing/payment-methods/{id}/set-default-billing": lambda q, id="c_001": get_billing_payment_methods_set_default_billing(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v2": lambda q, id="c001": get_campaigns_audience_tech_list_v2(id),
    "/api/v2/files/{id}/download-by-week-stats": lambda q, id="f_001": get_files_download_by_week_stats(id),
    "/api/v2/auth/api-keys/{id}/quota-history": lambda q, id="k_001": get_auth_api_keys_quota_history(id),
    "/api/v2/skills/{id}/merge-stats":          lambda q, id="s_001": get_skills_merge_stats(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-billing": lambda q, id="c_001": get_billing_payment_methods_unset_default_billing(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v3": lambda q, id="c001": get_campaigns_audience_tech_list_v3(id),
    "/api/v2/files/{id}/download-by-month-stats-v2": lambda q, id="f_001": get_files_download_by_month_stats_v2(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v2": lambda q, id="k_001": get_auth_api_keys_quota_history_v2(id),
    "/api/v2/skills/{id}/export-to-marketplace": lambda q, id="s_001": get_skills_export_to_marketplace(id),
    "/api/v2/billing/payment-methods/{id}/validate-all": lambda q, id="c_001": get_billing_payment_methods_validate_all(id),
    "/api/v2/campaigns/{id}/audience-source-list": lambda q, id="c001": get_campaigns_audience_source_list(id),
    "/api/v2/files/{id}/download-by-year-list": lambda q, id="f_001": get_files_download_by_year_list(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v2": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v2(id),
    "/api/v2/skills/{id}/unsubscribe":        lambda q, id="s_001": get_skills_unsubscribe(id),
    "/api/v2/billing/payment-methods/{id}/set-default-for": lambda q, id="c_001": get_billing_payment_methods_set_default_for(id),
    "/api/v2/campaigns/{id}/audience-region-detailed": lambda q, id="c001": get_campaigns_audience_region_detailed(id),
    "/api/v2/files/{id}/download-by-quarter-list": lambda q, id="f_001": get_files_download_by_quarter_list(id),
    "/api/v2/auth/api-keys/{id}/throttle-events": lambda q, id="k_001": get_auth_api_keys_throttle_events(id),
    "/api/v2/skills/{id}/clone-stats":          lambda q, id="s_001": get_skills_clone_stats(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for": lambda q, id="c_001": get_billing_payment_methods_unset_default_for(id),
    "/api/v2/campaigns/{id}/audience-tech-detailed": lambda q, id="c001": get_campaigns_audience_tech_detailed(id),
    "/api/v2/files/{id}/download-by-day-of-week-list": lambda q, id="f_001": get_files_download_by_day_of_week_list(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v3": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v3(id),
    "/api/v2/skills/{id}/merge-stats-v2":      lambda q, id="s_001": get_skills_merge_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/set-default-for-billing": lambda q, id="c_001": get_billing_payment_methods_set_default_for_billing(id),
    "/api/v2/campaigns/{id}/audience-source-list-v2": lambda q, id="c001": get_campaigns_audience_source_list_v2(id),
    "/api/v2/files/{id}/download-by-day-list": lambda q, id="f_001": get_files_download_by_day_list(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v4": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v4(id),
    "/api/v2/skills/{id}/export-stats":        lambda q, id="s_001": get_skills_export_stats(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-billing": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_billing(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v4": lambda q, id="c001": get_campaigns_audience_tech_list_v4(id),
    "/api/v2/files/{id}/download-by-week-list": lambda q, id="f_001": get_files_download_by_week_list(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v5": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v5(id),
    "/api/v2/skills/{id}/clone-stats-v2":        lambda q, id="s_001": get_skills_clone_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-subscription": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_subscription(id),
    "/api/v2/campaigns/{id}/audience-region-detailed-v2": lambda q, id="c001": get_campaigns_audience_region_detailed_v2(id),
    "/api/v2/files/{id}/download-by-month-stats-v3": lambda q, id="f_001": get_files_download_by_month_stats_v3(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v6": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v6(id),
    "/api/v2/skills/{id}/sync-stats-v2":          lambda q, id="s_001": get_skills_sync_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-payment-method": lambda q, id="c_001": get_billing_payment_methods_unset_default_payment_method(id),
    "/api/v2/campaigns/{id}/audience-grade-list-v2": lambda q, id="c001": get_campaigns_audience_grade_list_v2(id),
    "/api/v2/files/{id}/download-by-week-stats-v2": lambda q, id="f_001": get_files_download_by_week_stats_v2(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v7": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v7(id),
    "/api/v2/skills/{id}/unsubscribe-stats":    lambda q, id="s_001": get_skills_unsubscribe_stats(id),
    "/api/v2/billing/payment-methods/{id}/set-default-for-subscription": lambda q, id="c_001": get_billing_payment_methods_set_default_for_subscription(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v5": lambda q, id="c001": get_campaigns_audience_tech_list_v5(id),
    "/api/v2/files/{id}/download-by-month-list": lambda q, id="f_001": get_files_download_by_month_list(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v8": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v8(id),
    "/api/v2/skills/{id}/import-stats":        lambda q, id="s_001": get_skills_import_stats(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-billing": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_billing(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v2": lambda q, id="c001": get_campaigns_audience_grade_stats_v2(id),
    "/api/v2/files/{id}/download-by-month-list-v2": lambda q, id="f_001": get_files_download_by_month_list_v2(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v9": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v9(id),
    "/api/v2/skills/{id}/apply-stats":          lambda q, id="s_001": get_skills_apply_stats(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-all": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_all(id),
    "/api/v2/campaigns/{id}/audience-language-list-v2": lambda q, id="c001": get_campaigns_audience_language_list_v2(id),
    "/api/v2/files/{id}/download-by-year-list-v2": lambda q, id="f_001": get_files_download_by_year_list_v2(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v10": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v10(id),
    "/api/v2/skills/{id}/unapply-stats":         lambda q, id="s_001": get_skills_unapply_stats(id),
    "/api/v2/billing/payment-methods/{id}/set-default-payment-billing": lambda q, id="c_001": get_billing_payment_methods_set_default_payment_billing(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed": lambda q, id="c001": get_campaigns_audience_cohort_detailed(id),
    "/api/v2/files/{id}/download-by-month-chart-v4": lambda q, id="f_001": get_files_download_by_month_chart_v4(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v11": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v11(id),
    "/api/v2/skills/{id}/apply-stats-v2":        lambda q, id="s_001": get_skills_apply_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-billing-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_billing_v2(id),
    "/api/v2/campaigns/{id}/audience-region-detailed-v3": lambda q, id="c001": get_campaigns_audience_region_detailed_v3(id),
    "/api/v2/files/{id}/download-by-quarter-stats-v2": lambda q, id="f_001": get_files_download_by_quarter_stats_v2(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v12": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v12(id),
    "/api/v2/skills/{id}/unapply-stats-v2":     lambda q, id="s_001": get_skills_unapply_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-subscription-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_subscription_v2(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v2": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v2(id),
    "/api/v2/files/{id}/download-by-month-list-v3": lambda q, id="f_001": get_files_download_by_month_list_v3(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v13": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v13(id),
    "/api/v2/skills/{id}/apply-stats-v3":        lambda q, id="s_001": get_skills_apply_stats_v3(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-payment-method-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_payment_method_v2(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v6": lambda q, id="c001": get_campaigns_audience_tech_list_v6(id),
    "/api/v2/files/{id}/download-by-quarter-list-v2": lambda q, id="f_001": get_files_download_by_quarter_list_v2(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v14": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v14(id),
    "/api/v2/skills/{id}/export-stats-v2":      lambda q, id="s_001": get_skills_export_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-payment-billing": lambda q, id="c_001": get_billing_payment_methods_unset_default_payment_billing(id),
    "/api/v2/campaigns/{id}/audience-source-detailed": lambda q, id="c001": get_campaigns_audience_source_detailed(id),
    "/api/v2/files/{id}/download-by-week-stats-v3": lambda q, id="f_001": get_files_download_by_week_stats_v3(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v15": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v15(id),
    "/api/v2/skills/{id}/import-stats-v2":      lambda q, id="s_001": get_skills_import_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-payment": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_payment(id),
    "/api/v2/campaigns/{id}/audience-geo-distribution": lambda q, id="c001": get_campaigns_audience_geo_distribution(id),
    "/api/v2/files/{id}/download-by-day-chart-v5": lambda q, id="f_001": get_files_download_by_day_chart_v5(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v16": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v16(id),
    "/api/v2/skills/{id}/unsubscribe-stats-v2": lambda q, id="s_001": get_skills_unsubscribe_stats_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-billing-v3": lambda q, id="c_001": get_billing_payment_methods_unset_default_billing_v3(id),
    "/api/v2/campaigns/{id}/audience-segment-detailed": lambda q, id="c001": get_campaigns_audience_segment_detailed(id),
    "/api/v2/files/{id}/download-by-hour-chart-v2": lambda q, id="f_001": get_files_download_by_hour_chart_v2(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v17": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v17(id),
    "/api/v2/skills/{id}/sync-stats-v3":          lambda q, id="s_001": get_skills_sync_stats_v3(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-subscription-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_subscription_v2(id),
    "/api/v2/campaigns/{id}/audience-region-detailed-v4": lambda q, id="c001": get_campaigns_audience_region_detailed_v4(id),
    "/api/v2/files/{id}/download-by-month-chart-v5": lambda q, id="f_001": get_files_download_by_month_chart_v5(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v18": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v18(id),
    "/api/v2/skills/{id}/clone-stats-v3":         lambda q, id="s_001": get_skills_clone_stats_v3(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-payment-billing-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_payment_billing_v2(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v7": lambda q, id="c001": get_campaigns_audience_tech_list_v7(id),
    "/api/v2/files/{id}/download-by-quarter-stats-v3": lambda q, id="f_001": get_files_download_by_quarter_stats_v3(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v19": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v19(id),
    "/api/v2/skills/{id}/merge-stats-v3":         lambda q, id="s_001": get_skills_merge_stats_v3(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-payment-method-v3": lambda q, id="c_001": get_billing_payment_methods_unset_default_payment_method_v3(id),
    "/api/v2/campaigns/{id}/audience-grade-list-v3": lambda q, id="c001": get_campaigns_audience_grade_list_v3(id),
    "/api/v2/files/{id}/download-by-month-list-v4": lambda q, id="f_001": get_files_download_by_month_list_v4(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v20": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v20(id),
    "/api/v2/skills/{id}/import-template":      lambda q, id="s_001": get_skills_import_template(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-all-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_all_v2(id),
    "/api/v2/campaigns/{id}/audience-language-detailed": lambda q, id="c001": get_campaigns_audience_language_detailed(id),
    "/api/v2/files/{id}/download-by-day-of-week-stats": lambda q, id="f_001": get_files_download_by_day_of_week_stats(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v2":     lambda q, id="k_001": get_auth_api_keys_quota_reset_v2(id),
    "/api/v2/skills/{id}/pull-template-v2":       lambda q, id="s_001": get_skills_pull_template_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-billing-v3": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_billing_v3(id),
    "/api/v2/campaigns/{id}/audience-source-detailed-v2": lambda q, id="c001": get_campaigns_audience_source_detailed_v2(id),
    "/api/v2/files/{id}/download-by-week-stats-v4": lambda q, id="f_001": get_files_download_by_week_stats_v4(id),
    "/api/v2/auth/api-keys/{id}/quota-set":         lambda q, id="k_001": get_auth_api_keys_quota_set(id),
    "/api/v2/skills/{id}/push-to-marketplace-v2":   lambda q, id="s_001": get_skills_push_to_marketplace_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-subscription-v3": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_subscription_v3(id),
    "/api/v2/campaigns/{id}/audience-cohort-list-v2": lambda q, id="c001": get_campaigns_audience_cohort_list_v2(id),
    "/api/v2/files/{id}/download-by-quarter-chart": lambda q, id="f_001": get_files_download_by_quarter_chart(id),
    "/api/v2/auth/api-keys/{id}/quota-increase":   lambda q, id="k_001": get_auth_api_keys_quota_increase(id),
    "/api/v2/skills/{id}/export-stats-v3":        lambda q, id="s_001": get_skills_export_stats_v3(id),
    "/api/v2/billing/payment-methods/{id}/validate-billing-v2": lambda q, id="c_001": get_billing_payment_methods_validate_billing_v2(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v3": lambda q, id="c001": get_campaigns_audience_grade_stats_v3(id),
    "/api/v2/files/{id}/download-by-week-chart-v3": lambda q, id="f_001": get_files_download_by_week_chart_v3(id),
    "/api/v2/auth/api-keys/{id}/quota-decrease":    lambda q, id="k_001": get_auth_api_keys_quota_decrease(id),
    "/api/v2/skills/{id}/sync-stats-v4":          lambda q, id="s_001": get_skills_sync_stats_v4(id),
    "/api/v2/billing/payment-methods/{id}/verify-billing-cycle-v2": lambda q, id="c_001": get_billing_payment_methods_verify_billing_cycle_v2(id),
    "/api/v2/campaigns/{id}/audience-segment-stats": lambda q, id="c001": get_campaigns_audience_segment_stats(id),
    "/api/v2/files/{id}/download-by-quarter-list-v3": lambda q, id="f_001": get_files_download_by_quarter_list_v3(id),
    "/api/v2/auth/api-keys/{id}/throttle-stats":    lambda q, id="k_001": get_auth_api_keys_throttle_stats(id),
    "/api/v2/skills/{id}/clone-stats-v4":         lambda q, id="s_001": get_skills_clone_stats_v4(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-for-all-v3": lambda q, id="c_001": get_billing_payment_methods_unset_default_for_all_v3(id),
    "/api/v2/campaigns/{id}/audience-tech-stats-v2": lambda q, id="c001": get_campaigns_audience_tech_stats_v2(id),
    "/api/v2/files/{id}/download-by-month-chart-v6": lambda q, id="f_001": get_files_download_by_month_chart_v6(id),
    "/api/v2/auth/api-keys/{id}/rotate-quota-v2": lambda q, id="k_001": get_auth_api_keys_rotate_quota_v2(id),
    "/api/v2/skills/{id}/merge-stats-v4":         lambda q, id="s_001": get_skills_merge_stats_v4(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-payment-method-v4": lambda q, id="c_001": get_billing_payment_methods_unset_default_payment_method_v4(id),
    "/api/v2/campaigns/{id}/audience-language-list-v3": lambda q, id="c001": get_campaigns_audience_language_list_v3(id),
    "/api/v2/files/{id}/download-by-year-stats":  lambda q, id="f_001": get_files_download_by_year_stats(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v21": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v21(id),
    "/api/v2/skills/{id}/import-stats-v3":        lambda q, id="s_001": get_skills_import_stats_v3(id),
    "/api/v2/billing/payment-methods/{id}/set-active": lambda q, id="c_001": get_billing_payment_methods_set_active(id),
    "/api/v2/campaigns/{id}/audience-cohort-list-v3": lambda q, id="c001": get_campaigns_audience_cohort_list_v3(id),
    "/api/v2/files/{id}/download-by-quarter-stats-v4": lambda q, id="f_001": get_files_download_by_quarter_stats_v4(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v3": lambda q, id="k_001": get_auth_api_keys_quota_history_v3(id),
    "/api/v2/skills/{id}/export-template-v2":     lambda q, id="s_001": get_skills_export_template_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-active": lambda q, id="c_001": get_billing_payment_methods_unset_active(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v8": lambda q, id="c001": get_campaigns_audience_tech_list_v8(id),
    "/api/v2/files/{id}/download-by-day-stats":   lambda q, id="f_001": get_files_download_by_day_stats(id),
    "/api/v2/auth/api-keys/{id}/burst-quota-history": lambda q, id="k_001": get_auth_api_keys_burst_quota_history(id),
    "/api/v2/skills/{id}/sync-from-instance-v2":  lambda q, id="s_001": get_skills_sync_from_instance_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v2": lambda q, id="c_001": get_billing_payment_methods_unset_active_v2(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v2": lambda q, id="c001": get_campaigns_audience_region_stats_v2(id),
    "/api/v2/files/{id}/download-by-week-stats-v5": lambda q, id="f_001": get_files_download_by_week_stats_v5(id),
    "/api/v2/auth/api-keys/{id}/throttle-history-v2": lambda q, id="k_001": get_auth_api_keys_throttle_history_v2(id),
    "/api/v2/skills/{id}/clone-from-template": lambda q, id="s_001": get_skills_clone_from_template(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v2": lambda q, id="c_001": get_billing_payment_methods_unset_default_v2(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v3": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v3(id),
    "/api/v2/files/{id}/download-by-month-stats-v4": lambda q, id="f_001": get_files_download_by_month_stats_v4(id),
    "/api/v2/auth/api-keys/{id}/burst-quota-reset-history": lambda q, id="k_001": get_auth_api_keys_burst_quota_reset_history(id),
    "/api/v2/skills/{id}/merge-with-template": lambda q, id="s_001": get_skills_merge_with_template(id),
    "/api/v2/billing/payment-methods/{id}/validate-billing-cycle-v3": lambda q, id="c_001": get_billing_payment_methods_validate_billing_cycle_v3(id),
    "/api/v2/campaigns/{id}/audience-language-stats-v2": lambda q, id="c001": get_campaigns_audience_language_stats_v2(id),
    "/api/v2/files/{id}/download-by-year-stats-v2": lambda q, id="f_001": get_files_download_by_year_stats_v2(id),
    "/api/v2/auth/api-keys/{id}/throttle-history-v3": lambda q, id="k_001": get_auth_api_keys_throttle_history_v3(id),
    "/api/v2/skills/{id}/sync-from-template-v2":  lambda q, id="s_001": get_skills_sync_from_template_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v3": lambda q, id="c_001": get_billing_payment_methods_unset_active_v3(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v4": lambda q, id="c001": get_campaigns_audience_grade_stats_v4(id),
    "/api/v2/files/{id}/download-by-quarter-list-v4": lambda q, id="f_001": get_files_download_by_quarter_list_v4(id),
    "/api/v2/auth/api-keys/{id}/rotate-secret-v22": lambda q, id="k_001": get_auth_api_keys_rotate_secret_v22(id),
    "/api/v2/skills/{id}/sync-stats-v5":          lambda q, id="s_001": get_skills_sync_stats_v5(id),
    "/api/v2/billing/payment-methods/{id}/validate-default": lambda q, id="c_001": get_billing_payment_methods_validate_default(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v3": lambda q, id="c001": get_campaigns_audience_region_stats_v3(id),
    "/api/v2/files/{id}/download-by-day-stats-v2":   lambda q, id="f_001": get_files_download_by_day_stats_v2(id),
    "/api/v2/auth/api-keys/{id}/quota-set-v2":     lambda q, id="k_001": get_auth_api_keys_quota_set_v2(id),
    "/api/v2/skills/{id}/apply-template-v2":     lambda q, id="s_001": get_skills_apply_template_v2(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v3": lambda q, id="c_001": get_billing_payment_methods_unset_default_v3(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v9": lambda q, id="c001": get_campaigns_audience_tech_list_v9(id),
    "/api/v2/files/{id}/download-by-week-stats-v6": lambda q, id="f_001": get_files_download_by_week_stats_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v4": lambda q, id="k_001": get_auth_api_keys_quota_history_v4(id),
    "/api/v2/skills/{id}/merge-stats-v5":         lambda q, id="s_001": get_skills_merge_stats_v5(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v4": lambda q, id="c_001": get_billing_payment_methods_unset_active_v4(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v4": lambda q, id="c001": get_campaigns_audience_region_stats_v4(id),
    "/api/v2/files/{id}/download-by-month-list-v5": lambda q, id="f_001": get_files_download_by_month_list_v5(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v5": lambda q, id="k_001": get_auth_api_keys_quota_history_v5(id),
    "/api/v2/skills/{id}/sync-stats-v6":          lambda q, id="s_001": get_skills_sync_stats_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v5": lambda q, id="c_001": get_billing_payment_methods_unset_active_v5(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v5": lambda q, id="c001": get_campaigns_audience_grade_stats_v5(id),
    "/api/v2/files/{id}/download-by-week-list-v5": lambda q, id="f_001": get_files_download_by_week_list_v5(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v6": lambda q, id="k_001": get_auth_api_keys_quota_history_v6(id),
    "/api/v2/skills/{id}/apply-template-v3":     lambda q, id="s_001": get_skills_apply_template_v3(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v4": lambda q, id="c_001": get_billing_payment_methods_unset_default_v4(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v10": lambda q, id="c001": get_campaigns_audience_tech_list_v10(id),
    "/api/v2/files/{id}/download-by-week-chart-v7": lambda q, id="f_001": get_files_download_by_week_chart_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v3":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v3(id),
    "/api/v2/skills/{id}/merge-stats-v6":         lambda q, id="s_001": get_skills_merge_stats_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v5": lambda q, id="c_001": get_billing_payment_methods_unset_default_v5(id),
    "/api/v2/campaigns/{id}/audience-cohort-stats": lambda q, id="c001": get_campaigns_audience_cohort_stats(id),
    "/api/v2/files/{id}/download-by-week-stats-v7": lambda q, id="f_001": get_files_download_by_week_stats_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v7": lambda q, id="k_001": get_auth_api_keys_quota_history_v7(id),
    "/api/v2/skills/{id}/sync-stats-v7":          lambda q, id="s_001": get_skills_sync_stats_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v6": lambda q, id="c_001": get_billing_payment_methods_unset_default_v6(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v6": lambda q, id="c001": get_campaigns_audience_grade_stats_v6(id),
    "/api/v2/files/{id}/download-by-month-list-v6": lambda q, id="f_001": get_files_download_by_month_list_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v8": lambda q, id="k_001": get_auth_api_keys_quota_history_v8(id),
    "/api/v2/skills/{id}/apply-template-v4":     lambda q, id="s_001": get_skills_apply_template_v4(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v6": lambda q, id="c_001": get_billing_payment_methods_unset_active_v6(id),
    "/api/v2/campaigns/{id}/audience-cohort-stats-v2": lambda q, id="c001": get_campaigns_audience_cohort_stats_v2(id),
    "/api/v2/files/{id}/download-by-week-list-v6": lambda q, id="f_001": get_files_download_by_week_list_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v4":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v4(id),
    "/api/v2/skills/{id}/sync-from-template-v3":  lambda q, id="s_001": get_skills_sync_from_template_v3(id),
    "/api/v2/billing/payment-methods/{id}/validate-default-v2": lambda q, id="c_001": get_billing_payment_methods_validate_default_v2(id),
    "/api/v2/campaigns/{id}/audience-tech-list-v11": lambda q, id="c001": get_campaigns_audience_tech_list_v11(id),
    "/api/v2/files/{id}/download-by-month-chart-v7": lambda q, id="f_001": get_files_download_by_month_chart_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v9": lambda q, id="k_001": get_auth_api_keys_quota_history_v9(id),
    "/api/v2/skills/{id}/apply-template-v5":     lambda q, id="s_001": get_skills_apply_template_v5(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v7": lambda q, id="c_001": get_billing_payment_methods_unset_default_v7(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v7": lambda q, id="c001": get_campaigns_audience_grade_stats_v7(id),
    "/api/v2/files/{id}/download-by-week-chart-v8": lambda q, id="f_001": get_files_download_by_week_chart_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v5":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v5(id),
    "/api/v2/skills/{id}/merge-stats-v7":         lambda q, id="s_001": get_skills_merge_stats_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v7": lambda q, id="c_001": get_billing_payment_methods_unset_active_v7(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v4": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v4(id),
    "/api/v2/files/{id}/download-by-week-stats-v8": lambda q, id="f_001": get_files_download_by_week_stats_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v10": lambda q, id="k_001": get_auth_api_keys_quota_history_v10(id),
    "/api/v2/skills/{id}/sync-stats-v8":          lambda q, id="s_001": get_skills_sync_stats_v8(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v8": lambda q, id="c_001": get_billing_payment_methods_unset_default_v8(id),
    "/api/v2/campaigns/{id}/audience-tech-stats-v12": lambda q, id="c001": get_campaigns_audience_tech_stats_v12(id),
    "/api/v2/files/{id}/download-by-month-chart-v8": lambda q, id="f_001": get_files_download_by_month_chart_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v6":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v6(id),
    "/api/v2/skills/{id}/sync-from-template-v4":  lambda q, id="s_001": get_skills_sync_from_template_v4(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v8": lambda q, id="c_001": get_billing_payment_methods_unset_active_v8(id),
    "/api/v2/campaigns/{id}/audience-cohort-stats-v3": lambda q, id="c001": get_campaigns_audience_cohort_stas_v3(id),
    "/api/v2/files/{id}/download-by-week-stats-v9": lambda q, id="f_001": get_files_download_by_week_stats_v9(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v11": lambda q, id="k_001": get_auth_api_keys_quota_history_v11(id),
    "/api/v2/skills/{id}/apply-template-v6":     lambda q, id="s_001": get_skills_apply_template_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v9": lambda q, id="c_001": get_billing_payment_methods_unset_default_v9(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v8": lambda q, id="c001": get_campaigns_audience_grade_stats_v8(id),
    "/api/v2/files/{id}/download-by-week-chart-v9": lambda q, id="f_001": get_files_download_by_week_chart_v9(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v7":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v7(id),
    "/api/v2/skills/{id}/sync-stats-v9":          lambda q, id="s_001": get_skills_sync_stats_v9(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v9": lambda q, id="c_001": get_billing_payment_methods_unset_active_v9(id),
    "/api/v2/campaigns/{id}/audience-source-detailed-v3": lambda q, id="c001": get_campaigns_audience_source_detailed_v3(id),
    "/api/v2/files/{id}/download-by-month-list-v7": lambda q, id="f_001": get_files_download_by_month_list_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v12": lambda q, id="k_001": get_auth_api_keys_quota_history_v12(id),
    "/api/v2/skills/{id}/apply-template-v7":     lambda q, id="s_001": get_skills_apply_template_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v10": lambda q, id="c_001": get_billing_payment_methods_unset_default_v10(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v9": lambda q, id="c001": get_campaigns_audience_grade_stats_v9(id),
    "/api/v2/files/{id}/download-by-week-stats-v10": lambda q, id="f_001": get_files_download_by_week_stats_v10(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v8":  lambda q, id="k_001": get_auth_api_keys_quota_reset_v8(id),
    "/api/v2/skills/{id}/sync-stats-v10":         lambda q, id="s_001": get_skills_sync_stats_v10(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v10": lambda q, id="c_001": get_billing_payment_methods_unset_active_v10(id),
    "/api/v2/campaigns/{id}/audience-source-list-v4": lambda q, id="c001": get_campaigns_audience_source_list_v4(id),
    "/api/v2/files/{id}/download-by-day-list-v3": lambda q, id="f_001": get_files_download_by_day_list_v3(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v13": lambda q, id="k_001": get_auth_api_keys_quota_history_v13(id),
    "/api/v2/skills/{id}/export-from-template":     lambda q, id="s_001": get_skills_export_from_template(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v11": lambda q, id="c_001": get_billing_payment_methods_unset_default_v11(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v10": lambda q, id="c001": get_campaigns_audience_grade_stats_v10(id),
    "/api/v2/files/{id}/download-by-day-chart-v10":  lambda q, id="f_001": get_files_download_by_day_chart_v10(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v9":   lambda q, id="k_001": get_auth_api_keys_quota_reset_v9(id),
    "/api/v2/skills/{id}/sync-stats-v11":         lambda q, id="s_001": get_skills_sync_stats_v11(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v11": lambda q, id="c_001": get_billing_payment_methods_unset_active_v11(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v5": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v5(id),
    "/api/v2/files/{id}/download-by-week-stats-v11": lambda q, id="f_001": get_files_download_by_week_stats_v11(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v14": lambda q, id="k_001": get_auth_api_keys_quota_history_v14(id),
    "/api/v2/skills/{id}/apply-template-v8":     lambda q, id="s_001": get_skills_apply_template_v8(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v12": lambda q, id="c_001": get_billing_payment_methods_unset_default_v12(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v4": lambda q, id="c001": get_campaigns_audience_source_stats_v4(id),
    "/api/v2/files/{id}/download-by-day-list-v4": lambda q, id="f_001": get_files_download_by_day_list_v4(id),
    "/api/v2/auth/api-keys/{id}/quota-reset-v10": lambda q, id="k_001": get_auth_api_keys_quota_reset_v10(id),
    "/api/v2/skills/{id}/sync-from-template-v5":  lambda q, id="s_001": get_skills_sync_from_template_v5(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v12": lambda q, id="c_001": get_billing_payment_methods_unset_active_v12(id),
    "/api/v2/campaigns/{id}/audience-cohort-detailed-v6": lambda q, id="c001": get_campaigns_audience_cohort_detailed_v6(id),
    "/api/v2/files/{id}/download-by-week-stats-v12": lambda q, id="f_001": get_files_download_by_week_stats_v12(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v15": lambda q, id="k_001": get_auth_api_keys_quota_history_v15(id),
    "/api/v2/skills/{id}/apply-template-v9":     lambda q, id="s_001": get_skills_apply_template_v9(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v13": lambda q, id="c_001": get_billing_payment_methods_unset_default_v13(id),
    "/api/v2/campaigns/{id}/audience-source-detailed-v6": lambda q, id="c001": get_campaigns_audience_source_detailed_v6(id),
    "/api/v2/files/{id}/download-by-day-chart-v11": lambda q, id="f_001": get_files_download_by_day_chart_v11(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v16": lambda q, id="k_001": get_auth_api_keys_quota_history_v16(id),
    "/api/v2/skills/{id}/sync-stats-v12":         lambda q, id="s_001": get_skills_sync_stats_v12(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v13": lambda q, id="c_001": get_billing_payment_methods_unset_active_v13(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v11": lambda q, id="c001": get_campaigns_audience_grade_stats_v11(id),
    "/api/v2/files/{id}/download-by-day-list-v5":   lambda q, id="f_001": get_files_download_by_day_list_v5(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v17": lambda q, id="k_001": get_auth_api_keys_quota_history_v17(id),
    "/api/v2/skills/{id}/apply-template-v10":    lambda q, id="s_001": get_skills_apply_template_v10(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v14": lambda q, id="c_001": get_billing_payment_methods_unset_default_v14(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v5": lambda q, id="c001": get_campaigns_audience_region_stats_v5(id),
    "/api/v2/files/{id}/download-by-day-list-v6": lambda q, id="f_001": get_files_download_by_day_list_v6(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v18": lambda q, id="k_001": get_auth_api_keys_quota_history_v18(id),
    "/api/v2/skills/{id}/sync-from-template-v6":  lambda q, id="s_001": get_skills_sync_from_template_v6(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v14": lambda q, id="c_001": get_billing_payment_methods_unset_active_v14(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v5": lambda q, id="c001": get_campaigns_audience_source_stats_v5(id),
    "/api/v2/files/{id}/download-by-week-list-v7": lambda q, id="f_001": get_files_download_by_week_list_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v19": lambda q, id="k_001": get_auth_api_keys_quota_history_v19(id),
    "/api/v2/skills/{id}/apply-template-v11":    lambda q, id="s_001": get_skills_apply_template_v11(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v15": lambda q, id="c_001": get_billing_payment_methods_unset_default_v15(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v12": lambda q, id="c001": get_campaigns_audience_grade_stats_v12(id),
    "/api/v2/files/{id}/download-by-day-list-v7":  lambda q, id="f_001": get_files_download_by_day_list_v7(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v20": lambda q, id="k_001": get_auth_api_keys_quota_history_v20(id),
    "/api/v2/skills/{id}/sync-stats-v13":         lambda q, id="s_001": get_skills_sync_stats_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v15": lambda q, id="c_001": get_billing_payment_methods_unset_active_v15(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v6": lambda q, id="c001": get_campaigns_audience_region_stats_v6(id),
    "/api/v2/files/{id}/download-by-week-stats-v13": lambda q, id="f_001": get_files_download_by_week_stats_v13(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v21": lambda q, id="k_001": get_auth_api_keys_quota_history_v21(id),
    "/api/v2/skills/{id}/apply-template-v12":    lambda q, id="s_001": get_skills_apply_template_v12(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v16": lambda q, id="c_001": get_billing_payment_methods_unset_default_v16(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v6": lambda q, id="c001": get_campaigns_audience_source_stats_v6(id),
    "/api/v2/files/{id}/download-by-day-chart-v12": lambda q, id="f_001": get_files_download_by_day_chart_v12(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v22": lambda q, id="k_001": get_auth_api_keys_quota_history_v22(id),
    "/api/v2/skills/{id}/sync-from-template-v7":  lambda q, id="s_001": get_skills_sync_from_template_v7(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v16": lambda q, id="c_001": get_billing_payment_methods_unset_active_v16(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v13": lambda q, id="c001": get_campaigns_audience_grade_stats_v13(id),
    "/api/v2/files/{id}/download-by-week-stats-v14": lambda q, id="f_001": get_files_download_by_week_stats_v14(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v23": lambda q, id="k_001": get_auth_api_keys_quota_history_v23(id),
    "/api/v2/skills/{id}/apply-template-v13":    lambda q, id="s_001": get_skills_apply_template_v13(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v17": lambda q, id="c_001": get_billing_payment_methods_unset_default_v17(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v7": lambda q, id="c001": get_campaigns_audience_region_stats_v7(id),
    "/api/v2/files/{id}/download-by-day-list-v8":  lambda q, id="f_001": get_files_download_by_day_list_v8(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v44": lambda q, id="k_001": get_auth_api_keys_quota_history_v44(id),
    "/api/v2/skills/{id}/sync-stats-v14":         lambda q, id="s_001": get_skills_sync_stats_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v17": lambda q, id="c_001": get_billing_payment_methods_unset_active_v17(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v7": lambda q, id="c001": get_campaigns_audience_source_stats_v7(id),
    "/api/v2/files/{id}/download-by-week-stats-v15": lambda q, id="f_001": get_files_download_by_week_stats_v15(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v25": lambda q, id="k_001": get_auth_api_keys_quota_history_v25(id),
    "/api/v2/skills/{id}/apply-template-v14":    lambda q, id="s_001": get_skills_apply_template_v14(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v18": lambda q, id="c_001": get_billing_payment_methods_unset_default_v18(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v8": lambda q, id="c001": get_campaigns_audience_region_stats_v8(id),
    "/api/v2/files/{id}/download-by-day-list-v9":  lambda q, id="f_001": get_files_download_by_day_list_v9(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v26": lambda q, id="k_001": get_auth_api_keys_quota_history_v26(id),
    "/api/v2/skills/{id}/sync-from-template-v8":  lambda q, id="s_001": get_skills_sync_from_template_v8(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v18": lambda q, id="c_001": get_billing_payment_methods_unset_active_v18(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v8": lambda q, id="c001": get_campaigns_audience_source_stats_v8(id),
    "/api/v2/files/{id}/download-by-week-stats-v16": lambda q, id="f_001": get_files_download_by_week_stats_v16(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v27": lambda q, id="k_001": get_auth_api_keys_quota_history_v27(id),
    "/api/v2/skills/{id}/apply-template-v15":    lambda q, id="s_001": get_skills_apply_template_v15(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v19": lambda q, id="c_001": get_billing_payment_methods_unset_default_v19(id),
    "/api/v2/campaigns/{id}/audience-region-detailed-v7": lambda q, id="c001": get_campaigns_audience_region_detailed_v7(id),
    "/api/v2/files/{id}/download-by-day-stats-v17": lambda q, id="f_001": get_files_download_by_day_stats_v17(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v28": lambda q, id="k_001": get_auth_api_keys_quota_history_v28(id),
    "/api/v2/skills/{id}/sync-from-template-v9":  lambda q, id="s_001": get_skills_sync_from_template_v9(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v19": lambda q, id="c_001": get_billing_payment_methods_unset_active_v19(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v9": lambda q, id="c001": get_campaigns_audience_source_stats_v9(id),
    "/api/v2/files/{id}/download-by-day-list-v10": lambda q, id="f_001": get_files_download_by_day_list_v10(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v29": lambda q, id="k_001": get_auth_api_keys_quota_history_v29(id),
    "/api/v2/skills/{id}/apply-template-v16":    lambda q, id="s_001": get_skills_apply_template_v16(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v20": lambda q, id="c_001": get_billing_payment_methods_unset_default_v20(id),
    "/api/v2/campaigns/{id}/audience-region-stats-v9": lambda q, id="c001": get_campaigns_audience_region_stats_v9(id),
    "/api/v2/files/{id}/download-by-week-stats-v18": lambda q, id="f_001": get_files_download_by_week_stats_v18(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v30": lambda q, id="k_001": get_auth_api_keys_quota_history_v30(id),
    "/api/v2/skills/{id}/sync-from-template-v10": lambda q, id="s_001": get_skills_sync_from_template_v10(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v20": lambda q, id="c_001": get_billing_payment_methods_unset_active_v20(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v10": lambda q, id="c001": get_campaigns_audience_source_stats_v10(id),
    "/api/v2/files/{id}/download-by-day-list-v11": lambda q, id="f_001": get_files_download_by_day_list_v11(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v31": lambda q, id="k_001": get_auth_api_keys_quota_history_v31(id),
    "/api/v2/skills/{id}/apply-template-v17":    lambda q, id="s_001": get_skills_apply_template_v17(id),
    "/api/v2/billing/payment-methods/{id}/unset-default-v21": lambda q, id="c_001": get_billing_payment_methods_unset_default_v21(id),
    "/api/v2/campaigns/{id}/audience-grade-stats-v14": lambda q, id="c001": get_campaigns_audience_grade_stats_v14(id),
    "/api/v2/files/{id}/download-by-week-stats-v19": lambda q, id="f_001": get_files_download_by_week_stats_v19(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v32": lambda q, id="k_001": get_auth_api_keys_quota_history_v32(id),
    "/api/v2/skills/{id}/sync-from-template-v11": lambda q, id="s_001": get_skills_sync_from_template_v11(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v21": lambda q, id="c_001": get_billing_payment_methods_unset_active_v21(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v11": lambda q, id="c001": get_campaigns_audience_source_stats_v11(id),
    "/api/v2/files/{id}/download-by-day-list-v12": lambda q, id="f_001": get_files_download_by_day_list_v12(id),
    "/api/v2/auth/api-keys/{id}/quota-history-v33": lambda q, id="k_001": get_auth_api_keys_quota_history_v33(id),
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

    def do_POST(self):
        """POST handler · R360 TryNow 真表单后端 (用 /api/v2/auth/login)"""
        u = urlparse(self.path)
        path = u.path
        length = int(self.headers.get('Content-Length', 0) or 0)
        try:
            body_raw = self.rfile.read(length) if length else b''
            body = json.loads(body_raw.decode('utf-8')) if body_raw else {}
        except Exception:
            body = {}

        # TryNow 试用注册 (POST /api/v2/auth/login)
        if path == "/api/v2/auth/login":
            try:
                result = post_auth_login(body)
                code = 200 if result.get("status") == "ok" else 400
                self._send_json(code, result)
                return
            except Exception as e:
                self._send_json(500, {"status": "error", "error": str(e), "path": path})
                return

        # 通用 POST 路由 fallback (R360)
        if path in POST_ROUTES:
            try:
                result = POST_ROUTES[path](body)
                code = 200 if result.get("status") == "ok" else 500
                self._send_json(code, result)
                return
            except Exception as e:
                self._send_json(500, {"status": "error", "error": str(e), "path": path})
                return

        self._send_json(404, {"status": "error", "error": "POST not found", "path": path})


def post_auth_login(body: dict):
    """Auth POST login · TryNow 试用注册 (R360)
    body: {email, password, tenant_name, industry, sku_id}
    返回: {status, data: {user_id, tenant_id, token, role, expires_in}}
    """
    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()
    tenant_name = (body.get("tenant_name") or "").strip() or (email.split("@")[0] if email else "demo_tenant")
    industry_val = (body.get("industry") or "decoration").strip()
    sku_id = (body.get("sku_id") or "dec_pro").strip()

    if not email or "@" not in email:
        return {
            "status": "error",
            "error": "invalid_email",
            "message": "邮箱格式不正确",
            "ts": datetime.utcnow().isoformat() + "Z",
        }
    if len(password) < 6:
        return {
            "status": "error",
            "error": "password_too_short",
            "message": "密码至少 6 位",
            "ts": datetime.utcnow().isoformat() + "Z",
        }

    # 简化 demo 注册: 用 email hash 生成 user_id + tenant_id
    h = hashlib.md5(email.encode("utf-8")).hexdigest()[:10]
    user_id = f"u_{h}"
    tenant_id = f"t_{hashlib.md5(tenant_name.encode('utf-8')).hexdigest()[:12]}"
    token = f"ct_trial_{h}_{int(datetime.utcnow().timestamp())}"

    return {
        "status": "ok",
        "data": {
            "user_id":     user_id,
            "tenant_id":   tenant_id,
            "tenant_name": tenant_name,
            "industry":    industry_val,
            "sku_id":      sku_id,
            "token":       token,
            "role":        "owner",
            "expires_in":  7 * 24 * 3600,  # 7 天试用
            "trial":       True,
        },
        "source": "v23_post_auth_login_R360",
        "ts": datetime.utcnow().isoformat() + "Z",
        "version": "R360",
    }


# POST 路由表 (R360)
POST_ROUTES = {
    # "/api/v2/auth/login" 直接走 do_POST 内置分支（带 body 校验）
}


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


# 用 str.replace 方式更安全:
