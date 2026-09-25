"""Wave 2 REVISED: Shadow Adapter — compares Candidate router vs Live's REAL route_model().

v1.0 used fabricated fixtures. v1.1 uses:
- Live's REAL routing tasks from model_aggregator.route_model()
- Live's REAL MODELS registry
- Side-by-side comparison: Candidate router vs Live's route_model()
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(r"D:\CloudTech-Portable")))

from router_v2 import RouterV2, Capability  # type: ignore
from quality_aware_router import QualityAwareRouter  # type: ignore
try:
    from model_aggregator import route_model, MODELS as LIVE_MODELS
    LIVE_IMPORT_OK = True
except Exception as e:
    LIVE_IMPORT_OK = False
    LIVE_IMPORT_ERROR = f"{type(e).__name__}: {e}"


# REAL Live routing tasks — taken from model_aggregator.route_model() source
REAL_LIVE_TASKS = [
    "social_post", "long_article",
    "video_ad", "video_social", "video_cinematic", "video_creative",
    "image_render",
    "voice_narrator", "voice_enterprise",
]


def run_real_shadow_comparison() -> Dict[str, Any]:
    """Run BOTH routers on REAL Live tasks and compare."""
    if not LIVE_IMPORT_OK:
        return {"status": "FAIL", "error": LIVE_IMPORT_ERROR}

    candidate_router = QualityAwareRouter()

    comparisons = []
    for task in REAL_LIVE_TASKS:
        # Live's actual choice
        live_route = route_model(task, budget="balanced")
        live_model_id = live_route.get("model_id")

        # Candidate router's choice (using task name as input)
        candidate_decision = candidate_router.route(task)
        candidate_model_id = candidate_decision.chosen_tool.live_model_id

        # Comparison
        match = live_model_id == candidate_model_id
        comparisons.append({
            "task": task,
            "live_model": live_model_id,
            "candidate_model": candidate_model_id,
            "live_reason": live_route.get("reason"),
            "candidate_capability": candidate_decision.capability.value,
            "candidate_score": candidate_decision.final_score,
            "match": match,
            "match_type": "exact" if match else "divergent",
        })

    # Aggregate
    n = len(comparisons)
    n_match = sum(1 for c in comparisons if c["match"])
    n_divergent = n - n_match

    return {
        "schema_version": "1.1",
        "title": "Wave 2 Shadow v1.1 — REAL Live route_model vs Candidate router",
        "live_source": "D:\\CloudTech-Portable\\model_aggregator.py::route_model",
        "candidate_source": "D:\\CloudTech-Live-Execution\\CloudTech_rc2_Live_Direct_Execution_20260925\\src\\cloudtech\\live_migration\\router_v2.py::RouterV2",
        "tasks_tested": n,
        "matches": n_match,
        "divergences": n_divergent,
        "match_rate_pct": round(100.0 * n_match / n, 2),
        "divergence_rate_pct": round(100.0 * n_divergent / n, 2),
        "comparisons": comparisons,
        "analysis": {
            "exact_matches": [c["task"] for c in comparisons if c["match"]],
            "divergences": [
                {"task": c["task"], "live": c["live_model"], "candidate": c["candidate_model"]}
                for c in comparisons if not c["match"]
            ],
        },
        "note": "v1.0 used fabricated 110 fixtures. v1.1 uses 9 REAL Live routing tasks from model_aggregator.route_model().",
    }


def main():
    print("[Wave 2 v1.1] Shadow Adapter — REAL Live vs Candidate comparison\n")

    if not LIVE_IMPORT_OK:
        print(f"[Wave 2] FATAL: Cannot import Live: {LIVE_IMPORT_ERROR}")
        return 1

    print(f"[Step 1] Import Live route_model from D:\\CloudTech-Portable\\model_aggregator.py")
    print(f"        LIVE_MODELS has {sum(len(m) for m in LIVE_MODELS.values())} models across {len(LIVE_MODELS)} types")
    print(f"        Live routing tasks: {len(REAL_LIVE_TASKS)}")

    print(f"\n[Step 2] Run both routers side-by-side")
    result = run_real_shadow_comparison()

    print(f"\n[Step 3] Comparison results:")
    print(f"  Total tasks: {result['tasks_tested']}")
    print(f"  Matches: {result['matches']} ({result['match_rate_pct']}%)")
    print(f"  Divergences: {result['divergences']} ({result['divergence_rate_pct']}%)")

    print(f"\n  Per-task:")
    for c in result["comparisons"]:
        marker = "✓" if c["match"] else "✗"
        print(f"    {marker} {c['task']:20s} live={c['live_model']:20s} candidate={c['candidate_model']:20s}")

    print(f"\n  Analysis:")
    print(f"    Exact matches: {result['analysis']['exact_matches']}")
    print(f"    Divergences:")
    for d in result["analysis"]["divergences"]:
        print(f"      - {d['task']}: Live={d['live']}  vs  Candidate={d['candidate']}")

    # Emit evidence
    output_path = Path(r"D:\CloudTech-Live-Execution\CloudTech_rc2_Live_Direct_Execution_20260925\artifacts\wave2_shadow_diff_v1_1.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[Wave 2] Emitted: {output_path}")

    print(f"\n[Wave 2] === CONCLUSION ===")
    print(f"  Candidate router DIVERGES from Live route_model on {result['divergences']}/{result['tasks_tested']} tasks")
    print(f"  This is HONEST evidence — not '0.91% mismatch' on fake fixtures")
    print(f"  Divergences show Candidate's cost-based picks differ from Live's hardcoded picks")
    return 0


if __name__ == "__main__":
    sys.exit(main())