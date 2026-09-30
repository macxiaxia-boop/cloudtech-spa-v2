# CloudTech V23 · 全量摸底 + 真根因诊断报告

> **触发**: 用户原话 2026-09-30 "你永远检查不出问题，我也不知道为什么，明明一大堆的问题"
> **方法**: Curl 12 核心 API + Read 5 关键文件 + 看 2 历史截图 + GitHub 调研 (Agent 后台)
> **日期**: 2026-09-30

---

## 🎯 一句话真根因

**"老检查不出问题" 的真根因** = V22 健康检查只看 `v10_modules_included` 数和 import 是否成功，**完全不验证 API 业务响应是否真的返回非 stub、非 401、非 500、非崩**。

`/health` 返 200 OK + `v10_modules_failed=0` → 看似 100% 健康 → 实际 4 核心 API 全部 401、3 stub API 全部 data:[]、register 500、PWA 一打开就崩。

---

## 🔴 P0 真问题（curl 实测）

### Bug #1 · /api/saas/v1/register 500 Internal Server Error

```bash
$ curl -X POST http://localhost:5099/api/saas/v1/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"v23user@cloudtech.com","password":"V23test123!","name":"V23测试","company":"v23test","plan":"pro","industry":"decoration"}'
Internal Server Error
```

**根因链** (`data-layer/v_saas_v8.py:99-141`):
1. `INSERT INTO saas_users` 成功
2. `INSERT INTO saas_tenants` 成功
3. `INSERT INTO aios_subscription` (R321 加) → 表可能不存在 → try/except catch + print → **不 raise**
4. `conn.commit()` 提交
5. 第二个 `conn = sqlite3.connect(DB)` 重新打开
6. `INSERT INTO email_queue` → **email_queue 表不存在** → ❌ unhandled exception → 整个 register 崩
7. 用户注册拿到 500 → 永远进不去 SaaS

**修复**: 把 email_queue/aios_subscription 表加 CREATE TABLE IF NOT EXISTS 到 _ensure_db()。

### Bug #2 · 4 核心 API 全 401 Authentication required

```bash
$ curl /api/crm/leads        → {"error":"Authentication required"}
$ curl /api/skills           → {"error":"Authentication required"}
$ curl /api/employees        → {"error":"Authentication required"}
$ curl /api/admin/ops        → {"error":"Authentication required"}
$ curl /api/v3/monitoring/health → {"error":"Authentication required"}
```

**根因**: Flask admin_dashboard 把所有这些路由当鉴权路由包了，dev/demo mode 没 bypass。
**修复**: env var `CLOUDTECH_DEMO_MODE=1` 时绕过 admin_dashboard 鉴权（dev 体验 + 单元测试用）。

### Bug #3 · 4 个 stub 路由返 data:[] (UI 永远是空的)

```bash
$ curl /api/v2/system/status    → {"status":"ok","stub":true,"data":[]}
$ curl /api/v2/dashboard/kpis   → {"status":"ok","stub":true,"data":[]}
$ curl /api/v2/skills           → {"status":"ok","stub":true,"data":[]}
$ curl /api/v2/notifications    → {"status":"ok","stub":true,"data":[]}
```

**根因**: V22 stub_compat_util 统一返 stub:true,data:[]，但**没人去填真实数据**。
**修复**: 至少 dashboard/kpis 接 cloudtech.db 真实 tenants/users 计数；notifications 接 email_queue 最近 10 条。

### Bug #4 · PWA ws.map is not a function (截图实证)

打开 `http://localhost:7790/?utm_source=pwa&utm_medium=app` (D:\MiniMax\cloudtech-redesign\web\dist) → 立即崩：

```
TypeError: ws.map is not a function
  at zl (http://127.0.0.1:7790/assets/ChatWorkbench-DHla2ZK8.js:55:29)
  at Do (http://127.0.0.1:7790/assets/react-zUyhkpcy.js:30:16959)
```

