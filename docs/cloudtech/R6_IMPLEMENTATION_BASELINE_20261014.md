# CloudTech × 灵策参考能力增量施工基线 R6

**唯一仓库**：`macxiaxia-boop/cloudtech-spa-v2`  
**当前隔离 PR**：[PR #2](https://github.com/macxiaxia-boop/cloudtech-spa-v2/pull/2)  
**分支**：`fix/cloudtech-v4-p0-security-20261014`  
**审计时间**：2026-10-14  
**状态**：`NOT_PRODUCTION_READY`、`PR_DRAFT_NOT_MERGED`、`LOCAL_WINDOWS_NOT_AUDITED`

## 原目标锁定

- 基于现有 CloudTech 源码与业务功能增量施工，不另造一套 Lynxce、不重复建立仓库。
- 已研究的公开 15 个模块、263 个入口条目和建议 40 项原子能力，仅视为**需求映射与计划范围**，不能视为 CloudTech 已实施 263 项业务能力。
- 原 84 项施工队列继续有效；关闭任务必须有真实 commit、功能证据和验收日志。

## 本 PR 已提交的实际代码（需要合并前回归）

| 模块 | 已改内容 | 剩余红线 |
|---|---|---|
| V4 API | 租户归属校验、同租户幂等、资源绑定授权、任务列表 | Worker / DB 原子事务 / RBAC / 审批执行 |
| V4 Task | 节点重复回执不双计费，重复创建同一 nonce 线程安全 | 多进程 DB 幂等及真正失败恢复 |
| V4 Gateway | 现有路由接入单一 gateway | 实际运行部署与浏览器 E2E |
| SaaS 身份 | 禁止硬编码 JWT 密钥，新账户 PBKDF2，旧账户登录升级哈希，数据库校验 `/me` | 邮箱验证、服务端登出吊销、审计限流、线上部署 |
| Web SPA | 使用真实 SaaS token，不再自动授予 mock admin；取消四个假工作空间 | 生产反向代理、Token 安全存储、完整角色授权 |
| V4 Workflows | 页面从实际路由契约及租户运行列表读取，标记内存与 Worker 状态 | 真正执行节点、持久化与成品归档 |
| LLM | MiniMax 自引用假成功禁止；已有 Provider Router 仅在显式授权和实际密钥下运行；V4 LLM 契约 | 真实密钥、模型响应/费用实证 |
| 图像/视频/ASR | 生产禁用虚构图片、假视频、固定字幕；模拟模式仅供隔离测试 | 接实际供应商、可追溯资产版本和账单 |
| 原文和内容 | 用户提供 HTML → 真实提取正文、图片、视频引用；API 和前端入口 | 授权网页下载、版本资产存储、后续创作 |
| 会议 | V4 使用现有 WF-G-018 从真实提供的转写提取决议/行动项 | 音频转写、语义级核验、真实待办落库 |
| 本地 OCR | 可选 Tesseract、允许目录、文件格式/大小/路径检查 | 本地依赖部署、PDF 支持及真实资产传输 |
| 作者检索/指标 | 对用户真实提供的数据本地查询和汇总 | 授权平台连接器、可验证采集凭证 |
| TTS | 未配置真实供应商时明确阻断 | 有凭证的真实供应商及音频成品 |
| 技能 | 本地元数据清单/哈希检查、私有交接说明、可配置技能根路径 | Windows 真实技能内容尚未挂载 GitHub CI |
| CI | SPA 构建恢复，V4 JUnit 从实际数据计算，不使用写死通过数 | 全量 verify、Lighthouse 和跨端 E2E 仍需修复 |

## GitHub 证据（最后已核验的运行）

- 本阶段已核验基线：`262 PASS / 3 FAIL / 3 SKIP`，V4 Tests run `38506637156`。
- 3 FAIL 均是本地 `skill_orchestrator` 资产在 GitHub Linux runner 缺失，**不得虚构补件**。
- 同期 SPA Bundle Size Check PASS；Lighthouse 的其他质量门槛未通过。
- 更晚提交以 GitHub PR 和 Actions 的实际结果为准，不把上次数字冒充最新结果。

## 连贯的工程优先级

**P0-A**：Codex 在 Windows 本地审计 `D:\CloudTech-Portable\data\skill_orchestrator`，执行 `python scripts/cloudtech_skill_inventory.py --minimum 100`；确认来源与实际数据，严禁上传私有内容到公开仓库。

**P0-B**：接入 durable DB WorkPathRun、outbox、计费流水和重复回执唯一键；停止把内存记录等同于持久化。

**P0-C**：在授权的私有环境中验证 SaaS JWT + frontend + Gateway + V4 真实身份闭环；对 /me、跨租户 API、Token 有效期/吊销执行 E2E。

**P0-D**：完成供应商接入合约：任务请求、异步回执、真实资产、费用结算、失败恢复，优先功能链路“用户上传素材 → 明确编辑意图 → 出图/视频 → 版本记录 → 导出”。

**P0-E**：生产环境安全：版权与抓取授权、SSR F、私有素材隔离、邮箱验证、事件审计、基础 WAF/rate-limit、配置管理和灾备。

**P1**：跨功能复用：博主主页 → 作品选取 → 原文转写/图文提取 → 二创分析 → 多平台文案/媒体 → 审批 → 导出；与既有 CloudTech 内容工作流相连。

**P2**：其余功能映射、APP/特效模板和平台管理模块依真实缺口和客户价值实施，不为凑页面或宣传数量生成空实现。

## 不允许的动作
- 不合并尚未通过全部门禁的 PR，不自动部署生产，不执行真实付费 API 调用。
- 不假报邮件已发送、模型已推理、订单已收费或任务已恢复。
- 不创建每次迭代一个新的 GitHub 仓库，不公开用户私有数据。
- 不在 GitHub Linux CI 中将 Windows 不可达目录标记为“已真实通过”。

## 最终验收
每个业务链路须同时拥有：用户输入、鉴权租户、资源 ID、真实 Provider/本地执行器、输出证明、持久化、失败重试、费用账本、前端展现和自动化测试。任何一项未成立，该链路最高 `PARTIALLY_IMPLEMENTED`。
