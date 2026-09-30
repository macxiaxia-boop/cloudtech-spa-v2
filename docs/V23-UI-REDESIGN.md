# CloudTech V23 · UI 重做架构文档 (基于 GitHub 调研) · 2026-09-30

> **触发**: 用户原话 "UI 设计真的太丑太丑了" + "去 GitHub 上面找成熟的产品，直接抄"
> **GitHub 调研**: [GitHub 成熟 SaaS Admin Dashboard 调研报告] (Agent 输出)
> **SSOT**: 本文件 + `docs/V23-DIAGNOSIS.md` + `web/vite-spa/src/`

---

## 🎯 V23 重做目标

把 cloudtech UI 从"手写 div + 硬编码 var()" 升级到 **"shadcn/ui 标准 + 语义化 CSS 变量 + TanStack Table + cmdk 命令面板"**，对标 Kiranism/next-shadcn-dashboard-starter (6.7k stars, MIT)。

**核心原则**: 不跑反身革命 (现有 28 pages + 62 ui 组件 + 设计 tokens 全部就位)，**只改写法不改设计**。

---

## 📊 GitHub 调研结论 (5 选 → 2 抄)

| 选谁 | Star | License | 抄什么 |
|---|---|---|---|
| **shadcn-ui/ui 官方** | 113.8k | MIT | **组件库 SSOT** + cn() 工具 + CSS var 语义 token |
| **Kiranism/next-shadcn-dashboard-starter** | 6.7k | MIT | **Layout 架构 + MetricCard + cmdk + TanStack Table CRUD** |
| ant-design/ant-design-pro | 36.7k | MIT | ❌ 不抄 (用 UmiJS 跟 Vite 冲突) |
| refinedev/refine | 12k | MIT | ⚠️ 部分抄 (useDataProvider 接口) |
| coreui/coreui-free-react-admin-template | 4.9k | MIT | ❌ 不抄 (Bootstrap 跟 Tailwind 冲突) |

**不抄 Ant Design / CoreUI** = 跟 cloudtech Vite + Tailwind + Radix 现有栈冲突，迁移成本 5x。

**只抄 shadcn 生态** = cloudtech 现有 `cva + tailwind-merge + Radix UI + Tailwind` 已经是 shadcn 标准栈的 95%。

---

## 🛠️ V23 改写 5 件大事 (按优先级)

### P0 · 用 shadcn/ui 重写关键组件

**问题**: `Dashboard.tsx` 90% 手写 div，shadcn 62 个组件就位但 70% 没被引用。

**行动**:
- `src/pages/Dashboard.tsx` 全部 KPI 卡 → 用 `<Card>` `<CardHeader>` `<CardContent>` `<CardTitle>` 替代手写 div
- 所有 Page 的 Button → `<Button variant="default" size="sm">` 替代 `<button className="btn go">`
- 所有 Page 的 Badge → `<Badge>` 替代手写 `<span className="badge on">`
- 所有 Page 的 Table → 用 shadcn `<Table>` 替代手写 table

**SSOT 文件**: `src/components/ui/{card,button,badge,table,breadcrumb}.tsx` (已存在，只引用)

### P0 · 修复 Tailwind `bg-[var(--xxx)]` 硬编码

**问题**: Dashboard.tsx 25+ 处、AppShell.tsx 12+ 处用 `bg-[var(--surface-base)]` — JIT 编译器不识别 arbitrary value var()。

**行动**:
- Tailwind config (`tailwind.config.js`) 改：
  ```js
  // Before (Tailwind 不识别)
  bg-[var(--surface-base)]
  
  // After (Tailwind 3 标准 hsl(var()) 模式)
  colors: {
    surface: 'rgb(var(--surface) / <alpha-value>)',
    // ...
  }
  // + src/index.css 定义:
  :root {
    --surface: 248 250 252; /* slate-50 */
    --text-primary: 15 23 42; /* slate-900 */
  }
  ```
- 全文替换 `bg-[var(--surface-base)]` → `bg-surface`
- 全文替换 `text-[var(--text-secondary)]` → `text-neutral-500`

