# CloudTech V4 — Developer Guide (2026-10-13 · R1536 续)

> 接手 V4 workpath / adapter / provider 工作的开发者必读
> **本仓 mock-only**, 真实 provider HTTP / OAuth / Postgres migration 必须经 L4 user 拍板

---

## 1. 架构分层

```
┌──────────────────────────────────────────────┐
│  vite-spa (React 18.3 + TS 5.6)              │  ← 前端 (v45 build)
│  + src/lib/workpath-client.ts (新)            │     调用 /v4/* 端点
└──────────────┬───────────────────────────────┘
               ↓ HTTP
┌──────────────────────────────────────────────┐
│  api/v4/__init__.py (FastAPI router)          │  ← 11 endpoint
│  + 注入到现有 FastAPI app (main entry)         │
└──────────────┬───────────────────────────────┘
               ↓
┌──────────────────────────────────────────────┐
│  workflows/v4/                                │  ← 横向基础设施 (本 R 新增)
│  ├ orchestrator (状态机)                      │
│  ├ media_gate (7 类白名单 + 14 类黑名单)       │
│  ├ idempotency (防双扣费)                     │
│  ├ budget (reserve/settle/release)            │
│  ├ asset_resolver (alias → version)           │
│  ├ contract (typed workpath 校验)             │
│  ├ registry (200 SKILL.md → 193 ops)          │
│  └ paths (6 旗舰 workpath 定义)               │
└──────────────┬───────────────────────────────┘
               ↓
┌──────────────────────────────────────────────┐
│  adapters/ (mock-only, 5 模块)                │  ← 业务 adapter
│  ├ platform/ (6 平台采集)                     │
│  ├ transcribe/ (4 ASR provider)               │
│  ├ article/ (URL 解析 + 严格 license)         │
│  ├ content/ (二创 + difflib QC)               │
│  └ media/ (4 provider + 真实 HTTP client 接口) │
└──────────────┬───────────────────────────────┘
               ↓ (待真实 HTTP)
┌──────────────────────────────────────────────┐
│  Provider (mock 当前, 真实待 L4 拍)            │
│  ├ DoubaoSeedream (ark.cn-beijing.volces.com) │  ← 已存 DOUBAO_API_KEY
│  ├ Jimeng (待定 endpoint)                     │
│  ├ Yihook (workbuddy connector 已 live)       │
│  └ Kling (待定 endpoint)                      │
└──────────────────────────────────────────────┘
```

---

## 2. 关键不变量

### 2.1 媒体门禁 (红线 #60 + V4 spec §09)
```python
from workflows.v4.media_gate import MediaGate

# 任何 METERED_MEDIA cost_class 操作必须命中 7 类白名单之一
ALLOWED = {"image.generate", "image.edit", "image.inpaint", "image.reference_fusion",
           "video.generate", "video.extend", "video.image_to_video"}

# 任何 黑名单 op 全局拒绝 (chat/qa/plan/analyze/transcribe/research/code/extract/...)
DENIED = {"chat", "qa", "plan", "analyze", "transcribe", "research", "code", "extract",
          "download", "scrape", "route", "publish", "generic_completion", "embedding"}
```

### 2.2 幂等键 (红线 #60 防双扣费)
```python
key = IdempotencyStore.compute_key(
    tenant_id="t1", project_id="p1",
    path_id="WP-VIDEO-TRANSCRIBE", node_id="asr",
    payload={"video_url": "..."}  # sha256 序列化
)
# 同 payload → 同 key → 同 run_id → provider 不重调
```

### 2.3 预算门禁 (V4 spec §09)
```python
# reserve → settle/release (失败 release, 成功 settle)
res = BudgetGate.reserve(tenant_id, run_id, node_id, CostClass.METERED_MEDIA, cents=100, cap_cents=1000)
try:
    actual = provider_dispatch(req)
    BudgetGate.settle(res.reservation_id, actual)
except ProviderError:
    BudgetGate.release(res.reservation_id)  # 失败不扣费
```

### 2.4 资产别名 (V4 spec §D 图 6 沙发替换)
```python
# 上传时: alias → asset_version
AssetResolver.bind(tenant_id, project_id, conversation_id, "图6", "sofa", "asset_sofa", "v1", "msg_1")

# 多轮续办时解析
binding = AssetResolver.resolve(tenant_id, conversation_id, "图6")  # 当前版本
hist = AssetResolver.resolve(tenant_id, conversation_id, "图6", at_message_id="msg_1")  # 历史确定

# 沙发替换: parent_version_id 必须匹配当前版本
AssetResolver.new_version(tenant_id, project_id, conversation_id, "图6",
                         "asset_sofa_new", "v2", parent_version_id="v1")
```

