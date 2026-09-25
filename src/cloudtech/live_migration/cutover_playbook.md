# CloudTech rc2 — Cutover Playbook (Human-in-the-Loop)

**Audience**: Operator (you) · **Mode**: READ-ONLY-BY-DEFAULT until explicit approval
**STOP_GATEs**: 3 active — **DO NOT execute cutover without addressing all 3 first**

---

## ⚠️ Critical Reminders Before You Start

1. **This playbook describes the cutover sequence — it does NOT execute it automatically.**
2. **All 3 STOP_GATEs must be resolved BEFORE Phase 1 begins.** See §1 below.
3. **Rollback is one command away.** `cutover.halt` returns traffic to Live legacy router immediately.
4. **You can pause at any phase boundary.** Each phase has an explicit promotion step.

---

## §1 · Resolve 3 STOP_GATEs (Before Phase 1)

### 1.1 `PRODUCTION_BACKENDS_REQUIRED`

You must verify all 3 production backends are reachable:

```bash
# Health check from the runtime host
curl -f http://localhost:5099/health        # CloudTech-Portable (uvicorn)
curl -f http://localhost:18792/health       # AIOS daemon (or your actual port)
# OpenClaw — check its health endpoint per your config
```

Expected output: `{"status":"ok",...}` for each. If any returns non-200, **STOP** and fix before continuing.

### 1.2 `REAL_PROVIDER_CREDENTIALS_REQUIRED`

You must provide real Provider API keys **via `.env`** (never committed, never logged).

```bash
# Edit your .env (NOT in candidate isolated copy — in Live system)
# CloudTech-Portable root
echo "DEEPSEEK_API_KEY=<your-real-key>" >> D:/CloudTech-Portable/.env
echo "OPENAI_API_KEY=<your-real-key>"      >> D:/CloudTech-Portable/.env    # optional failover

# Verify .env is gitignored
cd D:/CloudTech-Portable
git check-ignore .env && echo "OK .env is gitignored" || echo "WARN .env NOT gitignored"
```

**Never** paste keys into chat, terminal output, or git history. The Wave 10 staging uses `FakeProvider` for safety; you only need real keys for the actual cutover.

### 1.3 `USER_AUTHORIZATION_FOR_CUTOVER`

**This is the L5 gate.** You must explicitly state in chat:

> "Wave 10 切生产授权。Provider 凭据已配置,生产后端 health 通过,接受切流风险。开始 Phase 1 (5%)。"

Until this exact acknowledgment is given, no cutover action is taken.

---

## §2 · Phase 1: Canary 5% (Highest Risk)

### 2.1 Enter Phase 1

```bash
# Set feature flag to route 5% of traffic through Candidate rc2
export CLOUDTECH_RC2_TRAFFIC_PCT=5
export CLOUDTECH_RC2_ENABLED=true

# Restart CloudTech-Portable gateway
cd D:/CloudTech-Portable
# (your supervisor / WinSW restart command)
```

### 2.2 Watch for 30 minutes

Monitor at 1-minute intervals:

| Metric | Pass Threshold | Action if Failed |
|---|---|---|
| Success rate | ≥ 95% | Rollback (see §6) |
| p95 latency | ≤ 3000 ms | Rollback |
| 5xx error rate | ≤ 5% | Rollback |
| Cost per request | ≤ 3x baseline | Investigate, possibly rollback |

```bash
# Real-time metrics (in another terminal)
watch -n 60 'curl -s http://localhost:5099/metrics | grep rc2_'
```

### 2.3 Promotion Decision

After 30 minutes, if all thresholds hold:

```bash
# Promote to Phase 2
export CLOUDTECH_RC2_TRAFFIC_PCT=25
# Restart gateway
```

If any threshold fails: see §6 Rollback.

---

## §3 · Phase 2: Gradual 25% (60 minutes)

Same structure as Phase 1 with stricter thresholds:

| Metric | Threshold |
|---|---|
| Success rate | ≥ 95% |
| p95 latency | ≤ 2500 ms |
| Error rate | ≤ 5% |
| Cost vs Live | ≤ 2x |

Watch for cost spikes — Phase 2 is where you'd first see sustained production cost.

```bash
# Promote to Phase 3 after 60 min
export CLOUDTECH_RC2_TRAFFIC_PCT=50
```

---

## §4 · Phase 3: Majority 50% (120 minutes)

| Metric | Threshold |
|---|---|
| Success rate | ≥ 96% |
| p95 latency | ≤ 2000 ms |
| Error rate | ≤ 4% |

This is the most realistic load test. Compare side-by-side with Live legacy router metrics.

```bash
# Promote to Phase 4 after 120 min
export CLOUDTECH_RC2_TRAFFIC_PCT=100
```

---

## §5 · Phase 4: Full 100% (Indefinite)

Terminal phase. After 30 minutes of full-traffic observation:

```bash
# Mark cutover COMPLETE
export CLOUDTECH_RC2_CUTOVER_STATE=COMPLETE
```

**Keep Live legacy router in standby for 7 days.** Do not delete the legacy router code or routes during this period.

After 7 days of stable full-traffic operation, you may retire Live legacy router.

---

## §6 · Rollback (One Command)

At any phase, **immediate rollback**:

```bash
export CLOUDTECH_RC2_ENABLED=false
export CLOUDTECH_RC2_TRAFFIC_PCT=0
# Restart gateway
```

All traffic returns to Live legacy router within ~10 seconds (one health-check cycle).

See [rollback_runbook.md](rollback_runbook.md) for emergency procedures beyond the simple feature flag.

---

## §7 · Post-Cutover Checklist

After Phase 4 (Full 100%) runs for 30 minutes without issues:

- [ ] Cutover state set to `COMPLETE` in Live config
- [ ] Feature flag `CLOUDTECH_RC2_ENABLED=true` permanently
- [ ] Live legacy router kept in standby (do NOT delete)
- [ ] Effect Ledger database backed up to `E:/移动硬盘/AI生态灾难恢复备份/cloudtech_rc2_20260925/`
- [ ] Audit dir `C:/Users/xinzh/Desktop/CloudTech_Live_Audit_20260925_200726/` archived
- [ ] Bundle `LIVE_EVIDENCE_RETURN_BUNDLE.zip` copied to permanent storage
- [ ] SHA-256 verified against `LIVE_SHA256SUMS.txt`
- [ ] Operator (you) reviews final metrics dashboard

---

## §8 · What This Playbook Does NOT Cover

- **Data migration** of any stateful data (none required for rc2 router migration)
- **Schema migration** of the SQLite Effect Ledger (handled by Wave 9 rollback test)
- **Provider-side changes** (DeepSeek / OpenAI config is read-only on our side)
- **End-user communication** (this is internal SaaS, no user-facing changes)

---

**Cutover Playbook v1.0** · Generated 2026-09-25 · Wave 10 staging artifact
**Companion documents**: [production_cutover.yaml](production_cutover.yaml) · [rollback_runbook.md](rollback_runbook.md) · [evidence_gate.py](evidence_gate.py)