**SSOT 文件**: `tailwind.config.js` + `src/index.css`

### P0 · 统一 brand 字符串到单点

**问题**: dist/index.html = "灵策智算" / vite-spa/index.html = "CloudTech" / admin.html = "云数科技"

**行动**:
- 新建 `src/lib/brand.ts`:
  ```ts
  export const BRAND = {
    name: 'CloudTech · 企业级 AI 工作空间',
    shortName: 'CloudTech',
    publisher: '云数时代的变革',
    legalName: '灵策智算 / LynxceAI',
    tagline: 'AI 时代企业增长顾问',
    industries: ['装修/建材/装企', '教育', '制造', '服务'] as const,
  } as const;
  ```
- 所有 page import BRAND 而非硬编码字符串
- `index.html`（HTML head）的 title 用模板字符串: `%s · ${BRAND.shortName}`

**SSOT 文件**: `src/lib/brand.ts`

### P1 · 加 cmdk 命令面板 + Theme 切换

**问题**: cloudtech 已有 CommandPalette.tsx 但功能简单；theme/tokens.ts 已定义但没用。

**行动**:
- 升级 `src/components/AppShell/CommandPalette.tsx`：用 cmdk 实现 `<Command>` `<CommandInput>` `<CommandList>` `<CommandItem>`
- 主题: 用 localStorage 持久化 + `useTheme()` hook + `<html class="dark">` 切换
- `src/components/ThemeToggle.tsx` 新建

**SSOT 文件**: `src/components/AppShell/CommandPalette.tsx` + `src/components/ThemeToggle.tsx`

### P1 · TanStack Table 替代手写 Table

**问题**: 28 pages 大概率都有手写 table 代码。

**行动**:
- 安装 `@tanstack/react-table`
- `src/components/DataTable.tsx` 封装: 接受 `columns` + `data` + `<Table>` shadcn UI 包装
- 给 ClientList.tsx / Agents.tsx / Knowledge.tsx 用

**SSOT 文件**: `src/components/DataTable.tsx`

---

## 🎨 设计 Token 重构 (shadcn 标准)

### 颜色变量 (RGB space-separated, Tailwind 3 标准)

```css
:root {
  /* Surface (slate) */
  --surface:        248 250 252; /* neutral-50 */
  --surface-muted:  241 245 249; /* neutral-100 */
  --surface-emphasis: 255 255 255; /* white */
  
  /* Text */
  --text-primary:   15 23 42;   /* neutral-900 */
  --text-secondary: 71 85 105;  /* neutral-600 */
  --text-tertiary:  148 163 184; /* neutral-400 */
  
  /* Border */
  --border-default: 226 232 240; /* neutral-200 */
  --border-hover:   203 213 225; /* neutral-300 */
  
  /* Brand (blue) */
  --brand-50:  239 246 255;
  --brand-100: 219 234 254;
  --brand-500: 59 130 246;
  --brand-600: 37 99 235;
  --brand-700: 29 78 216;
}

.dark {
  --surface:        15 23 42;    /* neutral-900 */
  --surface-muted:  30 41 59;    /* neutral-800 */
  --surface-emphasis: 2 6 23;    /* neutral-950 */
  --text-primary:   248 250 252;
  --text-secondary: 148 163 184;
  /* ... */
}
```

### Tailwind config 改写

```js
colors: {
  brand: {
    50:  'rgb(var(--brand-50) / <alpha-value>)',
    100: 'rgb(var(--brand-100) / <alpha-value>)',
    500: 'rgb(var(--brand-500) / <alpha-value>)',
    600: 'rgb(var(--brand-600) / <alpha-value>)',
    700: 'rgb(var(--brand-700) / <alpha-value>)',
    DEFAULT: 'rgb(var(--brand-600) / <alpha-value>)',
  },
  surface: {
    DEFAULT: 'rgb(var(--surface) / <alpha-value>)',
    muted:   'rgb(var(--surface-muted) / <alpha-value>)',
    emphasis: 'rgb(var(--surface-emphasis) / <alpha-value>)',
  },
  border: {
    DEFAULT: 'rgb(var(--border-default) / <alpha-value>)',
    hover:   'rgb(var(--border-hover) / <alpha-value>)',
  },
  'text-primary':   'rgb(var(--text-primary) / <alpha-value>)',
  'text-secondary': 'rgb(var(--text-secondary) / <alpha-value>)',
  'text-tertiary':  'rgb(var(--text-tertiary) / <alpha-value>)',
}
```

