import pathlib
base = pathlib.Path(r"D:\CloudTech-Portable\FINAL_HANDOFF\evidence")
base.mkdir(exist_ok=True, parents=True)
handoff_dir = pathlib.Path(r"D:\CloudTech-Portable\_handoffs")
handoff_dir.mkdir(exist_ok=True, parents=True)

template = """# Handoff to dev sub-agent #{n}

**Date**: 2026-10-08T20:45:00+08:00

## Honest declaration
USER ClaudeCode CLI is BLOCKED (model routing unrecognized_model).
This sub-agent is Codex internal multi_agent_v1__spawn_agent, NOT user CC.
Report must state: Codex sub-agent dispatched, NOT user CC.
No fabrication. CC real ACK absent.

## Project context
- Repo: D:\\CloudTech-Portable\\.git (master branch, HEAD 5a5aac75)
- 561+ test PASS baseline (real pytest)
- 24 FINAL_HANDOFF artifacts + 1 status json

## Real blockers
- GitHub push: proxy 7897 down
- Provider API: no key + no signed contract
- Pilot customer: no CRM
- PG cluster: SQLite only
- AIOS Real Closed Loop: no external entry authorization

## Allowed executor
This Codex sub-agent (NOT user CC) can:
- Write Python files in: workflows/tests/, tests/, FINAL_HANDOFF/evidence/, billing_real.py
- Run pytest for verification
- Commit to D:\\CloudTech-Portable\\.git master branch
- NOT modify: .gitignore, _pycache_, .env, requirements.txt critical deps, Windows DNS, admin_dashboard.py major logic

## Tasks assigned to #{n}
See: D:\\CloudTech-Portable\\FINAL_HANDOFF\\evidence\\subagent_{n}_task.md

## Acceptance
Real test output, real pytest counts, real SHA. NO skip-without-reason.

## Sign-off
Codex sub-agent #{n} dispatched (NOT user CC).
"""

for n in [61, 62, 63, 64]:
    p = handoff_dir / f"subagent_{n}_handoff.md"
    p.write_text(template.format(n=n), encoding="utf-8")
    print(f"wrote {p}")
