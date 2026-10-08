# 42 — V6.2 LIVE DASHBOARD + V6.3 NEXT-BATCH DISPATCH

**Date**: 2026-10-08T22:35:00+08:00
**Sub-agent**: dev #84 (Peano)
**Supersedes**: previous `_LIVE_DASHBOARD.json` (3348B V6.1 expanded → 1587B V6.2 compact)
**Status**: ✅ dashboard written, next-batch queue committed to evidence

---

## 1. Dashboard 文件

| 字段 | 值 |
|------|----|
| 路径 | `D:\CloudTech-Portable\FINAL_HANDOFF\_LIVE_DASHBOARD.json` |
| 大小 | 1587 bytes |
| 编码 | UTF-8 (无 BOM) |
| 格式 | 单行 JSON,机器可读 |
| 内容 | V6.2 compact summary: supervisor / role / host_bridge / cumulative_totals / current_agents_live |
| 更新频率 | 每个 sub-agent 完成 commit 后刷新一次 (Codex supervisor 在 dispatch 循环内调用) |

---

## 2. User 验证步骤

### 2.1 实时 audit 命令 (一键查 V6.2 状态)

```powershell
cd D:\CloudTech-Portable
python -m json.tool FINAL_HANDOFF\_LIVE_DASHBOARD.json
```

期望输出: 格式化 JSON,字段包含 title / updated_at / supervisor / cumulative_session_totals / current_agents_live 等。

### 2.2 完整 audit (dashboard + pytest + git)

```powershell
cd D:\CloudTech-Portable

# 1. 看 dashboard
Get-Content FINAL_HANDOFF\_LIVE_DASHBOARD.json

# 2. 跑全量 pytest (基线 524/0/7)
python -m pytest tests/ workflows/tests/ --tb=no -q

# 3. 看最近 10 个 commit
git log --oneline -10

# 4. 看子-agent evidence 文件清单
Get-ChildItem FINAL_HANDOFF\evidence\*.md | Sort-Object Name
```

### 2.3 Cat 等价 (Windows)

```powershell
type D:\CloudTech-Portable\FINAL_HANDOFF\_LIVE_DASHBOARD.json
```

### 2.4 Python 程序化访问 (供下游脚本/agent)

```python
import json
from pathlib import Path
dash = json.loads(Path(r"D:\CloudTech-Portable\FINAL_HANDOFF\_LIVE_DASHBOARD.json").read_text(encoding="utf-8"))
print(f"Sub-agents dispatched: {dash['cumulative_session_totals']['sub_agents_dispatched']}")
print(f"PASS count: {dash['cumulative_session_totals']['actual_pass_count']}")
print(f"Active agents: {[a['id'] for a in dash['current_agents_live'] if a['status'] == 'active']}")
```

---

## 3. V6.3 NEXT-BATCH — 5 Tasks Dispatch Queue

> **Status**: Specs written, ready for Codex supervisor dispatch via `multi_agent_v1__spawn_agent`.
> **Per-task pattern**: single dev sub-agent, ~30 min wall-clock, evidence file per AIOS convention.

### Task T01 — Integration Test Suite (积分测试)

