# T07 — AIOS Capability Invocation · Real Evidence

> **Task**: T07 AIOS 能力调用部分真实 evidence
> **Subagent**: #77 (Turing-2, dev) — V6.2 supervisor delegated
> **Date**: 2026-10-08
> **Status**: ✅ 23/23 BILL acceptance tests PASS + 7/7 spot-check checks PASS

---

## 1. Scope

| 维度 | 验证内容 |
|---|---|
| 真实 run 过的 test | `pytest tests/test_bill_acceptance.py -v --tb=short` → 23 PASS |
| 5 case 抽检 | 实时跑 `BILL-001 / 002 / 003 / 004b / 013` 详尽状态 |
| Mock 边界 | `MockProvider` 不含真实 HTTP / 支付 SDK 引用 |
| Ledger invariant | I-1 ~ I-6 全部 `ok=True, msg='ok'` |

---

## 2. Deliverables

| 文件 | SHA-256 (前 16 字符) | 用途 |
|---|---|---|
| `D:\CloudTech-Portable\billing_real.py` | `DF5A52CC5E95A86C` | 真实 in-memory ledger 引擎 (842 行) |
| `D:\CloudTech-Portable\tests\test_bill_acceptance.py` | `1CC417B20EB1F77E` | 23 个 BILL 验收 test |
| `D:\CloudTech-Portable\_t07_bill_evidence.py` | `DF64A9F70D9C95F9` | 本次 evidence 跑测脚本 (7 个 spot check) |
| `D:\CloudTech-Portable\FINAL_HANDOFF\evidence\_t07_pytest_short.log` | `2D4206D14510776E` | pytest --tb=short 实跑日志 |
| `D:\CloudTech-Portable\FINAL_HANDOFF\evidence\_t07_pytest_full.log` | `0445B0067B42FE4E` | pytest -v 实跑日志 |
| `D:\CloudTech-Portable\FINAL_HANDOFF\evidence\_t07_evidence_run.log` | `6A7F6673B3863598` | 5-case spot check 实跑日志 |

完整 SHA-256 可重算: `Get-FileHash <path> -Algorithm SHA256`

---

## 3. Real Test Execution — `pytest -v --tb=short`

**命令**:
```bash
cd D:\CloudTech-Portable
python -m pytest tests/test_bill_acceptance.py -v --tb=short
```

**实跑结果** (23/23 PASS, 0.23s):

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
collected 23 items

tests/test_bill_acceptance.py::test_BILL_001_reserve_settle_release_conservation PASSED [  4%]
tests/test_bill_acceptance.py::test_BILL_002_concurrent_idempotency_10x PASSED [  8%]
tests/test_bill_acceptance.py::test_BILL_003_callback_replay_100x_no_double_charge PASSED [ 13%]
tests/test_bill_acceptance.py::test_BILL_004a_insufficient_balance_rejected PASSED [ 17%]
tests/test_bill_acceptance.py::test_BILL_004b_hard_budget_exceeded PASSED [ 21%]
tests/test_bill_acceptance.py::test_BILL_005_streaming_abort_final_receipt PASSED [ 26%]
tests/test_bill_acceptance.py::test_BILL_006_input_output_cache_separate_pricing PASSED [ 30%]
tests/test_bill_acceptance.py::test_BILL_007_price_change_preserves_historical_bills PASSED [ 34%]
tests/test_bill_acceptance.py::test_BILL_008_failed_topup_not_credit PASSED [ 39%]
tests/test_bill_acceptance.py::test_BILL_009_refund_correction_single_direction PASSED [ 43%]
tests/test_bill_acceptance.py::test_BILL_010_provider_monthly_reconciliation_diff PASSED [ 47%]
tests/test_bill_acceptance.py::test_BILL_011_multi_currency_rate_versioning PASSED [ 52%]
tests/test_bill_acceptance.py::test_BILL_012_multimodal_unit_accounting PASSED [ 56%]
tests/test_bill_acceptance.py::test_BILL_013_append_only_ledger_invariant PASSED [ 60%]
tests/test_bill_acceptance.py::test_BILL_014_hard_budget_concurrent_enforcement PASSED [ 65%]
tests/test_bill_acceptance.py::test_BILL_015_partial_release_returns_only_released PASSED [ 69%]
tests/test_bill_acceptance.py::test_BILL_016_idempotency_on_reservation PASSED [ 73%]
tests/test_bill_acceptance.py::test_BILL_017_settle_at_lower_amount PASSED [ 78%]
tests/test_bill_acceptance.py::test_BILL_018_correction_with_related_entry PASSED [ 82%]
tests/test_bill_acceptance.py::test_BILL_019_failed_callback_no_balance_credit PASSED [ 86%]
tests/test_bill_acceptance.py::test_BILL_020_rate_version_snapshot_in_settlement PASSED [ 91%]
tests/test_bill_acceptance.py::test_BILL_021_multimodal_mixed_units_one_event PASSED [ 95%]
tests/test_bill_acceptance.py::test_BILL_022_charge_id_dedup_across_providers PASSED [100%]

