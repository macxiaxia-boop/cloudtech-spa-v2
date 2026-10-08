"""WF-T-008 实验对照与 SOP 候选 — 装修业务
========================================
输入: tenant_id, experiments[] (含 hypothesis, variant_a, variant_b, sample_size, metric)
输出: experiment_results[], sop_candidates[]
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class Experiment(BaseModel):
    name: str
    hypothesis: str
    variant_a: str
    variant_b: str
    sample_size: int = Field(..., ge=1, le=10000)
    metric_a: float = Field(..., ge=0)
    metric_b: float = Field(..., ge=0)
    duration_days: int = Field(default=14, ge=1, le=90)
    confidence: float = Field(default=0.95, ge=0.5, le=0.99)


class ExperimentInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    experiments: List[Experiment] = Field(..., min_length=1, max_length=20)
    workflow_id: str = Field(default="WF-T-008", pattern=r"^WF-T-\d{3}$")


class ExperimentResult(BaseModel):
    name: str
    winner: str  # A/B/inconclusive
    lift_pct: float
    p_value_estimate: float
    sample_adequate: bool
    recommendation: str


class SOPCandidate(BaseModel):
    title: str
    source_experiment: str
    confidence: str  # low/medium/high
    body: str


class ExperimentOutput(BaseModel):
    total: int
    results: List[ExperimentResult]
    sop_candidates: List[SOPCandidate]


def _significance_estimate(a: float, b: float, n: int) -> float:
    """简化版: 基于差距与样本量估 p_value 上界 (无第三方库)"""
    if a + b == 0:
        return 1.0
    diff = abs(a - b)
    avg = (a + b) / 2
    if avg == 0:
        return 1.0
    rel = diff / avg
    # 简化: rel * sqrt(n) 越大, p 越小
    import math
    score = rel * math.sqrt(max(n, 1))
    if score >= 3.0:
        return 0.001
    if score >= 2.0:
        return 0.01
    if score >= 1.0:
        return 0.05
    return 0.2


@run_workflow(workflow_id="WF-T-008", tenant_field="tenant_id")
def run_experiment(inp: ExperimentInput) -> ExperimentOutput:
    if not inp.experiments:
        raise WorkflowError("WF-T008-EMPTY", "experiments 不能为空")

    results: List[ExperimentResult] = []
    sop_candidates: List[SOPCandidate] = []

    for e in inp.experiments:
        p = _significance_estimate(e.metric_a, e.metric_b, e.sample_size)
        adequate = e.sample_size >= 100
        if not adequate:
            winner = "inconclusive"
            rec = "样本不足, 延长实验"
            lift = 0.0
        elif p < (1 - e.confidence):
            if e.metric_b > e.metric_a:
                winner = "B"
                lift = ((e.metric_b - e.metric_a) / e.metric_a * 100) if e.metric_a else 100.0
                rec = f"采纳 B 方案 (lift {lift:.1f}%)"
            else:
                winner = "A"
                lift = ((e.metric_a - e.metric_b) / e.metric_b * 100) if e.metric_b else 100.0
                rec = f"采纳 A 方案 (lift {lift:.1f}%)"
            sop_title = f"SOP: {e.variant_b if winner == 'B' else e.variant_a} 标准化"
            sop_body = f"假设: {e.hypothesis}\n采纳: {winner}\n样本: {e.sample_size}\n结论: {rec}"
            confidence = "high" if p < 0.01 else "medium"
            sop_candidates.append(SOPCandidate(
                title=sop_title,
                source_experiment=e.name,
                confidence=confidence,
                body=sop_body,
            ))
        else:
            winner = "inconclusive"
            lift = ((e.metric_b - e.metric_a) / e.metric_a * 100) if e.metric_a else 0.0
            rec = "差距不显著, 继续实验"

        results.append(ExperimentResult(
            name=e.name,
            winner=winner,
            lift_pct=round(lift, 1),
            p_value_estimate=p,
            sample_adequate=adequate,
            recommendation=rec,
        ))

    return ExperimentOutput(
        total=len(results),
        results=results,
        sop_candidates=sop_candidates,
    )


validate_json = lambda s: validate_workflow_json(s, ExperimentInput)
validate_yaml = lambda s: validate_workflow_yaml(s, ExperimentInput)