**Goal**: 在 `tests/` 下加 1 个跨模块 integration test 文件,验证 wf + billing + crm + content 的协同。
**File**: `D:\CloudTech-Portable\tests\test_integration_v63.py` (NEW)
**Scope (≥8 case)**:
- Lead 创建 → content 生成 → billing 配额扣减 → wf 执行 → email 发送 (5 模块串联)
- 失败回滚: 任意一步 raise,前序状态保留 (无脏数据)
- 多 tenant 隔离: tenant A 的 lead 不可被 tenant B 查询
- 并发幂等: 100 个相同 idempotency_key 并发提交,只 1 笔入账
- API → Service → DB 三层串联 (FastAPI test_client + 真实 SQLite)
- Email mock 验证 4 模板 (welcome / follow-up / proposal / win)
- Content fingerprint SHA-256 重复检测
- Workflow state machine: pending → running → completed (success_rate=1.0)
**Verification**: `pytest tests/test_integration_v63.py -q` → ≥8 PASS, 0 FAIL
**Forbidden**: 真实 Provider API / SMTP / Pilot / PG / `_r*.py` / `admin_dashboard.py` 红线 / 跨工程 `D:\AIOS\`

### Task T02 — Provider Adapter Layer (DONE by Peirce #83)

**Status**: ✅ **DONE — 36/36 PASS** (28 旧 + 8 新)
**Evidence**: `D:\CloudTech-Portable\FINAL_HANDOFF\evidence\41_PROVIDER_ADAPTER.md`
**Summary**: `BillingProvider` ABC + `MockProvider` (保留) + `StripeProvider` (stub) + `OpenAIProvider` (stub);真调位用 `__REAL_PROVIDER_CALL_NEEDED__` 标记;无 key / 无网络 / 无 side effect。
**Action**: Codex supervisor 在 commit 时连同本 evidence 一起 stage。

### Task T03 — Multi-tenant Stress (1000+ tenants)

**Goal**: 验证引擎在 1000+ tenant / 每 tenant 100+ 记录下的性能不退化。
**File**: `D:\CloudTech-Portable\tests\test_stress_multitenant.py` (NEW)
**Scope (≥5 case)**:
- 1000 tenant 创建 < 5s (batch insert)
- 1000 tenant 并发查询 < 10s (线程池)
- 每 tenant 100 条 ledger entry,余额总和校验 (I-2 不变量)
- 1000 tenant 配额扣减全跑完无死锁
- 内存峰值 < 500MB (用 `tracemalloc` 测)
**Verification**: `pytest tests/test_stress_multitenant.py -q -s` → ≥5 PASS, 0 FAIL;打印每个 case 耗时
**Forbidden**: 同上
**Sub-agent candidate**: Linnaeus (active) — 已经是 stress 方向

### Task T04 — Pilot Realistic Data Generation (PILOT CRM 数据生成器)

**Goal**: 生成 1 套"看起来像真业务"的 pilot 数据,供 USER 后续接入真 CRM 时导入。
**File**: `D:\CloudTech-Portable\workflows\impl\_pilot_data_gen.py` (NEW) + `D:\CloudTech-Portable\tests\test_pilot_data_gen.py` (NEW)
**Scope (≥6 case)**:
- 生成 50 个 tenant: 名字 / 行业 / 套餐 (starter / pro / enterprise) / 创建时间 (近 6 月分布)
- 每 tenant 30 个 lead: 姓名 / 公司 / 邮箱 / 状态 (new / qualified / won / lost) 分布符合 30/40/20/10
- 每 tenant 100 条 billing ledger: 含 reservation / settlement / refund / correction
- Email template 渲染: 4 模板 × 50 tenant = 200 邮件草稿 (JSONL)
- 导出到 `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\` (CSV + JSONL)
- 一键导入脚本 `import_pilot_data.py` (idempotent)
**Verification**:
```
python workflows/impl/_pilot_data_gen.py
pytest tests/test_pilot_data_gen.py -q  # → ≥6 PASS
```
**Forbidden**: 真实 Pilot CRM 接入 (只生成数据文件,不调 API)
**Blocked-on**: User 拿到真 CRM credentials 后,可直接用生成的 CSV/JSONL 导入

### Task T05 — CI Pipeline (本地模拟 GitHub Actions)

**Goal**: 在仓库根加 `.github/workflows/ci.yml` + 本地 `run_ci.ps1`,模拟 CI 4 阶段。
**Files** (NEW):
- `D:\CloudTech-Portable\.github\workflows\ci.yml` (GitHub Actions 格式,4 job: lint / type / test / build)
- `D:\CloudTech-Portable\run_ci.ps1` (本地等价)
**Scope**:
- Job 1 `lint`: `ruff check .` (若未装 ruff, fallback `python -m compileall -q .`)
- Job 2 `type`: `mypy billing_real.py tests/ --ignore-missing-imports` (若未装 mypy, fallback `python -c "import billing_real"`)
- Job 3 `test`: `python -m pytest tests/ workflows/tests/ --tb=short -q`
- Job 4 `build`: `python -c "from billing_real import BillingEngine, MockProvider, StripeProvider, OpenAIProvider; print('imports OK')"`
- run_ci.ps1: 顺序跑 4 阶段,任一 fail 立即 stop,返回 exit code
- 新增 `tests/test_ci_smoke.py`: 验证 run_ci.ps1 文件存在 + 4 阶段命令都在
**Verification**:
```powershell
cd D:\CloudTech-Portable
.\run_ci.ps1           # 4 stage 全 PASS
pytest tests/test_ci_smoke.py -q  # → ≥3 PASS
```
**Blocked-on (NOT this task)**: 实际 GitHub push (proxy 127.0.0.1:7897 down — `blockers_per_master_section_22.1_github_push`)
**Forbidden**: 真实 push / 真实 CI provider / `_r*.py` / 红线 / 跨工程

---

## 4. Dispatch 总览 (本 batch 5 task)

| # | Task | Sub-agent | Est. time | Est. +PASS | Status |
|---|------|-----------|-----------|-----------|--------|
| T01 | Integration test suite | 待派 (#85?) | 30 min | +8 | QUEUED |
| T02 | Provider adapter | Peirce #83 | DONE | +8 | ✅ DONE |
| T03 | Multi-tenant stress | Linnaeus (active) | 35 min | +5 | QUEUED |
| T04 | Pilot data gen | 待派 (#86?) | 40 min | +6 | QUEUED |
| T05 | CI pipeline | 待派 (#87?) | 25 min | +3 | QUEUED |

**Cumulative expected after this batch**: 524 + 8 + 5 + 6 + 3 = **546 PASS** (0 FAIL, 7 SKIP 保持)

---

## 5. 累计状态 (post this commit)

```
git_commits:           20 (was 19, +1 for this dashboard commit)
actual_pass_count:     524
actual_fail_count:     0
actual_skip_count:     7
test_files:            28 (+ tests/test_bill_provider_interface.py 由 Peirce 待 commit)
wf_modules:            24
wf_tests:              24
acceptance_bodies:     85
sub_agents_dispatched: 20
sub_agents_completed:  13 (含 Aquinas / Carnot / Peirce / Maxwell 4 个本 batch)
sub_agents_active:     6 (Linnaeus / Confucius / Sartre / Copernicus / Hippocrates / Galileo)
```

> 注: Linnaeus (#85?) 和 Confucius 仍是 active,dashboard JSON 已记录。

---

## 6. 红线 & 范围合规

| 红线 | 状态 |
|------|------|
| ❌ 不可写 `protocols/version/_r*.py` | ✅ 本 commit 不触碰 |
| ❌ 不可改 `admin_dashboard.py` 红线段 | ✅ 本 commit 不触碰 |
| ❌ 不可跨工程 `D:\AIOS\` 写入 | ✅ 本 commit 仅在 `D:\CloudTech-Portable\` |

---

## 7. 文件清单 (本 commit)

```
M  FINAL_HANDOFF/_LIVE_DASHBOARD.json       # 1587B V6.2 compact
?? FINAL_HANDOFF/evidence/42_FINAL_DASHBOARD.md   # 本文件
```

---

**Sign-off**: Codex sub-agent #84 (Peano) — V6.2 LIVE DASHBOARD + V6.3 NEXT-BATCH queue 已 commit。
Codex supervisor 下个 dispatch 循环可按 §3 顺序派 T01 / T03 / T04 / T05 (T02 已 DONE)。
