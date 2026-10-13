"""V4 — Typed WorkPath Contract 校验
按 V4 spec §04 + §08 typed contract 定义:
  id, revision, title, domain, goal, triggers[], preconditions[], inputs[{role,mime,min,max}],
  planner, steps[{id,operation,requires,produces,condition,retries,checkpoint,cost_class}],
  quality_gates[], exported_artifacts[], recovery, privacy, permissions, billing_policy, evidence
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class InputSpec:
    role: str
    mime: str
    min: int = 1
    max: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "mime": self.mime, "min": self.min, "max": self.max}


@dataclass
class StepSpec:
    id: str
    operation: str
    requires: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    retries: int = 3
    checkpoint: Optional[str] = None
    cost_class: str = "FREE_LOCAL"
    node_kind: str = "TRANSFORM"


@dataclass
class WorkPathDefinition:
    id: str
    revision: int
    title: str
    domain: str
    goal: str
    triggers: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    inputs: List[InputSpec] = field(default_factory=list)
    planner: str = "default"
    steps: List[StepSpec] = field(default_factory=list)
    quality_gates: List[str] = field(default_factory=list)
    exported_artifacts: List[str] = field(default_factory=list)
    recovery: Dict[str, Any] = field(default_factory=dict)
    privacy: str = "public"
    permissions: List[str] = field(default_factory=list)
    billing_policy: str = "FREE_LOCAL"
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "revision": self.revision,
            "title": self.title,
            "domain": self.domain,
            "goal": self.goal,
            "triggers": self.triggers,
            "preconditions": self.preconditions,
            "inputs": [i.to_dict() for i in self.inputs],
            "planner": self.planner,
            "steps": [s.__dict__ for s in self.steps],
            "quality_gates": self.quality_gates,
            "exported_artifacts": self.exported_artifacts,
            "recovery": self.recovery,
            "privacy": self.privacy,
            "permissions": self.permissions,
            "billing_policy": self.billing_policy,
            "evidence": self.evidence,
        }


class ContractError(Exception):
    pass


def validate_definition(def_dict: Dict[str, Any]) -> WorkPathDefinition:
    """dict → WorkPathDefinition; 字段缺失 raise ContractError"""
    required = {"id", "revision", "title", "domain", "goal"}
    missing = required - set(def_dict.keys())
    if missing:
        raise ContractError(f"[C-001] 缺字段: {sorted(missing)}")
    inputs = [
        InputSpec(**i) if isinstance(i, dict) else i
        for i in def_dict.get("inputs", [])
    ]
    steps = [
        StepSpec(**s) if isinstance(s, dict) else s
        for s in def_dict.get("steps", [])
    ]
    return WorkPathDefinition(
        id=def_dict["id"],
        revision=int(def_dict["revision"]),
        title=def_dict["title"],
        domain=def_dict["domain"],
        goal=def_dict["goal"],
        triggers=def_dict.get("triggers", []),
        preconditions=def_dict.get("preconditions", []),
        inputs=inputs,
        planner=def_dict.get("planner", "default"),
        steps=steps,
        quality_gates=def_dict.get("quality_gates", []),
        exported_artifacts=def_dict.get("exported_artifacts", []),
        recovery=def_dict.get("recovery", {}),
        privacy=def_dict.get("privacy", "public"),
        permissions=def_dict.get("permissions", []),
        billing_policy=def_dict.get("billing_policy", "FREE_LOCAL"),
        evidence=def_dict.get("evidence", {}),
    )


def validate_inputs(defn: WorkPathDefinition, provided: Dict[str, Any]) -> List[str]:
    """校验 provided inputs 是否满足 min/max; 返回缺哪些 role"""
    role_counts: Dict[str, int] = {}
    for k, v in provided.items():
        role_counts[k] = role_counts.get(k, 0) + (1 if isinstance(v, list) else 1)
    missing: List[str] = []
    for spec in defn.inputs:
        got = role_counts.get(spec.role, 0)
        if got < spec.min:
            missing.append(f"{spec.role}(need>={spec.min}, got={got})")
    return missing
