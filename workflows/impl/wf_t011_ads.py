"""WF-T-011 广告只读复盘与预算建议 — 装修业务
============================================
输入: tenant_id, campaigns[] (含 spend/impressions/clicks/cv), budget_total
输出: roi_by_campaign[], recommendations[], budget_reallocation{}
只读: 禁止任何实际写操作 (CAPI/Pixel/广告平台), 仅复盘 + 建议
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class AdCampaign(BaseModel):
    campaign_id: str
    name: str
    platform: str = "douyin"
    spend: float = Field(..., ge=0)
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    revenue: float = Field(default=0, ge=0)

    @field_validator("platform")
    @classmethod
    def p_ok(cls, v):
        if v not in ("douyin", "xiaohongshu", "tencent", "kuaishou", "baidu"):
            raise ValueError("platform ∈ {douyin, xiaohongshu, tencent, kuaishou, baidu}")
        return v


class AdsInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    campaigns: List[AdCampaign] = Field(..., min_length=1, max_length=100)
    budget_total: float = Field(..., ge=0)
    target_roi: float = Field(default=2.0, ge=0.5)
    workflow_id: str = Field(default="WF-T-011", pattern=r"^WF-T-\d{3}$")


class ROIRow(BaseModel):
    campaign_id: str
    name: str
    spend: float
    roi: float
    cpa: float
    verdict: str  # scale/hold/pause


class AdsOutput(BaseModel):
    total_spend: float
    total_revenue: float
    blended_roi: float
    roi_by_campaign: List[ROIRow]
    recommendations: List[str]
    budget_reallocation: dict


@run_workflow(workflow_id="WF-T-011", tenant_field="tenant_id")
def run_ads(inp: AdsInput) -> AdsOutput:
    if inp.budget_total <= 0:
        raise WorkflowError("WF-T011-BUDGET", "budget_total 必须 > 0")
    if not inp.campaigns:
        raise WorkflowError("WF-T011-CAMP", "campaigns 不能为空")

    rows: List[ROIRow] = []
    total_spend = 0.0
    total_revenue = 0.0
    candidates = []  # (roi, name)
    for c in inp.campaigns:
        total_spend += c.spend
        total_revenue += c.revenue
        roi = (c.revenue / c.spend) if c.spend > 0 else 0.0
        cpa = (c.spend / c.conversions) if c.conversions > 0 else 0.0
        if roi >= inp.target_roi:
            verdict = "scale"
            candidates.append((roi, c.campaign_id, c.name, c.spend))
        elif roi >= inp.target_roi * 0.5:
            verdict = "hold"
        else:
            verdict = "pause"
        rows.append(ROIRow(
            campaign_id=c.campaign_id, name=c.name,
            spend=round(c.spend, 2), roi=round(roi, 2),
            cpa=round(cpa, 2), verdict=verdict,
        ))

    blended = (total_revenue / total_spend) if total_spend > 0 else 0.0
    recs = [f"整体 ROI {blended:.2f} (目标 {inp.target_roi})"]

    # 预算重分配 (简单: 把暂停的预算挪给 scale)
    paused_spend = sum(c.spend for c in inp.campaigns if (c.revenue / c.spend if c.spend else 0) < inp.target_roi * 0.5)
    scale_pool = sum(c.spend for c in inp.campaigns if (c.revenue / c.spend if c.spend else 0) >= inp.target_roi)
    realloc = {
        "from_paused_pool": round(paused_spend, 2),
        "to_scale_pool": round(scale_pool + paused_spend * 0.5, 2),
        "keep_buffer": round(paused_spend * 0.5, 2),
    }
    if blended < inp.target_roi:
        recs.append("整体 ROI 低于目标, 建议先优化转化率再扩量")
    if paused_spend > inp.budget_total * 0.3:
        recs.append(f"暂停池 {paused_spend} 占总预算 {paused_spend/inp.budget_total:.1%}, 立即重定向")

    return AdsOutput(
        total_spend=round(total_spend, 2),
        total_revenue=round(total_revenue, 2),
        blended_roi=round(blended, 2),
        roi_by_campaign=rows,
        recommendations=recs,
        budget_reallocation=realloc,
    )


validate_json = lambda s: validate_workflow_json(s, AdsInput)
validate_yaml = lambda s: validate_workflow_yaml(s, AdsInput)