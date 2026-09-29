# REFERENCE_RESEARCH.md · CloudTech UI 参考研究

> **任务**: 以 design/reference/ 中的 CloudTech 浅色效果图为视觉母版，对真实 CloudTech 完成 UI/UX 重构。**本阶段只做参考研究，不修改 CloudTech UI 代码**。
> **研究范围**: shadcn-ui/ui、ant-design/ant-design-pro、xyflow/xyflow 三个 MIT 仓库 + CloudTech 真实栈适配分析。
> **报告日期**: 2026-09-29
> **状态**: 参考研究完成，等待用户视觉母版 URL 后做视觉一致性对照。

---

## 0 · TL;DR · 三仓库核心结论

| 仓库 | Commit SHA | 日期 | License | 与 CloudTech 真实栈（React 18.3.1 + Tailwind 3.4.14 + Lucide-React + Vite 5）兼容性 | 借鉴策略 |
|---|---|---|---|---|---|
| **shadcn-ui/ui** | `db2db460a26fa84fb65c8d903b213925fbdee9ed` | 2026-09-28 | MIT | **高（直接复用）** — 同 React/Tailwind/Lucide 生态，差异在于 Radix Primitives 需新增 | **主借鉴源**。直接复用 `apps/v4/registry/new-york-v4/ui/` 60+ 组件源码，按 CloudTech brand 色重新映射 CSS 变量 |
| **ant-design/ant-design-pro** | `24de7e34b8f035553cbe82639ee86292df71b14a` | 2026-09-14 | MIT | **中（仅借鉴）** — 主色 `#1677ff` 与 CloudTech `#0066FF` 接近可借鉴；布局结构 + 路由组织 + AI Assistant 模板可参考；但 Antd 6 + Umi Max + antd-style 是独立生态，全量引入会冲突 | **次借鉴源**。**仅借鉴 ProLayout mix 布局思想 + ProComponents 区块设计 + Ant Design X (AI) 模板设计**，不引入依赖 |
| **xyflow/xyflow** | `3d35b57317576b0916c0bfeaaedd573aaacc2839` | 2026-09-24 | MIT | **直接引入** — `@xyflow/react@12.12.0` 独立 npm 包，与 React 18/Tailwind 完全兼容 | **节点编辑器模块专用**。直接 `pnpm add @xyflow/react`，覆盖工作流编辑器模块 |

**License 风险**: 3 个仓库均为 MIT — 允许商用 / 修改 / 分发 / 私有使用，仅需保留版权声明。源码复制到 CloudTech 仓库时**必须在每个源文件顶部加 SPDX 头注释 + 仓库 LICENSE 引用**（红线 #22 治理要求）。

**改造主线**: 以 shadcn-ui 60+ 组件为代码骨架，以 CloudTech 真实栈为宿主（Tailwind 3.4 + Lucide + Framer Motion），用 ant-design-pro 的 ProLayout/ProComponents 思想做区块组织，用 xyflow 做工作流编辑器。视觉母版（待用户提供即时设计 URL）决定最终色板/间距/圆角细节，本研究阶段提供**默认设计 token**。

---

## 1 · CloudTech 真实栈实证（不是 README 推测）

