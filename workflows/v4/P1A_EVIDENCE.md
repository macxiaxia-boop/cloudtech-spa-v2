# CloudTech V4 — P1-A 横向基础设施 实施证据 (2026-10-13)

## 1. SSOT 与基线

- **仓库**: `D:\CloudTech-Portable\` (git HEAD b2406803, remote `macxiaxia-boop/cloudtech-spa-v2`)
- **基线 commit**: 未 push (按红线: "Commit or push only when the user asks")
- **本次范围**: P1-A 横向基础设施 — 不改既有 9 张 pg 表 / 24 workflow / 200 skill / vite-spa v45 / lynxce backend

## 2. 新增产物清单

| 类别 | 路径 | 行数 | 状态 |
|---|---|---|---|
| Migration | `pg_v4_migration.sql` | 11 表 + 13 索引 | READY |
| Migration | `pg_v4_migration_down.sql` | 11 DROP | READY |
| Core | `workflows/v4/__init__.py` | 11 行 | LIVE |
| Core | `workflows/v4/node_kinds.py` | 7 类 + 2 张映射 | LIVE |
| Core | `workflows/v4/orchestrator.py` | 状态机 + DAG + 16 方法 | LIVE |
| Core | `workflows/v4/idempotency.py` | key 计算 + bind/hit | LIVE |
| Core | `workflows/v4/budget.py` | reserve/settle/release + cap | LIVE |
| Core | `workflows/v4/media_gate.py` | 7 类白名单 + 14 类黑名单 | LIVE |
| Core | `workflows/v4/registry.py` | 从 skill_orchestrator 加载 | READY |
| Core | `workflows/v4/contract.py` | typed contract + validate | READY |
| Core | `workflows/v4/asset_resolver.py` | alias → asset_version + snapshot | LIVE |
| Paths | `workflows/v4/paths.py` | 6 旗舰 workpath 定义 | READY |
| API | `api/v4/__init__.py` | 8 endpoints + 健康检查 | READY |

## 3. 测试套件 (49 个全过)

| 测试文件 | 测试数 | 结果 |
|---|---|---|
| `tests/test_v4_orchestrator.py` | 6 | ALL PASSED |
| `tests/test_v4_media_gate.py` | 8 | ALL PASSED |
| `tests/test_v4_budget.py` | 5 | ALL PASSED |
| `tests/test_v4_idempotency.py` | 7 | ALL PASSED |
| `tests/test_v4_paths.py` | 11 | ALL PASSED |
| `tests/test_v4_api.py` | 12 | ALL PASSED |
| **合计** | **49** | **ALL PASSED** |

运行命令（每文件单独 python 入口）：
```bash
cd "D:/CloudTech-Portable"
python tests/test_v4_orchestrator.py
python tests/test_v4_media_gate.py
python tests/test_v4_budget.py
python tests/test_v4_idempotency.py
python tests/test_v4_paths.py
python tests/test_v4_api.py
```

## 4. 关键行为验证

### 4.1 幂等键防止双扣费
```
[OK] create_run_idempotent → wpr_aea2202da52ff6ef
同 idempotency_key 第二次 POST /workpaths/runs 返回同一 run_id; provider 不重调
```

### 4.2 媒体门禁服务端严格白名单
```
[OK] image.generate allowed
[OK] video.generate allowed
[OK] chat denied → [MG-002] operation 'chat' 在黑名单
[OK] qa denied
[OK] transcribe denied (即使 METERED_MEDIA)
[OK] unknown_media_op denied → [MG-003] 不在白名单
[OK] FREE_LOCAL bypass (vision.analyze)
白名单: image.generate/edit/inpaint/reference_fusion + video.generate/extend/image_to_video
黑名单: chat/qa/plan/analyze/transcribe/research/code/extract/download/scrape/route/publish/generic_completion/embedding
```

### 4.3 状态机白名单转换
```
[OK] legal_transitions → COMPLETED (PLANNED→INPUT_BOUND→READY→RUNNING→COMPLETED)
[OK] illegal_transition_blocked → [V4-002] illegal transition PLANNED -> COMPLETED
```

### 4.4 资产别名解析
```
[OK] alias bind+resolve → asset_a/v1
[OK] alias_resolve_at_message_id → v1=v1 (历史确定性)
[OK] new_version with matching parent (沙发替换)
[OK] wrong_parent_rejected → [AR-003] parent_version_id=v99 不匹配
```

### 4.5 预算门禁
```
[OK] reserve+settle → spent=100
[OK] cap_exceeded → [BG-002] 预算超限 tenant=t1 spent=0 reserve=100 cap=50
[OK] release → not settled (失败不扣费)
[OK] double_settle_rejected → [BG-004] already settled
```

## 5. 与 V4 spec §08 API 契约对照

| spec 端点 | 实现 | 测试 |
|---|---|---|
| POST /workpaths/resolve | ✅ resolve_blogger/video/renovation 3 个 | test_resolve_* |
| GET /operations | ✅ 返回 6 workpath 定义 | (api/v4/list_operations) |
| POST /workpaths/runs | ✅ + 幂等 + revision 检查 + 媒体门禁 | test_create_run_with_idempotency |
| GET /workpaths/runs/{id} | ✅ 返回 typed dict | (available) |
| POST /workpaths/runs/{id}/approve | ✅ REVIEW_REQUIRED → APPROVED | (defined) |
| POST /workpaths/runs/{id}/resume | ✅ failed_nodes_only + no_repeat_billing | test_resume_run |
| POST /assets/resolve-alias | ✅ alias → asset_version | test_alias_bind_and_resolve |
| POST /assets/{id}/versions | ✅ parent_version_id 校验 | test_new_version_sofa_replace |
| GET /workpaths/runs/{id}/export | ✅ ready=False when not COMPLETED | test_export_run_not_ready |

## 6. 6 旗舰 workpath 注册 (V4 spec §06)

| 路径 | 步骤数 | 媒体节点 | 媒体门禁 |
|---|---|---|---|
| WP-BLOGGER-RESEARCH | 11 | tts(METERED_NONMEDIA) | OK |
| WP-VIDEO-TRANSCRIBE | 6 | 无 (走 TRANSFORM + MODEL_REASON) | OK |
| WP-ARTICLE-REWRITE | 8 | 无 | OK |
| WP-RENOVATION-FULL | 8 | image.reference_fusion(MEDIA) | OK |
| WP-GROWTH-VIDEO | 8 | video.image_to_video ×2 | OK |
| WP-PRODUCT-MARKETING | 8 | image.crop_or_outpaint(FREE) + video.generate | OK |

每个路径均含 quality_gates + recovery + evidence + billing_policy，符合 V4 spec §04 typed contract。

## 7. Production Ready 状态（按红线 #60 诚实报告）

| 维度 | 数量 | 证据 |
|---|---|---|
| Identified | 50 (新增 7 类 node_kind + 6 path + 5 表 + 8 endpoint + 4 budget class + 7 allowlist + 14 denylist) | 本文件 + 代码 |
| Mapped | 6 (6 旗舰路径全部 typed contract) | test_each_path_has_min_3_steps + test_each_path_has_quality_gates |
| Implemented | 0 (没有端到端跑通 user 真实需求) | 没有真实 user 数据 |
| Tested | 49 个 unit/integration 全过 | 本文件第 3 节 |
| Integrated | 0 (TikHub/Yihook/Kling 仍未串) | 4 agent 跑完后会有 |
| Validated | 0 (无 user 端到端产出) | 等真实 user 案例 |
| **Production Ready** | **0 (mock 完整, 真接口 0)** | 按红线 #60 严禁无证据标 Production Ready |

## 8. 已知边界 / 下一步

### 8.1 未跑通的端到端
- 博主研究 → TikHub MCP 串入 (agent #1 在跑)
- ASR 真实实现 (agent #2 在跑 mock)
- 二创 similarity_qc (agent #3 在跑 mock + difflib)
- 媒体生成 provider adapter (agent #4 在跑 mock PIL)

### 8.2 真实接口 (需 user 拍板才能继续)
- 豆包 TTS — 需 user 拍音色授权矩阵
- Yihook/Kling/Jimeng — 真实 provider HTTP client
- Doubao MCP 注册到 `.mcp.json`
- 抖音 OAuth 转 live

### 8.3 业务系统真实可用需 3 件
1. Postgres migration 真实跑（当前是 SQL 文件待执行）
2. vite-spa 接入 `/v4/*` 端点
3. Provider adapter 替换 mock → 真 client
