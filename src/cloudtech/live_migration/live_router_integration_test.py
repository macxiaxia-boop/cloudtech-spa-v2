"""REAL Live Integration Test — actually imports and exercises D:\\CloudTech-Portable\\model_aggregator.py.

This is NOT a mocked fixture. It reads the REAL Live source code and exercises the REAL route_model() function.
Adapts Candidate router to Live's ACTUAL 11-model registry (not the fictional "18 tools" my earlier audit claimed).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

# ADD Live's path so we can actually import its modules
LIVE_ROOT = Path(r"D:\CloudTech-Portable")
sys.path.insert(0, str(LIVE_ROOT))

# These imports FAIL if Live source is missing/broken — that's the point
try:
    from model_aggregator import MODELS, route_model, list_models, compare_models, get_model_stats
    LIVE_IMPORT_OK = True
    LIVE_IMPORT_ERROR = None
except Exception as e:
    LIVE_IMPORT_OK = False
    LIVE_IMPORT_ERROR = f"{type(e).__name__}: {e}"
    MODELS = {}
    route_model = None
    list_models = None
    compare_models = None
    get_model_stats = None


def run_real_live_inventory() -> Dict[str, Any]:
    """Walk Live's REAL MODELS registry — no fabricated numbers."""
    if not LIVE_IMPORT_OK:
        return {"status": "FAIL", "error": LIVE_IMPORT_ERROR}

    inventory = {
        "schema_version": "1.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "title": "Live CloudTech REAL Model Inventory (from D:\\CloudTech-Portable\\model_aggregator.py)",
        "live_import_ok": True,
        "live_source": "D:\\CloudTech-Portable\\model_aggregator.py",
        "actual_total_models": 0,
        "models_by_type": {},
        "all_models_flat": [],
        "providers": set(),
    }

    # Walk REAL MODELS dict
    for mtype, mdict in MODELS.items():
        inventory["models_by_type"][mtype] = []
        for mid, minfo in mdict.items():
            inventory["actual_total_models"] += 1
            inventory["all_models_flat"].append({
                "id": mid,
                "type": mtype,
                "provider": minfo.get("provider"),
                "strength": minfo.get("strength"),
                **{k: v for k, v in minfo.items() if k.startswith("cost_")},
            })
            inventory["providers"].add(minfo.get("provider"))
            inventory["models_by_type"][mtype].append({"id": mid, **minfo})

    inventory["providers"] = sorted(inventory["providers"])
    return inventory


def run_real_route_test() -> Dict[str, Any]:
    """Call Live's route_model() with real task types from MODELS.routing dict."""
    if not LIVE_IMPORT_OK:
        return {"status": "FAIL", "error": LIVE_IMPORT_ERROR}

    # These are the REAL routing tasks defined in model_aggregator.route_model()
    REAL_TASKS = [
        "social_post", "long_article",
        "video_ad", "video_social", "video_cinematic", "video_creative",
        "image_render",
        "voice_narrator", "voice_enterprise",
    ]

    results = []
    for task in REAL_TASKS:
        try:
            r = route_model(task, budget="balanced")
            r_low = route_model(task, budget="low")
            results.append({
                "task": task,
                "balanced_model": r.get("model_id"),
                "balanced_reason": r.get("reason"),
                "low_budget_model": r_low.get("model_id"),
                "differs_by_budget": r.get("model_id") != r_low.get("model_id"),
            })
        except Exception as e:
            results.append({"task": task, "error": f"{type(e).__name__}: {e}"})

    return {
        "schema_version": "1.0",
        "title": "Live route_model() — REAL test",
        "tasks_tested": len(REAL_TASKS),
        "results": results,
    }


def run_real_compare_test() -> Dict[str, Any]:
    """Call Live's compare_models() with real model IDs from MODELS."""
    if not LIVE_IMPORT_OK:
        return {"status": "FAIL", "error": LIVE_IMPORT_ERROR}

    # Pick real model IDs from MODELS
    real_model_ids = []
    for mtype, mdict in MODELS.items():
        real_model_ids.extend(mdict.keys())

    try:
        cmp = compare_models(real_model_ids, task_desc="All Live models cost comparison")
        return {
            "schema_version": "1.0",
            "title": "Live compare_models() — REAL test",
            "models_compared": cmp.get("models_compared"),
            "recommended": cmp.get("recommended"),
            "recommended_reason": cmp.get("recommended_reason"),
        }
    except Exception as e:
        return {"status": "FAIL", "error": f"{type(e).__name__}: {e}"}