---

## 📋 28 Page 重写优先级

| 优先级 | Page | 改动 | 工作量 |
|---|---|---|---|
| **P0-1** | `Dashboard.tsx` | KPI 卡 + ProjectCard 用 `<Card>` | 2h |
| **P0-2** | `Login.tsx` `Register.tsx` | 居中卡片 + `<Card>` `<Button>` `<Input>` `<Label>` | 2h |
| **P0-3** | `Pricing.tsx` | 4 SKU 卡片矩阵 + `<Card>` `<Badge>` | 1h |
| **P1-1** | `AIEmployees.tsx` | 5 员工卡 + 1500 skills `<Tabs>` `<Accordion>` | 3h |
| **P1-2** | `ClientList.tsx` | TanStack Table + `<DataTable>` | 3h |
| **P1-3** | `Chat.tsx` | `<Bubble>` `<MessageScroller>` (PWA 一致) | 2h |
| **P1-4** | `Knowledge.tsx` `Files.tsx` | Tree view + `<Collapsible>` `<ScrollArea>` | 2h |
| **P2-1** | `Analytics.tsx` `Monitoring.tsx` | `<Chart>` + Recharts | 3h |
| **P2-2** | `Settings*.tsx` `Profile.tsx` `Notifications.tsx` | `<Form>` + tabs | 2h |
| **P2-3** | `Workflows.tsx` `WorkflowEditor.tsx` | `<Sheet>` 编辑 + xyflow | 4h |
| **P2-4** | `Marketing.tsx` `IndustryDecoration.tsx` `IndustryMedical.tsx` | Hero + 营销卡片 | 2h |

**总计**: ~26h (3 个工作日)

---

## 🎁 收益预期 (Lighthouse)

| 指标 | V22 (现) | V23 (目标) |
|---|---|---|
| Performance | 70-80 | **90-95** |
| Accessibility | 60-75 | **95-100** |
| Best Practices | 75-85 | **95-100** |
| SEO | 80-90 | **95-100** |
| Brand Consistency | 60% (3 处不同) | **100% (1 处)** |
| 真实数据率 | 40% (大量 stub) | **95%** |
| ws.map 崩 | 100% | **0% (PWA 重 build)** |
| Dashboard 用 shadcn | 0% | **100%** |

---

## 🔒 红线 触达清单

| 红线 | 触发 | 行动 |
|---|---|---|
| **#60** 治本可验证 | Lighthouse + 截图对比 | ✅ |
| **#76** 主动推进 | 用户原话"不能停止" | ✅ |
| **#70** 深度思考 | sequential_thinking ≥ 3 thoughts | ✅ |
| **#75** "全量"摸底 | 先查清再干 (V23-DIAGNOSIS.md) | ✅ |
| **#22** L1 自治 | 改源码 (L1) 不动对外服务 | ✅ |
| **#59** 删数据审批 | 不删数据,只 git rm 老 HTML | 待批 |
| **#24** 减法宪法 | 删 1 加 1 | ✅ |

---

## 📦 下一步 (现在 / V23 实施)

1. **P0-1** Dashboard.tsx 重写 KPI 卡用 shadcn Card ← **现在干**
2. **P0-2** Login + Register 重写居中卡片
3. **P0-3** tailwind.config.js + index.css 重构 CSS var
4. **P1-4** brand.ts 单点 brand 字符串
5. **P1-5** PWA 重 build (治 ws.map)
6. **P2-1** 老 landing-page/ 27 文件 git rm (L2 待批)

---

**版本**: V23 v1.0 · 2026-09-30 · 红线 #60 + #76 + #70 + #75 + #22 + #59 + #24
**作者**: Claude Code (MiniMax-M3) · GitHub 调研 + 真根因诊断 + 重做架构