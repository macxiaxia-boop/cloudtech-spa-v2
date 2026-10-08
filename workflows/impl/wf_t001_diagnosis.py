"""WF-T-001 企业营销业务诊断 — 装修业务
=====================================
输入: tenant_id, industry, target_revenue, current_revenue, sample_size
输出: diagnosis_score (0-100), gaps[], recommendations[], funnel_health
校验: validate_workflow_json/yaml against this input model
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from ..base import (
    RunHistoryTracker, run_workflow, validate_workflow_json, validate_workflow_yaml,
    INDUSTRIES, DECORATION_CITIES, WorkflowError,
)


class DiagnosisInput(BaseModel):
    tenant_id: str = Field(..., min_length=2, max_length=50, pattern=r"^zq-")
    industry: str = Field(..., pattern=r"^(decoration|medical|education|catering|retail)$")
    target_revenue: float = Field(..., gt=0)
    current_revenue: float = Field(default=0.0, ge=0)
    sample_size: int = Field(default=30, ge=1, le=500)
    cities: List[str] = Field(default_factory=list)
    workflow_id: str = Field(default="WF-T-001", pattern=r"^WF-T-\d{3}$")

    @field_validator("cities")
    @classmethod
    def cities_allowed(cls, v):
        for c in v:
            if c not in DECORATION_CITIES and not c.startswith("zq-"):
                # 允许任意 zq- 前缀的 mock 城市
                pass
        return v


class BusinessGap(BaseModel):
    area: str  # awareness/consideration/conversion/retention
    current: float
    gap: float
    priority: str  # P0/P1/P2


class DiagnosisOutput(BaseModel):
    diagnosis_score: float = Field(..., ge=0, le=100)
    funnel_health: str  # poor/fair/good/excellent
    gaps: List[BusinessGap]
    recommendations: List[str]
    revenue_gap_pct: float
    next_actions: List[str]


@run_workflow(workflow_id="WF-T-001", tenant_field="tenant_id")
def run_diagnosis(inp: DiagnosisInput) -> DiagnosisOutput:
    if inp.target_revenue <= 0:
        raise WorkflowError("WF-T001-VAL", "target_revenue 必须 > 0")
    rev_gap_pct = ((inp.target_revenue - inp.current_revenue) / inp.target_revenue) * 100
    if rev_gap_pct < 0:
        rev_gap_pct = 0.0

    # Mock scoring
    score = max(0.0, min(100.0, 100.0 - rev_gap_pct * 0.6 - (10 if inp.sample_size < 10 else 0)))

    gaps = [
        BusinessGap(area="awareness", current=0.15, gap=0.35, priority="P0" if rev_gap_pct > 40 else "P1"),
        BusinessGap(area="consideration", current=0.20, gap=0.30, priority="P1"),
        BusinessGap(area="conversion", current=0.05, gap=0.10, priority="P0" if rev_gap_pct > 30 else "P2"),
        BusinessGap(area="retention", current=0.40, gap=0.20, priority="P2"),
    ]
    recs = [
        "启用 WF-T-002 建立本地选题池 (覆盖 awareness gap)",
        "用 WF-T-003 集中生产脚本 (覆盖 consideration gap)",
        "开通 WF-T-007 漏斗看板监控转化率",
    ]
    funnel_health = "excellent" if score >= 85 else ("good" if score >= 70 else ("fair" if score >= 50 else "poor"))
    return DiagnosisOutput(
        diagnosis_score=round(score, 1),
        funnel_health=funnel_health,
        gaps=gaps,
        recommendations=recs,
        revenue_gap_pct=round(rev_gap_pct, 1),
        next_actions=recs[:2],
    )


# 暴露校验器
validate_json = lambda s: validate_workflow_json(s, DiagnosisInput)
validate_yaml = lambda s: validate_workflow_yaml(s, DiagnosisInput)