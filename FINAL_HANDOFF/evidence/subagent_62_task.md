# Subagent #62 Task - 32 pages UI binding tests

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
- D:\AIOS cross-engine

## Acceptance
- 32/32 tests created
- pytest tests/test_ui_pages_binding.py runs

## Sign-off
Codex sub-agent #62 dispatched (NOT user CC).
