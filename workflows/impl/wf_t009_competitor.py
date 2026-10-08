"""WF-T-009 同城竞品观察 — 装修业务
==================================
输入: tenant_id, cities, competitors[] (公司名/平台账号/最近更新), lookback_days
输出: signals[] (含 type:launch/content/promo/closure), threat_level, opportunities[]
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError, PLATFORMS_T


class Competitor(BaseModel):
    company: str = Field(..., min_length=1)
    platforms: List[str] = Field(default_factory=list)
    last_update_days: int = Field(default=0, ge=0, le=365)
    estimated_followers: int = Field(default=0, ge=0)
    notes: str = Field(default="")


class CompetitorInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    cities: List[str] = Field(..., min_length=1, max_length=10)
    competitors: List[Competitor] = Field(..., min_length=1, max_length=50)
    lookback_days: int = Field(default=14, ge=1, le=90)
    workflow_id: str = Field(default="WF-T-009", pattern=r"^WF-T-\d{3}$")


class CompetitorSignal(BaseModel):
    company: str
    city: str
    type: str  # launch/content/promo/closure/inactive
    severity: str  # info/low/medium/high
    note: str


class CompetitorOutput(BaseModel):
    total_signals: int
    threat_level: str  # low/medium/high
    signals: List[CompetitorSignal]
    opportunities: List[str]


@run_workflow(workflow_id="WF-T-009", tenant_field="tenant_id")
def run_competitors(inp: CompetitorInput) -> CompetitorOutput:
    if not inp.cities:
        raise WorkflowError("WF-T009-CITY", "cities 不能为空")
    if not inp.competitors:
        raise WorkflowError("WF-T009-COMP", "competitors 不能为空")

    signals: List[CompetitorSignal] = []
    high_threat = 0
    opportunities: List[str] = []
    for c in inp.competitors:
        city = inp.cities[0] if inp.cities else "未知"
        if c.last_update_days > inp.lookback_days:
            signals.append(CompetitorSignal(
                company=c.company, city=city, type="inactive",
                severity="info", note=f"已 {c.last_update_days} 天未更新",
            ))
        elif c.last_update_days <= 2:
            signals.append(CompetitorSignal(
                company=c.company, city=city, type="launch",
                severity="high", note="近期高密度更新 (疑似新策略/活动)",
            ))
            high_threat += 1
        elif "促销" in c.notes or "折扣" in c.notes:
            signals.append(CompetitorSignal(
                company=c.company, city=city, type="promo",
                severity="medium", note="近期有促销动作",
            ))
        else:
            signals.append(CompetitorSignal(
                company=c.company, city=city, type="content",
                severity="low", note="常规更新",
            ))

        if c.estimated_followers < 1000:
            opportunities.append(f"跟进 {c.company} — 流量较小, 我方可补位")

    threat_level = "high" if high_threat >= 2 else ("medium" if high_threat == 1 else "low")
    return CompetitorOutput(
        total_signals=len(signals),
        threat_level=threat_level,
        signals=signals,
        opportunities=opportunities,
    )


validate_json = lambda s: validate_workflow_json(s, CompetitorInput)
validate_yaml = lambda s: validate_workflow_yaml(s, CompetitorInput)