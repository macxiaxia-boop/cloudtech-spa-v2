# UI_IMPLEMENTATION_PLAN.md · CloudTech UI 重构实施计划

> **基于**: design/research/deliverables/REFERENCE_RESEARCH.md + CLOUDTECH_DESIGN_SYSTEM.md + COMPONENT_MAPPING.csv
> **范围**: CloudTech UI/UX 全套重构（用户原话 8 大模块 + 18 路由）
> **真实栈**: React 18.3.1 + Tailwind 3.4.14 + Lucide-React + Framer Motion + React Router 6 + Vite 5
> **不修改**: 后端 (gateway_v22.py) + landing-page/ 静态 HTML + data-layer/* + 任何 v3_*.py

---

## 0 · 阶段路线（6 个 Phase · 连续推进 · v3 升级 2026-09-29）

| Phase | 名称 | 工期估算 | 交付 |
|---|---|---|---|
| **P0** | 设计系统基础 + AppShell（基于 v3 视觉母版）| 4-6 天 | globals.css + tokens + AppShell + Sidebar + Header + 60+ shadcn 组件 |
| **P1** | 核心工作台 + AI 对话 + 智能体（含 5 步向导）| 7-9 天 | Dashboard + Chat + Employees + AgentWizard（5 步 · v3）+ Tasks |
| **P2** | 工作流编辑器 + 知识库 + 文件管理 + 模型管理 | 8-10 天 | Workflows + xyflow（5 类节点库）+ Knowledge + Files + Models |
| **P3** | 登录（居中卡片）+ 营销 + 移动端 2 视图 | 5-7 天 | Login（v3 居中）+ Register + Marketing + 移动端 2 视图基线 |
| **P3.5** | **v3 选择工作空间**（独立模块）| **1-2 天** | **`/workspace/select` 路由 + 选择组织弹窗 + multi-tenant 隔离** |
| **P4** | v2/v3 新增模块（数据分析/团队/系统/个人中心）| 4-6 天 | Analytics + Team + SystemSettings（5 Tab · v3）+ Profile |
| **总工期估算** | — | **29-40 天** | — |

**v3 supersedes v2/v1 关键变化**:
- 路由: 32 → **33**（+1 新增：`/workspace/select`）
- 模块: 16 → **15**（v3 整合：去重 1 个模块，加 1 个新模块，净 0 变化）
- 登录页: v2 左右分栏 → **v3 居中卡片 + 全屏冰山渐变**
- 创建向导: v2 6 步 → **v3 5 步**（合并"角色+技能"为"技能配置"，新增"测试对话"）
- 系统设置: v2 4 Tab → **v3 5 Tab**（新增"系统日志"）
- 移动端: v2 3 视图 → **v3 2 视图**（精简）
- 工期: 28-38 天 → **29-40 天**（+1-2 天）
- Phase 数量: 5 → **6**（新增 P3.5）

---

## 1 · P0 · 设计系统基础 + AppShell（开工起点）

### 1.1 准备工作（必做）

- [ ] **建立独立工作分支**（红线 #22 L2）:
  ```bash
  cd /d/CloudTech-Portable
  git checkout -b ui-rebuild/v2-light
  git tag baseline-ui-rebuild-20260929 master
  git push origin ui-rebuild/v2-light
  ```
- [ ] **创建基线备份**（红线 #59 备份先行）:
  ```bash
  cp -r web/vite-spa web/vite-spa.bak-P0-20260929
  ```
- [ ] **`.gitignore` 追加**（红线 #22 L1 · 待用户批准）:
  ```
  # UI 重构研究目录（浅克隆参考仓库，不入库）
  design/research/references/_cloned/
  ```
- [ ] **暂存现有 untracked 改动**（避免施工中冲突）:
  ```bash
  git stash push -u -m "pre-ui-rebuild-20260929"
  ```

### 1.2 新增依赖（红线 #22 L2 · 待用户最终批准）

```bash
cd /d/CloudTech-Portable/web/vite-spa
pnpm add class-variance-authority@^0.7.1 \
  clsx@^2.1.1 \
  tailwind-merge@^2.5.5 \
  radix-ui@^1.4.4 \
  react-hook-form@^7.53.2 \
  zod@^3.23.8 \
  @hookform/resolvers@^3.9.1 \
  @xyflow/react@^12.12.0 \
  sonner@^1.7.1 \
  cmdk@^1.0.0
```
**新增 devDependencies**:
```bash
pnpm add -D tailwindcss-animate@^1.0.7
```

### 1.3 设计系统文件结构

```
web/vite-spa/src/
├── theme/
│   ├── globals.css           # CSS 变量 + Tailwind 指令
│   ├── tokens.ts             # TS 端 design tokens (供代码引用)
│   └── settings.ts           # navTheme/layout/colorPrimary 等
├── lib/
│   ├── utils.ts              # cn() helper (clsx + tailwind-merge)
│   └── format.ts             # 日期/数字格式化
├── components/
│   ├── ui/                   # shadcn 组件库 (60+)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── ... (60+)
│   │   ├── LICENSE-3RD-PARTY.md
│   │   └── index.ts          # 统一 export
│   ├── AppShell/             # 工作台框架
│   │   ├── BasicLayout.tsx
│   │   ├── AppSidebar.tsx
│   │   ├── AppHeader.tsx
│   │   ├── AppBreadcrumb.tsx
│   │   ├── AppFooter.tsx
│   │   └── CommandPalette.tsx
│   ├── shared/               # 跨页通用
│   │   ├── EmptyState.tsx
│   │   ├── LoadingSkeleton.tsx
│   │   ├── ErrorBoundary.tsx
│   │   ├── PageHeader.tsx
│   │   └── ConfirmDialog.tsx
│   └── workflow/             # xyflow 自定义节点 (Phase 2)
│       ├── nodes/
│       └── validators.ts
└── pages/
    └── (现有 19 页面 + 新增 5)
```

### 1.4 globals.css 落地（基于 CLOUDTECH_DESIGN_SYSTEM.md）

直接覆盖 `web/vite-spa/src/index.css` 完整重写。设计 token 见 CLOUDTECH_DESIGN_SYSTEM.md §2-§7。

### 1.5 tailwind.config.js 完整扩展

```js
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',           // 预留 dark mode hook
  theme: {
    extend: {
      colors: {
        brand: { 50: '...', ..., 950: '...' },
        neutral: { 0: '...', ..., 950: '...' },
        success: { 50: '...', ..., 700: '...' },
        warning: { 50: '...', ..., 700: '...' },
        destructive: { 50: '...', ..., 700: '...' },
        border: 'var(--border-default)',
        ring: 'var(--ring-color)',
        surface: { base: '...', subtle: '...', muted: '...' },
      },
      borderRadius: { ... },
      boxShadow: { ... },
      fontFamily: { ... },
      keyframes: {
        'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } },
        'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
```

### 1.6 shadcn 组件库复制（60+ 文件）

**逐个复制策略**:
1. 从 `_cloned/shadcn-ui/apps/v4/registry/new-york-v4/ui/{name}.tsx` 复制到 `web/vite-spa/src/components/ui/`
2. 每个文件顶部加 SPDX 头（见 REFERENCE_RESEARCH.md §2.5）
3. 检查并替换 `cn` import 路径为 `@/lib/utils`
4. 检查 `radix-ui` 命名空间 import（v4 meta package vs 各分立包）
5. 验证 Tailwind class 与 CloudTech globals.css 一致

**保留项**:
- `data-slot` 属性（测试和 CSS hook）
- 所有 ARIA 属性
- 焦点环样式
- 减少动态媒体查询

**修改项**:
- 圆角统一为 `rounded-md` (12px) 默认
- 默认按钮色为 `bg-brand-500`
- 移除 `dark:` 变体（暂留 light only）

### 1.7 AppShell 实现

```tsx
// src/components/AppShell/BasicLayout.tsx
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { CommandPalette } from './CommandPalette';
import { AppBreadcrumb } from './AppBreadcrumb';

export function BasicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-screen grid-cols-[auto_1fr] bg-surface-subtle">
      <AppSidebar />
      <div className="flex flex-col">
        <AppHeader />
        <main className="flex-1 px-6 py-4">
          <AppBreadcrumb />
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
```

**Sidebar 导航结构**（用户原话 8 大模块映射）:
```ts
const navItems = [
  { section: '工作台', items: [
    { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
    { icon: Bot, label: 'AI 数字员工', href: '/employees' },
  ]},
  { section: 'AI 能力', items: [
    { icon: MessageSquare, label: 'AI 对话', href: '/chat' },
    { icon: Workflow, label: '工作流', href: '/workflows' },
    { icon: ListTodo, label: '任务中心', href: '/tasks' },
  ]},
  { section: '资源', items: [
    { icon: BookOpen, label: '知识库', href: '/knowledge' },
    { icon: FileText, label: '案例库', href: '/cases' },
  ]},
  { section: '管理', items: [
    { icon: Activity, label: '监控', href: '/monitoring' },
    { icon: Settings, label: '设置', href: '/settings' },
  ]},
];
```

### 1.8 P0 验收标准
- [ ] `pnpm build` 无错
- [ ] `pnpm dev` 启动 5098 端口可访问
- [ ] AppShell 在 `/dashboard` 显示（左 sidebar + 顶 header + 内容区）
- [ ] 60+ shadcn 组件 import 不报错
- [ ] 全局 CSS 变量在 DevTools 中可见
- [ ] 焦点环可见
- [ ] 视觉一致性占位（待视觉母版 URL 后校准）

---

## 2 · P1 · 核心工作台 + AI 对话 + 智能体中心

### 2.1 Dashboard 重做（`/dashboard`）

**目标**: 客户后台 Dashboard，作为 SaaS 入口的"门面"
**保留**: 现有 fetch 数据（`/api/v2/billing/tenants/{id}/usage` + `/api/v2/sales/funnel/review`）
**改造**:
- AppShell 包裹
- 顶部 4 KPI 卡（Calls / Tokens / Quota Used / Active Industries）
- 中部 2 列布局：左侧调用趋势 chart + 右侧 Funnel Review 列表
- 底部 Phase45 Warnings 告警区
- Loading 用 Skeleton
- Empty 用 EmptyState

**使用组件**:
- Card + CardHeader + CardTitle + CardContent
- Chart (recharts 集成 via shadcn chart)
- Table + Badge + Progress
- Skeleton + EmptyState
- Alert (warning)

### 2.2 AI 对话（`/chat` · 新增路由）

**新增文件**:
- `src/pages/Chat.tsx`
- `src/components/chat/ChatStream.tsx`
- `src/components/chat/MessageBubble.tsx`
- `src/components/chat/ModelSelector.tsx`
- `src/components/chat/SessionList.tsx`

**功能**:
- 左侧 SessionList（240px）+ 中间消息流 + 右侧 ModelSelector（320px，可关闭）
- 消息流支持 Markdown 渲染 + 代码高亮
- 打字中动画（3 个 dot）
- Stop Generation 按钮
- 模型选择下拉（来自 `/api/v2/models`）
- 温度滑块（0-2）
- 系统提示 textarea

**API 接入**:
- POST `/api/v2/chat/completions` (SSE 流)
- GET `/api/v2/chat/sessions` (会话列表)
- POST `/api/v2/chat/sessions` (新建)
- DELETE `/api/v2/chat/sessions/{id}` (删除)

**注意事项**:
- **不引入 LangChain 等重依赖**
- SSE 用 fetch + ReadableStream 自实现
- Markdown 用 `marked` + `highlight.js` (轻量)

### 2.3 智能体中心（`/employees` 改造）

**当前状态**: 营销介绍页（5 AI 数字员工）
**改造**: 升级为智能体工作台
- 顶部 Tab: 我的智能体 / 模板市场 / 创建
- AgentCard 网格（每张卡片: 头像 + 名称 + 描述 + 状态 + 操作）
- 点击 AgentCard → Sheet 显示详情 + 配置
- "创建"按钮 → Dialog 表单（名称 + 描述 + 模型 + 系统提示 + 工具）
- 操作: 编辑 / 复制 / 删除（AlertDialog 确认）

**API 接入**:
- GET `/api/v2/agents`
- POST `/api/v2/agents`
- PUT `/api/v2/agents/{id}`
- DELETE `/api/v2/agents/{id}`

### 2.4 任务中心（`/tasks` · 新增路由）

**新增文件**:
- `src/pages/Tasks.tsx`
- `src/components/tasks/TaskTable.tsx`
- `src/components/tasks/TaskDetail.tsx`

**功能**:
- 顶部 Tab: 全部 / 运行中 / 已完成 / 失败
- FilterBar: 智能体筛选 + 时间范围筛选
- Table: 任务名 / 智能体 / 状态 Badge / 进度 Progress / 开始时间 / 耗时 / 操作
- 点击行 → Sheet 显示详情（日志 + 输入 + 输出 + 重试）
- 空状态: EmptyState + "创建第一个任务" CTA

### 2.5 P1 验收
- [ ] Dashboard / Chat / Employees / Tasks 4 页面可访问
- [ ] 数据 fetch 成功（mock 或真实 API）
- [ ] 6 个状态（加载/空/错误/成功/禁用/权限）全覆盖
- [ ] 视觉一致性占位
- [ ] Playwright 截图通过
- [ ] TypeScript 0 错

---

## 3 · P2 · 工作流编辑器 + 知识库 + 系统设置

### 3.1 工作流编辑器（`/workflows` · 新增 + xyflow）

**新增文件**:
- `src/pages/Workflows.tsx` (列表)
- `src/pages/workflows/Editor.tsx`
- `src/components/workflow/Toolbar.tsx`
- `src/components/workflow/NodePanel.tsx`
- `src/components/workflow/ConfigPanel.tsx`
- `src/components/workflow/nodes/{Start,LLM,Knowledge,Tool,Condition,Loop,End}Node.tsx`

**功能**:
- /workflows: WorkflowCard 网格 + 创建按钮
- /workflows/[id]: 三栏布局（节点库 + Canvas + 配置面板）
- Canvas: ReactFlow + Background(variant="dots") + Controls + MiniMap
- 节点拖拽从 NodePanel → Canvas
- 选中节点 → ConfigPanel 动态显示该节点参数
- 顶部 Toolbar: 名称 / 保存 / 运行 / 调试 / 发布

**xyflow 集成关键点**:
```tsx
import { ReactFlow, Background, Controls, MiniMap,
         useNodesState, useEdgesState, addEdge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import '@/styles/xyflow-theme.css';   // 覆盖 CSS 变量为 brand
```

**xyflow-theme.css**（覆盖默认灰阶为 brand 色）:
```css
.xy-flow.ct-theme {
  --xy-node-border-default: 1px solid var(--border-default);
  --xy-node-border-selected-default: 2px solid var(--brand-500);
  --xy-handle-background-color-default: var(--brand-500);
  --xy-node-color-default: var(--text-primary);
  --xy-node-background-color-default: var(--surface-base);
  --xy-edge-stroke-default: var(--neutral-400);
  --xy-edge-stroke-selected-default: var(--brand-500);
}
```

### 3.2 知识库（`/knowledge` · 新增路由 · 旧 /documents 保留）

**新增文件**:
- `src/pages/Knowledge.tsx`
- `src/components/knowledge/FolderTree.tsx`
- `src/components/knowledge/DocumentTable.tsx`
- `src/components/knowledge/DocumentUpload.tsx`
- `src/pages/knowledge/Viewer.tsx`

**功能**:
- 左侧 FolderTree (200px) + 中间 DocumentTable
- 顶部搜索框 (支持 Cmd+K 聚焦)
- 顶部"上传"按钮 → Dialog（拖拽 + 表单）
- Table: 文件名 / 类型 / 大小 / 修改时间 / 状态
- 点击行 → 右侧 Sheet 或新页 `/knowledge/[id]` 预览
- 多选 Checkbox + 批量操作

### 3.3 系统设置（`/settings` 强化）

**保留**: 公司信息 + 套餐
**新增分组**:
- **个人资料** (`/settings/profile`) — 姓名、邮箱、头像
- **账号安全** (`/settings/security`) — 修改密码、2FA
- **套餐与计费** (`/settings/billing`) — 升级/降级/发票
- **模型配置** (`/settings/models`) — 默认模型、API Key 列表
- **成员与权限** (`/settings/permissions`) — 邀请成员、角色矩阵
- **Webhook** (`/settings/webhooks`) — 事件订阅
- **运行状态** (`/settings/status`) — API 健康、API 限速

**技术**: Tabs 横向 + 左侧二级菜单（在 Tabs 之内）

### 3.4 Monitoring 重做（`/monitoring`）

**保留**: 监控与财务数据接入
**改造**: 用 Dashboard 同套 KPI + Chart 组件
- 顶部 KPI: 在线用户 / API QPS / 错误率 / 收入
- 中部: 调用趋势 + 错误日志
- 底部: Top 10 客户调用 + 财务汇总

### 3.5 P2 验收
- [ ] /workflows 列表 + Editor 可访问
- [ ] xyflow 节点拖拽 + 连线工作
- [ ] /knowledge 文件夹树 + 表格 + 搜索 + 上传工作
- [ ] /settings 7 个分组全部可达
- [ ] /monitoring 视觉与 Dashboard 一致

---

## 4 · P3 · 登录/营销/行业页 + 全验收

### 4.1 登录/注册（新增 3 路由）

**新增文件**:
- `src/pages/Login.tsx`
- `src/pages/Register.tsx`
- `src/pages/ForgotPassword.tsx`
- `src/contexts/AuthContext.tsx`

**布局**: 左侧品牌色渐变 + 右侧表单（基于 Antd Pro login 截图参考）
**功能**:
- 邮箱 + 密码 + 记住我 + 忘记密码链接
- 注册: 邮箱 + 密码 + 确认 + 同意条款
- 忘记密码: 邮箱 + 验证码
- 成功后跳转到 `/dashboard`
- AuthContext 持久化到 localStorage

### 4.2 Marketing 视觉母版化重做

**保留**: 现有数据 + 路由
**改造**: 用新设计系统重做 Hero / Feature Grid / Pricing Table / CTA / Footer
**重点**: 与视觉母版对齐（颜色/字体/间距）

### 4.3 行业页 + 资源页轻量化

**改造**: 保留现有 SEO 内容，UI 套用新设计系统
- /industries/decoration
- /industries/medical
- /cases
- /clients
- /blog
- /faq
- /opc-story
- /content-sop
- /funnel
- /pricing
- /try
- /documents (保留为介绍)

### 4.4 18 路由 + 5 新路由 = 23 路由 全验收

**验收清单** (VISUAL_ACCEPTANCE.md):
- [ ] 23 路由全部可访问
- [ ] 每路由 6 状态（加载/空/错误/成功/禁用/权限）
- [ ] TypeScript 0 错
- [ ] pnpm build 成功
- [ ] Lighthouse Performance ≥ 80
- [ ] 可访问性 WCAG AA 合规
- [ ] 视觉一致性占位（待视觉母版 URL 后校准）

### 4.5 视觉回归基线（关键）

- 用 Playwright 对 23 路由全量截图
- 保存到 `design/rebuild/screenshots/baseline-v2-light-{page}.png`
- 后续 PR 修改后自动对比

---

## 5 · 不做清单（红线 #59 + 范围保护）

明确**不做**（避免范围蔓延）:
- ❌ 修改 backend (gateway_v22.py, data-layer/*, v3_*.py)
- ❌ 修改 landing-page/ 静态 HTML（17 个 .html）
- ❌ 修改 ai_compliance/, agent/, analytics/, billing/, api/ 等后端模块
- ❌ 数据库迁移 / schema 变更
- ❌ 真实数据删除
- ❌ 密钥/凭据修改
- ❌ 部署到生产
- ❌ 修改现有 brand 颜色（仅扩展不替换）
- ❌ 删除现有 19 个 .tsx 页面文件
- ❌ 引入 Antd / Antd Pro / Material UI / styled-components
- ❌ 引入 LangChain / Vercel AI SDK（除非 chat 需要）

---

## 6 · 风险与缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| 视觉母版 URL 一直未提供 | 中 | 用默认设计 token 推进；母版到位后做校准 |
| radix-ui meta package 与 CloudTech Vite 冲突 | 低 | 实证安装；失败则分散装各 radix 包 |
| xyflow 与 React 18 StrictMode 兼容 | 低 | xyflow 12.x 已修复；如遇双渲染则移除 StrictMode |
| pnpm install 网络问题 | 中 | 备用 yarn；公司内网代理 |
| Lighthouse 性能下降 | 中 | 用 dynamic import + code splitting；shadcn 组件按需引入 |
| i18n 硬编码中文 | 低 | 暂用 dict 自实现；Phase 4 引入 react-i18next |
| 数据 API 不存在（如 /chat/completions） | 中 | 用 mock + MSW；后端补齐后切换 |
| 真实业务功能回归 | 高 | 保留所有现有 fetch 调用 + 数据契约；逐步替换 UI 壳 |

---

## 7 · 持续执行原则

1. **每完成一个 Phase 立即截图 + 验收**（红线 #2 每个 ✓ 前 Glob 实证）
2. **每个 PR 都可回滚**（tag baseline + 分支保护）
3. **不引入新依赖未经批准**（section 1.2 列表是初始批准基线）
4. **每个 shadcn 组件复制后立即 SPDX 头注释**（LICENSE 合规）
5. **每周一次大同步**：AGENTS.md + CORE-RULES.md + MEMORY.md（红线 #6 4 步同步）

---

## 8 · 完整文件交付清单（实施完成后）

```
design/research/deliverables/         ← 本阶段已完成
├── REFERENCE_RESEARCH.md             ✓
├── REFERENCE_SOURCE_MAP.csv          ✓
├── CLOUDTECH_DESIGN_SYSTEM.md        ✓
├── COMPONENT_MAPPING.csv             ✓
├── UI_IMPLEMENTATION_PLAN.md         ✓ (本文件)
└── VISUAL_ACCEPTANCE.md              ✓

design/rebuild/                       ← 实施阶段建立
├── AUDIT.md
├── PAGE_INVENTORY.csv
├── DESIGN_SYSTEM.md (镜像)
├── IMPLEMENTATION_PLAN.md (镜像)
├── PROGRESS.json
├── TEST_REPORT.md
├── VISUAL_REVIEW.md
├── FINAL_HANDOFF.md
└── screenshots/
    ├── baseline-v2-light-{page}.png  ← 23 路由
    └── after-v2-light-{page}.png     ← 视觉对比
```

---

**计划状态**: 等用户拍板：
1. 工作分支命名 `ui-rebuild/v2-light` 是否 OK？
2. .gitignore 追加 `_cloned/` 是否 OK？
3. 新增依赖清单（1.2）是否 OK？
4. 视觉母版即时设计 URL 是否提供？

确认后立即进入 P0 实施。
