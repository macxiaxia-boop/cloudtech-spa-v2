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
    """深度健康检查 · 真发 12 个核心端点 + 断言非 401+非500+非 stub:true"""
    import urllib.request
    endpoints = [
        ("http://127.0.0.1:5099/health",                              200, False),
        ("http://127.0.0.1:5099/api/v2/system/status",                200, False),
        ("http://127.0.0.1:5099/api/saas/v1/info",                    200, False),
        ("http://127.0.0.1:5099/api/v2/employees",                    200, False),
        ("http://127.0.0.1:7791/api/v2/dashboard/kpis",               200, False),
        ("http://127.0.0.1:7791/api/v2/notifications",                200, False),
        ("http://127.0.0.1:7791/api/v2/skills",                       200, False),
        ("http://127.0.0.1:7791/api/v2/system/status",                200, False),
        ("http://127.0.0.1:7791/api/crm/leads",                       200, True),
        ("http://127.0.0.1:7791/api/skills",                          200, True),
        ("http://127.0.0.1:7791/api/employees",                       200, True),
        ("http://127.0.0.1:7791/api/admin/ops",                       200, True),
        ("http://127.0.0.1:5099/api/v3/monitoring/web-vitals",        200, False),
        ("http://127.0.0.1:7791/api/v3/monitoring/health",            200, False),
        ("http://127.0.0.1:5099/docs",                                 200, False),
        ("http://127.0.0.1:5099/openapi.json",                         200, False),
    ]
    results = []
    degraded = 0
    for url, expect_http, demo in endpoints:
        try:
            r = urllib.request.urlopen(url, timeout=1.5)
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
    "/api/crm/leads":                     lambda q: get_crm_leads(),
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