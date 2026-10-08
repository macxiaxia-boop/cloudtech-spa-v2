# 41 — V6.2 Provider Adapter Layer (DONE)

**Date**: 2026-10-08
**Sub-agent**: dev #83 (Poincaré)
**Status**: ✅ 8/8 new + 28/28 regression — **36/36 PASS**
**Red line compliance**: #95 EXTEND (Adapter 模式 + 接入位标记)

---

## 1. 目标

把 `billing_real.py` 内的 `MockProvider` 抽成 `BillingProvider` 抽象接口，并提供 2 个真实供应商 stub (Stripe + OpenAI)。真接口完整、但**不真调**（无 key），由 `__REAL_PROVIDER_CALL_NEEDED__` 标记真调接入位，让 user 修 CC 后可 grep 替换。

## 2. 变更摘要

| 文件 | 变更 | 行数 |
|------|------|------|
| `D:\CloudTech-Portable\billing_real.py` | 加 `from abc import ABC, abstractmethod` + `BillingProvider` ABC + `MockProvider(BillingProvider)` + `StripeProvider(BillingProvider)` + `OpenAIProvider(BillingProvider)` | 254 行新增 (842 → 1096) |
| `D:\CloudTech-Portable\tests\test_bill_provider_interface.py` | **新建** 8 case 测试 | 13.8 KB |
| `D:\CloudTech-Portable\FINAL_HANDOFF\evidence\41_PROVIDER_ADAPTER.md` | **新建** 本 evidence | — |

## 3. 接口设计 — `BillingProvider` (ABC)

```python
class BillingProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    @abstractmethod
    def issue_callback(self, *, tenant_id, idempotency_key, amount, currency, success=True): ...
    @abstractmethod
    def replay(self, callback) -> object: ...
    @abstractmethod
    def deliver_count(self, charge_id) -> int: ...
    @abstractmethod
    def issue_monthly_bill(self, year, month, entries) -> dict: ...
    @abstractmethod
    def get_monthly_bill(self, year, month): ...
```

**3 个实现**：
- `MockProvider` — 完全 in-memory，测试/离线开发用（保留原有方法 + 加 `@property name` 覆写 ABC）
- `StripeProvider` — 接口完整 + `__REAL_PROVIDER_CALL_NEEDED__` 标记真调位 + `mode='stub'` 默认走 in-memory
- `OpenAIProvider` — 同 StripeProvider 模式

## 4. 8 case 测试 — 全 PASS

```
tests/test_bill_provider_interface.py::test_case_01_abc_cannot_be_instantiated PASSED
tests/test_bill_provider_interface.py::test_case_02_mockprovider_implements_interface PASSED
tests/test_bill_provider_interface.py::test_case_03_stripe_provider_implements_interface PASSED
tests/test_bill_provider_interface.py::test_case_04_openai_provider_implements_interface PASSED
tests/test_bill_provider_interface.py::test_case_05_engine_di_accepts_all_three_providers PASSED
tests/test_bill_provider_interface.py::test_case_06_issue_callback_returns_provider_callback PASSED
tests/test_bill_provider_interface.py::test_case_07_real_providers_no_api_call_in_any_mode PASSED
tests/test_bill_provider_interface.py::test_case_08_real_providers_have_real_call_marker PASSED
```

| # | Case | 验证内容 |
|---|------|----------|
| 1 | ABC instantiation fails | `BillingProvider()` 抛 `TypeError: abstract` |
| 2 | MockProvider implements interface | `isinstance(MockProvider(), BillingProvider) == True` |
| 3 | StripeProvider implements interface | `isinstance(StripeProvider(), BillingProvider) == True` |
| 4 | OpenAIProvider implements interface | `isinstance(OpenAIProvider(), BillingProvider) == True` |
| 5 | Engine DI accepts all 3 | `BillingEngine(provider=X)` 3 个 provider 都行 |
| 6 | issue_callback contract | 返回 `ProviderCallback` (Pydantic) + 字段契约统一 |
| 7 | No API call in any mode | stub 走 in-memory + live 抛 `NotImplementedError` |
| 8 | Real call marker exists | `__REAL_PROVIDER_CALL_NEEDED__` 在 Stripe/OpenAI 类属性，marker 含 7 关键词 |

## 5. 关键约束验证

### 5.1 红线 #95 EXTEND ✅
- Adapter pattern: `BillingProvider` ABC + 3 个实现
- 接入位显式标记: 17 个 `__REAL_PROVIDER_CALL_NEEDED__` 出现 (2 类属性 + 5 方法 × 2 provider + 注释 grep 串)
- 单测可独立跑: 36/36 测试不依赖网络/真实 API

### 5.2 6 invariant logic 不变 ✅
- `BillingEngine` 6 invariant 方法 (`invariant_append_only`, `invariant_idempotency`, `invariant_no_negative_amount`, `invariant_correction_pairs`, `invariant_charge_id_dedup`, `invariant_balance_conservation`) 全部保留
- 28/28 现有 BILL acceptance 测试无回归

### 5.3 不真调 Provider API ✅
- `StripeProvider(mode="live")` / `OpenAIProvider(mode="live")` 立即 `raise NotImplementedError(self.__REAL_PROVIDER_CALL_NEEDED__)`
- 无 key 配置、无网络请求、无 side effect

### 5.4 不可写 protocols/version/_r*.py ✅
- 只动 `billing_real.py` (主文件) + 新建 `tests/test_bill_provider_interface.py` + evidence
- 无 `_r*.py` / `protocols.py` / `version.py` 写入

### 5.5 不可改 admin_dashboard.py 红线 ✅
- `admin_dashboard.py` 未触碰

## 6. 验证命令与结果

```bash
$ cd D:\CloudTech-Portable
$ python -m pytest tests/test_bill_acceptance.py tests/test_bill_provider_interface.py -q
....................................                                     [100%]
36 passed in 0.27s
```

**最终结果**: **36/36 PASS** (28 旧 + 8 新)

## 7. user 启用真调指南（CC 修好后）

```python
# 1. 拿到 key 后, 把 live 模式启用
from billing_real import StripeProvider, OpenAIProvider
stripe = StripeProvider(api_key="sk_live_xxx", mode="live")   # 当前 raise
openai = OpenAIProvider(api_key="sk-xxx", mode="live")         # 当前 raise

# 2. 启用流程: grep "__REAL_PROVIDER_CALL_NEEDED__" → 替换 raise 为真 HTTP
# grep 命令: 
#   grep -n "__REAL_PROVIDER_CALL_NEEDED__" billing_real.py
# 替换每处 raise 为真实 SDK 调用 (stripe.Charge.create / openai.Usage.list)

# 3. 跑真接口测试 (本地开发):
python -c "
from billing_real import StripeProvider
p = StripeProvider(api_key='sk_test_xxx', mode='live')
# 此时 issue_callback 应该走真 HTTP, 而不是 raise
"
```

## 8. 文件清单

```
D:\CloudTech-Portable\
├── billing_real.py                                # 修改 (842 → 1096 行)
├── tests\
│   └── test_bill_provider_interface.py            # 新建 (13.8 KB, 8 case)
└── FINAL_HANDOFF\evidence\
    ├── 41_PROVIDER_ADAPTER.md                     # 本文件
    └── _v62_pytest.log                            # pytest 完整 log
```

---

**V6.2 Provider Adapter Layer — SHIPPED** ✅