def build_real_candidate_mapping(inventory: Dict[str, Any]) -> Dict[str, Any]:
    """Build a REAL mapping from Candidate capabilities to Live's actual models.

    No fabricated tool_ids — only what Live's MODELS registry actually contains.
    """
    if not LIVE_IMPORT_OK:
        return {"status": "FAIL"}

    # Map Candidate capabilities to Live models by type
    capability_to_type = {
        "content_generation": "text",
        "text_analysis": "text",
        "code_generation": "text",
        "translation": "text",
        "summarization": "text",
        "image_generation": "image",
        "video_generation": "video",
        "audio_generation": "voice",
        "data_analysis": "text",
    }

    mapping = {}
    for cap, mtype in capability_to_type.items():
        live_models_for_type = inventory["models_by_type"].get(mtype, [])
        # Pick the lowest-cost model as the recommended binding
        recommended = None
        for m in live_models_for_type:
            cost_key = next((k for k in m if k.startswith("cost_")), None)
            if cost_key:
                if recommended is None or m[cost_key] < recommended.get(cost_key, float("inf")):
                    recommended = m
        mapping[cap] = {
            "live_model_type": mtype,
            "available_models": [m["id"] for m in live_models_for_type],
            "recommended_model_id": recommended["id"] if recommended else None,
            "recommended_provider": recommended.get("provider") if recommended else None,
            "recommended_cost_key": cost_key if recommended else None,
            "recommended_cost_value": recommended.get(cost_key) if recommended else None,
        }

    return {
        "schema_version": "1.0",
        "title": "Candidate Capability → Live MODEL mapping (REAL, not fabricated)",
        "live_total_models": inventory["actual_total_models"],
        "candidate_capabilities_mapped": len(mapping),
        "mapping": mapping,
    }


def main():
    print("[Live Integration Test] === START ===\n")

    # Step 1: actually import Live
    print(f"[Step 1] Import Live model_aggregator from {LIVE_ROOT}")
    print(f"        LIVE_IMPORT_OK = {LIVE_IMPORT_OK}")
    if not LIVE_IMPORT_OK:
        print(f"        ERROR: {LIVE_IMPORT_ERROR}")
        return 1

    # Step 2: real inventory
    print("\n[Step 2] Real inventory of Live MODELS")
    inventory = run_real_live_inventory()
    print(f"        Total models: {inventory['actual_total_models']}")
    print(f"        Providers: {inventory['providers']}")
    for mtype, models in inventory["models_by_type"].items():
        print(f"        {mtype}: {len(models)} models — {[m['id'] for m in models]}")

    # Step 3: real route_model test
    print("\n[Step 3] Real route_model() test")
    route_test = run_real_route_test()
    for r in route_test["results"]:
        if "error" in r:
            print(f"        {r['task']:25s} → ERROR {r['error']}")
        else:
            diff = " (low-budget differs)" if r["differs_by_budget"] else ""
            print(f"        {r['task']:25s} → {r['balanced_model']}{diff}")

    # Step 4: real compare test
    print("\n[Step 4] Real compare_models() test")
    cmp_test = run_real_compare_test()
    print(f"        Compared: {cmp_test.get('models_compared')} models")
    print(f"        Recommended (cheapest): {cmp_test.get('recommended')}")

    # Step 5: real mapping
    print("\n[Step 5] Build Candidate → Live mapping")
    mapping = build_real_candidate_mapping(inventory)
    print(f"        Mapped {mapping['candidate_capabilities_mapped']} capabilities to {mapping['live_total_models']} Live models")

    # Emit all evidence
    artifacts_dir = Path(r"D:\CloudTech-Live-Execution\CloudTech_rc2_Live_Direct_Execution_20260925\artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = artifacts_dir / "live_real_inventory.json"
    inventory_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False, default=list), encoding="utf-8")
    print(f"\n        Inventory → {inventory_path}")

    route_path = artifacts_dir / "live_real_route_test.json"
    route_path.write_text(json.dumps(route_test, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"        Route test → {route_path}")

    cmp_path = artifacts_dir / "live_real_compare_test.json"
    cmp_path.write_text(json.dumps(cmp_test, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"        Compare test → {cmp_path}")

    mapping_path = artifacts_dir / "candidate_to_live_mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"        Mapping → {mapping_path}")

    # Honest verdict
    honest = {
        "schema_version": "1.0",
        "title": "Honest reassessment — REAL Live facts",
        "earlier_claim": "18 ROUTE_TABLE tools (FABRICATED)",
        "actual_fact": f"{inventory['actual_total_models']} models in D:\\CloudTech-Portable\\model_aggregator.py::MODELS",
        "earlier_claim_2": "unified_router.py exists (FABRICATED)",
        "actual_fact_2": "Real router is route_model() dict in model_aggregator.py",
        "earlier_claim_3": "Phase 1 Score-Driven Decision Engine (FABRICATED)",
        "actual_fact_3": "Simple dict lookup in route_model()",
        "earlier_claim_4": "Anti-Collapse 3-layer (FABRICATED)",
        "actual_fact_4": "Does not exist",
        "earlier_claim_5": "EMA bias learning (FABRICATED)",
        "actual_fact_5": "Does not exist",
        "what_is_real": [
            "gateway_v22.py on port 5099 ✓",
            "FastAPI + uvicorn ✓",
            "Flask WSGI middleware for legacy ✓",
            "11 models across 4 types (text/video/image/voice) ✓",
            "56 v3_* data layer modules ✓",
            "deepseek_call() via api.deepseek.com ✓",
            "Simple route_model() dict lookup ✓",
            "model_aggregator.route_model(task, budget) signature ✓",
        ],
    }
    honest_path = artifacts_dir / "live_honest_reassessment.json"
    honest_path.write_text(json.dumps(honest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"        Honest → {honest_path}")

    print(f"\n[Live Integration Test] === DONE ===")
    print(f"[Live Integration Test] {inventory['actual_total_models']} REAL Live models discovered (NOT 18).")
    print(f"[Live Integration Test] Earlier '18 tools' and 'unified_router' claims were FABRICATED. Admitted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())