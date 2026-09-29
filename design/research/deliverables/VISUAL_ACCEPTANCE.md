# VISUAL_ACCEPTANCE.md · CloudTech UI 重构视觉验收标准

> **基于**: design/research/deliverables/CLOUDTECH_DESIGN_SYSTEM.md + UI_IMPLEMENTATION_PLAN.md
> **范围**: CloudTech UI/UX 重构完成后，对 23 个路由的视觉与交互验收
> **状态**: 待视觉母版 URL 提供后做最终校准

---

## 1 · 验收原则

- **逐路由验收**: 23 个路由 × 6 状态 = 138 个验收点
- **证据优先**: 每个 ✓ 必须有截图/录屏/测试结果支撑（红线 #2）
- **可重复**: 用 Playwright 截图脚本自动化视觉回归
- **不可通过修改标准来掩盖问题**: 偏差必须修复实现，不修标准

---

## 2 · 路由 × 状态验收矩阵

### 2.1 33 路由清单（v3 视觉母版 · 2026-09-29 supersede v2）

| # | 路由 | 页面 | Phase | v3 模块 | 验收优先级 |
|---|---|---|---|---|---|
| 1 | `/login` | Login | P3 | **02 登录/注册（v3 居中卡片 + 冰山渐变）** | P0 |
| 2 | `/register` | Register | P3 | 02 | P1 |
| 3 | `/forgot-password` | ForgotPassword | P3 | 02 | P2 |
| 4 | `/` | Marketing / 官网品牌页 | P0+P3 | **01 官网/品牌页（v3 强化）** | P0 |
| **5** | **`/workspace/select`** | **WorkspaceSelector** | **P3.5** | **03 选择工作空间（v3 新增）** | **P1** |
| 6 | `/dashboard` | Dashboard | P0+P1 | 04 工作台（+ AI 今日简报 + 团队任务分布）| P0 |
| 7 | `/chat` | Chat | P1 | 05 AI 对话空间（+ 会话时间线 + 代码块）| P0 |
| 8 | `/employees` | AIEmployees | P1 | 06 智能体中心（+ 数据分析专家）| P0 |
| 9 | `/employees/new` | AgentCreateWizard | P1 | **07 创建/配置（v3 5 步向导）** | P0 |
| 10 | `/employees/[id]/edit` | AgentEdit | P1 | 07 | P0 |
| 11 | `/workflows` | Workflows | P2 | **08 工作流编排（v3 独立完整页）** | P0 |
| 12 | `/workflows/[id]` | WorkflowEditor | P2 | 08 | P0 |
| 13 | `/tasks` | Tasks | P1 | 09 任务中心 | P0 |
| 14 | `/knowledge` | Knowledge | P2 | 10 知识库 | P0 |
| 15 | `/files` | Files | P2 | 11 文件管理（网格视图）| P0 |
| 16 | `/analytics` | Analytics | P4 | 12 数据分析中心 | P1 |
| 17 | `/settings/team` | Team | P4 | 13 团队与权限（成员卡形式）| P2 |
| 18 | `/settings/system` | SystemSettings | P4 | **14 系统设置（v3 5 Tab）** | P2 |
| 19 | `/profile` | Profile | P4 | 15 个人中心 | P2 |
| 20 | `/settings/profile` | Settings/Profile | P2 | (旧) | P1 |
| 21 | `/settings/billing` | Settings/Billing | P2 | (旧) | P1 |
| 22 | `/settings/models` | Settings/Models | P2 | (旧) | P1 |
| 23 | `/settings/permissions` | Settings/Permissions | P2 | (旧) | P2 |
| 24 | `/settings/status` | Settings/Status | P2 | (旧) | P2 |
| 25 | `/monitoring` | Monitoring | P2 | (旧) | P1 |
| 26 | `/notifications` | Notifications | P4 | (旧) | P2 |
| 27 | `/pricing` | Pricing | P3 | Marketing | P2 |
| 28 | `/clients` | ClientList | P3 | 营销 | P2 |
| 29 | `/cases` | CaseLibrary | P3 | 营销 | P2 |
| 30 | `/funnel` | Funnel | P3 | 营销 | P3 |
| 31 | `/mobile/dashboard` | MobileDashboard | P4 | **15 移动端（v3 2 视图）** | P1 |
| 32 | `/mobile/employees` | MobileEmployees | P4 | 15 | P1 |
| 33 | `/mobile/chat` | MobileChat | P4 | 15 | P2 |

