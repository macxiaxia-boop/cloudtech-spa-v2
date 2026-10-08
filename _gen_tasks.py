import pathlib
base = pathlib.Path(r"D:\CloudTech-Portable\FINAL_HANDOFF\evidence")

task61 = """# Subagent #61 Task - 24 workflow individual tests

## Tasks
For each of 24 workflow modules in workflows/impl/wf_*.py, write corresponding test in workflows/tests/test_wf_*.py:
- workflows/tests/test_wf_t001_diagnosis.py through test_wf_g024_export.py
- >= 5 cases per test (basic + error path + boundary)
- Use mock only, no real Provider/external API

## Out-of-scope
- protocols/version/handoff/_r*.py/顶层 .md
- .gitignore/_pycache_/.env
- admin_dashboard.py major logic
- D:\\AIOS cross-engine

## Acceptance
- 24/24 test files created
- pytest workflows/tests runs

## Sign-off
Codex sub-agent #61 dispatched (NOT user CC).
"""

task62 = """# Subagent #62 Task - 32 pages UI binding tests

## Tasks
File: tests/test_ui_pages_binding.py
For each UI-001 through UI-032:
- test function using Flask test_client
- reuse session_token from admin_token fixture (test_api already fix)
- GET page route → assert 200 + DB call (mock)
- POST/PUT action → assert 200/422
- edge states: loading/empty/unauthorized/missing token

## Out-of-scope
- protocols/version/handoff/_r*.py/顶层 .md
- .gitignore/_pycache_/.env
- admin_dashboard.py major logic (unless bug fix)
- D:\\AIOS cross-engine

## Acceptance
- 32/32 tests created
- pytest tests/test_ui_pages_binding.py runs

## Sign-off
Codex sub-agent #62 dispatched (NOT user CC).
"""

task63 = """# Subagent #63 Task - 87 acceptance test bodies

## Tasks
Modify tests/test_cloudtech_acceptance.py
For each of 87 acceptance functions:
- Replace pytest.skip() with REAL test body
- Use mock for Provider/customer/PG
- Per master spec §27.1 (CORE/SEC/WF/KB/CON/MOD/BILL/MKT/CRM/BI/PILOT/OPS/UI/COMM/DE/DEP)

## Out-of-scope
- protocols/version/handoff/_r*.py/顶层 .md
- .gitignore/_pycache_/.env
- real Provider API/Pilot/PG
- admin_dashboard.py major logic
- D:\\AIOS cross-engine

## Acceptance
- 87/87 acceptance functions have body
- pytest tests/test_cloudtech_acceptance.py runs
- evidence: FINAL_HANDOFF/evidence/20_ACCEPTANCE_BODIES.md

## Sign-off
Codex sub-agent #63 dispatched (NOT user CC).
"""

task64 = """# Subagent #64 Task - Real throughput audit (T09)

## Tasks
Run ADDON/throughput_audit.py with REAL data (not example):
1. Read existing events from D:\\CloudTech-Portable\\FINAL_HANDOFF\\
2. Read git log actual commits
3. Read test count from pytest output
4. Compute actual effective throughput:
   - tokens_consumed_estimated (estimated not fake)
   - effective_passes (real pytest)
   - blocked_external count
   - quality_work_count
5. Generate FINAL_HANDOFF/18_THROUGHPUT_REAL.md with REAL numbers

## Out-of-scope
- protocols/version/handoff/_r*.py/顶层 .md
- Fake Token numbers
- D:\\AIOS cross-engine

## Acceptance
- Real (not example) audit output
- Estimated labels where data is not official
- Comparison vs original 87 example baseline

## Sign-off
Codex sub-agent #64 dispatched (NOT user CC).
"""

for i, t in enumerate([task61, task62, task63, task64]):
    n = 61 + i
    p = base / f"subagent_{n}_task.md"
    p.write_text(t, encoding="utf-8")
    print(f"wrote {p}")
