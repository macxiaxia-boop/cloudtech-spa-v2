# 45 — V6.3 T04 Pilot Realistic Data Generation (DONE)

**Date**: 2026-10-08
**Sub-agent**: dev #93 (V6.3 T04 — Pilot Data Generation)
**Status**: ✅ 8/8 new + 268/268 regression — **276/276 PASS** (8 new + 268 workflows/tests/)
**Red line compliance**: #1 (真实数据 > 训练数据) + #95 EXTEND (Adapter 模式)

---

## 1. 目标

按 `evidence/42_FINAL_DASHBOARD.md` §3 T04 spec 实现 Pilot 真实业务数据生成器:
50 tenants / 30 leads each / 100 ledger each / 200 email drafts,导出 CSV+JSONL 到 `FINAL_HANDOFF/pilot_data/`,含幂等导入脚本。

**关键约束 (红线 #1)**: 不能用纯 fake 数据。所有 tenant 必须引用 `data/customers/*.json` 真实 POC,所有金额必须从 `data/business_data/t30_5_industries.json` 的 baseline_30d 派生。

---

## 2. 文件清单

| 文件 | 行数 | 用途 |
|------|------|------|
| `D:\CloudTech-Portable\workflows\impl\_pilot_data_gen.py` | **726** | NEW — pilot data 生成器 (CLI + lib) |
| `D:\CloudTech-Portable\tests\test_pilot_data_gen.py` | **262** | NEW — 8 case 测试 |
| `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\tenants.csv` | 50 行 + header | NEW — tenant 主表 |
| `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\tenants.jsonl` | 50 行 | NEW — JSONL 镜像 |
| `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\leads.jsonl` | 1500 行 | NEW — leads (50×30) |
| `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\billing_ledger.jsonl` | 5000 行 | NEW — ledger (50×100) |
| `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\email_drafts.jsonl` | 200 行 | NEW — 4 模板×50 tenant |
| `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\import_pilot_data.py` | — | NEW — 幂等导入脚本 |
| `D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\manifest.json` | — | NEW — 程序化读取入口 |

**总新增代码行数**: 726 (impl) + 262 (test) = **988 行**, 加 7 个数据文件 + 1 import 脚本

---

## 3. 真实数据驱动 (红线 #1)

| 数据源 | 用法 | 覆盖率 |
|--------|------|--------|
| `data/customers/*.json` (30 POC) | tenant.name / industry / scale / location / pain_points / decision_makers 全部 seed | 100% tenant 引用 |
| `data/business_data/t30_5_industries.json` | channel_primary / content_type_primary / baseline_30d → 推算 ledger 金额 | 5 industries 全覆盖 |
| 真 POC 决策者姓名前缀 (王/李/张) | 扩展为 lead 姓名池 + 扩展 contact 池 | 30+ surnames |

**Plan 映射规则 (基于真 scale_label)**:
- ≥5000万 → enterprise (WF-G-013 quota 5000/seats 50)
- ≥1000万 → pro (quota 500/seats 10)
- 其余 → starter (quota 100/seats 3)

---

## 4. 8 case 测试 — 全 PASS

```
tests/test_pilot_data_gen.py::test_case_01_tenants_count_and_dual_format PASSED
tests/test_pilot_data_gen.py::test_case_02_lead_status_distribution_30_40_20_10 PASSED
tests/test_pilot_data_gen.py::test_case_03_billing_ledger_4_kinds_present PASSED
tests/test_pilot_data_gen.py::test_case_04_email_drafts_4_templates_x_50_tenants PASSED
tests/test_pilot_data_gen.py::test_case_05_real_data_driven_not_pure_fake PASSED
tests/test_pilot_data_gen.py::test_case_06_import_script_idempotent PASSED
tests/test_pilot_data_gen.py::test_case_07_plan_mapping_rule PASSED
tests/test_pilot_data_gen.py::test_case_08_outputs_and_manifest_complete PASSED
```

| # | Case | 验证内容 |
|---|------|----------|
| 1 | tenants 50 + dual format | CSV 50 行 + JSONL 50 行 + 必要字段齐全 |
| 2 | lead status 分布 | 30/40/20/10 ±2% (new/qualified/won/lost) |
| 3 | billing ledger 4 kind | reservation/settlement/refund/correction 全在, 每种 ≥5% |
| 4 | 200 email drafts | 4 模板 × 50 tenant, 每 tenant 收到 4 封 |
| 5 | 真实数据驱动 (红线 #1) | ≥10 distinct POC, 5 industries, pain_points 来自真 POC |
| 6 | 导入脚本幂等 | subprocess 跑 2 次, raw_count == unique_count, dict 等 |
| 7 | plan 映射规则 | scale ≥5000→enterprise, ≥1000→pro, 其余→starter |
| 8 | outputs + manifest | 7 文件齐全, manifest 含 task_id/seed/sources/counts/red_line_compliance |

---

## 5. CLI 用法

```powershell
cd D:\CloudTech-Portable
python workflows\impl\_pilot_data_gen.py
# → tenants: 50 (csv=50, jsonl=50)
# → leads: 1500
# → billing_ledger: 5000
# → email_drafts: 200
# → import_script: D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\import_pilot_data.py
# → manifest: D:\CloudTech-Portable\FINAL_HANDOFF\pilot_data\manifest.json
```

可选参数:
- `--out DIR` (default `FINAL_HANDOFF/pilot_data`)
- `--tenants 50`
- `--leads-per-tenant 30`
- `--ledger-per-tenant 100`
- `--seed 42`

---

## 6. 累计状态 (post this commit)

| 指标 | 变化 |
|------|------|
| git_commits | 19 → 20 |
| actual_pass_count (V6.3 session) | 524 → 524 + 8 = **532** |
| actual_fail_count | 0 → 0 (本次新增无 FAIL) |
| actual_skip_count | 7 (不变) |
| test_files | 28 → 29 (新增 test_pilot_data_gen.py) |
| wf_modules | 24 (不变) |
| wf_tests | 24 (不变) |
| acceptance_bodies | 85 (不变) |
| sub_agents_dispatched | 20 → 21 |
| sub_agents_completed | 13 → 14 |

**新 PASS 增量**: +8 (T04 pilot data gen — dev #93)

---

## 7. 红线 & 范围合规

| 红线 | 状态 |
|------|------|
| ❌ 不可写 `protocols/version/_r*.py` | ✅ 本 commit 不触碰 |
| ❌ 不可改 `admin_dashboard.py` 红线段 | ✅ 本 commit 不触碰 |
| ❌ 不可跨工程 `D:\AIOS\` 写入 | ✅ 本 commit 仅在 `D:\CloudTech-Portable\` |
| ❌ 不可调外部 API (CRM/Stripe/OpenAI live) | ✅ 仅本地落盘 (红线 #95 EXTEND) |
| ❌ 不可 fake 数据 (>红线 #1) | ✅ 100% 数据源从 data/customers + data/business_data 读取 |

---

## 8. Sub-agent 报告

**Sub-agent**: dev #93 (V6.3 T04 — Pilot Data Generation)
**Spec source**: `evidence/42_FINAL_DASHBOARD.md` §3 T04
**Total time**: ~25 min (含真实数据源勘察 + 6 个 dataclass 设计 + CLI + 8 case 测试)
**Verification**: 8/8 PASS + 268/268 regression PASS = **276/276 PASS**

---

**Sign-off**: Codex sub-agent #93 (V6.3 T04) — Pilot Realistic Data Generation 已 commit。
Codex supervisor 下个 dispatch 循环可继续派 T05 (CI pipeline)。

> **Codex supervisor note**: 下个任务 T05 — dev #94, scope 与 evidence/42 §3 T05 对齐。CI Pipeline 4 stage + run_ci.ps1 + test_ci_smoke.py ≥3 PASS。Blocked-on proxy 127.0.0.1:7897 down (已在 spec 注明)。