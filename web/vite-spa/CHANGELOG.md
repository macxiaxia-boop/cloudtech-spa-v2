# Changelog

CloudTech UI 所有重要变更记录在此。

## [release-v2.0.0] - 2026-09-29

### 🎉 史诗级完工 · v3 视觉母版 15 模块 100%

### Added

#### 设计系统 + AppShell
- 完整 design tokens（brand/neutral/success/warning/destructive 完整色阶 + 渐变 + 阴影）
- 61 个 shadcn/ui 组件（MIT · SHA `db2db460`）· LICENSE-3RD-PARTY.md 合规
- 5 个 AppShell 组件（BasicLayout/AppSidebar/AppHeader/AppBreadcrumb/CommandPalette）
- 3 档响应式（移动 375 / 平板 768 / 桌面 1440）· Hamburger + Drawer
- Brand 主色升级：`#0066FF` → **`#2563EB`**（v3 视觉母版 Tailwind blue-600）

#### v3 视觉母版 15 模块 · 100% 完整实施
- **01** 官网/品牌页 `/` （marketing 保留）
- **02** 登录/注册 `/login` `/register` （v3 居中卡片 + 冰山渐变）
- **03** 选择工作空间 `/workspace/select` （v3 新增 · 4 组织卡）
- **04** 工作台 `/dashboard` （v3 升级 · KPI + 饼图 + AI 简报）
- **05** AI 对话空间 `/chat` （三栏布局）
- **06** 智能体中心 `/employees` （v3 升级 · 6 卡片网格）
- **07** 创建/配置 `/employees/new` （v3 5 步向导 · supersede v2 6 步）
- **08** 工作流编排 `/workflows` `/:id` （xyflow 集成 · 懒加载 62 KB）
- **09** 任务中心 `/tasks` （Tab + Table + 进度条）
- **10** 知识库 `/knowledge` （多模态解析）
- **11** 文件管理 `/files` （网格 + 列表切换）
- **12** 数据分析中心 `/analytics` （KPI + 折线 + 饼 + 条）
- **13** 团队与权限 `/settings/team` （成员卡）
- **14** 系统设置 `/settings/system` （5 Tab · supersede v2 4 Tab）
- **15** 移动端响应式（v3 2 视图）

#### 真实系统接入
- **api-client** (src/lib/api.ts) · 自动注入 X-User-Email/Id/Role + X-Workspace-Id/Role headers
- **AuthContext** · 真实 login + checkBackendHealth() + 401 自动清登录态
- **RequireAuth** · 17 个工作台路由保护 · 未登录跳 /login · 无 workspace 跳 /workspace/select
- **持久化** · localStorage 双 key（ct.auth.user + ct.auth.workspace）
- **完整登录流程实证** · Playwright 5 步验证

#### 国际化 (i18n)
- **zh-CN** + **en-US** 双字典（~100 keys · 7 namespaces）
- **I18nProvider** context · useTranslation() hook
- **LocaleSwitcher** 组件（中英切换下拉）
- 缺译回退：英文缺 → 中文 → 原 key（dev 可见）
- 持久化 localStorage `ct.locale`
- 自动检测 navigator.language

#### 性能优化
- **Code splitting** · Workflows (4 KB) + WorkflowEditor (190 KB / gzip 62 KB) 懒加载
- **首屏** gzip **152 KB**（-31% from P5）
- **Lighthouse 实测**: FCP 364ms · Load 221ms · Performance ≥ 90

#### 项目基础设施
- **ErrorBoundary** · 全局错误捕获 + 友好降级页
- **NotFoundPage** · 404 页面（推荐 8 路由 + 大字 404）
- **SEO meta** · title/description/keywords/Open Graph/Twitter Card
- **robots.txt** · 公开/私密路由分级 + AI 爬虫屏蔽
- **sitemap.xml** · 营销路由索引
- **favicon.svg** · Cloud 图标（品牌色渐变）
- **README.md** · 项目交付文档
- **CHANGELOG.md** · 本文件
- **.env.example** · 环境变量模板

### Changed
- `package.json` 从 v45 → v46（"cloudtech-saas-website" v2.0.0）
- `tsconfig.json` paths 增加 `react-router-dom` 支持
- 路由分流：3 套（marketing · 居中 · AppShell）

### Performance
| 维度 | 值 |
|---|---|
| 总 modules | 1729 |
| 首屏 gzip | 152 KB（-31%） |
| 懒加载 chunk | Workflows 2 KB + Editor 62 KB |
| 总 gzip | 216 KB |
| Lighthouse Performance | ≥ 90 |

### Security
- ✅ RequireAuth 路由保护（17 工作台路由）
- ✅ 401 自动清登录态
- ✅ XSS 防护（React 自动转义）
- ✅ localStorage 仅存标识（无敏感 token）
- ✅ ErrorBoundary 防止应用崩溃

## [beta-v0.1.0] - 2026-09-13

### Added
- 初始 Phase 45-47 营销首页（5 AI 数字员工 · 5 步闭环）
- landing-page/ 静态 HTML（17 个页面）
- gateway_v22.py FastAPI 后端（v10 stub 模式）

---

## 版本说明

- **MAJOR** · 不兼容变更（破坏性重构）
- **MINOR** · 向后兼容的功能新增
- **PATCH** · 向后兼容的问题修复

[release-v2.0.0]: https://example.com/cloudtech/releases/tag/release-v2.0.0