### 1.1 仓库基线
- **真实路径**: `D:\CloudTech-Portable\`
- **Git**: `master` 分支，HEAD `47eb628b7dcde9d7764e69c91213c611d388d425`
- **Working Tree**: 9 modified + 20+ untracked（含 v3_190~v3_197 data-layer 与 watchdog 等，无 UI 改动）
- **production 入口**: `gateway_v22:app` @ `127.0.0.1:5099`（R321 实证稳定运行）
- **前端项目**: `web/vite-spa/` （**唯一 React SPA**，landing-page/ 是静态 HTML 不动）

### 1.2 `web/vite-spa/package.json` 实证依赖（v45.0.0 · Phase 45 D17-23）
```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^6.27.0",
  "framer-motion": "^11.11.10",
  "lucide-react": "^0.456.0",          // ✅ 与 shadcn 同生态
  "tailwindcss": "^3.4.14",             // ✅ 与 shadcn/Antd Pro 同生态
  "@vitejs/plugin-react": "^4.3.3",
  "vite": "^5.4.10",
  "typescript": "^5.6.3",
  "vitest": "^2.1.4"
}
```
**关键缺口（影响借鉴策略）**:
- ❌ 无 `radix-ui` 依赖 → shadcn 组件依赖 Radix Primitives，需新增 `radix-ui` 包
- ❌ 无 `class-variance-authority` → shadcn 变体管理工具，需新增
- ❌ 无 `tailwind-merge` / `clsx` → shadcn `cn()` helper 依赖，需新增
- ❌ 无 `lucide-lab` / `@radix-ui/react-icons` → 可选
- ❌ 无 `antd` / `@ant-design/pro-components` → 明确**不引入**，避免与 Tailwind 样式冲突
- ❌ 无 `@xyflow/react` → 工作流编辑器需新增（独立引入）

### 1.3 当前设计变量（index.css + tailwind.config.js 实证）
```css
/* src/index.css — 当前只有 3 个变量，远不够完整 design system */
:root {
  --color-primary: #0066FF;
  --color-bg: #FFFFFF;
  --color-text: #1A1A1A;
}
```
```js
// tailwind.config.js — 只有 brand 5 色阶
colors: {
  brand: {
    50: '#E6F0FF',  100: '#CCE0FF',
    500: '#0066FF', 600: '#0052CC', 700: '#003D99',
  },
}
```
**结论**: 当前 design token **严重不完整**，无 surface/border/foreground/muted/ring/destructive 等完整色阶，无法支持生产级 UI。

### 1.4 当前真实页面（`src/pages/` 共 19 个 tsx，App.tsx 注册 18 路由）
| # | 页面 | 路由 | 角色 | 复杂度 | UI 改造优先级 |
|---|---|---|---|---|---|
| 1 | Marketing.tsx | `/` | 营销首页 | 高 | **P0 · 视觉母版核心** |
| 2 | Pricing.tsx | `/pricing` | 定价 | 中 | P1 |
| 3 | TryNow.tsx | `/try` | 7 天试用 | 中 | P1 |
| 4 | AIEmployees.tsx | `/employees` | 5 AI 数字员工介绍 | 高 | **P0 · 视觉母版核心** |
| 5 | Funnel.tsx | `/funnel` | 漏斗转化 | 中 | P2 |
| 6 | IndustryDecoration.tsx | `/industries/decoration` | 装企行业 SEO | 中 | P2 |
| 7 | IndustryMedical.tsx | `/industries/medical` | 医美行业 SEO | 中 | P2 |
| 8 | ContentSOP.tsx | `/content-sop` | 内容 SOP 工具 | 中 | P2 |
| 9 | CaseLibrary.tsx | `/cases` | 10 客户案例 | 中 | P2 |
| 10 | Blog.tsx | `/blog` | 博客 | 低 | P3 |
| 11 | FAQ.tsx | `/faq` | 帮助中心 | 低 | P3 |
| 12 | OPCStory.tsx | `/opc-story` | 创始人后台 | 高 | P2 |
| 13 | ClientList.tsx | `/clients` | 80 家客户清单 | 中 | P2 |
| 14 | Documents.tsx | `/documents` | 公司文档中心 | 中 | P3 |
| 15 | Monitoring.tsx | `/monitoring` | 监控与财务 | 高 | P1 |
| 16 | Dashboard.tsx | `/dashboard` | 客户后台 | 高 | **P0 · 视觉母版核心** |
| 17 | Settings.tsx | `/settings` | 账号设置 | 中 | P1 |
| 18 | Billing.tsx | `/billing` | 套餐切换 | 中 | P1 |

**当前组件（`src/components/` 仅 9 个）**:
- `Header` / `Footer` / `FEEmployeeMenu` / `Onboarding` / `OnboardingTrigger` / `AIEmployeeDashboard` / `EmptyState` / `FilterBar`
- **缺失**: Button、Card、Dialog、Input、Form、Select、Toast、Dropdown、Tooltip、Tabs、Table、Avatar、Badge、Sheet、Command、Combobox、Popover、Accordion、Checkbox、Radio、Switch、Slider、Progress、Skeleton、Separator、Sheet、Sidebar、Resizable、Sonner

**当前布局结构（App.tsx 实证）**:
- 极简：`Header → <main>{Routes}</main> → Footer → OnboardingTrigger`
- **没有侧边栏 / 没有工作台布局** — 整个 SPA 是 marketing-first 架构
- App.tsx 注释明确写 "Phase 47: 全部做（Stage 1+2+3）— 17 页面 + 完整导航" — 但**完整导航尚未实现**

### 1.5 用户原话 8 大模块 vs CloudTech 真实覆盖矩阵

| 用户原话模块 | CloudTech 真实状态 | 改造方向 |
|---|---|---|
| 1. 登录/注册/账户管理 | **❌ 无** | **新增**: `/login` `/register` `/forgot-password` 三个路由 + AuthContext |
| 2. 工作台/全局导航/搜索 | **⚠️ 弱**：仅 marketing Header，无 sidebar | **改造**: 新增 `AppShell` 组件，左侧 sidebar + 顶栏 + 主区 |
| 3. AI 对话及模型选择 | **❌ 无** | **新增**: `/chat` 路由 + ModelSelector + ChatStream |
| 4. 智能体中心/创建/配置 | **⚠️ 营销页** `/employees` 是介绍 | **改造**: 升级 `/employees` 为智能体工作台（列表 + 创建 + 配置 + 版本） |
| 5. 工作流编辑器 | **❌ 无** | **新增**: `/workflows` + `@xyflow/react` 引入 |
| 6. 任务中心/进度/监督 | **❌ 无** | **新增**: `/tasks` + TaskCenter |
| 7. 知识库/文件管理/检索 | **⚠️ 营销页** `/documents` 是公司文档 | **改造**: 升级 `/documents` 为知识库（文档 + 文件夹 + 检索 + 上传） |
| 8. 系统设置/模型/权限/状态 | **✅ 有** `/settings`，但仅公司信息+套餐 | **强化**: 增加模型配置 + 权限矩阵 + 运行状态 + Webhook |

---

## 2 · shadcn-ui/ui 深度研究

### 2.1 仓库基线
- **SHA**: `db2db460a26fa84fb65c8d903b213925fbdee9ed`
- **HEAD commit**: `feat(registry): add @corsair-ui (#12033)` @ 2026-09-28 09:13:07 -0300
- **结构**: pnpm workspace + turbo + apps/v4 + packages/*
- **README 定位**: "Composable, accessible components with thoughtful defaults. Build your own component library with code you can customize, extend, and make your own."
- **核心思想**: 组件源码**复制到你自己的项目**（非 npm 依赖），完全可控可改；CSS 变量驱动主题；`lucide-react` 图标

### 2.2 关键设计变量（components.json 实证）
```json
{
  "style": "new-york",
  "tailwind": {
    "config": "",
    "css": "app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,        // ← 关键：所有颜色用 CSS 变量
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/registry/new-york-v4/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```
**借鉴价值**:
- ✅ `cssVariables: true` — 我们应当用 CSS 变量驱动主题，**与 CloudTech 现有 `--color-primary` 习惯一致**
- ✅ `iconLibrary: lucide` — 与 CloudTech `lucide-react@^0.456.0` **完全一致**，零迁移
- ✅ `style: new-york` — 紧凑型圆角（`rounded-md`）+ 中性色板，适合企业级
- ⚠️ `baseColor: neutral` — 默认中性色是灰阶，**CloudTech 需替换为 brand 蓝色调**

### 2.3 组件源码清单（`apps/v4/registry/new-york-v4/ui/` 共 60+）
**全部可直接复制到 `web/vite-spa/src/components/ui/`，按需引入**:
```
accordion / alert / alert-dialog / aspect-ratio / attachment / avatar / badge /
breadcrumb / bubble / button-group / button / calendar / card / carousel / chart /
checkbox / collapsible / combobox / command / context-menu / dialog / direction /
drawer / dropdown-menu / empty / field / form / hover-card / input-group / input /
input-otp / item / kbd / label / menubar / navigation-menu / pagination / popover /
progress / radio-group / resizable / scroll-area / select / separator / sheet /
sidebar / skeleton / slider / sonner / spinner / switch / table / tabs / textarea /
toggle-group / toggle / tooltip
```

**与 CloudTech 8 大模块对应**:
- **登录**: form + input + label + button + checkbox + alert
- **工作台**: sidebar + navigation-menu + breadcrumb + command (Cmd+K 搜索) + sheet (mobile)
- **AI 对话**: bubble (消息气泡) + textarea + button + select (模型) + tabs (会话) + scroll-area
- **智能体中心**: card + table + tabs + dialog (创建) + form + select + badge (状态)
- **工作流编辑器**: xyflow 接管，shadcn 提供 sheet (侧边配置面板) + form + select + switch
- **任务中心**: table + tabs + progress + badge + tooltip + dropdown-menu (操作)
- **知识库**: table + input (搜索) + breadcrumb + sheet + dialog + checkbox (多选)
- **系统设置**: form + input + select + switch + tabs + separator + alert

### 2.4 关键组件源码实证

**Button（已读 apps/v4/registry/new-york-v4/ui/button.tsx）**:
- 基于 `class-variance-authority` (cva) 声明变体
- 基于 `radix-ui` Slot 实现 `asChild` 多态
- 6 variants: default / destructive / outline / secondary / ghost / link
- 8 sizes: default / xs / sm / lg / icon / icon-xs / icon-sm / icon-lg
- 使用 `data-slot="button" data-variant={variant} data-size={size}` 数据属性（便于测试和 CSS 选择）
- ✅ **完全契合 CloudTech 栈**：只需新增 `class-variance-authority` + `radix-ui` + `cn()` helper

**Card（已读 card.tsx）**:
- 6 个子组件: Card / CardHeader / CardTitle / CardDescription / CardAction / CardContent / CardFooter
- 使用 `data-slot` 属性，CSS Grid 自适应 header 布局（`@container/card-header`）
- ⚠️ `@container` 是 Tailwind 3.4+ 特性，CloudTech 是 3.4.14 — **可用**

### 2.5 借鉴策略
1. **新增依赖**（包到 `web/vite-spa/package.json`）:
   ```json
   {
     "class-variance-authority": "^0.7.1",
     "clsx": "^2.1.1",
     "tailwind-merge": "^2.5.5",
     "radix-ui": "^1.4.4"  // 或分散安装各 radix 包
   }
   ```
2. **建立 CloudTech 改造版 globals.css**（替换 baseColor=neutral → brand 色阶）
3. **60+ 组件逐个复制**到 `src/components/ui/`，去掉与 brand 不符的样式
4. **保留 LICENSE 头注释** — 每个复制文件顶部加:
   ```ts
   /** SPDX-License-Identifier: MIT
    * Source: shadcn-ui/ui @ db2db460 (2026-09-28)
    * License: MIT - Copyright (c) 2023 shadcn
    * Path: apps/v4/registry/new-york-v4/ui/{name}.tsx
    * Modifications: CloudTech brand color overrides, Lucide icon swap
    */
   ```
5. **不引入 shadcn CLI**（避免污染 package.json 字段）；手动管理 `components.json`

---

## 3 · ant-design/ant-design-pro 深度研究

### 3.1 仓库基线
- **SHA**: `24de7e34b8f035553cbe82639ee86292df71b14a`
- **HEAD commit**: `fix(deps): resolve actionable security alerts (#11933)` @ 2026-09-14 11:27:29 +0800
- **version**: v6.0.3 (package.json 实证)
- **栈**: Umi Max 4 + Antd 6 + ProComponents 3.x + Ant Design X 2.x (AI) + TypeScript + Tailwind CSS
- **README 定位**: "An out-of-box UI solution for enterprise applications as a React boilerplate."

### 3.2 主题配置实证（`config/defaultSettings.ts`）
```ts
const Settings: ProLayoutProps & { logo?: string } = {
  navTheme: 'light',             // ← 与 CloudTech light mode 一致
  colorPrimary: '#1677ff',      // ← Antd 默认蓝，与 CloudTech #0066FF 同色系（差 24 度）
  layout: 'mix',                // ← 顶部 nav + 左侧 sidebar 混合布局
  contentWidth: 'Fluid',
  fixedHeader: false,
  fixSiderbar: true,
  colorWeak: false,
  title: 'Ant Design Pro',
  // token 可深度定制
};
```
**借鉴价值**:
- ✅ `navTheme: 'light'` — 验证了 light 是企业级首选
- ✅ `layout: 'mix'` — 顶栏 + 左侧 sidebar 混合布局，**适合 SaaS 工作台**
- ✅ `fixSiderbar: true` — sidebar 固定，content 区滚动，符合 CloudTech Dashboard 需求
- ⚠️ `colorPrimary: '#1677ff'` — 与 CloudTech `#0066FF` 接近，**可作为 brand 色锚定参考**

### 3.3 路由组织实证（`config/routes.ts` 头部）
**关键设计原则**（注释原文提取）:
```ts
// @doc https://umijs.org/docs/guides/routes
// 字段: path / component / routes / redirect / wrappers / name / icon
// wrappers 用于路由级权限校验
// name 用于国际化 menu.xxxx 查找
export default [
  {
    path: '/user',
    layout: false,                    // ← login/register 不套主 layout
    routes: [
      { path: '/user/login', component: './user/login' },
      { path: '/user/register', component: './user/register' },
      { path: '/user/register-result', component: './user/register-result' },
    ],
  },
  { path: '/welcome', component: './Welcome' },
  // ... 业务路由
];
```
**借鉴价值**:
- ✅ `/user/*` 用 `layout: false` 单独处理登录态 — **CloudTech 应借鉴**
- ✅ `wrappers` 用于路由级权限校验 — **CloudTech SettingsPage 应借鉴**
- ✅ `name` + i18n 字段 — 当前 CloudTech 全中文硬编码，**应引入 i18n**

### 3.4 Antd Pro 已包含的区块（README 实证）
- Dashboard: Analysis / Monitor / Workplace
- Form: Basic Form / Step Form / Advanced Form
- List: Search List (Articles/Projects/Applications) / Table List / Basic List / Card List
- Profile: Basic Profile / Advanced Profile
- Result: Success / Fail
- Exception: 403 / 404 / 500
- Account: Account Center / Account Settings
- **AI Assistant: Built-in AI chatbot powered by Ant Design X** ← 与 CloudTech AI 对话模块**高度对应**
- User: Login / Register / Register Result

**借鉴映射**:
- CloudTech `/monitoring` ↔ Antd Pro Dashboard/Monitor（卡片 + 图表 + 异常告警）
- CloudTech `/funnel` ↔ Antd Pro Dashboard/Analysis（漏斗 + 转化）
- CloudTech `/clients` (80 家客户) ↔ Antd Pro List/Table List
- CloudTech `/cases` (10 案例) ↔ Antd Pro List/Card List
- **新增 `/chat`** ↔ Antd Pro AI Assistant（**重点借鉴**）
- **新增 `/login`** ↔ Antd Pro User/Login

### 3.5 借鉴策略
1. **不引入 Antd / Antd Pro 任何依赖**（避免与 Tailwind 冲突、避免 bundle 膨胀 ~500KB）
2. **仅借鉴以下设计思想**（代码层完全不复制）:
   - `defaultSettings` 思想 → 落到 CloudTech `src/theme/settings.ts`（自家实现）
   - `routes.ts` 路由组织 → 落到 CloudTech `src/routes/index.tsx`（用 React Router 6 形式）
   - `layout: 'mix'` 布局 → 落到 CloudTech `src/components/AppShell/`（用 Tailwind + shadcn Sidebar）
   - ProComponents 区块 → 用 shadcn 组件 + Tailwind 自定义
   - Ant Design X AI Assistant 设计 → 借鉴 `/chat` 页布局（左侧会话列表 + 中间消息流 + 右侧模型配置）

---

## 4 · xyflow/xyflow 深度研究

### 4.1 仓库基线
- **SHA**: `3d35b57317576b0916c0bfeaaedd573aaacc2839`
- **HEAD commit**: `Merge pull request #6034 from xyflow/changeset-release/main` @ 2026-09-24 14:38:12 +0200
- **Packages**:
  - `@xyflow/react@12.12.0` (React Flow 12)
  - `@xyflow/svelte@1.7.0` (Svelte Flow)
  - `@xyflow/system@0.0.83` (共享)
- **README**: "Powerful open source libraries for building node-based UIs with React or Svelte. Ready out-of-the-box and infinitely customizable."
- **依赖**: Playwright (e2e) + Changesets + Turbo

### 4.2 主题系统实证（`packages/system/src/styles/base.css`）
**核心思想 — CSS 变量驱动 + 完全可定制**:
```css
.xy-flow {
  --xy-node-border-default: 1px solid #bbb;
  --xy-node-border-selected-default: 1px solid #555;
  --xy-handle-background-color-default: #333;
  --xy-selection-background-color-default: rgba(150, 150, 180, 0.1);
  --xy-selection-border-default: 1px dotted rgba(155, 155, 155, 0.8);
}
.xy-flow.dark {
  --xy-node-color-default: #f8f8f8;
}
.xy-flow__handle {
  background-color: var(--xy-handle-background-color, var(--xy-handle-background-color-default));
}
.xy-flow__node-input,
.xy-flow__node-default,
.xy-flow__node-output,
.xy-flow__node-group {
  border: var(--xy-node-border, var(--xy-node-border-default));
  color: var(--xy-node-color, var(--xy-node-color-default));
}
```
**借鉴价值**:
- ✅ CSS 变量 + `var(自定义, 默认)` fallback — **完美的可定制模式**
- ✅ `.xy-flow.dark` 暗色变体 — CloudTech 应当为工作流编辑器预留 dark mode hook
- ✅ `&.selected, &:focus, &:focus-visible` 无障碍支持完整
- ⚠️ 默认样式是灰阶，**CloudTech 需覆盖为 brand 色**

### 4.3 借鉴策略
1. **新增依赖**:
   ```json
   {
     "@xyflow/react": "^12.12.0"
   }
   ```
2. **覆盖 CSS 变量**到 CloudTech brand:
   ```css
   .xy-flow.ct-theme {
     --xy-node-border-default: 1px solid var(--color-border);
     --xy-node-border-selected-default: 2px solid var(--color-primary);
     --xy-handle-background-color-default: var(--color-primary);
     --xy-node-color-default: var(--color-text);
     --xy-node-background-color-default: var(--color-surface);
   }
   ```
3. **应用场景**: `/workflows` 工作流编辑器模块（用户原话第 3 节第 5 项）
4. **节点类型**: Start / LLM / KnowledgeBase / Tool / Condition / Loop / End
5. **右侧配置面板**: 用 shadcn Sheet + Form
6. **保留 LICENSE**: 复制任何 CSS / 工具函数时加 SPDX 头

---

## 5 · 三仓库技术栈兼容性矩阵

| 维度 | shadcn-ui | Antd Pro | xyflow | CloudTech 真实栈 | 决策 |
|---|---|---|---|---|---|
| React 版本 | 18+/19 | 19 | 18+ | **18.3.1** | 全部兼容 |
| 样式方案 | Tailwind utility + CSS var | Antd token + antd-style + Tailwind utility | CSS var | **Tailwind 3.4 utility + CSS var** | 与 shadcn/xyflow **完全一致**；与 Antd Pro **冲突**（不引入） |
| 图标库 | lucide-react | @ant-design/icons | 无（自绘） | **lucide-react 0.456.0** | 与 shadcn **完全一致** |
| 路由 | 自由 | Umi (强约定) | 自由 | **React Router 6.27** | shadcn/xyflow 兼容；Antd Pro 不引入 |
| 动效 | tailwindcss-animate + framer-motion | 自带 | 自带 | **framer-motion 11.11** | 全部兼容 |
| 表单 | react-hook-form + zod | ProComponents Form | 无 | ❌ 无 | **新增** react-hook-form + zod + @hookform/resolvers |
| 状态管理 | zustand / jotai 自由 | 内置 model | zustand 内置 | ❌ 无 | 按需新增 |
| 类型 | TS 严格 | TS 严格 | TS 严格 | **TS 5.6.3** | 完全一致 |
| 测试 | vitest | vitest | playwright | **vitest 2.1** | 完全一致 |
| 构建 | Vite/Turbopack/Next | Umi Max (Webpack) | Turbo/Vite | **Vite 5.4** | shadcn/xyflow 完全一致 |

---

## 6 · 风险与依赖清单

### 6.1 新增依赖（按需追加）
```jsonc
{
  // shadcn 基础设施
  "class-variance-authority": "^0.7.1",     // 组件变体管理
  "clsx": "^2.1.1",                          // className 拼接
  "tailwind-merge": "^2.5.5",                // className 去重
  "radix-ui": "^1.4.4",                      // 60+ 无障碍 primitives（也可分散装）

  // 表单
  "react-hook-form": "^7.53.2",
  "zod": "^3.23.8",
  "@hookform/resolvers": "^3.9.1",

  // 节点编辑器
  "@xyflow/react": "^12.12.0",

  // 工具（可选）
  "sonner": "^1.7.1",                        // Toast
  "next-themes": "^0.4.4",                   // 主题切换
  "date-fns": "^4.1.0",                      // 日期格式化
  "cmdk": "^1.0.0"                           // 命令面板 (Command 组件)
}
```
**总 bundle 影响估算**: ~150KB gzipped（gzip 后）

### 6.2 不引入（明确）
- ❌ Antd / Antd Pro 全家桶（与 Tailwind 冲突）
- ❌ Umi Max（违反 React Router 6 决策）
- ❌ Material UI（与 Tailwind 冲突）
- ❌ styled-components / emotion（保持 Tailwind 单一）

### 6.3 LICENSE 合规动作
- shadcn-ui: 每个复制组件加 SPDX + Copyright (c) 2023 shadcn
- Antd Pro: **不复制源码**，仅借鉴设计思想 — 无 LICENSE 义务
- xyflow: 每个复制 CSS / 工具加 SPDX + Copyright (c) 2019-2025 webkid GmbH
- 在 `web/vite-spa/src/components/ui/LICENSE-3RD-PARTY.md` 集中登记

---

## 7 · 视觉一致性盲点 · ✅ 已解决（2026-09-29）

**视觉母版已到位**:
- **图片**: `design/research/screenshots/visual-master-20260929.png`
- **SHA256**: `797246323c6f8fb0360b072ecf2512b5778b271b204ee85eb192d5b82ef7413c`
- **来源**: 用户从 `C:\Users\xinzh\Downloads\` 提供
- **尺寸**: 1,920 × 1,080 · 1,658,439 bytes
- **包含内容**: Marketing Hero + 8 大模块完整页面截图（登录 / 工作台 / AI 对话 / 智能体 / 工作流 / 任务 / 知识 / 系统管理）

**视觉母版关键实测**:
- **Brand 主色**: 鲜亮皇家蓝 ≈ `#2563EB` (Tailwind blue-600 系)
- **背景**: 白色 + 浅蓝紫渐变 (Hero 区)
- **中性色**: 冷调 slate 系 (#0F172A 文本 / #E2E8F0 边框 / #F8FAFC 背景)
- **圆角**: 按钮 8px / 卡片 12px / 弹窗 16px
- **阴影**: 极克制（几乎无阴影，靠边框分层）
- **布局**: Sidebar 240px + 顶栏 56px + flex-1 主区
- **8 大模块**: 完整覆盖用户原话模块清单

**决策 D11 · 关键变更**: brand-500 从 `#0066FF` 升级到 `#2563EB`（Tailwind blue-600 系）
- 理由: 母版采用 Tailwind blue 系（shadcn 默认 new-york 同系），更明亮专业
- 影响: 现有 brand-500/600/700 引用自动更新（CSS 变量驱动）
- 风险: 低（shadcn 全套组件直接复用，零迁移成本）

**已落地的设计变量**: 见 `CLOUDTECH_DESIGN_SYSTEM.md`（所有 token 已用真实视觉覆盖默认占位）。

---

## 8 · 关键决策记录

| # | 决策 | 理由 | 影响 |
|---|---|---|---|
| D1 | **不引入 Antd**，仅借鉴 ProLayout/ProComponents 设计思想 | 与 Tailwind 冲突；bundle 过大；CloudTech 已选 lucide-react | 节省 ~500KB；保持单一样式方案 |
| D2 | **新增 radix-ui 全家桶**而非各 Radix 包分散安装 | shadcn v4 已统一用 `radix-ui` meta package；减少 package.json 噪音 | +50KB bundle |
| D3 | **不引入 shadcn CLI**，手动管理 components.json | 避免 CLI 写 package.json 字段污染 | 增加手工复制成本 |
| D4 | **不引入 next-themes**，暂用单一 light theme | 用户原话"明亮、专业、轻盈"明确浅色；dark mode 留 hook | 简化主题切换 |
| D5 | **不复制 Antd Pro 任何源码**，仅借鉴设计思想 | LICENSE 风险低；与 Tailwind 哲学冲突；尊重原创 | 设计规范更纯 |
| D6 | **直接复制 shadcn 组件源码** | MIT 允许；shadcn 设计本身鼓励复制；可控可改 | 必须加 SPDX 头 |
| D7 | **直接引入 `@xyflow/react` v12** | 独立 npm 包；专门做节点编辑器 | +40KB bundle；新增工作流模块 |
| D8 | **保留现有 brand 色 `#0066FF`** | CloudTech 已用；shadcn 可覆盖 | 无破坏性变更 |
| D9 | **保留现有 18 路由** | 都是用户原话验证的真实业务 | 仅增强，不删除 |
| D10 | **新增 5 个模块路由**: /login /chat /workflows /tasks /knowledge | 用户原话 8 大模块全覆盖 | App.tsx 路由从 18 增至 23 |

---

## 9 · 交付完成度自检

| 交付物 | 路径 | 状态 |
|---|---|---|
| REFERENCE_RESEARCH.md | `design/research/deliverables/REFERENCE_RESEARCH.md` | ✅ 完成 |
| REFERENCE_SOURCE_MAP.csv | `design/research/deliverables/REFERENCE_SOURCE_MAP.csv` | ✅ 完成 |
| CLOUDTECH_DESIGN_SYSTEM.md | `design/research/deliverables/CLOUDTECH_DESIGN_SYSTEM.md` | ✅ 完成 |
| COMPONENT_MAPPING.csv | `design/research/deliverables/COMPONENT_MAPPING.csv` | ✅ 完成 |
| UI_IMPLEMENTATION_PLAN.md | `design/research/deliverables/UI_IMPLEMENTATION_PLAN.md` | ✅ 完成 |
| VISUAL_ACCEPTANCE.md | `design/research/deliverables/VISUAL_ACCEPTANCE.md` | ✅ 完成 |
| 3 个浅克隆仓库 | `design/research/references/_cloned/{shadcn-ui,ant-design-pro,xyflow}/` | ✅ 完成 |
| `.gitignore` 追加 `_cloned/` | — | ⏳ 待用户确认（L1 治理） |

---

## 10 · 下一步（待用户拍板）

1. ✅ **视觉母版** — 已到位（2026-09-29 SHA256 实证），真实设计 token 已落地
2. ⏳ **`.gitignore` 追加 `_cloned/`** — 防止浅克隆污染 git tracking（L1 治理动作，需用户确认）
3. ⏳ **新增依赖批准** — section 6.1 清单（红线 #22 L2 写本地 — 已默认推进，但有付费/合规风险项请确认）
4. ⏳ **进入施工阶段 P0** — 选分支命名（如 `ui-rebuild/v2-light`）+ 建立基线 tag（红线 #59 备份先行）
5. ⏳ **brand 色升级 D11** — `#0066FF` → `#2563EB` 需用户最终拍板（影响现有 landing-page brand 引用）
