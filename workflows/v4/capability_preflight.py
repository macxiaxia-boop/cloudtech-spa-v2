"""Read-only capability preflight for the SIX existing V4 workpaths.

Evidence level: static source contracts, never a live provider probe. An
installed package, stub or mock is NOT a verified integration. This module
does not execute any operation or touch network/filesystems.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from .contract import WorkPathDefinition
from .paths import FLAGSHIP_PATHS, get_path


# Audited from workflows/v4/registry.py and current adapters; keep conservative.
# LOCAL_IMPLEMENTED means this operation has a deterministic local code path,
# NOT that the whole business path is ready.
LOCAL_IMPLEMENTED: dict[str, str] = {
    "url.normalize": "workflows/v4/registry.py:url.normalize",
    "content.dedupe": "workflows/v4/registry.py:content.dedupe",
}
MOCK_ONLY: dict[str, str] = {
    "platform.permission_check": "adapters/platform/permission_gate.py",
    "platform.homepage_parse": "adapters/platform/homepage_parser.py",
    "transcript.extract": "adapters/transcribe/asr_engine.py",
    "video.frame_extract": "adapters/transcribe/frame_extractor.py",
    "content.structure.analyze": "adapters/content/structure_analyzer.py",
    "content.original_script.generate": "adapters/content/original_script_generator.py",
    "content.storyboard.generate": "adapters/content/director.py",
    "doubao.tts": "workflows/v4/registry.py:doubao.tts",
    "content.similarity.review": "adapters/content/similarity_qc.py",
    "export.zip": "workflows/v4/registry.py:export.zip",
}


def inspect_definition(defn: WorkPathDefinition) -> dict[str, Any]:
    """Return DAG shape and non-executable blockers, without calling adapters."""
    seen: set[str] = set()
    invalid: list[str] = []
    for step in defn.steps:
        if step.id in seen:
            invalid.append(f"duplicate node id: {step.id}")
        seen.add(step.id)

    prior: set[str] = set()
    nodes = []
    for step in defn.steps:
        if step.operation in LOCAL_IMPLEMENTED:
            status, evidence = "LOCAL_IMPLEMENTED", LOCAL_IMPLEMENTED[step.operation]
        elif step.operation in MOCK_ONLY:
            status, evidence = "MOCK_ONLY", MOCK_ONLY[step.operation]
        else:
            status, evidence = "ADAPTER_UNMAPPED", None
        missing = [dep for dep in step.requires if dep not in seen]
        if missing:
            invalid.append(f"{step.id} refers to missing node(s): {missing}")
        if step.id in step.requires:
            invalid.append(f"{step.id} depends on itself")
        prior.add(step.id)
        nodes.append({
            "id": step.id,
            "operation": step.operation,
            "requires": list(step.requires),
            "capability": status,
            "source_evidence": evidence,
            "cost_class": step.cost_class,
            "node_kind": step.node_kind,
            "checkpoint": step.checkpoint,
            "needs_provider_proof": status != "LOCAL_IMPLEMENTED",
            "blocked": status != "LOCAL_IMPLEMENTED" or bool(missing),
        })

    # Topological cycle detection even when every dependency ID exists.
    pending = {n["id"]: set(n["requires"]) for n in nodes}
    completed: set[str] = set()
    while pending:
        ready = {name for name, deps in pending.items() if deps <= completed}
        if not ready:
            invalid.append("cycle or unresolvable dependency graph")
            break
        completed |= ready
        for name in ready:
            del pending[name]

    counts = Counter(n["capability"] for n in nodes)
    is_ready = bool(nodes) and not invalid and all(
        n["capability"] == "LOCAL_IMPLEMENTED" for n in nodes
    )
    first_nodes = [
        n["id"] for n in nodes if not n["requires"] and
        n["capability"] == "LOCAL_IMPLEMENTED"
    ]
    return {
        "path_id": defn.id,
        "revision": defn.revision,
        "total_nodes": len(nodes),
        "execution_ready": is_ready,
        "level": "STATIC_SOURCE_PREFLIGHT_NOT_RUNTIME_VALIDATION",
        "checks": {
            "graph_valid": not bool(invalid),
            "errors": invalid,
            "local_implemented": counts["LOCAL_IMPLEMENTED"],
            "mock_only": counts["MOCK_ONLY"],
            "adapter_unmapped": counts["ADAPTER_UNMAPPED"],
        },
        "nodes": nodes,
        "safe_first_nodes": first_nodes,
        "reason": None if is_ready else "Path contains unverified/mock/missing operations or invalid dependencies",
    }


def inspect_path(path_id: str) -> dict[str, Any]:
    return inspect_definition(get_path(path_id))


def inspect_all_paths() -> dict[str, Any]:
    paths = [inspect_definition(defn) for defn in FLAGSHIP_PATHS.values()]
    return {
        "total_paths": len(paths),
        "execution_ready_paths": sum(p["execution_ready"] for p in paths),
        "total_nodes": sum(p["total_nodes"] for p in paths),
        "paths": paths,
    }
