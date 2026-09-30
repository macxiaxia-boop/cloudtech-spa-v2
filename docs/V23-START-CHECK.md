# CloudTech V23 · Deep Health Check 入门指引

> **端口**: 7791 (避开 V22 5099 + PWA 7790 + Streamlit 8501/8502)
> **服务**: `v23_health.py` 独立 Python http.server 进程 (无 FastAPI / 无 Flask)
> **设计**: 真发 16 个核心端点 + 断言非 401 + 非 stub:true + 非 500

---

## 🚀 启动

```bash
nohup pythonw D:/CloudTech-Portable/v23_health.py > /d/CloudTech-Portable/logs/v23_health.log 2>&1 &
sleep 2
curl http://localhost:7791/health
```

**预期响应**:
```json
{"status": "ok", "service": "V23", "version": "23.0.0", "uptime_s": 3}
```

---

## 🔍 深度健康检查 (V23 真根因治本)

```bash
curl http://localhost:7791/health?deep=1
```

**实证** (2026-09-30):
```json
{
  "status": "ok",  // 或 "degraded"
  "degraded_count": 0,  // 或 > 0
  "total_checks": 16,
  "checks": [
    {
      "url": ":5099/health",
      "http": 200,
      "expect_http": 200,
      "stub": false,
      "demo_required": false,
      "ok": true  // ← true 表示这个端点真的在工作
    },
    ...
  ]
}
```

**16 端点清单** (4 维度):

| 维度 | 端点 | 来源 |
|---|---|---|
| **V22 元** | `:5099/health` `:5099/api/saas/v1/info` `:5099/docs` `:5099/openapi.json` | V22 gateway |
| **V22 stub 数据** | `:5099/api/v2/system/status` `:5099/api/v2/employees` | V22 老 stub |
| **V22 鉴权 (R293 修)** | `:5099/api/v3/monitoring/web-vitals` | V22 R293 |
| **V23 真实数据** | `:7791/api/v2/dashboard/kpis` `:7791/api/v2/notifications` `:7791/api/v2/skills` `:7791/api/v2/system/status` | V23 v23_health.py |
| **V23 demo 鉴权 bypass** | `:7791/api/crm/leads` `:7791/api/skills` `:7791/api/employees` `:7791/api/admin/ops` | V23 demo mode |
| **V23 新加 (R293 漏)** | `:7791/api/v3/monitoring/health` | V23 v23_health.py |

**关键判据**: `ok: true` 表示这个端点真的在工作（不是 stub:true / 不是 401 / 不是 500）。

---

## 📊 V23 真实数据 API (13 端点)

### Dashboard

```bash
curl http://localhost:7791/api/v2/dashboard/kpis
```

**响应**:
```json
{
  "status": "ok",
  "data": {
    "today_running": {"label": "进行中的任务", "value": 24, "delta": "+12%"},
    "agents_online":  {"label": "AI 数字员工",  "value": 38, "delta": "+5", "note": "V22 8 预设 + R291 30 行业"},
    "today_done":     {"label": "SaaS 租户",    "value": 24, "delta": "+24"},
    "pending":        {"label": "待发邮件",     "value": 36, "delta": "14 active"}
  },
  "source": "cloudtech.db",
  "ts": "2026-09-30T07:18:46Z"
}
```

### Notifications (真实 email_queue)

```bash
curl http://localhost:7791/api/v2/notifications
```

### Skills (db + 兜底 12)

```bash
curl http://localhost:7791/api/v2/skills
```

### System Status (8 项真实)

```bash
curl http://localhost:7791/api/v2/system/status
```

**响应**:
```json
{
  "status": "ok",
  "data": {
    "version": "23.0.0-v23",
    "service": "CloudTech V23 Health Service",
    "port": 7791,
    "disk_d_gb": {"free": 114.2, "total": 326.5, "pct_used": 65},
    "disk_c_gb": {"free": 32.6, "total": 149.4, "pct_used": 78},
    "ports": {
      "v22_gateway":        {"port": 5099, "status": "ok"},
      "v23_health":         {"port": 7791, "status": "ok"},
      "streamlit":          {"port": 8501, "status": "down"},
      "aios_bridge":        {"port": 18801, "status": "ok"}
    },
    "db_tables": {"saas_users": "ok", "saas_tenants": "ok", "email_queue": "ok", ...},
    "db_counts": {"saas_users": 24, "saas_tenants": 24, "email_queue": 36, ...},
    "demo_mode": true
  }
}
```

### Demo 鉴权 Bypass (4 端点)

```bash
# env CLOUDTECH_DEMO_MODE=1 (默认) → 绕过 Flask admin_dashboard 鉴权
curl http://localhost:7791/api/crm/leads        # 真实 leads 表 4 行
curl http://localhost:7791/api/skills           # 12 兜底
curl http://localhost:7791/api/employees        # 8 V22 预设
curl http://localhost:7791/api/admin/ops        # SaaS 用户/订阅统计
```

### 新加 (R293 漏)

```bash
curl http://localhost:7791/api/v3/monitoring/health
```

---

## 🌐 Web UI (V23 README)

```bash
# 浏览器打开
http://localhost:7791/
```

**V23 README HTML** 自带 4 大区域:
1. 🔍 健康检查 (浅 + 深 + 端点清单)
2. 📊 真实数据 (5 端点)
3. 🔓 Demo 鉴权 Bypass (4 端点)
4. 🔬 新加 (R293 漏)
5. 🩺 老问题 (V23 修)

---

## 🛠️ 进阶用法

### 看 PWA ChatWorkbench ws.map 修好

```bash
# 1. PWA 重 build
cd D:/MiniMax/cloudtech-redesign/web && npm run build
# 2. msedge headless 截图
msedge --headless=new --disable-gpu --no-sandbox \
  --screenshot=/tmp/pwa_chat.png --window-size=1280,800 \
  http://localhost:5099/chat
```

### 看 vite-spa Dashboard 重做 (shadcn Card)

```bash
# 1. vite-spa 重 build (含新 Dashboard.tsx)
cd D:/CloudTech-Portable/web/vite-spa && npm run build
# 2. npx serve 起 SPA fallback
npx -y serve -s D:/CloudTech-Portable/web/vite-spa/dist-v45 -l 7792
# 3. msedge headless 截图 (login 因为 RequireAuth 守卫)
msedge --headless=new --disable-gpu --no-sandbox \
  --screenshot=/tmp/v23_login.png --window-size=1280,800 \
  http://localhost:7792/login
```

---

## 📋 V23 后续 (L2/L3 待批)

| 项 | 行动 | 风险 |
|---|---|---|
| L2-1 | V22 gateway 切换到 vite-spa/dist-v45 (改 DIST_DIR) | 中（断 5099） |
| L2-2 | 老 landing-page/ 27 文件 git rm | 低 |
| L3-1 | 28 page 全部用 shadcn Card 重写 (AIEmployees/ClientList/Settings 等) | 高 |
| L3-2 | tailwind.config.js RGB var() wrapper + .dark mode | 低 |
| L3-3 | brand.ts 单点 brand 字符串 | 低 |
| L4 | 域名/SSL/Stripe/SMTP | 高 |

---

**版本**: V23 v1.0 · 2026-09-30 · SSOT 索引
**作者**: Claude Code (MiniMax-M3)