**v3 关键变化**:
- ✅ +1 路由 `/workspace/select`（P3.5 新增）
- 🔄 创建向导从 6 步 → **5 步**（合并"角色+技能"为"技能配置"，新增"测试对话"）
- 🔄 系统设置从 4 Tab → **5 Tab**（新增"系统日志"）
- 🔄 移动端从 3 视图 → **2 视图**（删除对话页）
- ⚠️ v2 "01 营销首页" → v3 升级为 **"01 官网/品牌页（落地页）"**

**保留路由（不改）**: /try /blog /faq /opc-story /content-sop /industries/decoration /industries/medical /documents /billing

### 2.2 每路由 6 状态验收清单

| 状态 | 验证项 | 通过标准 |
|---|---|---|
| **loading** | 数据加载中 | 显示 Skeleton / Spinner，无布局抖动 |
| **empty** | 数据为空 | 显示 EmptyState + CTA 引导，无空白 |
| **error** | 数据错误 | 显示 ErrorBoundary + 重试按钮，错误可定位 |
| **success** | 数据正常 | 完整渲染，无 console error，无布局溢出 |
| **disabled** | 权限/状态禁用 | 控件 opacity 50%，cursor not-allowed，提示原因 |
| **permission** | 权限不足 | 跳 403 页面或显示提示，引导联系管理员 |

---

## 3 · 视觉一致性验收（每个路由）

### 3.1 全局设计系统一致性

| 检查项 | 通过标准 | 验证方式 |
|---|---|---|
| 主色 `#0066FF` 一致 | 所有 primary CTA、链接、激活态用 brand-500/600 | DevTools 颜色检查 |
| 中性色统一 | 所有文本/边框/背景用 neutral-* 色阶 | DevTools 颜色检查 |
| 字体一致 | 全局 var(--font-sans) | DevTools computed font |
| 圆角规范 | Button=8 / Card=12 / Dialog=16 | DevTools borderRadius |
| 阴影规范 | shadow-xs/sm/md/lg/xl 与设计系统一致 | DevTools boxShadow |
| 间距网格 | 所有间距是 4 倍数（4/8/12/16/24/32...） | DevTools margin/padding |
| 焦点环可见 | Tab 键焦点环 3px ring + 2px offset | 手动键盘测试 |
| 减少动态偏好 | `prefers-reduced-motion: reduce` 时禁用动画 | DevTools rendering panel |
| 暗色模式 hook | html.dark 类切换正常（暂留 light only） | DevTools |

### 3.2 组件级一致性

| 组件 | 检查项 |
|---|---|
| Button | 6 variants × 6 状态全部正常；loading spinner 显示 |
| Input | focus ring 可见；error 状态有 destructive 边框 + 提示 |
| Card | hover 阴影加深；CardHeader 标题字号一致 |
| Dialog | 遮罩半透明；Esc 关闭；点击遮罩关闭（可配置） |
| Sheet | 滑入动画流畅；focus trap 正常 |
| DropdownMenu | 键盘 ↑↓ 导航；Enter 确认 |
| Select | 单选/多选正常；placeholder 可见 |
| Toast | 4 秒自动消失；可手动关闭；错误/成功/警告图标 |
| Table | 表头 sticky；行 hover 背景；列对齐一致 |
| Tabs | 激活态下划线；内容切换无布局跳动 |
| Sidebar | 当前路由高亮；可折叠；移动端 Sheet 切换 |
| Command | Cmd+K 触发；模糊搜索；键盘导航 |