============================= 23 passed in 0.23s ==============================
```

**关键事实**:
- 23 个 test_BILL_xxx 函数全部 PASSED
- 0 failed, 0 error, 0 skip
- `--tb=short` 即便失败也仅显示短 traceback;本次无失败 → traceback 部分为空
- 总耗时 0.23s, 在本地 Python 3.13.14 / pytest-9.1.1 下

---

## 4. 5-Case Spot Check — Real Live Run

**脚本**: `D:\CloudTech-Portable\_t07_bill_evidence.py`
**实跑输出** (摘录, 完整见 `_t07_evidence_run.log`):

### SPOT-1 / BILL-001 — reserve → settle → release 守恒

```
[before] available=1000 reserved=0
[reserve] entry_id=res_4b5cf478f2e9 amount=60.0000 status=ReservationStatus.PENDING
[settle]  entry_id=set_6881c3083423 amount=60.0000
[after]  available=940.0000 reserved=0.0000
[verify] expected=940.0000, pass=True
```

**事实**: 1000 − 60 = 940 ✓; ReservationEntry 状态 PENDING → SETTLED ✓; ledger_size 增加 2 ✓

### SPOT-2 / BILL-002 — 10 线程同 idempotency_key 并发

```
[threads started] 10 concurrent workers, elapsed=1.7ms
[unique reservations returned] 1 (expected: 1)
[errors] 0
[ledger reservations] 1
[reserved] 6.0000 (expected: 6.0000)
[verify] pass=True
```

**事实**: 10 个线程在 1.7ms 内全部拿到同一个 reservation entry_id, 余额只锁 1 次 ✓

### SPOT-3 / BILL-003 — 同 charge_id 投递 100 次

```
[iterations] 100 deliveries, elapsed=0.2ms
[unique settle entries returned] 1 (expected: 1)
[ledger SETTLEMENT rows for charge_id] 1
[provider deliver_count] 99
[available] 995 (expected: 995.0000)
[verify] pass=True
```

**事实**: 投递 100 次(含原始 + 99 次 replay), 仅 1 条 SETTLEMENT, 余额只扣 5 CNY 一次 ✓; provider 记录 99 次重放(deliver_count=99) ✓

### SPOT-4 / BILL-004b — hard_budget 并发拒绝

```
[20 threads] successes=5 rejects=15
[reserved] 99.9990 (must be <= 100)
[ledger size] 5
[verify] pass=True
```

**事实**: 20 线程并发 reserve, 5 成功 + 15 拒绝(hard_budget=100, 每笔 ~20); reserved=99.9990 不超 100 ✓

### SPOT-5 / BILL-013 + I-1 ~ I-6 全量 invariant

```
[tenant_a ledger size] 9
[tenant_b ledger size] 0
  [OK ] I-1 append_only: msg='ok'
  [OK ] I-2 balance_conservation: msg='ok'
  [OK ] I-3 no_negative_amount: msg='ok'
  [OK ] I-4 correction_pairs: msg='ok'
  [OK ] I-5 idempotency: msg='ok'
  [OK ] I-6 charge_id_dedup: msg='ok'
