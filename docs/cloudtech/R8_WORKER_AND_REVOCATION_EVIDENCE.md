# CloudTech V4 R8 — 独立 Worker 实施证据与验收接续

**唯一仓库**：`macxiaxia-boop/cloudtech-spa-v2`  
**施工分支**：`fix/cloudtech-v4-p0-security-20261014`  
**PR**：https://github.com/macxiaxia-boop/cloudtech-spa-v2/pull/2 （DRAFT / NO MERGE）  
**最近实际 V4 CI 证据**：https://github.com/macxiaxia-boop/cloudtech-spa-v2/actions/runs/38509886194  
**本阶段已核实**：299 PASS、3 FAIL、3 SKIP。3 FAIL 是 GitHub Linux runner 缺少 Windows 私有技能目录，仍未得到实际内容；切勿以测试数量冒充功能数量。

## 实际交付，不只是架构

| 工程模块 | 实际新增/升级源码 | 已验证的原子行为 |
|---|---|---|
| SQLite 事务队列 | `workflows/v4/sqlite_run_store.py` | `v4_local_jobs` UNIQUE(run_id)、原有节点费用回执唯一约束、事务校验租约后写入真实输出 |
| Worker 领取和恢复 | `workflows/v4/local_job_queue.py` | BEGIN IMMEDIATE 互斥领取、租约过期重新领取、attempts 有界、重试指数延迟、永久失败入库 |
| 防“旧 Worker 覆盖新结果” | `SQLiteRunStore.mutate(...,lease_token=)` | 提交时验证令牌和有效期，输出与队列 DONE 在同一事务完成 |
| 真正独立的进程 | `workflows/v4/local_worker.py` | 子 Python 进程打开同一个 DB → 解析用户提供的 HTML → 完成节点 → 重启可见；不依赖 HTTP 请求持续运行 |
| 真实运行状态 | `v4_local_worker_heartbeats` | 仅 --loop 进程定时写心跳；失联后在 API 中变为离线 |
| 后端 API | `api/v4/__init__.py` | 租户隔离的 `enqueue-local` 与 `local-queue`，明确仅入队不代表已经完成 |
| UI 接入 | `web/vite-spa/src/lib/workpath-client.ts` + `src/pages/Workflows.tsx` | 真实入队 → 轮询 → 读取 DB 结果，Worker 不在线时保留待办而非假成功 |
| 企业权限实时撤销 | `api/v4/auth.py`、`data-layer/v_saas_v8.py` | 验签后读 SaaS 用户-企业关系；企业禁用、用户被移除、数据库丢失时拒绝请求 |
| Windows 可运行入口 | `scripts/start_cloudtech_v4_worker.ps1` | 启动前检查开发环境、仓库源码、数据库路径和 Python；不会自动部署生产/付费调用 |
| 回归证据 | `tests/test_v4_local_worker_queue.py`、`tests/test_v4_p0_membership.py` | 子进程、互斥抢占、陈旧令牌、崩溃重领、僵尸任务、心跳过期、越权入队、JWT 撤销 |

## Windows Codex 明确的执行动作

前提：使用**现有** CloudTech Windows 工作区的代码，先审核本地真实源码与 PR 差异。不执行 git reset --hard；不要同步私有 SKILL.md 到公开仓库。

```powershell
# 只在已审查的开发/隔离测试目录内运行，不影响真实客户/生产数据。
$env:CLOUDTECH_ENV = 'development'
$env:CLOUDTECH_V4_SQLITE_RUN_STORE = 'D:\CloudTech-Portable\data\v4_staging_runs.sqlite3'
# 先查看现有 Gateway 的环境与 DB 配置是否和 worker 完全一致。

# 终端 A：启动现有 FastAPI 网关（按 CloudTech 的实际启动方式）
python -m uvicorn gateway_v22:app --host 127.0.0.1 --port 5099

# 终端 B：显式启动真正的常驻本地 Worker；Ctrl+C 可退出
.\scripts\start_cloudtech_v4_worker.ps1 -Mode Loop -DbPath $env:CLOUDTECH_V4_SQLITE_RUN_STORE
```

完成身份登录后，调用：
1. `POST /v4/workpaths/runs`：path_id 为 `WP-LOCAL-ARTICLE-EXTRACT`，输入 `{"html":"<article><p>真实内容</p></article>"}`，使用可核验 JWT、tenant_id。
2. `POST /v4/workpaths/runs/{id}/enqueue-local`：只入队，返回 `queued_only=true`。
3. `GET /v4/workpaths/runs/{id}/local-queue`：真实 `QUEUED → LEASED → DONE`，离线要真实显示离线。
4. `GET /v4/workpaths/runs/{id}`：真实持久化节点输出、内容哈希和零费用凭证。
5. 重启 Worker 与网关后重新读取运行记录；重复用户请求不应产生新收费任务。
6. 另起两个 Worker 进程同时轮询同一个单机 DB，验证同一任务只由一个持有有效租约。
7. 用开发环境关闭一个 Worker、模拟租约过期，验证下一个 Worker 接手；过期进程不能再覆盖结果。

**不可省略**：`CLOUDTECH_SAAS_DB_PATH` 必须指向实际已存在的 SaaS 用户与租户 SQLite 数据库，JWT 密钥必须来自安全的环境配置。不能把 `CLOUDTECH_ALLOW_INSECURE_DEV_AUTH=1` 作为生产验收。不要在公开日志里打印 token 或客户 HTML。

## 约束及未闭环项

本 Worker 只执行**一个经过验证的本地确定性原子操作**：用户 HTML 的实际解析。它不代表 6 条旗舰工作流、263 公开研究入口、40 个候选原子能力全部已实现。无需猜想地标明：

- **依然缺少**生产多实例 PostgreSQL 事务、队列可靠投递、授权供应商真实媒体回执和付费计费对账。
- **真实 Windows 技能资产**：`D:\CloudTech-Portable\data\skill_orchestrator` 在 GitHub Linux 上不可访问。仅在有本地访问时运行 `scripts/cloudtech_skill_inventory.py`，不得把其原文提交公开仓库来“刷绿”。
- **CI 总体验证**：`verify.yml` 当前存在无测试 Job 的失败运行，原因尚未得到可引用的 Job 日志；不能将它标记为通过。
- **Lighthouse**：已知多个安全/无障碍/资源性能问题，尚未全量验收。
- **用户本机启用**：没有本地执行通道，GitHub 上的进程测试不等于用户 Windows 已运行服务。
- **生产部署**：未授权自动合并、生产发布、付费 Provider 调用、生产数据迁移与账号密钥变更。

## 下一批必须补的原子能力

1. 提供正式 PostgreSQL 后端及含队列租约、事务 outbox 与 provider request key 的独立可验证实现，运行多实例争抢/崩溃测试。
2. 为原 CloudTech 的其他**本地无外部副作用**节点复用 WorkPath Runner 的执行入口，逐个加入真实操作声明、输入绑定、产物与质量门槛；严禁直接放行任意 operation 名称。
3. 真实供应商适配在明确授权后接入，并进行付款前后的账单/结果核对。
4. 将 Windows 原始技能资产经过私有清点，按技能 maturity `INDEXED → LOADABLE → EXECUTABLE → INTEGRATED → VALIDATED` 推进。
5. 继续修复前端真正的账号验证、CSP、Lighthouse 和生产安全端到端门禁。

每次完成必须附 commit + 真实 CI + 功能输入/输出/失败/成本证据，禁止为了展示进度新增无意义文件。
