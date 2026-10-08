# Subagent #61 Task - 24 workflow individual tests

## Tasks
For each of 24 workflow modules in workflows/impl/wf_*.py, write corresponding test in workflows/tests/test_wf_*.py:
- workflows/tests/test_wf_t001_diagnosis.py through test_wf_g024_export.py
- >= 5 cases per test (basic + error path + boundary)
- Use mock only, no real Provider/external API

## Out-of-scope
- protocols/version/handoff/_r*.py/顶层 .md
- .gitignore/_pycache_/.env
- admin_dashboard.py major logic
- D:\AIOS cross-engine

## Acceptance
- 24/24 test files created
- pytest workflows/tests runs

## Sign-off
Codex sub-agent #61 dispatched (NOT user CC).
