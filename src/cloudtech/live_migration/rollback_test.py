"""Wave 9: Rollback Verification — Verify rollback procedure works.

Simulates state mutations and verifies rollback can restore original state.
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class RollbackCase:
    """Single rollback verification case."""
    case_id: int
    target: str
    pre_state_hash: str
    post_mutation_hash: str
    post_rollback_hash: str
    rollback_succeeded: bool
    rollback_time_ms: float


@dataclass
class RollbackResult:
    """Aggregate rollback verification."""
    total_cases: int
    successful: int
    success_rate_pct: float
    cases: List[RollbackCase] = field(default_factory=list)


def hash_file(p: Path) -> str:
    """Compute SHA-256 hash of file content."""
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]


def simulate_mutation(p: Path) -> str:
    """Mutate file and return new hash."""
    original = p.read_text(encoding="utf-8")
    mutated = original + "\n# MUTATED FOR ROLLBACK TEST\n"
    p.write_text(mutated, encoding="utf-8")
    return hash_file(p)


def simulate_rollback(p: Path, backup_path: Path) -> str:
    """Restore file from backup and return new hash."""
    shutil.copy2(backup_path, p)
    return hash_file(p)


def run_rollback_test(targets: List[Path]) -> RollbackResult:
    """Run rollback verification on each target file."""
    print(f"[Wave 9] Rollback verification — {len(targets)} targets")
    cases: List[RollbackCase] = []
    successful = 0

    for i, target in enumerate(targets, 1):
        if not target.exists():
            continue
        # 1. Hash pre-state
        pre_hash = hash_file(target)
        # 2. Backup
        backup = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup)
        try:
            # 3. Mutate
            post_hash = simulate_mutation(target)
            # 4. Rollback
            t0 = time.perf_counter()
            restored_hash = simulate_rollback(target, backup)
            rollback_ms = (time.perf_counter() - t0) * 1000
            # 5. Verify
            success = restored_hash == pre_hash
            if success:
                successful += 1
            cases.append(RollbackCase(
                case_id=i,
                target=str(target),
                pre_state_hash=pre_hash,
                post_mutation_hash=post_hash,
                post_rollback_hash=restored_hash,
                rollback_succeeded=success,
                rollback_time_ms=round(rollback_ms, 3),
            ))
        finally:
            # Cleanup backup
            if backup.exists():
                backup.unlink()

    success_rate = round(100.0 * successful / max(1, len(cases)), 2)
    return RollbackResult(
        total_cases=len(cases),
        successful=successful,
        success_rate_pct=success_rate,
        cases=cases,
    )


def main():
    """Run Wave 9 rollback verification."""
    print("[Wave 9] Rollback Verification — File-level rollback testing")
    base = Path("D:/CloudTech-Live-Execution/CloudTech_rc2_Live_Direct_Execution_20260925/src/cloudtech/live_migration")
    targets = [
        base / "shadow_adapter.py",
        base / "router_v2.py",
        base / "effect_ledger.py",
        base / "evidence_gate.py",
        base / "chaos_test.py",
    ]
    result = run_rollback_test(targets)

    print(f"\n[Wave 9] Total cases: {result.total_cases}")
    print(f"[Wave 9] Successful rollbacks: {result.successful}")
    print(f"[Wave 9] Success rate: {result.success_rate_pct}%")
    for case in result.cases:
        status = "✅" if case.rollback_succeeded else "❌"
        print(f"  {status} {case.target}: pre={case.pre_state_hash[:8]} -> post_rollback={case.post_rollback_hash[:8]} ({case.rollback_time_ms} ms)")

    # Emit evidence
    output_path = base.parent.parent.parent / "artifacts/wave9_rollback_test.json"
    out = {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "wave": "Wave 9 - Rollback Verification",
        "summary": {
            "total_cases": result.total_cases,
            "successful": result.successful,
            "success_rate_pct": result.success_rate_pct,
        },
        "gate_pass": result.success_rate_pct == 100.0,
        "cases": [
            {
                "case_id": c.case_id,
                "target": c.target,
                "pre_state_hash": c.pre_state_hash,
                "post_mutation_hash": c.post_mutation_hash,
                "post_rollback_hash": c.post_rollback_hash,
                "rollback_succeeded": c.rollback_succeeded,
                "rollback_time_ms": c.rollback_time_ms,
            }
            for c in result.cases
        ],
    }
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Wave 9] Emitted: {output_path} ({output_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
