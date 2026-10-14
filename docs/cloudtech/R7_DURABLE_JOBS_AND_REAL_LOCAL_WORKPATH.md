# CloudTech × 灵策增量施工 R7｜可执行任务与真实恢复

**仓库**：`macxiaxia-boop/cloudtech-spa-v2`  
**施工分支**：`fix/cloudtech-v4-p0-security-20261014`  
**PR**：[#2](https://github.com/macxiaxia-boop/cloudtech-spa-v2/pull/2)（草稿，不得直接合并）  
**实际进度基线**：2026-10-14，V4 CI **286 PASS / 3 FAIL / 3 SKIP**；最新证据 [Actions 38508438426](https://github.com/macxiaxia-boop/cloudtech-spa-v2/actions/runs/38508438426)。  
**状态**：`PARTIALLY_IMPLEMENTED` / `NOT_PRODUCTION_READY`。测试通过数绝不等于业务能力数。

## 本阶段关闭的原子缺口

| 原子缺口 | 真实实现位置 | 测试证据 | 已明确的局限 |
|---|---|---|---|
| Task 重启后丢失 | `workflows/v4/sqlite_run_store.py` + 现有 `orchestrator.py` | DB 重连状态恢复 | 仅单机本地 SQLite；生产多机仍需事务 DB |
| 并发相同请求重复创建 | SQLite `UNIQUE(idempotency_key)` + payload fingerprint；V4 API 并发收敛 | 同时 24 个 HTTP 创建请求 → 唯一 READY Run | 尚无全链路分布式队列与 Provider 去重 |
| 节点重复回执多次费用 | `v4_node_receipts` 单节点主键和供应商回执唯一索引 | 重复完成只计一次；冲突回执回滚 | 仅回执记录，不等于外部账单已真实对账 |
| 失败数据库提交仍报成功 | `V4Orchestrator._edit` 原子事务分支；异常明确上抛 | 失败回滚与状态一致性 | DB 备份、容灾和生产限流未验收 |
| 已有提取功能不能形成任务闭环 | `WP-LOCAL-ARTICLE-EXTRACT` + `/v4/workpaths/runs/{id}/execute-local` | 创建→真实 HTML 解析→节点落库→重启读取→输出导出 | 仅确定性单节点；无外部网页抓取或模型创作 |
| 状态提交前崩溃 | `/v4/workpaths/runs/{id}/reconcile-local` | 完成回执/hash 验证后收口，0 额外费用 | 缺少已完成回执时不擅自重跑 |
| 前端不能调用有任务记录的真实执行 | `web/vite-spa/src/pages/Workflows.tsx` + `workpath-client.ts` | SPA Build + Bundle Size PASS | 尚需浏览器真人 E2E 与账号隔离审计 |

**为什么单独增加第七条路径？** 原有六条旗舰仍完整保留，包含模型/外部平台/媒体节点，实际并未全部接通。第七条路径只使用 CloudTech 已有真实 HTML 解析能力，将可验证的小闭环先落在现有任务引擎；不得以此冒充六条旗舰全部可运行。

## Codex Windows 精确施工环境（严禁私有内容公开）

1. 在现有主仓同步 **PR #2 的代码**，与本地版本做 diff 和冲突审查，保留本地较新的真实实现。不得强制重置本地历史、创建第二个主仓或覆盖私有数据库。
2. 准备单独的开发/隔离测试目录。只在开发环境设置：
   ```powershell
   $env:CLOUDTECH_ENV = "development"
   $env:CLOUDTECH_V4_SQLITE_RUN_STORE = "D:\\CloudTech-Portable\\data\\v4_staging_runs.sqlite3"
   ```
   该文件父目录必须事先存在。不要将此路径指向正在运行的生产数据文件。
3. 在重启现有网关后，检查 `GET /v4/health` 的 `run_storage` 是否实际显示 `SQLITE_LOCAL_DURABLE`，并核验已配置的 SaaS 身份。严禁仅靠自己填写的 tenant_id 当成真实登录。
4. 用具备授权的测试 HTML 走页面或 API：`POST /v4/workpaths/runs`（`WP-LOCAL-ARTICLE-EXTRACT`）→ `POST /v4/workpaths/runs/{id}/execute-local` → `GET /v4/workpaths/runs/{id}`。在不发生外部调用情况下核对内容哈希、零费用和提交回执。
5. 单机重启网关，重新读取 Run，并测试同幂等键再次提交仍返回相同 Run ID；跨租户返回 404；含未完成回执的运行不得自动恢复。
6. 跨进程 SQLite 和单机状态正确 ≠ 生产可靠的多副本 Worker。进入生产前必须引入具备 **unique key、CAS/锁、fencing、outbox、ledger** 的正式数据库方案以及消费者执行租约，完成崩溃与重复回执测试。
7. 其余三个失败来自 `D:\\CloudTech-Portable\\data\\skill_orchestrator` 在 GitHub Linux runner 不可访问。通过 `scripts/cloudtech_skill_inventory.py` 做本地真实清点；保留私有技能原文，不在公开 GitHub 建占位文件。详见 `SKILL_ASSET_HANDOFF.md`。
8. 暂未授权真实 Provider 扣费、真实邮件投递、生产 DB 迁移、公开发布或自动合并，保持禁止。每个新里程碑必须有原子能力调用轨迹和 CI 证据。

## 保持不变的高优先级缺口

- **P0 真实基础设施**：跨进程/跨机器 DB、队列 Worker、租约/心跳/fencing、跨节点效果/费用流水、幂等恢复、审计事件。
- **P0 客户身份**：JWT 实签验收、服务端租户成员校验/吊销、邮箱验证、负载下的授权和速率限制。
- **P0 原始资产**：本地私有 skill 文件及 Windows CloudTech 原源码同步；无实际来源不得标记 Implemented。
- **P0 提供商/素材**：有授权的真实图像、视频、ASR、OCR、TTS 调用、异步回执、素材版本追踪和 cost reconciliation。
- **P1 业务链**：博主主页→真实作品→原文→分析→二创→图/视频生产→人工审核→导出，重点实做用户原有多单点功能串联。
- **P1 前端质量**：Lighthouse 仍有 CSP、a11y、页面资源等问题，不通过不宣称整体验收。
- **研究覆盖**：研究包 15 个模块、263 个公开可见条目、40 个候选可复用引擎是需求与架构工作账本，不能转化为已实现数量。

## 验收合同（执行层红线）

一个动作只有满足：用户授权、输入真实、租户验证、实际执行、来源记录、结果落库、错误恢复、费用证据、测试并可由用户读取，才可标记为集成完成。孤立函数单测通过只算 Tested；任务 CRUD 通过只算部分 Implemented；仍在内存/未调用 Provider 的旗舰不可冒充 Production Ready。