---

## 3. 新增 workpath 步骤

如要新增路径, 不要改 `workflows/v4/paths.py` 改 typed contract, 而是:

1. 在 `workflows/v4/paths.py` 末尾加新 `WorkPathDefinition(...)`, 6 字段必填 (id/revision/title/domain/goal/steps)
2. 每个 step 必须 `cost_class` 合法 (FREE_LOCAL / METERED_NONMEDIA / METERED_MEDIA / EXTERNAL_WRITE)
3. METERED_MEDIA 必须命中 7 类白名单
4. 加 `test_v4_paths.py` 测试验证
5. 在 `api/v4/__init__.py` 无需改, `get_path()` 自动发现

---

## 4. 新增 adapter 步骤

如要新增 adapter (e.g. `adapters/video_edit/`)：

1. 新建 `adapters/video_edit/__init__.py` 暴露 public API
2. 实现 typed contract dataclass + mock 函数 (严禁真实 HTTP)
3. 写 `tests/test_adapters_video_edit.py` (≥6 tests)
4. 写 `adapters/video_edit/EVIDENCE.md` 诚实报告 mock + 真实调用 = 0
5. 接入 `workflows/v4/paths.py` 引用 (如有需要)

---

## 5. 真实 HTTP client 接通

如要写真实 provider HTTP client (L4 拍后)：

1. 在 `adapters/media/real_http_clients.py` 中扩展 `JimengHttpClient/YihookHttpClient/KlingHttpClient/DoubaoSeedreamHttpClient`
2. 实现 `_call(req: MediaRequest, auth_token: str) -> MediaResponse`
3. **必经三件**: MediaGate.check (服务端强制) + IdempotencyStore.check + BudgetGate.reserve/settle
4. **必须带**: retry + timeout + provider_req_id + cost_cents 真实计算
5. 写 `test_real_http_<provider>.py` 用真实 provider 但用 mock fixture
6. 写 `EVIDENCE.md` 记录真实调用实证

---

## 6. CI / Pre-commit

- `.github/workflows/v4-tests.yml`: PR 自动跑 12 测试文件
- `.git-hooks/pre-commit-v4-tests.py`: 本地 commit 前拦截 (symlink 到 .git/hooks/pre-commit)

---

## 7. 真实数据库迁移

```bash
# 1. Dry-run 审计 (推荐先跑)
python scripts/run_v4_migration.py

# 2. 真实执行 (L4 拍板后, 必须 DATABASE_URL)
python scripts/run_v4_migration.py --execute --db-url postgresql://user:pass@host/db
```

⚠️ **红线 #22 L5**: 真实 DB 写入是不可逆的, 必须 L4 user 拍板。

---

## 8. 7 维基线标准

每个新 workpath / adapter / endpoint 必须按 V4 spec §13 报告:
- Identified / Mapped / Implemented / Tested / Integrated / Validated / Production Ready
- 严禁在 0 测试时标 Implemented
- 严禁在 mock-only 时标 Production Ready (红线 #60)

---

## 9. 常用文件位置

| 需求 | 文件 |
|---|---|
| 看 6 旗舰路径定义 | `workflows/v4/paths.py` |
| 看媒体门禁白名单 | `workflows/v4/media_gate.py` |
| 看 200 skill 注册表 | `workflows/v4/registry.py` |
| 看 API 端点契约 | `api/v4/__init__.py` |
| 看 mock provider | `adapters/media/provider_registry.py` |
| 看真实 HTTP 接口契约 | `adapters/media/real_http_clients.py` |
| 看迁移 SQL | `pg_v4_migration.sql` |
| 跑所有测试 | `scripts/run_all_v4_tests.py` 或 `pytest tests/test_v4_*.py tests/test_adapters_*.py -v` |
| 看 L4 待拍清单 | `C:\Users\xinzh\work_zone\ct_v4_audit\L4_DECISION_CHECKLIST.md` |
| 看 R1536 实施证据 | `workflows/v4/P1A_EVIDENCE.md` + `C:\Users\xinzh\work_zone\ct_v4_audit\V4_COMPLETE.md` |
