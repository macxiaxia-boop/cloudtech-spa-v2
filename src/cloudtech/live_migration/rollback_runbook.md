# CloudTech rc2 — Emergency Rollback Runbook

**When to use this runbook**: ANY of these conditions during or after cutover:
- Success rate < 90% sustained > 5 minutes
- 5xx error storm (> 20 errors/min)
- p95 latency > 5x baseline
- Any P0 incident traced to Candidate rc2 router
- Operator judgment ("this feels wrong, revert")

**Time to rollback target**: < 60 seconds end-to-end.

---

## §1 · FASTEST Rollback (Feature Flag Only)

**Use when**: 95% of cases. The feature flag reverts all traffic to Live legacy router.

### Step 1 — Disable Candidate rc2 (5 sec)

```bash
# One command, immediate effect
export CLOUDTECH_RC2_ENABLED=false
export CLOUDTECH_RC2_TRAFFIC_PCT=0
```

### Step 2 — Restart gateway (15 sec)

```bash
# CloudTech-Portable (uvicorn:5099)
# Use your supervisor / WinSW restart, e.g.:
winsw restart CloudTechGateway    # if you have a WinSW service

# OR direct kill+restart
taskkill /F /IM uvicorn.exe
cd D:/CloudTech-Portable
python -m uvicorn gateway_v22:app --host 0.0.0.0 --port 5099 &
```

### Step 3 — Verify (10 sec)

```bash
# Hit health endpoint, confirm Live legacy router is responding
curl -f http://localhost:5099/health
# Expected: {"status":"ok","router":"live-legacy","cutover_state":"ROLLED_BACK"}

# Verify traffic is back to baseline
watch -n 5 'curl -s http://localhost:5099/metrics | grep rc2_traffic_pct'
# Expected: rc2_traffic_pct 0.0 (all traffic on Live)
```

**Total time**: ~30 seconds. **Rollback COMPLETE.**

---

## §2 · File-Level Rollback (If Feature Flag Fails)

**Use when**: Feature flag toggle has no effect (e.g., env not reloaded, gateway stuck).

### Step 1 — Identify changed files

```bash
# Check what's been modified since cutover started
cd D:/CloudTech-Portable
git status --short
# Expected: only files in src/cloudtech/live_migration/ are NEW
# (from the Candidate isolated copy push)

# List exact files changed
git diff --name-only main..cloudtech-live-reconciliation-rc2
```

### Step 2 — Revert to pre-cutover commit

```bash
# Save current state (so we can investigate later)
git branch cloudtech-rollback-$(date +%Y%m%d_%H%M%S)

# Force the live branch back to pre-cutover HEAD
git checkout cloudtech-live-reconciliation-rc2
git reset --hard <pre-cutover-commit-sha>    # from your audit log

# Verify
git log --oneline -5
```

### Step 3 — Restart all 3 Live systems

```bash
# CloudTech-Portable
winsw restart CloudTechGateway

# OpenClaw Workbench
winsw restart OpenClawWorkbench

# AIOS ecosystem (only if rc2 affected it)
winsw restart AIOSSupervisor
```

### Step 4 — Verify all health checks

```bash
curl -f http://localhost:5099/health       # CloudTech
curl -f http://localhost:18792/health      # AIOS (or your port)
# OpenClaw health per your config
```

**Time**: ~3-5 minutes. Use only if §1 fails.

---

## §3 · Database-Level Rollback (Effect Ledger)

**Use when**: Effect Ledger SQLite corruption suspected OR you want to purge cutover-period effects.

### Step 1 — Stop gateway writes

```bash
# The feature flag in §1 already does this, but explicitly:
export CLOUDTECH_RC2_EFFECT_LEDGER_ENABLED=false
winsw restart CloudTechGateway
```

### Step 2 — Snapshot current ledger

```bash
# Save pre-cleanup copy
cp D:/CloudTech-Live-Execution/runtime_logs/effect_ledger.db \
   D:/CloudTech-Live-Execution/runtime_logs/effect_ledger_pre_rollback_$(date +%Y%m%d_%H%M%S).db
```

### Step 3 — Truncate or rebuild