### 3.3 页面级视觉对照（基于 2026-09-29 视觉母版 SHA256 实证）

**视觉母版**: `design/research/screenshots/visual-master-20260929.png`
**SHA256**: `797246323c6f8fb0360b072ecf2512b5778b271b204ee85eb192d5b82ef7413c`

| 页面 | 关键视觉元素 | 母版对照指标 |
|---|---|---|
| Marketing | Hero 大标题 + 5 个能力 chip | 大标题 48px / 700 · 副标 20px · 描述 16px · 浅蓝紫渐变背景 · 无插图纯文字 |
| Login (01) | 居中卡片 + 邮箱/密码 + 第三方 | 卡片宽 400px / 圆角 12px / 阴影极轻 / 第三方按钮 3 个 (Google/GitHub/Microsoft) |
| Dashboard (02) | Sidebar + 4 KPI 卡 + 快速开始 + 最近任务 | KPI 数字 32px · 状态色 = 进行中蓝/已完成绿/失败红 · 进度条 brand-600 |
| Chat (03) | 左侧会话 + 中间气泡 + 输入框 | 会话列表 240px · 气泡左右对齐 · AI 气泡可嵌图表 · 输入框固定底部 |
| AIEmployees (04) | Tab + 卡片网格 3 列 | 智能体卡片 12px 圆角 · 顶部图标 12px 圆角彩色背景 · 底部 pill 标签 |
| WorkflowEditor (05) | 三栏布局 + 5 节点 | 节点库 200px / Canvas 点状网格 / 配置面板 320px / 节点圆形（开始）/ 方形（操作） |
| Tasks (06) | Tab + Table + 进度条 + 状态徽章 | 进度条 brand-600 · 状态徽章圆角 6px · 进行中蓝/已完成绿/失败红 |
| Knowledge (07) | Tab + 搜索 + Table | 文件类型彩色图标 · 大小右对齐 · 修改时间相对显示 |
| Settings (08) | Tab + Table + 开关 | 5 个模型行 · 开关 brand-600 · 服务商次要文字 |

**色板对照表**（CloudTech 落地 vs 母版实测）:

| 元素 | 母版实测 | CloudTech 落地 |
|---|---|---|
| 主色 brand-600 | #2563EB | ✓ 已升级 |
| 文本 primary | #0F172A | ✓ --neutral-900 |
| 边框 default | #E2E8F0 | ✓ --neutral-200 |
| 背景 subtle | #F8FAFC | ✓ --neutral-50 |
| Success 500 | #10B981 | ✓ --success-500 |
| Warning 500 | #F59E0B | ✓ --warning-500 |
| Destructive 500 | #EF4444 | ✓ --destructive-500 |
| Accent purple | #8B5CF6 | ✓ --accent-purple-500 |
| Accent orange | #F97316 | ✓ --accent-orange-500 |

---

## 4 · 交互验收

### 4.1 键盘操作（每路由）

| 键 | 行为 |
|---|---|
| Tab | 焦点可遍历所有交互元素 |
| Shift+Tab | 反向遍历 |
| Enter / Space | 激活按钮/链接 |
| Esc | 关闭 Dialog/Sheet/Dropdown |
| ↑↓ ←→ | 列表/菜单/Sheet 内导航 |
| Cmd/Ctrl + K | 打开命令面板（全局） |
| / | 聚焦页面搜索框（如有） |
| Cmd/Ctrl + S | 保存（如适用） |

### 4.2 表单交互（每路由含表单的）

| 验证项 | 通过标准 |
|---|---|
| 必填校验 | 提交时显示错误提示 |
| 邮箱格式 | 实时校验 |
| 密码强度 | 强度条 + 提示 |
| 错误提示位置 | 字段下方，关联 aria-describedby |
| 提交 loading | 按钮显示 spinner + 禁用 |
| 提交成功 | Toast 提示 + 路由跳转/数据更新 |
| 提交失败 | 错误 Toast + 表单不重置 |

