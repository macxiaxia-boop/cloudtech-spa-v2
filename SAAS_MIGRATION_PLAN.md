# 灵策智算 SaaS 化路径图 · R291 · 2026-09-26

> **用户拍板:cloudtech 升级为灵策智算 SaaS · L1 自治全谱**

## 🎯 定位重塑

```
旧: cloudtech = 个人独立项目 (D:\CloudTech-Portable)
新: cloudtech = 灵策智算 SaaS 后端 (D:\CloudTech-Portable)
    ├─ 对外品牌: 灵策智算 / LynxceAI / 云数时代的变革
    ├─ 公众号: lynxce-ai
    ├─ 站名: 心之所向丶便是光
    ├─ 服务: 4 行业 SaaS (装修/教育/制造/服务)
    ├─ SKU: 12 (basic/pro/enterprise × 4 行业 = ¥199/1999/2999 月)
    └─ 客户: B2B (装修公司/教培机构/制造厂/服务门店)
```

## 📊 现状盘点 (R290 末)

| 能力 | 状态 | SaaS 化差距 |
|---|---|---|
| 50 端点 + WebSocket | ✅ | 0 |
| JWT 24h 认证 | ✅ | 0 |
| Stripe mock checkout + webhook | ✅ | 需真 API key (L5) |
| 12 SKU 定价 | ✅ | 0 |
| 多租户隔离 (x-tenant-id) | ✅ | 0 |
| 实时事件 | ✅ | 0 |
| 审计 + trace | ✅ | 0 |
| 限流 | ✅ | 0 |
| **找回密码** | ❌ | 缺 |
| **升降级 + 取消** | ❌ | 缺 |
| **邮件通知** | ❌ | 缺 (需 SMTP) |
| **SaaS landing page** | ❌ | 缺 |
| **推荐系统** | ❌ | 缺 |
| **用量超额阻断 (402)** | ❌ | 缺 |
| **客户支持工单** | ❌ | 缺 |
| **数据分析 + 漏斗** | ❌ | 缺 |
| **域名 + SSL** | ❌ | L5 用户 |
| **Stripe 真账号** | ❌ | L5 用户 |

## 🛣 三阶段推进路径

### Phase 1 · R291 (本轮 · L1 自治)
- [x] SaaS landing page (公开营销页 · 4 行业 · 12 SKU)
- [x] 找回密码 (forgot + reset + email queue)
- [x] 升降级 + 取消 (subscription upgrade/downgrade/cancel)
- [x] 推荐系统 (referral code + 积分 + leaderboard)
- [x] 用量超额阻断 (402 + hard block)
- [x] 邮件通知 (smtp queue + 6 模板)
- [x] 数据分析 (funnel + retention)
- [x] 客户支持工单 (ticket CRUD)

### Phase 2 · R292 (待用户拍板)
- [ ] 域名 + 服务器部署 (L5 用户)
- [ ] Stripe 真账号 + webhook (L5 用户)
- [ ] 法务页面 (隐私政策 + 服务条款 + SLA)
- [ ] 营销工具 (邮件 marketing + 短信 + push)
- [ ] A/B 测试框架
- [ ] 增长引擎 (推荐奖励 + 邀请赛)

### Phase 3 · R293+ (商业化)
- [ ] 企业版 (SSO + 自定义域名 + 专属客户经理)
- [ ] API marketplace (对外开放 API)
- [ ] 生态合作 (伙伴系统 + 分销)
- [ ] 国际化 (i18n + 多币种)

## 🔴 L1 vs L5 边界

### L1 自治 (本轮全部做)
代码 + 配置 + 测试 + 文档 + 邮件模板 + landing page

### L5 边界 (用户必须操作)
1. 域名注册 (lynxce.ai 或 cloudtech.live)
2. SSL 证书 (Let's Encrypt 或 Cloudflare)
3. Stripe 真账号 + API key (Webhook signing secret)
4. SMTP 真账号 (SendGrid/Mailgun/QQ企业邮)
5. 微信公众号认证 (公众号: lynxce-ai)
6. 服务器 (Vercel + Render + 阿里云)

## 🏛 架构关系 (确认版)

```
用户(创始人)
    │
    ├─ 灵策智算 SaaS (= cloudtech 升级)
    │    D:\CloudTech-Portable
    │    V22 backend + 50+ 端点 + 多租户 + Stripe + JWT
    │    4 行业 × 3 plan × 4 档位
    │
    ├─ AIOS (内部能力底座)
    │    D:\AIOS
    │    §3-§20 (77 组件)
    │    供应: OAuth/SAML/Langfuse/Helicone/Webhook/国密/SDK/RBAC/灾备
    │
    └─ cloudtech (个人项目)
         = 灵策智算 SaaS 后端 (升级后)
         = AIOS 的 bridge 目标 (cloudtech-saas 服务)
```

## 🎁 本轮 (R291) 推进清单

### 新增模块 (8 个 · L1 自治)
1. **v_recovery_v7** — 找回密码 (forgot/reset/email queue)
3 端点
2. **v_subscription_lifecycle_v7** — 升降级/取消
3 端点
4. **v_referral_v7** — 推荐码/积分/leaderboard
4 端点
5. **v_billing_quota_v7** — 用量超额阻断 (402)
3 端点
6. **v_email_queue_v7** — 邮件队列 (smoke)
5 端点
7. **v_analytics_v7** — 数据分析 (funnel/retention/cohort)
4 端点
8. **v_support_ticket_v7** — 客户支持工单
4 端点

### 新增文件 (3 个)
- `landing-page/index.html` — SaaS 营销页 (公开)
- `landing-page/pricing.html` — 价格页
- `landing-page/docs.html` — API 文档

### 累计
- v1-v6: 50 端点
- v7 新增: 28 端点
- **总: 78 端点**

## ✅ 验证

每模块独立 PASS:
- curl 端到端测
- DB 表创建 + 数据写入
- 跨模块联动 (如推荐 → 订阅 → 计费)
- landing page HTML 渲染 (Playwright)

## 🏁 收口

R291 → FINAL_EXECUTION_REPORT_v22_saas.md
Memory → R291-cloudtech-v22-saas-migration.md