# V6.2 NEXT BATCH — Dispatch Queue for Codex Supervisor

**Date**: 2026-10-08T21:45:00+08:00
**Author**: Codex sub-agent #73 (Shannon)
**Project**: CloudTech-Portable / AI 数字营销中台
**Status**: V6.2 sub-agent queue (continuation work)

---

## Current state (post #73 hand-off)

- **test_models.py**: 13/13 PASS (8 original + 5 email edge cases)
- **test_db_integration.py**: 5/5 PASS (new file, 5 CloudTech DB edge cases)
- **Combined delta this turn**: +10 PASS, 0 FAIL, 0 SKIP
- **Cumulative V6.2 baseline**: ~334 PASS (from 324 prior)

## Ready-for-dispatch (next 5 items)

These are concrete next work items that build on the V6.2 momentum and
do **not** require blocked infrastructure (no Provider API / Pilot / PG /
SMTP / GitHub push).

---

### Task 74 — `wf_runs_state_transitions` (acceptance expansion)

**File**: `tests/test_cloudtech_acceptance.py`
**Goal**: Replace the 23 currently-passing-but-thin acceptance skeletons
with real state-machine assertions for `pipeline_runs` and
`workflow_executions` (if present). Cover:
- running → completed (success_rate=1.0)
- running → failed (success_rate=0.0, error_message set)
- running → cancelled (mid-flight abort)
- pending → running (start trigger)
**Verification**: `pytest tests/test_cloudtech_acceptance.py -q` →
≥23 PASS (no new FAIL).
**Forbidden**: protocols/version/handoff/_r*.py, real Provider API.

---

### Task 75 — `test_api_integration` (FastAPI/Flask routes)

**File**: `tests/test_api_integration.py` (NEW)
**Goal**: Write 8 E2E tests using Flask `test_client()` for the top
public routes (`/api/health`, `/api/v1/auth/register`,
`/api/v1/auth/login`, `/api/v1/tenant/info`,
`/api/v1/content/generate` mocked, `/api/v1/billing/plans`).
Use `monkeypatch` to mock `openai`/`deepseek`/`doubao` calls.
**Verification**: `pytest tests/test_api_integration.py -q` → 8 PASS,
no FAIL.
**Forbidden**: cross-engine D:\AIOS, real Provider API.

---

### Task 76 — `test_crm_workflow` (CRM deep integration)

**File**: `tests/test_crm.py` (augment) + `tests/test_crm_integration.py` (NEW)
**Goal**: Add 6 tests covering:
- Lead create → qualify → won (state machine)
- Lead → opportunity → quote → invoice (4-stage)
- Tenant scoping (lead of tenant A never visible to tenant B)
- Email-template rendering with all 4 templates (welcome, follow-up,
  proposal, win)
- Bulk import (CSV parsing) → 100 leads
- Soft-delete (is_active flag, not hard delete)
**Verification**: `pytest tests/test_crm.py tests/test_crm_integration.py -q`
→ +6 PASS.
**Forbidden**: real Provider API.

---

### Task 77 — `test_content_pipeline_e2e` (full content flow)

**File**: `tests/test_content_pipeline.py` (NEW)
**Goal**: 5 tests for content creation pipeline:
- `generate_content` returns valid `GenerateV2Request` schema
- Platform-specific formatter applies max_chars correctly
  (xiaohongshu 1000 / wechat 5000 / douyin 200)
- Hashtag extraction from base_content (regex over `#\w+`)
- Content fingerprint SHA-256 (idempotency guard for re-generation)
- Multi-platform batch (1 topic → 3 platform variants)
**Verification**: `pytest tests/test_content_pipeline.py -q` → 5 PASS.
**Forbidden**: real Provider API.

---

### Task 78 — `test_billing_payments_e2e` (payment flow)

**File**: `tests/test_billing_payments.py` (NEW)
**Goal**: 6 tests covering the full payment lifecycle using
`payment_orders.py` + `wechat_pay.py`:
- Order create (pro plan = 999)
- Order confirm → status=paid
- Refund flow (cancel within 24h)
- Quota re-calculation after payment
- Plan upgrade (starter → pro) updates tenant_billing row
- Invoice URL generation (HMAC signature mock)
**Verification**: `pytest tests/test_billing_payments.py -q` → 6 PASS.
**Forbidden**: real WeChat Pay API, real bank integration.

---

## Acceptance criteria (Codex supervisor gate)

Each task should:
1. Be a single sub-agent (dev role)
2. Land in ≤ 30 minutes wall-clock
3. Net +N PASS (where N is the documented goal) with 0 regression
4. Produce evidence file in `FINAL_HANDOFF/evidence/` per AIOS convention
5. Use only allowed scope: `tests/`, `*.py` source for tests, evidence files

## Out-of-scope (still BLOCKED — do NOT touch)

- ❌ GitHub push (proxy down)
- ❌ Real Provider API (DeepSeek/豆包/Kimi)
- ❌ Real Pilot integration
- ❌ PostgreSQL cluster
- ❌ SMTP sending
- ❌ `protocols/version/_r*.py` (central AIOS core)
- ❌ Cross-engine `D:\AIOS\` writes

## Dispatch order (recommended)

74 → 75 → 76 → 77 → 78 (sequential, single agent each)

Total expected: +48 PASS in V6.2 cumulative count.

---

**Sign-off**: Codex sub-agent #73 (Shannon) completed 31_NEXT_BATCH_TASKS.md.
Ready for Codex supervisor dispatch loop continuation.