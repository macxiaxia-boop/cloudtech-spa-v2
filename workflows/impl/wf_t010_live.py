"""WF-T-010 直播活动准备和复盘 — 装修业务
=========================================
输入: tenant_id, activity_name, planned_start, target_gmv, host, products[]
输出: prep_checklist[], risk_flags[], retrospective (peak_watchers/orders/roi), improvements[]
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class LiveProduct(BaseModel):
    sku: str
    name: str
    price: float = Field(..., ge=0)
    stock: int = Field(default=0, ge=0)


class LivePrepInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    activity_name: str = Field(..., min_length=2, max_length=100)
    planned_start: str
    target_gmv: float = Field(default=0, ge=0)
    host: str = Field(default="unknown")
    products: List[LiveProduct] = Field(..., min_length=1, max_length=200)
    mode: str = Field(default="prep")  # prep / retro
    # retro 字段
    peak_watchers: Optional[int] = Field(default=None, ge=0)
    orders: Optional[int] = Field(default=None, ge=0)
    actual_gmv: Optional[float] = Field(default=None, ge=0)

    @field_validator("mode")
    @classmethod
    def m_ok(cls, v):
        if v not in ("prep", "retro"):
            raise ValueError("mode ∈ {prep, retro}")
        return v


class PrepItem(BaseModel):
    item: str
    status: str  # pending/ok/risk


class LiveOutput(BaseModel):
    mode: str
    prep_checklist: List[PrepItem]
    risk_flags: List[str]
    retrospective: Optional[dict] = None
    improvements: List[str]
    estimated_attainment: float  # retro: actual/target


@run_workflow(workflow_id="WF-T-010", tenant_field="tenant_id")
def run_live(inp: LivePrepInput) -> LiveOutput:
    if not inp.products:
        raise WorkflowError("WF-T010-PROD", "products 不能为空")
    prep = []
    risks = []
    # prep checks
    if not inp.host or inp.host == "unknown":
        risks.append("⚠️ 主播未指定")
        prep.append(PrepItem(item="指定主播", status="risk"))
    else:
        prep.append(PrepItem(item="指定主播", status="ok"))
    if inp.target_gmv <= 0:
        risks.append("⚠️ 目标 GMV 未设定")
        prep.append(PrepItem(item="目标 GMV", status="risk"))
    else:
        prep.append(PrepItem(item="目标 GMV", status="ok"))
    total_stock = sum(p.stock for p in inp.products)
    if total_stock == 0:
        risks.append("🚨 全部商品库存为 0")
        prep.append(PrepItem(item="商品库存", status="risk"))
    else:
        prep.append(PrepItem(item="商品库存", status="ok"))
    prep.append(PrepItem(item="预热短视频 (3 条)", status="pending"))
    prep.append(PrepItem(item="直播间脚本", status="pending"))

    retro = None
    improvements = []
    est_attainment = 0.0
    if inp.mode == "retro":
        if inp.actual_gmv is None or inp.target_gmv <= 0:
            raise WorkflowError("WF-T010-RETRO", "retro 模式需要 actual_gmv + target_gmv")
        est_attainment = inp.actual_gmv / inp.target_gmv
        retro = {
            "peak_watchers": inp.peak_watchers or 0,
            "orders": inp.orders or 0,
            "actual_gmv": inp.actual_gmv,
            "target_gmv": inp.target_gmv,
            "conversion_rate": (inp.orders or 0) / max(inp.peak_watchers or 1, 1),
        }
        if est_attainment < 0.6:
            improvements.extend(["重做预热短视频", "优化主播脚本, 强化前 5 分钟"])
        elif est_attainment < 0.9:
            improvements.append("增加商品上架节奏")
        else:
            improvements.append("达成, 复制剧本")

    return LiveOutput(
        mode=inp.mode,
        prep_checklist=prep,
        risk_flags=risks,
        retrospective=retro,
        improvements=improvements,
        estimated_attainment=round(est_attainment, 3),
    )


validate_json = lambda s: validate_workflow_json(s, LivePrepInput)
validate_yaml = lambda s: validate_workflow_yaml(s, LivePrepInput)