```

**事实**: 6 条 invariant 全部 `ok=True, msg='ok'`; tenant_a ledger=9 条(TOPUP seed + 3 RES + 3 SETTLE + 1 TOPUP_FAILED + 1 CORRECTION) ✓

### 总汇总

```
==============================================================================
  T07 SUMMARY — end 2026-10-08T13:08:54.925415+00:00 (0.01s)
==============================================================================
  [PASS] SPOT-1 BILL-001 reserve/settle/release
  [PASS] SPOT-2 BILL-002 concurrent idempotency
  [PASS] SPOT-3 BILL-003 callback replay 100x
  [PASS] SPOT-4 BILL-004b hard_budget concurrent
  [PASS] SPOT-5 BILL-013 + I-1..I-6 invariants
  [PASS] MOCK BOUNDARY no real API
  [PASS] TEST DOCSTRING mock only

  >>> 7/7 checks PASS <<<
```

---

## 5. Ledger Invariant — I-1 to I-6 Real Verified

`billing_real.py` 中 6 条公开 invariant 查询, 实测全部 PASS:

| ID | 不变量 | 实现入口 | 实测结果 |
|---|---|---|---|
| **I-1** | append-only (ledger 只能 add, 不能修改/删除历史) | `BillingEngine.invariant_append_only()` | `ok=True msg='ok'` |
| **I-2** | balance 守恒 `available = ΣTOPUP - ΣSETTLEMENT - ΣCORRECTION + ΣREFUND` | `BillingEngine.invariant_balance_conservation(tenant_id)` | `ok=True msg='ok'` |
| **I-3** | settled amount 永不为负 (Decimal >= 0) | `BillingEngine.invariant_no_negative_amount()` | `ok=True msg='ok'` |
| **I-4** | CORRECTION 必带 `related_entry_id` 指向已存在 entry | `BillingEngine.invariant_correction_pairs()` | `ok=True msg='ok'` |
| **I-5** | 同 `idempotency_key` 至多一笔 settle | `BillingEngine.invariant_idempotency()` | `ok=True msg='ok'` |
| **I-6** | 同 `charge_id` 在 ledger 中至多 1 次 | `BillingEngine.invariant_charge_id_dedup()` | `ok=True msg='ok'` |

聚合入口: `BillingEngine.check_all_invariants(tenant_id)` 跑全部 + 返回 `(ok, msgs)`。

**22 个 test_BILL_xxx 结尾都调用 `check_all_invariants(tenant_id)`** — 见 `tests/test_bill_acceptance.py` 每条 `ok, msgs = eng.check_all_invariants(...); assert ok`。

---

## 6. Provider Mock 边界 (无真 API)

`billing_real.py` 中 `MockProvider` 类**完全 in-memory**, 不含真实网络/支付通道引用:

### 6.1 类内部状态审计 (实跑 dump)

```
[MockProvider class] attrs starting with _:
    _delivered_count: defaultdict
    _lock: lock
    _monthly_bills: list
    _sent_callbacks: list