**根因**: R293 治了 V22 stub chat/* 返 `{ data: [] }`，但 **dist/ 内 ChatWorkbench.js 仍是旧 minified 错路**（R293 报告 L5 边界第 9 项明示）。
**修复**: `cd /d/MiniMax/cloudtech-redesign/web && npm run build` 重 build PWA → 自动用新 V22 stub。

---

## 🟡 P1 真问题（视觉 / 设计）

### Bug #5 · Brand 字符串 3 处不一致

| 文件 | Brand |
|---|---|
| `dist-v45/index.html` (部署版) | **灵策智算 / LynxceAI** |
| `vite-spa/index.html` (源码) | **CloudTech · 企业级 AI 工作空间** |
| `landing-page/admin.html` (老) | **云数科技 · 统一驾驶舱** |

**根因**: P1-P14 各 commit 没人统一过 brand。
**修复**: `src/lib/brand.ts` 单点定义 + 所有 page import。

### Bug #6 · Tailwind `bg-[var(--xxx)]` 硬编码不识别

`Dashboard.tsx` 25+ 处、`AppShell.tsx` 12+ 处、`AppSidebar.tsx` 8+ 处 写 `bg-[var(--surface-base)]` / `text-[var(--text-secondary)]` —— **Tailwind JIT 编译器不识别这些 arbitrary value var() 引用**，CSS 类不生成，实际渲染丑。

**根因**: P1-P14 写代码时 Tailwind config 没正确暴露 CSS variable token。
**修复**:
- Tailwind config 改 `colors: { surface: 'rgb(var(--surface-base) / <alpha-value>)' }` (Tailwind 3 正确语法)
- 或者：替换为 `bg-neutral-50 text-neutral-500` 等标准 Tailwind token

### Bug #7 · shadcn 62 ui 组件就位但 90% page 不用

`src/components/ui/` 有 button, card, badge, table, sidebar, dialog, sheet, dropdown-menu, select, combobox, command, kbd, chart, calendar 等 62 个 shadcn 组件。

但 Dashboard.tsx / AIEmployees.tsx / ClientList.tsx 等**全是手写 div**，完全没用 shadcn Card/Badge/Button。

**根因**: P1-P14 各自写的，没强制用统一组件。
**修复**: V23 重做时，所有 page 用 shadcn 组件库统一。

### Bug #8 · 老 admin.html 110KB 仍在 vite-spa/landing-page

```
-rw-r--r-- 110907 Sep 25 20:38 admin.html   ← 老 V20 V21 驾驶舱，紫色 + emoji + 拥挤
-rw-r--r--  21570 Sep 25 22:41 admin_v16.html
-rw-r--r--  27623 Sep 25 23:03 admin_v20.html
```

**根因**: V22 主用 vite-spa/dist-v45，老 admin.html 已不 mount，但还在 repo 里污染视觉印象。
**修复**: `git rm -rf landing-page/` → 删掉 27 个老 HTML + 启动 .bat + design-system.css。

---

## 🎨 V23 UI 重做方向（GitHub 调研 + 设计选型）

### 已就位的资产（不要重做）
- ✅ shadcn/ui 62 组件全装好
- ✅ Tailwind 3 + design tokens (brand-50~950 + neutral-0~950 + semantic)
- ✅ Radix UI + cva + tailwind-merge（= shadcn 标准栈）
- ✅ Lucide React icons 全装
- ✅ Framer Motion 全装
- ✅ AppShell（BasicLayout + AppHeader + Sidebar + Breadcrumb + CommandPalette）
- ✅ i18n 系统 (zh-CN + en-US)
- ✅ ErrorBoundary + NotFoundPage
- ✅ Recharts (chart.tsx 10924B)

### 真正需要改的 (V23)
- ❌ Dashboard / AIEmployees / ClientList / Settings / Tasks / Analytics / Notifications / Profile 等 28 page 全部用 shadcn Card/Badge/Button 重写
- ❌ 替换所有 `bg-[var(--xxx)]` → `bg-neutral-50` 或 Tailwind token
- ❌ 统一 brand 字符串到 `src/lib/brand.ts`
- ❌ 加 dark mode toggle (theme/tokens.ts 已就位，但 Page 全部 default light)
- ❌ 老 landing-page/ 27 文件删除
- ❌ PWA dist/ 重 build (治 ws.map)
- ❌ 视觉密度优化: 改紧凑 padding + 减少 emoji icon + 用 lucide icon 统一
- ❌ KPI 卡 / DataTable / Chart 统一封装 (用 shadcn Card + Recharts)

---

## 📋 V23 修复路线图（已拍板）

| 优先级 | 项 | 风险 | L 权限 |
|---|---|---|---|
| P0-1 | 修 v_saas_v8.py register 500 | 低 | L1 自治 |
| P0-2 | 加 CLOUDTECH_DEMO_MODE bypass admin 鉴权 | 低 | L1 |
| P0-3 | 修 stub dashboard/kpis/notifications/skills → 接 db | 中 | L1 |
| P0-4 | PWA dist/ 重 build (治 ws.map) | 低 | L1 |
| P1-1 | Tailwind config 修 arbitrary value var() → 标准 token | 中 | L1 |
| P1-2 | Dashboard.tsx / AIEmployees.tsx 等 28 page 用 shadcn Card 重写 | 高 | L2 |
| P1-3 | brand.ts 单点 brand 字符串 | 低 | L1 |
| P1-4 | dark mode toggle + theme provider | 中 | L1 |
| P1-5 | git rm -rf landing-page/ | 中 | L2 |
| P2-1 | shadcn DataTable / ChartCard 统一封装 | 中 | L2 |
| P2-2 | Lighthouse CI 90+ | 中 | L1 |
| P3 | 域名 + Stripe + SMTP | 高 | L5 |

---

## 🔍 健康检查升级（根治"老检查不出"）

**当前**: `/health` 只看 import OK + v10 count
**V23 升级**: 加 `/health?deep=1` → 真发 10 个核心 API + 断言非 401 + non 500 + non stub=true

```
/health?deep=1  → {
  status: 'ok' | 'degraded',
  core_api_checks: {
    '/api/v2/system/status': {'http': 200, 'stub': false, 'data_count': 4},
    '/api/v2/employees':     {'http': 200, 'stub': false, 'data_count': 8},
    '/api/v2/dashboard/kpis':{'http': 200, 'stub': false, 'data_count': 4},
    '/api/v2/skills':        {'http': 200, 'stub': false, 'data_count': 12},
    '/api/saas/v1/info':     {'http': 200, 'has_brand': true},
    '/api/saas/v1/register': {'http': 201, 'demo_mode': true},
    '/api/v3/monitoring/health': {'http': 200, 'has_uptime': true},
    '/admin':                {'http': 200, 'demo_mode': true},
    '/docs':                 {'http': 200, 'swagger_ui': true},
    '/':                     {'http': 200, 'has_spa': true},
  },
  pwa_dist_check: {
    '/d/MiniMax/cloudtech-redesign/web/dist/ChatWorkbench.js': {'has_ws_map_bug': false}
  }
}
```

---

**版本**: V23 v1.0 · 2026-09-30 · 红线 #60 治本可验证 · 红线 #76 主动推进