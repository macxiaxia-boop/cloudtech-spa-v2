"""CloudTech Live startup bootstrap — feature-flagged QualityAwareRouter injection.

Per Option A (user authorized 2026-09-25): add parallel routing path WITHOUT
modifying Live sealed core (gateway_v22.py / model_aggregator.py / fastapi_app.py).

How it works:
- This script is the NEW entry point (replaces `uvicorn gateway_v22:app`)
- If CLOUDTECH_RC2_USE_QUALITY_AWARE=1, monkey-patches model_aggregator.route_model
  to dispatch through QualityAwareRouter when available
- Otherwise, runs Live's gateway unchanged
- Live sealed core files are NOT touched — only new files in src/cloudtech/live_migration/

Usage:
    # Default (Live behavior unchanged):
    python -m cloudtech.live_migration.start_cloudtech

    # Enable QualityAwareRouter (parallel path):
    CLOUDTECH_RC2_USE_QUALITY_AWARE=1 python -m cloudtech.live_migration.start_cloudtech

    # Or with explicit port:
    CLOUDTECH_RC2_USE_QUALITY_AWARE=1 python -m cloudtech.live_migration.start_cloudtech --port 5099
"""
from __future__ import annotations

import os
import sys
import argparse
import logging
from pathlib import Path

# Ensure Live root is on sys.path so we can import gateway_v22 and model_aggregator
LIVE_ROOT = Path(r"D:\CloudTech-Portable")
if str(LIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(LIVE_ROOT))

# Ensure our package is on sys.path
PKG_ROOT = Path(__file__).parent
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("cloudtech.bootstrap")


def apply_quality_aware_patch() -> bool:
    """If feature flag is set, monkey-patch model_aggregator.route_model.

    Returns True if patch was applied, False otherwise.
    """
    if os.environ.get("CLOUDTECH_RC2_USE_QUALITY_AWARE") != "1":
        log.info("[bootstrap] CLOUDTECH_RC2_USE_QUALITY_AWARE != 1 → Live sealed core unchanged")
        return False

    try:
        import model_aggregator
        from quality_aware_router import QualityAwareRouter
    except ImportError as e:
        log.error(f"[bootstrap] Cannot apply patch: {e}")
        return False

    # Save original for diagnostics
    _original_route_model = model_aggregator.route_model

    def _patched_route_model(task: str, budget: str = "balanced") -> dict:
        """Patched route_model — uses QualityAwareRouter.

        Live signature preserved: route_model(task, budget) → dict with model_id, reason.
        """
        try:
            router = QualityAwareRouter()
            decision = router.route(task)
            chosen = decision.chosen_tool.live_model_id
            # Find the model details from Live's MODELS dict
            for t, mdict in model_aggregator.MODELS.items():
                if chosen in mdict:
                    return {
                        "task": task,
                        "model_id": chosen,
                        "model": mdict[chosen],
                        "reason": f"[QUALITY_AWARE_V2] task={task}, q-weighted",
                    }
            # Fallback to original if chosen not found
            return _original_route_model(task, budget)
        except Exception as e:
            log.warning(f"[bootstrap] QualityAwareRouter failed for task={task}: {e}; falling back to original")
            return _original_route_model(task, budget)

    model_aggregator.route_model = _patched_route_model
    log.info("[bootstrap] ✅ Monkey-patched model_aggregator.route_model → QualityAwareRouter (parallel path)")
    log.info(f"[bootstrap]    Original kept as _original_route_model for fallback")
    return True


def main():
    parser = argparse.ArgumentParser(description="CloudTech Live startup bootstrap")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5099)
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    patched = apply_quality_aware_patch()

    # Install observability dashboard (only if QualityAwareRouter is enabled)
    if patched:
        try:
            from observability_dashboard import install_dashboard
            log.info("[bootstrap] installing observability dashboard...")
            install_dashboard()
        except ImportError as ie:
            log.warning(f"[bootstrap] observability_dashboard not found ({ie}); continuing without it")
        except Exception as ex:
            log.warning(f"[bootstrap] observability_dashboard install failed: {type(ex).__name__}: {ex}")

    # Now import and run Live's gateway (sealed core untouched)
    import uvicorn
    log.info(f"[bootstrap] Starting Live gateway_v22 on {args.host}:{args.port}")
    log.info(f"[bootstrap] QualityAwareRouter: {'ENABLED' if patched else 'disabled (Live default)'}")
    uvicorn.run(
        "gateway_v22:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()