```

**事实**: 仅有 4 个内部字段, 无 `_session` / `_client` / `_api_key` / `_url` ✓

### 6.2 源码字符串扫描 (静态)

`billing_real.py` 中扫描的禁用关键字:

| 关键字 | 命中 |
|---|---|
| `requests.` | **0** |
| `httpx.` | **0** |
| `aiohttp.` | **0** |
| `urllib.request` | **0** |
| `stripe.` | **0** |
| `alipay.` | **0** |
| `wechat_pay` | **0** |
| `pay_sdk` | **0** |

**结论**: `networking-only module] NONE — pure in-memory mock` ✓

### 6.3 测试文件 mock 使用审计

`tests/test_bill_acceptance.py` 中:

| 项 | 数值 |
|---|---|
| `MockProvider(` 实例化次数 | **5** (在 fixtures / BILL-011 / BILL-014 / BILL-022 等) |
| 真实网络字符串 (`requests.` / `stripe.` / `urllib.request` / `httpx.`) | **0** |
| `@pytest.fixture` 数 | 3 (`provider`, `engine`, `engine_with_balance`) |
| `def test_BILL_*` 函数数 | **23** |

所有 23 个 test 全部依赖 `MockProvider` 提供 callback 流量 — 没有 1 个 test 调用任何真实 HTTP / SDK。

### 6.4 文档化的"out-of-scope"边界

`BILL_IMPL_20261008_1744.md` §8 中明文:

> ❌ 真实 Provider API (无 HTTP/SDK 调用)
> ❌ 真实 Stripe / 支付通道

---

## 7. Test → Mock 映射表 (per-test docstring/边界)

| Test | Mock 使用方式 | docstring 关键 |
|---|---|---|
| BILL-001 | `@pytest.fixture provider` → `MockProvider(name="mock_provider_a")` | "真实计费/对账引擎 ... 不依赖第三方 billing 服务 (mock provider)" |
| BILL-002 | 同上 fixture | "10 个线程同时 reserve 同一 idempotency_key → 恰好 1 个 reservation" |
| BILL-003 | `eng._provider.issue_callback(...)` | "同一 charge_id 投递 100 次 → ledger 中恰好 1 个 SETTLEMENT" |
| BILL-004a | fixture `engine` | "纯预付费 — 余额 0, 任何 reserve 都被拒" |
| BILL-004b | fixture `engine` | "后付费 — 硬预算被突破时拒绝" |
| BILL-005 | `eng._provider.issue_callback(...)` | "流式调用提前中止/用量不明 → 最终回执对账" |
| BILL-006 | fixture | "混合 3 种单位 — 分别按各自价格结算" |
| BILL-007 | `eng.publish_pricebook(...)` | "成本价变更不影响历史账单" |
| BILL-008 | `eng.topup(...)` | "失败充值不入余额" |
| BILL-009 | `ProviderCallback(... amount=Decimal('-30'))` | "退款/修正单向记账" |
| BILL-010 | `eng._provider.issue_monthly_bill(...)` | "供应商月账单对账差异单" |
| BILL-011 | 直接 `MockProvider(name=...)` | "跨币种与汇率版本化" |
| BILL-012 | fixture | "多模态单位核算" |
| BILL-013 | fixture | "append-only ledger invariant" |
| BILL-014 | 直接 `MockProvider` + 20 threads | "hard budget enforcement (并发场景)" |
| BILL-015 | fixture | "partial reservation release" |
| BILL-016 | fixture | "idempotency on reservation (多次 reserve 同 key)" |
| BILL-017 | fixture | "settlement at lower amount than reservation" |
| BILL-018 | fixture | "correction with related entry (单向)" |
| BILL-019 | `ProviderCallback(success=False)` | "failed callback (chargeback) — only negative entry, no double" |
| BILL-020 | fixture + 2 个 `publish_pricebook` | "rate version snapshot preserved" |
| BILL-021 | fixture + 自定义 pricebook | "multi-modal mixed unit (token + image + audio) in one event" |
| BILL-022 | 2 个 `MockProvider(name="provider_A/B")` | "charge code dedup across providers" |

所有 23 个 test 走 mock — 无任何 1 个 test 触达真实 API。

---

## 8. 23/23 PASS 真实 evidence (细节)

`pytest --tb=short -v` 输出验证(摘录):

| Test # | Test 函数 | 结果 | 耗时累计 |
|---|---|---|---|
| 1 | test_BILL_001_reserve_settle_release_conservation | PASSED | 4% |
| 2 | test_BILL_002_concurrent_idempotency_10x | PASSED | 8% |
| 3 | test_BILL_003_callback_replay_100x_no_double_charge | PASSED | 13% |
| 4 | test_BILL_004a_insufficient_balance_rejected | PASSED | 17% |
| 5 | test_BILL_004b_hard_budget_exceeded | PASSED | 21% |
| 6 | test_BILL_005_streaming_abort_final_receipt | PASSED | 26% |
| 7 | test_BILL_006_input_output_cache_separate_pricing | PASSED | 30% |
| 8 | test_BILL_007_price_change_preserves_historical_bills | PASSED | 34% |
| 9 | test_BILL_008_failed_topup_not_credit | PASSED | 39% |
| 10 | test_BILL_009_refund_correction_single_direction | PASSED | 43% |
| 11 | test_BILL_010_provider_monthly_reconciliation_diff | PASSED | 47% |
| 12 | test_BILL_011_multi_currency_rate_versioning | PASSED | 52% |
| 13 | test_BILL_012_multimodal_unit_accounting | PASSED | 56% |
| 14 | test_BILL_013_append_only_ledger_invariant | PASSED | 60% |
| 15 | test_BILL_014_hard_budget_concurrent_enforcement | PASSED | 65% |
| 16 | test_BILL_015_partial_release_returns_only_released | PASSED | 69% |
| 17 | test_BILL_016_idempotency_on_reservation | PASSED | 73% |
| 18 | test_BILL_017_settle_at_lower_amount | PASSED | 78% |
| 19 | test_BILL_018_correction_with_related_entry | PASSED | 82% |
| 20 | test_BILL_019_failed_callback_no_balance_credit | PASSED | 86% |
| 21 | test_BILL_020_rate_version_snapshot_in_settlement | PASSED | 91% |
| 22 | test_BILL_021_multimodal_mixed_units_one_event | PASSED | 95% |
| 23 | test_BILL_022_charge_id_dedup_across_providers | PASSED | 100% |

**最终行**: `============================= 23 passed in 0.23s ==============================`

> **注**: BILL-004 拆分为 4a (余额不足) + 4b (硬预算), 故 22 个验收维度 ↔ 23 个 test 函数。

---

## 9. 复跑命令

完整复跑以验证本 evidence:

```bash
cd D:\CloudTech-Portable

# 1. 跑全部 BILL test
python -m pytest tests/test_bill_acceptance.py -v --tb=short

# 2. 跑 5-case 抽检 + invariant 真实验证 + mock 边界
python _t07_bill_evidence.py

# 3. 文件 hash 验证
Get-FileHash billing_real.py -Algorithm SHA256
Get-FileHash tests/test_bill_acceptance.py -Algorithm SHA256
Get-FileHash _t07_bill_evidence.py -Algorithm SHA256
```

期望:
1. `23 passed in <1s`
2. `7/7 checks PASS`
3. 三个 SHA-256 与本文件 §2 表一致

---

## 10. Out-of-scope (严格遵守)

| 项 | 状态 |
|---|---|
| 修改 `billing.py` (legacy token-based) | ❌ untouched |
| 修改 `billing_pkg/` | ❌ untouched |
| 修改 `database.py` / 真实 SQLite 表 | ❌ untouched |
| 真实 HTTP / Stripe / 支付 SDK 调用 | ❌ untouched |
| 修改 `protocol_*.md` / `version_*.md` / `handoff_*.md` | ❌ untouched |
| 修改 `.git` / `.gitignore` | ❌ untouched |
| 跨工程 (写到 `D:\CloudTech-Portable\` 之外) | ❌ untouched |

---

## 11. 验收命令汇总 (一键)

```bash
cd D:\CloudTech-Portable && \
  python -m pytest tests/test_bill_acceptance.py -v --tb=short && \
  python _t07_bill_evidence.py
```

**期望输出**:
```
============================= 23 passed in 0.XX s =============================
...
  >>> 7/7 checks PASS <<<
```

---

**End of T07 Evidence — Subagent #77 (Turing-2)**