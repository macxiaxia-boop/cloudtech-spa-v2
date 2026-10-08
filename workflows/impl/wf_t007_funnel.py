"""WF-T-007 获客漏斗与周复盘 — 装修业务
=====================================
输入: tenant_id, week_start, funnel_data (impressions/clicks/leads/quotes/contracts)
输出: stage_metrics[], conversion_rates[], drop_off_alerts[], weekly_summary
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class FunnelData(BaseModel):
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    leads: int = Field(default=0, ge=0)
    quotes: int = Field(default=0, ge=0)
    contracts: int = Field(default=0, ge=0)


class FunnelInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    week_start: str  # ISO date YYYY-MM-DD
    current: FunnelData
    last_week: FunnelData = Field(default_factory=FunnelData)
    city: str = Field(default="厦门")
    workflow_id: str = Field(default="WF-T-007", pattern=r"^WF-T-\d{3}$")

    @field_validator("week_start")
    @classmethod
    def date_ok(cls, v):
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("week_start 必须是 YYYY-MM-DD")
        return v


class StageMetric(BaseModel):
    stage: str
    value: int
    conversion_rate: float  # 0-1
    week_over_week: float  # 百分比变化


class FunnelOutput(BaseModel):
    week_start: str
    stages: List[StageMetric]
    drop_off_alerts: List[str]
    weekly_summary: str
    overall_conversion: float  # impressions → contracts
    top_priority_action: str


def _safe_rate(num: int, denom: int) -> float:
    if denom <= 0:
        return 0.0
    return round(num / denom, 4)


def _safe_pct(curr: float, prev: float) -> float:
    if prev == 0:
        return 0.0 if curr == 0 else 100.0
    return round((curr - prev) / prev * 100.0, 1)


@run_workflow(workflow_id="WF-T-007", tenant_field="tenant_id")
def run_funnel(inp: FunnelInput) -> FunnelOutput:
    c = inp.current
    stages = [
        StageMetric(stage="impressions", value=c.impressions, conversion_rate=1.0,
                    week_over_week=_safe_pct(c.impressions, inp.last_week.impressions)),
        StageMetric(stage="clicks", value=c.clicks,
                    conversion_rate=_safe_rate(c.clicks, c.impressions),
                    week_over_week=_safe_pct(c.clicks, inp.last_week.clicks)),
        StageMetric(stage="leads", value=c.leads,
                    conversion_rate=_safe_rate(c.leads, c.clicks),
                    week_over_week=_safe_pct(c.leads, inp.last_week.leads)),
        StageMetric(stage="quotes", value=c.quotes,
                    conversion_rate=_safe_rate(c.quotes, c.leads),
                    week_over_week=_safe_pct(c.quotes, inp.last_week.quotes)),
        StageMetric(stage="contracts", value=c.contracts,
                    conversion_rate=_safe_rate(c.contracts, c.quotes),
                    week_over_week=_safe_pct(c.contracts, inp.last_week.contracts)),
    ]
    alerts: List[str] = []
    if stages[2].conversion_rate < 0.05:
        alerts.append(f"⚠️ 点击→线索 转化率仅 {stages[2].conversion_rate:.1%}, 行业基准 5-8%")
    if stages[4].conversion_rate < 0.2:
        alerts.append(f"⚠️ 报价→合同 转化率仅 {stages[4].conversion_rate:.1%}, 行业基准 20-30%")
    for s in stages:
        if s.week_over_week < -30.0:
            alerts.append(f"📉 {s.stage} 周环比 {s.week_over_week}%, 建议复盘")

    overall = _safe_rate(c.contracts, c.impressions)
    if not alerts:
        summary = f"周 {inp.week_start} 整体健康, 整体转化率 {overall:.2%}"
    else:
        summary = f"周 {inp.week_start} 有 {len(alerts)} 项告警, 整体转化率 {overall:.2%}"

    return FunnelOutput(
        week_start=inp.week_start,
        stages=stages,
        drop_off_alerts=alerts,
        weekly_summary=summary,
        overall_conversion=overall,
        top_priority_action=alerts[0] if alerts else "维持当前节奏, 重点扩量 awareness",
    )


validate_json = lambda s: validate_workflow_json(s, FunnelInput)
validate_yaml = lambda s: validate_workflow_yaml(s, FunnelInput)