# AIOS × CloudTech V5 工程治理入口（非新母版）

- 本目录仅是受控施工的 GitHub 导航，**不取代**用户 Library 中的六总账与原始 P0–P13 证据。
- 历史来源：用户 Library `/AIOS_CloudTech_跨窗口真实承接母包_V4_20261014.zip` 与 `/AIOS_CloudTech_P0-P13_完成未完成_功能路径_文件汇总_总交接包_20261014.zip`。
- 唯一可持续总账：Library `/AIOS_CloudTech/AIOS_CloudTech_V5_唯一工程总账_20261014.zip`（版本化更新，不新建主仓）。
- AIOS：`macxiaxia-boop/aios-sovereignty-v` Draft PR #3，HEAD `79adeb099ba058805e1f6fe70fab37f4ee0896c1`（本轮只读核验）。
- CloudTech 并行 Draft PR #1：`fix/cloudtech-pipeline-truth-p5-20261014`，基于 2026-10-14 已增量修复失效静态引用、路由降级与 Lighthouse 无障碍缺陷。
- CloudTech 当前 Draft PR #2：`fix/cloudtech-v4-p0-security-20261014`，租户/持久化/本地三路径主体仍不可与 PR #1 直接覆盖。

## 真实已检查的 12 个同名文件

1. `.github/workflows/lighthouse-ci.yml` — 两版本完全相同；保留。
2. `.github/workflows/verify.yml` — 校验覆盖和触发不同；合并门禁而非择一。
3. `api/v4/__init__.py` — 路由、授权、持久化与本地 prefix 不同；逐 endpoint 对照。
4. `api/v4/asgi.py` — 标题/版本合同差异；跑真实双进程 HTTP。
5. `api/v4/auth.py` — JWT 签名、staging fail-closed 与 SaaS membership 撤销校验；合并更严格保证。
6. `tests/test_v4_api.py` — 无真实 Worker 必须返回 501，不得以 preview 冒充恢复。
7. `tests/test_v4_end_to_end_mock.py` — 同上，兼顾真实 Worker 分支。
8. `tests/test_v4_end_to_end_paths.py` — 保留六条旗舰与三条真实本地确定性路径；Mock 不能算生产。
9. `tests/test_v4_registry_real_load.py` — 显式错误私有 Skill 路径必须 FAIL；CI 缺少本机目录可 SKIP 外部集成。
10. `workflows/v4/capability_preflight.py` — operation 级与 path 级能力状态均保留。
11. `workflows/v4/orchestrator.py` — PR1 快照存储与 PR2 事务 RunStore 是 P0 高危冲突；先迁移、再双进程恢复/幂等测试。
12. `workflows/v4/registry.py` — Mock permission 必须 fail-closed，保留本地 HTML/字幕/文本路径。

## 不可逾越的 CI / 发布边界

- PR1 的前端首次构建失败已通过**实际提交**修复；PR2 最新已观测到 Lighthouse 首页无障碍分数由 0.85 提升至 0.95，但 Lighthouse 整体仍未全绿。
- 不允许降低 Lighthouse 阈值、仅修改断言/Mock 以假装通过。
- 三个 PR 都保持 Draft；不要自动合并或生产部署、不要从云端推断 Windows 本机状态。
- 所有来源 3,920 catalog 对象是候选目录，非已实现数。生产就绪比率 `UNKNOWN`。
- 必须将已实施代码的 SHA、独立 CI、数据库/Provider/Windows 权限阻断回写 **MASTER_EVIDENCE / MASTER_TASKS / MASTER_BLOCKERS / STATE_SNAPSHOT**。

## 当前可推进的真实 READY 工作

- 整理两条 PR 的 Lighthouse 断言逐条修复；PWA / 真实 API 回执不允许伪造。
- 本地/CI 独立跑 PR1、PR2 V4/Verify/Lighthouse；逐路径验证无授权、无服务、无 worker 时的失败语义。
- 创建受控**临时集成试验环境**仅做代码/测试预检，不修改 PR Draft 状态；保护 PR1 持久快照与 PR2 事务存储各自的有效行为。

本文件是持续施工索引，不是已生产可用证明。