```bash
# Option A: truncate to last-known-good timestamp
python -c "
import sqlite3
conn = sqlite3.connect('D:/CloudTech-Live-Execution/runtime_logs/effect_ledger.db')
conn.execute('DELETE FROM effects WHERE started_at > \"2026-09-25 19:00:00\"')
conn.commit()
print(f'Removed {conn.total_changes} effects after cutover start')
"

# Option B: drop and recreate (loses all history — last resort)
rm D:/CloudTech-Live-Execution/runtime_logs/effect_ledger.db
# (next request will recreate it with empty schema)
```

### Step 4 — Verify

```bash
python -c "
import sqlite3
conn = sqlite3.connect('D:/CloudTech-Live-Execution/runtime_logs/effect_ledger.db')
n = conn.execute('SELECT COUNT(*) FROM effects').fetchone()[0]
print(f'Effect ledger now has {n} entries (post-rollback)')
"
```

**Time**: ~2 minutes.

---

## §4 · Provider Credential Rotation (If Compromised)

**Use when**: A Provider API key was leaked during cutover (extremely unlikely, but defensive).

### Step 1 — Revoke leaked key

Go to the Provider's dashboard (DeepSeek / OpenAI / etc.) and **revoke the leaked key immediately**. This invalidates the key server-side.

### Step 2 — Generate new key

In the Provider dashboard, create a new API key.

### Step 3 — Update .env

```bash
# Edit .env
nano D:/CloudTech-Portable/.env
# Replace DEEPSEEK_API_KEY=<old> with DEEPSEEK_API_KEY=<new>

# Verify
grep -c "^DEEPSEEK_API_KEY=.\\{20,\\}" D:/CloudTech-Portable/.env
# Expected: 1
```

### Step 4 — Restart

```bash
winsw restart CloudTechGateway
# Verify health
curl -f http://localhost:5099/health
```

**Time**: ~2 minutes (assuming you have Provider dashboard access).

---

## §5 · Communication During Rollback

If the rollback is due to a P0 incident:

1. **Don't panic.** Run §1 first — it solves 95% of cases.
2. **Capture evidence**: take a screenshot of metrics showing the failure.
3. **Note timestamp** when rollback was initiated.
4. **Wait 5 minutes** after rollback to confirm stability before declaring "rollback complete".
5. **Post-mortem within 24 hours**:
   - What threshold was breached?
   - Was it a Candidate rc2 bug or a transient infra issue?
   - Was the rollback fast enough?
   - Do thresholds need adjustment?

---

## §6 · Rollback Decision Matrix

| Symptom | §1 Fast | §2 File | §3 DB | §4 Credential |
|---|---|---|---|---|
| High error rate | ✅ Try first | If §1 fails | — | — |
| Latency spike | ✅ Try first | If §1 fails | — | — |
| Gateway stuck / unhealthy | §1 may not work | ✅ Use this | — | — |
| Effect ledger corruption | ✅ stops writes | — | ✅ Use this | — |
| API key leak | — | — | — | ✅ Use this immediately |

---

## §7 · Post-Rollback Verification Checklist

- [ ] Live legacy router responding to traffic (verify with real request)
- [ ] All 3 health endpoints return 200
- [ ] Metrics show `rc2_traffic_pct=0`
- [ ] No errors in gateway logs in past 5 minutes
- [ ] Cost per request returned to baseline
- [ ] If cutover was > 25%, post-mortem scheduled within 24h
- [ ] If rollback involved credential rotation, verify new key works on test request

---

## §8 · Rollback Testing (Do This BEFORE Cutover)

Wave 9 already validated **file-level rollback** (5/5 cases PASS). To validate §1 in this runbook:

```bash
# Dry-run rollback (with FakeProvider, no real traffic)
cd D:/CloudTech-Live-Execution/CloudTech_rc2_Live_Direct_Execution_20260925
.venv/Scripts/python.exe src/cloudtech/live_migration/run_all_waves.py
# Expected: 6/6 waves PASSED (including Wave 9 rollback_test.py)
```

---

**Rollback Runbook v1.0** · Generated 2026-09-25 · Wave 10 staging artifact
**Companion documents**: [cutover_playbook.md](cutover_playbook.md) · [production_cutover.yaml](production_cutover.yaml) · [rollback_test.py](rollback_test.py)