### 4.3 列表/表格交互

| 验证项 | 通过标准 |
|---|---|
| 排序 | 表头点击排序，箭头指示 |
| 筛选 | FilterBar 实时筛选 |
| 分页 | 页码跳转 + 每页条数选择 |
| 批量操作 | Checkbox 全选 + 批量操作菜单 |
| 行操作 | DropdownMenu 每行独立 |
| 空数据 | 显示 EmptyState + 引导 CTA |
| 加载更多 | 无限滚动或"加载更多"按钮 |

---

## 5 · 响应式验收（每个路由）

### 5.1 三档断点截图

| 断点 | 宽度 | 必查 |
|---|---|---|
| 桌面 | 1440 × 900 | 完整布局可用 |
| 平板 | 768 × 1024 | Sidebar 折叠；表格可读 |
| 手机 | 375 × 812 | Sidebar 隐藏用 Sheet；表格转 Card List；字号可读 |

### 5.2 窄屏退化规则

- Sidebar (256px) → Sheet/Drawer
- 4 列网格 → 2 列 → 1 列
- Table → Card List
- Dialog → Bottom Sheet
- 字号不缩小（保持 16px 最小）

---

## 6 · 可访问性验收（WCAG 2.1 AA）

| 检查项 | 工具 | 通过标准 |
|---|---|---|
| 颜色对比度 | axe DevTools / Lighthouse | 正文 ≥ 4.5:1 / 大字 ≥ 3:1 |
| 焦点环可见 | 手动键盘测试 | 3px ring + 2px offset |
| ARIA 属性 | axe DevTools | 0 violations |
| 表单标签 | axe DevTools | 所有 input 有关联 label |
| 替代文本 | axe DevTools | 所有 img/icon 有 alt/aria-label |
| 键盘可达 | 手动测试 | 0 mouse-only 交互 |
| 语义化 HTML | Lighthouse | header/nav/main/footer/button 正确使用 |
| Skip Link | 手动测试 | 提供"跳到主要内容"链接 |
| 实时区域 | axe DevTools | Toast 用 aria-live |

---

## 7 · 性能验收

| 指标 | 工具 | 通过标准 |
|---|---|---|
| Lighthouse Performance | Chrome DevTools | ≥ 80 |
| Lighthouse Accessibility | Chrome DevTools | ≥ 90 |
| Lighthouse Best Practices | Chrome DevTools | ≥ 90 |
| Lighthouse SEO | Chrome DevTools | ≥ 90 |
| First Contentful Paint | Chrome DevTools | ≤ 1.5s |
| Largest Contentful Paint | Chrome DevTools | ≤ 2.5s |
| Time to Interactive | Chrome DevTools | ≤ 3.5s |
| Total Blocking Time | Chrome DevTools | ≤ 300ms |
| Cumulative Layout Shift | Chrome DevTools | ≤ 0.1 |
| Bundle Size (gzipped) | vite build | ≤ 300KB 初始包 |

---

## 8 · 测试验收

### 8.1 单元测试（vitest）
- [ ] 每个 shadcn 组件有 snapshot test
- [ ] 表单验证逻辑测试
- [ ] API fetch 适配器测试
- [ ] utility 函数测试
- [ ] 覆盖率 ≥ 70%

### 8.2 端到端测试（Playwright · v2 32 路由）
- [ ] 32 路由 × 6 状态 = 192 个 E2E 用例（v2 supersedes v1 23 路由 138 用例）
- [ ] 关键用户旅程: 登录（左右分栏）→ Dashboard（含运行概览）→ Chat → 创建 Agent（6 步向导）→ 配置 Workflow（5 类节点库）→ 任务中心 → 知识库/文件管理（视图切换）→ 数据分析 → 通知 → 个人中心
- [ ] 截图回归: 32 路由基线 + 修改后对比

