# 12_PROVIDER_COST_RECONCILIATION.md

**Status**: NOT_RUN (no real provider contract in scope)

## Findings

- 没有真实 supplier API key 或 contract (BLOCKED_EXTERNAL)
- 只有 mock billing implementation (per tests/test_d31_37_billing_quotas.py 22/22 PASS in mock env)
- BILL-001~013 全部 NOT_TESTED in production

## What blocks 风险

需用户单独提供:
1. 供应商 API 密钥 (openai/anthropic/aliyun 等) + signed contract
2. 价格版本 schema (provider 不同 model 不同 token 计费 / 分组)
3. 双账本 schema (cost vs customer)
5. Real partner 模型调用回执

## Status

provider_key_present: NO
real_provider_calls_made: 0
billing_reconciliation_runs: 0
cost_usd_known: 1 (BILL mock only)
customer_charge_usd_known: 0

When provider_key present + real contracts:
- T12: 计价合同 / 原始用量 Event (FT-023 ~ $0025)
- T13: Credits 双分录 / 幂等 (FT-026, FT-028)
- T15: 客户账单 + 供应商对账 (FT-030, FT-031)
- T16: 真实授权 Provider Golden Task

## Action: BLOCKED_NO_REAL_PROVIDER
