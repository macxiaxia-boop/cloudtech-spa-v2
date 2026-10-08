"""WF-T-012 客户问题归类与报价辅助 — 装修业务
===========================================
输入: tenant_id, questions[] (含 content + intent), pricing_config
输出: categorized[] (type/urgency/answer_hint), quote_drafts[]
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class CustomerQuestion(BaseModel):
    qid: str
    content: str = Field(..., min_length=2)
    city: str = Field(default="厦门")
    declared_intent: str = Field(default="unknown")  # pricing/timeline/design/process/legal
    room_area_sqm: float = Field(default=0, ge=0)


class PricingConfig(BaseModel):
    base_per_sqm: float = Field(default=1500.0, ge=0)
    renovation_included: bool = False
    city_modifier: float = Field(default=1.0, ge=0.5, le=3.0)


class QuoteInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    questions: List[CustomerQuestion] = Field(..., min_length=1, max_length=200)
    pricing_config: PricingConfig = Field(default_factory=PricingConfig)
    workflow_id: str = Field(default="WF-T-012", pattern=r"^WF-T-\d{3}$")


class Categorized(BaseModel):
    qid: str
    detected_type: str
    urgency: str  # low/medium/high
    answer_hint: str


class QuoteDraft(BaseModel):
    qid: str
    package_name: str
    price_low: float
    price_high: float
    includes: List[str]
    notes: str


class QuoteOutput(BaseModel):
    total: int
    categorized: List[Categorized]
    quote_drafts: List[QuoteDraft]


_TYPE_KEYWORDS = {
    "pricing": ["价格", "多少钱", "报价", "预算", "费用", "贵"],
    "timeline": ["工期", "多久", "时间", "几个月", "几天"],
    "design": ["设计", "风格", "户型", "软装", "效果"],
    "process": ["流程", "工序", "步骤", "顺序", "节点"],
    "legal": ["合同", "条款", "违约", "质保", "售后"],
}


def _classify(content: str) -> str:
    text = content.lower()
    for k, kws in _TYPE_KEYWORDS.items():
        if any(kw in text for kw in kws):
            return k
    return "other"


def _urgency(text: str) -> str:
    if any(k in text for k in ["急", "马上", "立刻", "尽快", "月底"]):
        return "high"
    if any(k in text for k in ["看看", "了解", "咨询", "随便"]):
        return "low"
    return "medium"


@run_workflow(workflow_id="WF-T-012", tenant_field="tenant_id")
def run_quote(inp: QuoteInput) -> QuoteOutput:
    if not inp.questions:
        raise WorkflowError("WF-T012-Q", "questions 不能为空")

    categorized: List[Categorized] = []
    drafts: List[QuoteDraft] = []
    cfg = inp.pricing_config

    for q in inp.questions:
        t = _classify(q.content)
        u = _urgency(q.content)
        hint = f"回复模板: 关于{t}, 建议从 {'价格区间' if t == 'pricing' else '流程节点'} 切入"
        categorized.append(Categorized(
            qid=q.qid, detected_type=t, urgency=u, answer_hint=hint,
        ))
        if t == "pricing" and q.room_area_sqm > 0:
            base = cfg.base_per_sqm * q.room_area_sqm * cfg.city_modifier
            drafts.append(QuoteDraft(
                qid=q.qid,
                package_name=f"{q.city} {q.room_area_sqm:.0f}㎡ 半包" if not cfg.renovation_included else f"{q.city} {q.room_area_sqm:.0f}㎡ 全包",
                price_low=round(base * 0.85, 0),
                price_high=round(base * 1.15, 0),
                includes=["拆改", "水电", "瓦木", "油漆"] if not cfg.renovation_included else ["拆改", "水电", "瓦木", "油漆", "主材"],
                notes="最终报价以量房为准",
            ))

    return QuoteOutput(
        total=len(categorized),
        categorized=categorized,
        quote_drafts=drafts,
    )


validate_json = lambda s: validate_workflow_json(s, QuoteInput)
validate_yaml = lambda s: validate_workflow_yaml(s, QuoteInput)