### 8.3 视觉回归测试（v2 32 路由）
- [ ] Playwright 截图脚本覆盖 32 路由 × 3 断点（桌面 1440 / 平板 768 / 手机 375）= **96 张基线图**
- [ ] 差异阈值 0.1%（像素差异）
- [ ] 自动报警到 CI

---

## 9 · 数据契约验收

- [ ] 现有 18 路由的 fetch 调用 100% 保留
- [ ] 现有数据 shape 不破坏（如 DashboardPage 的 `UsageData` / `FunnelReview`）
- [ ] 新增 5 路由的 API 与后端 mock 一致
- [ ] 错误状态正确处理（401/403/404/500）
- [ ] 加载状态用真实 API delay 或 MSW mock

---

## 10 · 完整验收清单（提交 PR 前）

### 10.1 功能验收（v2 32 路由）
- [ ] 32 路由全部可访问（无 404）
- [ ] 每路由 6 状态全覆盖（loading/empty/error/success/disabled/permission）
- [ ] AppShell 在所有路由一致显示
- [ ] 现有 18 路由数据不丢失（保留 fetch 调用与数据契约）
- [ ] **v2 新增 9 路由全部上线**（创建向导/文件管理/模型管理/团队/系统/数据分析/通知/个人/移动端）
- [ ] 视觉母版 v2 对齐（SHA256 `5d6f1e40...`）

### 10.2 技术验收
- [ ] TypeScript 0 错（`pnpm tsc --noEmit`）
- [ ] ESLint 0 错（`pnpm lint`）
- [ ] pnpm build 成功（`pnpm build`）
- [ ] pnpm test 全部通过（`pnpm test`）
- [ ] shadcn 组件 LICENSE 头 100% 添加
- [ ] 无 console.error / console.warning
- [ ] 无 404 资源

### 10.3 性能验收
- [ ] Lighthouse Performance ≥ 80
- [ ] Lighthouse Accessibility ≥ 90
- [ ] Bundle gzipped ≤ 300KB

### 10.4 可访问性验收
- [ ] axe DevTools 0 violations
- [ ] 键盘 100% 可达
- [ ] WCAG AA 颜色对比

### 10.5 响应式验收
- [ ] 桌面 (1440×900) 截图通过
- [ ] 平板 (768×1024) 截图通过
- [ ] 手机 (375×812) 截图通过

### 10.6 视觉验收（v2 32 路由）
- [ ] **32 路由 × 3 断点 = 96 张基线截图保存**（v2 supersedes v1）
- [ ] 视觉对比无偏差或偏差已修

### 10.7 文档验收
- [ ] design/rebuild/AUDIT.md 更新
- [ ] design/rebuild/PROGRESS.json 更新
- [ ] design/rebuild/TEST_REPORT.md 更新
- [ ] design/rebuild/VISUAL_REVIEW.md 更新
- [ ] design/rebuild/FINAL_HANDOFF.md 起草

---

## 11 · 不通过的处理

发现验收不通过时：
1. **记录**: 设计/rebuild/ISSUES.md 写明根因 + 证据 + 影响范围
2. **修复**: 修实现，不修标准
3. **复测**: 修复后重新跑全部验收
4. **不可通过删除功能来掩盖**（用户原话红线）

---

## 12 · 验收工具栈

- **Playwright**: 视觉回归 + E2E
- **axe DevTools**: 可访问性
- **Lighthouse**: 性能
- **vitest**: 单元测试
- **tsc + eslint**: 类型 + 代码质量
- **vite build**: 构建

---

## 13 · 持续验收节奏

| 阶段 | 频率 | 工具 |
|---|---|---|
| 开发中 | 每次提交 | Playwright 当前路由截图 + axe |
| Phase 完成 | Phase 收口 | 23 路由 × 3 断点全量截图 + Lighthouse |
| PR 提交 | 每次 | CI 全跑 + reviewer 手动验证 |
| 视觉母版到位 | 一次性 | 与母版对比 + 校准 token |

---

**验收状态**: 等待视觉母版 URL；URL 到位后立即补充 §3.3 的母版对照具体指标。
