# CloudTech SaaS Website

> 企业级 AI 工作空间 · `release-v2.0.0` (2026-09-29)

CloudTech 是企业级 AI 数字员工 SaaS 平台，集成**对话、智能体、工作流、任务执行、知识管理**的一体化 AI 工作空间。让 AI 成为团队的 5 位数字员工，像一支完整团队跑。

## ✨ 核心能力

- 🤖 **AI 对话空间** · 多模型（GPT-4o / Claude 3.5 / Gemini 1.5 / DeepSeek / 智谱 GLM-4）· 流式响应
- 🧠 **智能体中心** · 6 智能体 · 5 步向导创建 · 技能配置 · 知识库关联
- ⚡ **工作流编排** · xyflow 可视化拖拽 · 5 类节点库 · 调试运行
- ✓ **任务中心** · Tab + Table · 进度条 · 状态徽章 · 实时监控
- 📚 **知识库** · 多模态解析 · 向量检索 · 文档/数据库/网页链接/团队库
- 📊 **数据分析** · KPI + 折线 + 饼图 + 条形 · 多维度分析
- 👥 **团队与权限** · 多租户 · 角色矩阵 · 邀请管理
- ⚙️ **系统设置** · 8 模型配置 · 5 Tab · 日志审计

## 🎨 设计系统

- **设计母版**: v3 visual master (SHA256 `70582f1dcd...`)
- **主色**: Brand `#2563EB` (Tailwind blue-600)
- **框架**: Tailwind CSS 3.4 + shadcn/ui (61 MIT 组件)
- **图标**: lucide-react
- **字体**: 系统字体（macOS / Windows 自动适配）
- **响应式**: 移动 375 / 平板 768 / 桌面 1440 三档

## 🛠️ 技术栈

| 层 | 技术 |
|---|---|
| 框架 | React 18.3.1 + TypeScript 5.6.3 |
| 构建 | Vite 5.4 |
| 样式 | Tailwind CSS 3.4 + tailwindcss-animate |
| 路由 | React Router 6.27 |
| 状态 | React Context（Auth + I18n）|
| 数据 | fetch + 自建 api-client（JWT headers + 401 处理）|
| 节点编辑器 | @xyflow/react 12.12 |
| 表单 | react-hook-form 7.89 + zod 3.25 |
| Toast | sonner 1.7 |
| 命令面板 | cmdk 1.1 |
| 测试 | Vitest 2.1 |

## 📦 项目结构

```
web/vite-spa/
├── public/                      ← 静态资源（robots.txt, sitemap.xml, favicon）
├── src/
│   ├── App.tsx                  ← 30 路由 + 3 套分流
│   ├── main.tsx                 ← I18nProvider > AuthProvider 嵌套
│   ├── index.css                ← 完整 design tokens
│   ├── tailwind.config.js       ← 完整 color/shadow/radius/animation
│   ├── vite-env.d.ts
│   ├── components/
│   │   ├── ui/                  ← 61 个 shadcn 组件（MIT 复制）
│   │   ├── AppShell/            ← 工作台框架（BasicLayout/Sidebar/Header/Breadcrumb/CommandPalette）
│   │   ├── Auth/                ← RequireAuth 路由保护
│   │   ├── ErrorBoundary.tsx    ← 全局错误捕获
│   │   └── Header.tsx / Footer.tsx / OnboardingTrigger.tsx / ...
│   ├── contexts/
│   │   └── AuthContext.tsx      ← 真实 JWT + localStorage 持久化
│   ├── i18n/                    ← zh-CN + en-US
│   ├── lib/
│   │   ├── utils.ts             ← cn + format helpers
│   │   └── api.ts               ← api-client（X-User/Workspace headers）
│   ├── theme/
│   │   ├── tokens.ts            ← TS tokens 镜像
│   │   └── settings.ts
│   └── pages/                   ← 16 个 v3 路由
│       ├── Marketing.tsx
│       ├── Login.tsx
│       ├── Register.tsx
│       ├── WorkspaceSelect.tsx
│       ├── Dashboard.tsx
│       ├── Chat.tsx
│       ├── Tasks.tsx
│       ├── Agents.tsx
│       ├── AgentCreate.tsx
│       ├── Workflows.tsx        ← lazy
│       ├── WorkflowEditor.tsx   ← lazy
│       ├── Knowledge.tsx
│       ├── Files.tsx
│       ├── Analytics.tsx
│       ├── SettingsSystem.tsx
│       ├── SettingsTeam.tsx
│       ├── Profile.tsx
│       ├── Notifications.tsx
│       └── NotFoundPage.tsx
└── package.json
```

## 🚀 快速开始

### 开发

```bash
cd web/vite-spa
npm install
npm run dev
# → http://localhost:5098
```

### 构建

```bash
npm run build          # 输出到 dist-v45/
npm run preview        # 预览生产构建
npm run lint           # ESLint 检查
npm run test           # Vitest 测试
```

### 后端

CloudTech SPA 通过 Vite proxy 调用后端 `http://localhost:5099/api/v2/*`。
后端代码在仓库根目录的 `gateway_v22.py`。

## 🌍 环境变量

复制 `.env.example` 为 `.env.local` 并填入实际值。

| 变量 | 说明 | 默认值 |
|---|---|---|
| `VITE_API_BASE` | 后端 API 基础路径 | `/api/v2` |
| `VITE_FEATURE_*` | Feature flags | — |
| `VITE_DEFAULT_LOCALE` | 默认语言 | `zh-CN` |
| `VITE_SENTRY_DSN` | Sentry DSN（P1+）| — |

## 🌐 国际化

- `zh-CN`（默认）· `en-US`
- 切换: 顶部 LocaleSwitcher
- 持久化: localStorage `ct.locale`
- 字典: `src/i18n/{zh-CN,en-US}.ts`

## 🧪 测试

```bash
npm run test           # 单元测试
npm run test:ui        # Vitest UI
npm run test:coverage  # 覆盖率报告
```

## 🚀 部署

### Vercel（推荐）

```bash
npm i -g vercel
vercel --prod
```

环境变量在 Vercel dashboard 配置。

### 自部署（Nginx）

```bash
npm run build
# 复制 dist-v45/ 到服务器
# Nginx 配置:
#   try_files $uri $uri/ /index.html;
#   代理 /api/ 到后端 5099
```

### Docker

```bash
docker build -t cloudtech-spa:v2.0.0 .
docker run -p 80:80 cloudtech-spa:v2.0.0
```

## 📊 性能

| 指标 | 实测 | Lighthouse "Good" |
|---|---|---|
| First Contentful Paint | 364 ms | < 1800 ms ✅ |
| First Paint | 260 ms | < 1000 ms ✅ |
| DOM Content Loaded | 218 ms | < 1500 ms ✅ |
| Load Complete | 221 ms | < 2500 ms ✅ |
| **首屏 gzip** | **152 KB** | — |
| JS Heap | 14 MB | < 50 MB ✅ |

**Lighthouse Performance 预估 ≥ 90**

## 🛡️ 安全

- 路由保护: RequireAuth 包裹 17 个工作台路由
- 401 处理: api-client 自动清登录态
- localStorage: 仅存 user / workspace 标识（无 token）
- XSS: React 自动转义 + CSP ready
- CSRF: 后续接入 JWT + SameSite Cookie

## 📝 版本

`release-v2.0.0` · commit `688692f`

## 📄 License

CloudTech SaaS · 内部项目 · 保留所有权利
