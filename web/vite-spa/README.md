# CloudTech SaaS Website — Phase 45 D17-23

## 技术栈

- **Vite 5** + **React 18** + **TypeScript 5**
- **Tailwind CSS 3** + **Framer Motion** + **Lucide React**
- **React Router 6** (BrowserRouter)
- **Vitest** + **jsdom** 测试

## 启动

```bash
cd web/vite-spa
npm install
npm run dev     # 5098 端口
npm run build   # 输出 dist-v45/
npm run preview # 预览生产构建
npm test        # 跑测试
```

## Phase 45 关键改动

### D4-7 砍端点/行业/员工
- ✅ FE 3 员工菜单收敛 (`src/components/FEEmployeeMenu.tsx`)
  - `content_writer` 内容创作
  - `customer_service` 智能客服
  - `market_researcher` 市场调研
- ⚠️ BE 5 员工不出现在前台菜单（隐藏在后端调用）

### D17-23 SaaS 官网脚手架
- ✅ Vite + React 18 + TS 5 完整脚手架
- ✅ Tailwind 3 主题（brand-50/100/500/600/700）
- ✅ SaaS 落地页 (Hero + FE 3 员工 + 2 行业管线 + CTA)
- ✅ 定价页 (免费 / 专业版 ¥499 / 企业版 ¥2,499)
- ✅ 代理 `/api/v2/*` → `localhost:5099` (FastAPI gateway)

## 与 web/dist/ 关系

- `web/dist/` = V10.19 历史构建（Aug 26）— 不动
- `web/vite-spa/` = Phase 45 D17-23 新脚手架 — 新路径
- `web/v12.2/cloudtech-spa.html` = 单文件 SPA — 不动

## 路由

| 路径 | 组件 | 说明 |
|---|---|---|
| `/` | `MarketingPage` | SaaS 首页 |
| `/pricing` | `PricingPage` | 3 档定价 |
| `/employees` | `FEEmployeeMenu` | FE 3 员工列表 |
| `/employees/:id` | （待补单员工页）| 内容创作/智能客服/市场调研 |
| `/login` | （待补） | 登录入口 |
| `/contact` | （待补） | 联系销售 |
| `*` | `NotFound` | 404 |

## 后续任务（D24-30）

- [ ] D24-27: 销售漏斗后端（线索 → CRM → 复盘）
- [ ] D28-30: CI/CD + OpenTelemetry 接入
- [ ] 域名备案 + HTTPS（用户拍板）
- [ ] SSE 流式输出（管线下步骤实时）
