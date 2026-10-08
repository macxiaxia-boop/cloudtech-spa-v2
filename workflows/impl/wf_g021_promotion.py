"""WF-G-021 SOP 候选受控晋升 — 通用
=================================
输入: tenant_id, candidates[] (含 title, source, confidence, evidence_count), promotion_threshold
输出: promoted[], on_hold[], rejected[], audit[]
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class SOPCandidate(BaseModel):
    sid: str
    title: str = Field(..., min_length=2)
    source: str  # experiment_id / observation_id
    confidence: str  # low/medium/high
    evidence_count: int = Field(default=1, ge=1)
    target_sop: str = Field(default="production")

    @field_validator("confidence")
    @classmethod
    def c_ok(cls, v):
        if v not in ("low", "medium", "high"):
            raise ValueError("confidence ∈ {low, medium, high}")
        return v


class PromotionInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    candidates: List[SOPCandidate] = Field(..., min_length=1, max_length=100)
    promotion_threshold: str = Field(default="high")
    workflow_id: str = Field(default="WF-G-021", pattern=r"^WF-G-\d{3}$")


_RANK = {"low": 0, "medium": 1, "high": 2}


class PromotionDecision(BaseModel):
    sid: str
    title: str
    decision: str  # promoted/on_hold/rejected
    reason: str


class PromotionOutput(BaseModel):
    promoted: List[str]
    on_hold: List[str]
    rejected: List[str]
    audit: List[PromotionDecision]


@run_workflow(workflow_id="WF-G-021", tenant_field="tenant_id")
def run_promotion(inp: PromotionInput) -> PromotionOutput:
    threshold = _RANK.get(inp.promotion_threshold, 2)
    promoted: List[str] = []
    on_hold: List[str] = []
    rejected: List[str] = []
    audit: List[PromotionDecision] = []
    for c in inp.candidates:
        rank = _RANK[c.confidence]
        if rank >= threshold and c.evidence_count >= 3:
            promoted.append(c.sid)
            audit.append(PromotionDecision(sid=c.sid, title=c.title, decision="promoted",
                                           reason=f"{c.confidence}+{c.evidence_count} 证据, 满足阈值"))
        elif rank >= threshold:
            on_hold.append(c.sid)
            audit.append(PromotionDecision(sid=c.sid, title=c.title, decision="on_hold",
                                           reason=f"高置信但证据仅 {c.evidence_count}, 继续收集"))
        else:
            rejected.append(c.title)
            audit.append(PromotionDecision(sid=c.sid, title=c.title, decision="rejected",
                                           reason=f"置信度 {c.confidence} 低于阈值"))
    return PromotionOutput(promoted=promoted, on_hold=on_hold, rejected=rejected, audit=audit)


validate_json = lambda s: validate_workflow_json(s, PromotionInput)
validate_yaml = lambda s: validate_workflow_yaml(s, PromotionInput)