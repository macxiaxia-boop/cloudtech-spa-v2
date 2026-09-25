"""Wave orchestrator: run all migration waves in sequence and emit consolidated evidence.

Run: .venv/Scripts/python.exe -m cloudtech.live_migration.run_all_waves
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict


WAVES = [
    ("Wave 2", "shadow_adapter.py", "shadow_diff"),
    ("Wave 3", "router_v2.py", "router_v2"),
    ("Wave 5", "effect_ledger.py", "effect_ledger"),
    ("Wave 7", "evidence_gate.py", "evidence_gate"),
    ("Wave 8", "chaos_test.py", "chaos_test"),
    ("Wave 9", "rollback_test.py", "rollback_test"),
    ("Wave 10", "e2e_fake_smoke.py", "wave10_smoke"),
]


def run_wave(label: str, script: str, key: str) -> Dict[str, Any]:
    """Run a single wave script and capture result."""
    base = Path("D:/CloudTech-Live-Execution/CloudTech_rc2_Live_Direct_Execution_20260925/src/cloudtech/live_migration")
    script_path = base / script
    print(f"\n{'='*60}")
    print(f"[{label}] Running {script}...")
    print(f"{'='*60}")
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(base.parent.parent.parent),
            timeout=120,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "label": label,
            "script": script,
            "key": key,
            "exit_code": result.returncode,
            "elapsed_ms": round(elapsed, 2),
            "stdout_tail": result.stdout[-500:] if result.stdout else "",
            "stderr_tail": result.stderr[-500:] if result.stderr else "",
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"label": label, "script": script, "key": key, "success": False, "error": "timeout 120s"}
    except Exception as e:
        return {"label": label, "script": script, "key": key, "success": False, "error": str(e)}


def main():
    """Run all waves."""
    print("[Orchestrator] CloudTech rc2 Live Migration — all waves")
    results = []
    for label, script, key in WAVES:
        result = run_wave(label, script, key)
        results.append(result)
        status = "✅" if result.get("success") else "❌"
        print(f"\n[{status}] {label} ({script}) — exit={result.get('exit_code')} elapsed={result.get('elapsed_ms')} ms")

    # Emit consolidated evidence
    artifacts_dir = Path("D:/CloudTech-Live-Execution/CloudTech_rc2_Live_Direct_Execution_20260925/artifacts")
    output_path = artifacts_dir / "all_waves_run.json"
    out = {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "title": "CloudTech rc2 Live Migration — All Waves Run",
        "waves_run": results,
        "summary": {
            "total_waves": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
        },
    }
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Orchestrator] Emitted: {output_path} ({output_path.stat().st_size:,} bytes)")
    print(f"[Orchestrator] {out['summary']['successful']}/{out['summary']['total_waves']} waves PASSED")


if __name__ == "__main__":
    main()
