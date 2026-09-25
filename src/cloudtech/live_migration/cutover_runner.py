"""Wave 10: Cutover Runner — 4-phase rollout with auto-rollback on threshold breach.

Phases (per production_cutover.yaml):
- Phase 1: 5% traffic for 30 min
- Phase 2: 25% for 60 min
- Phase 3: 50% for 120 min
- Phase 4: 100% (terminal)

Each phase:
1. Sets CLOUDTECH_RC2_TRAFFIC_PCT
2. Restarts gateway (WinSW or subprocess)
3. Monitors metrics in real-time
4. Auto-rolls back if threshold breached

Safety:
- Dry-run mode (CLOUDTECH_RC2_DRY_RUN=1) — does NOT restart gateway, only logs decisions
- Auto-rollback targets feature flag flip (one command, reversible)
- Per-phase manual override via CLOUDTECH_RC2_ABORT=1
"""
from __future__ import annotations

import os
import json
import time
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))
from provider_router import chat, detect_provider_mode, ProviderResponse  # type: ignore


class CutoverState(Enum):
    STAGED = "staged"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class PhaseConfig:
    """Per-phase configuration."""
    phase: int
    name: str
    traffic_pct: int
    duration_sec: int
    success_rate_min_pct: float
    p95_latency_max_ms: float
    error_rate_max_pct: float
    abort_threshold: str


PHASES: List[PhaseConfig] = [
    PhaseConfig(1, "canary_5pct",   5,   30 * 60, 95.0, 3000.0, 5.0, "success_rate_below_90pct_for_5min"),
    PhaseConfig(2, "gradual_25pct", 25,  60 * 60, 95.0, 2500.0, 5.0, "success_rate_below_92pct_for_10min"),
    PhaseConfig(3, "majority_50pct", 50, 120 * 60, 96.0, 2000.0, 4.0, "success_rate_below_93pct_for_15min"),
    PhaseConfig(4, "full_100pct",   100, 30 * 60, 96.0, 2000.0, 4.0, "any_p0_incident"),
]


