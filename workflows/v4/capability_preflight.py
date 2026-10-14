"""Conservative V4 workpath discovery from existing source definitions.

Read-only, no provider requests, no mock promoted to a business capability.
The legacy six flagship workpaths have NOT been integrated end-to-end.
Three user-supplied local transformations are explicitly distinguished.
"""
from __future__ import annotations

from typing import Any

from .paths import ALL_PATHS, get_path


def inspect_path(path_id: str) -> dict[str, Any]:
    definition = get_path(path_id)
    local_article = path_id == "WP-LOCAL-ARTICLE-EXTRACT"
    local_subtitle = path_id == "WP-LOCAL-SUBTITLE-EXPORT"
    local_analysis = path_id == "WP-LOCAL-ARTICLE-ANALYZE"
    steps = [
        {
            "id": step.id,
            "operation": step.operation,
            "requires": list(step.requires),
            "node_kind": step.node_kind,
            "cost_class": step.cost_class,
            "capability": (
                "USER_SUPPLIED_LOCAL_HTML" if local_article
                else "USER_SUPPLIED_LOCAL_TWO_NODE_ANALYSIS" if local_analysis
                else "USER_SUPPLIED_LOCAL_SUBTITLE_REQUIRES_WORKER" if local_subtitle
                else "ADAPTER_OR_PROVIDER_NOT_INDEPENDENTLY_VERIFIED"
            ),
            "verified_business_output": False,
        }
        for step in definition.steps
    ]
    return {
        "path_id": definition.id,
        "revision": definition.revision,
        "title": definition.title,
        "total_nodes": len(steps),
        "nodes": steps,
        "level": "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION",
        "execution_ready": False,  # only runtime + evidence may grant this
        "local_sync_supported": local_article,
        "local_worker_supported": local_subtitle or local_analysis,
        "business_validated": False,
        "requires_provider_auth": not (local_article or local_subtitle or local_analysis),
        "notice": (
            "User supplied HTML only; no web crawl, model or payment."
            if local_article else
            "Two actual deterministic stages: supplied HTML parse and lexical analysis. No AI."
            if local_analysis else
            "Provided transcript/subtitles only; does not perform ASR."
            if local_subtitle else
            "The declared DAG includes unverified adapter/provider operations."
        ),
    }


def inspect_all_paths() -> dict[str, Any]:
    paths = [inspect_path(pid) for pid in ALL_PATHS]
    return {
        "total_paths": len(paths),
        "execution_ready_paths": 0,
        "total_nodes": sum(p["total_nodes"] for p in paths),
        "paths": paths,
        "level": "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION",
    }