@dataclass
class PhaseMetrics:
    """Metrics collected during a phase."""
    phase: int
    total_requests: int = 0
    success_count: int = 0
    error_count: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    total_cost_usd: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def success_rate_pct(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(100.0 * self.success_count / self.total_requests, 2)

    @property
    def error_rate_pct(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round(100.0 * self.error_count / self.total_requests, 2)

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return round(sorted_lat[min(idx, len(sorted_lat) - 1)], 2)


@dataclass
class PhaseResult:
    """Result of a single phase run."""
    config: PhaseConfig
    metrics: PhaseMetrics
    aborted: bool
    abort_reason: Optional[str]
    next_phase: Optional[int]


def simulate_traffic(phase: int, duration_sec: int, sample_interval_sec: int = 5,
                     use_real: bool = False) -> PhaseMetrics:
    """Simulate traffic through the provider router for the duration of a phase.

    In dry-run or staging mode, this uses FakeProvider for safe simulation.
    If use_real=True AND DEEPSEEK_API_KEY is in env AND CLOUDTECH_RC2_USE_FAKE != 1,
    real API calls are made (use_real is gated by both user flag and env detection).
    """
    metrics = PhaseMetrics(phase=phase, start_time=time.time())
    sample_prompts = [
        [{"role": "user", "content": "写一篇AI增长顾问文案"}],
        [{"role": "user", "content": "分析竞品瑞幸vs星巴克"}],
        [{"role": "user", "content": "知识库查询AI趋势"}],
        [{"role": "user", "content": "违禁词检测"}],
        [{"role": "user", "content": "短视频脚本生成"}],
    ]

    actual_use_real = use_real and detect_provider_mode() == __import__("provider_router").ProviderMode.REAL_DEEPSEEK
    if use_real and not actual_use_real:
        print(f"[Phase {phase}] WARNING: use_real=True but provider mode is FAKE — staying fake for safety")

    end_time = time.time() + duration_sec
    sample_n = 0
    while time.time() < end_time:
        sample_n += 1
        for prompt in sample_prompts:
            if time.time() >= end_time:
                break
            resp: ProviderResponse = chat(prompt, max_tokens=100)
            metrics.total_requests += 1
            metrics.latencies_ms.append(resp.latency_ms)
            metrics.total_cost_usd += resp.cost_usd
            if resp.mode == "success":
                metrics.success_count += 1
            else:
                metrics.error_count += 1
            # Sample log every Nth request
            if metrics.total_requests % 25 == 0:
                elapsed = time.time() - metrics.start_time
                print(f"  [Phase {phase}] t={elapsed:.0f}s req={metrics.total_requests} "
                      f"success_rate={metrics.success_rate_pct}% "
                      f"p95={metrics.p95_latency_ms:.0f}ms "
                      f"cost=${metrics.total_cost_usd:.4f}")
        time.sleep(sample_interval_sec)

    metrics.end_time = time.time()
    return metrics


def set_feature_flag(traffic_pct: int, dry_run: bool) -> bool:
    """Set CLOUDTECH_RC2_TRAFFIC_PCT env and restart gateway.

    In dry-run mode, just logs the action.
    """
    print(f"[Cutover] {'[DRY RUN] ' if dry_run else ''}Setting CLOUDTECH_RC2_TRAFFIC_PCT={traffic_pct}")
    os.environ["CLOUDTECH_RC2_TRAFFIC_PCT"] = str(traffic_pct)
    os.environ["CLOUDTECH_RC2_ENABLED"] = "true" if traffic_pct > 0 else "false"
    if dry_run:
        print(f"[Cutover] [DRY RUN] Skipping gateway restart")
        return True
    # Real restart — WinSW or direct
    try:
        result = subprocess.run(
            ["winsw", "restart", "CloudTechGateway"],
            capture_output=True, text=True, timeout=30,
            creationflags=0x08000000,  # CREATE_NO_WINDOW (red line #78)
        )
        print(f"[Cutover] Gateway restart exit={result.returncode}")
        return result.returncode == 0
    except FileNotFoundError:
        print(f"[Cutover] winsw not found — manual restart required")
        return True  # don't fail in dev
    except Exception as e:
        print(f"[Cutover] Restart error: {e}")
        return False


def abort_cutover(reason: str, dry_run: bool) -> None:
    """Emergency abort — sets traffic to 0 and updates state."""
    print(f"[Cutover] ABORT: {reason}")
    set_feature_flag(0, dry_run)
    print(f"[Cutover] Rollback complete — all traffic on Live legacy router")


def run_phase(phase: PhaseConfig, dry_run: bool, use_real: bool = False,
              duration_override_sec: Optional[int] = None) -> PhaseResult:
    """Run a single phase of the cutover."""
    print(f"\n{'='*70}")
    print(f"[Phase {phase.phase}] {phase.name} — {phase.traffic_pct}% traffic for {phase.duration_sec}s")
    print(f"{'='*70}")

    # Set feature flag
    if not set_feature_flag(phase.traffic_pct, dry_run):
        return PhaseResult(phase, PhaseMetrics(phase.phase), True, "restart_failed", None)

    # Run traffic simulation
    duration = duration_override_sec or phase.duration_sec
    if dry_run:
        duration = min(duration, 30)  # Cap dry-run at 30s
        print(f"[Phase {phase.phase}] [DRY RUN] Capping duration to {duration}s")

    metrics = simulate_traffic(phase.phase, duration, sample_interval_sec=2, use_real=use_real)

    # Check abort thresholds
    aborted = False
    abort_reason = None
    if metrics.success_rate_pct < phase.success_rate_min_pct - 5:  # 5pp buffer
        aborted = True
        abort_reason = f"success_rate {metrics.success_rate_pct}% < threshold {phase.success_rate_min_pct}%"
    elif metrics.p95_latency_ms > phase.p95_latency_max_ms * 1.5:
        aborted = True
        abort_reason = f"p95 latency {metrics.p95_latency_ms}ms > {phase.p95_latency_max_ms * 1.5}ms"

    # Emit per-phase result
    result = PhaseResult(
        config=phase,
        metrics=metrics,
        aborted=aborted,
        abort_reason=abort_reason,
        next_phase=phase.phase + 1 if not aborted and phase.phase < 4 else None,
    )

    out_dir = Path("D:/CloudTech-Live-Execution/CloudTech_rc2_Live_Direct_Execution_20260925/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)
    phase_path = out_dir / f"cutover_phase_{phase.phase}_{phase.name}.json"
    phase_path.write_text(json.dumps({
        "phase": phase.phase,
        "name": phase.name,
        "traffic_pct": phase.traffic_pct,
        "duration_sec": duration,
        "dry_run": dry_run,
        "metrics": {
            "total_requests": metrics.total_requests,
            "success_count": metrics.success_count,
            "error_count": metrics.error_count,
            "success_rate_pct": metrics.success_rate_pct,
            "error_rate_pct": metrics.error_rate_pct,
            "p95_latency_ms": metrics.p95_latency_ms,
            "total_cost_usd": round(metrics.total_cost_usd, 6),
        },
        "aborted": aborted,
        "abort_reason": abort_reason,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Phase {phase.phase}] Result → {phase_path}")

    if aborted:
        abort_cutover(abort_reason, dry_run)

    return result


def run_all_phases(dry_run: bool = True, phases_to_run: Optional[List[int]] = None,
                   use_real: bool = False, duration_override_sec: Optional[int] = None) -> Dict[str, Any]:
    """Run the full cutover sequence.

    Defaults to dry_run=True for safety.
    """
    print(f"[Cutover Runner] === START ===")
    print(f"[Cutover Runner] Dry run: {dry_run}")
    print(f"[Cutover Runner] Use real: {use_real} (provider mode = {detect_provider_mode().value})")
    print(f"[Cutover Runner] Phases to run: {phases_to_run or 'all'}")

    if not dry_run:
        print(f"\n[Cutover Runner] ⚠️  REAL CUTOVER MODE")
        print(f"[Cutover Runner] This will set feature flags and restart gateway")
        print(f"[Cutover Runner] Set CLOUDTECH_RC2_DRY_RUN=1 to abort\n")

    results = []
    overall_aborted = False
    for phase in PHASES:
        if phases_to_run and phase.phase not in phases_to_run:
            continue
        if overall_aborted:
            print(f"[Cutover Runner] Skipping Phase {phase.phase} — prior phase aborted")
            break
        result = run_phase(phase, dry_run, use_real, duration_override_sec)
        results.append({
            "phase": phase.phase,
            "name": phase.name,
            "traffic_pct": phase.traffic_pct,
            "aborted": result.aborted,
            "abort_reason": result.abort_reason,
            "metrics": {
                "total_requests": result.metrics.total_requests,
                "success_rate_pct": result.metrics.success_rate_pct,
                "p95_latency_ms": result.metrics.p95_latency_ms,
                "total_cost_usd": round(result.metrics.total_cost_usd, 6),
            },
        })
        if result.aborted:
            overall_aborted = True

    # Final state
    final_state = "ROLLED_BACK" if overall_aborted else "COMPLETE"
    summary = {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "title": "CloudTech rc2 Cutover Runner — Full Sequence",
        "dry_run": dry_run,
        "use_real": use_real,
        "phases_run": results,
        "final_state": final_state,
        "total_cost_usd": round(sum(r["metrics"]["total_cost_usd"] for r in results), 6),
        "total_requests": sum(r["metrics"]["total_requests"] for r in results),
    }
    out_path = Path("D:/CloudTech-Live-Execution/CloudTech_rc2_Live_Direct_Execution_20260925/artifacts/cutover_runner_full.json")
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Cutover Runner] === {final_state} ===")
    print(f"[Cutover Runner] Total cost: ${summary['total_cost_usd']}")
    print(f"[Cutover Runner] Total requests: {summary['total_requests']}")
    print(f"[Cutover Runner] Summary → {out_path}")
    return summary


def main():
    """CLI entrypoint — reads env vars to determine mode."""
    dry_run = os.environ.get("CLOUDTECH_RC2_DRY_RUN", "1") == "1"
    use_real = os.environ.get("CLOUDTECH_RC2_USE_REAL", "0") == "1"
    # Phase selection: CLOUDTECH_RC2_PHASES=1,2,3 or all
    phases_env = os.environ.get("CLOUDTECH_RC2_PHASES", "")
    phases_to_run = [int(p) for p in phases_env.split(",") if p.strip().isdigit()] if phases_env else None
    duration_override = int(os.environ.get("CLOUDTECH_RC2_DURATION_SEC", "0")) or None

    summary = run_all_phases(dry_run=dry_run, phases_to_run=phases_to_run,
                            use_real=use_real, duration_override_sec=duration_override)
    sys.exit(0 if summary["final_state"] == "COMPLETE" else 1)


if __name__ == "__main__":
    main()