"""WF-G-022 月度 Token 成本对账 — 通用
===================================
输入: tenant_id, month (YYYY-MM), daily_usage[] (provider + tokens + cost_yuan)
输出: by_provider[] (含 tokens, cost_yuan, cost_usd), total, anomalies[]
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class DailyUsage(BaseModel):
    date: str  # YYYY-MM-DD
    provider: str
    tokens: int = Field(..., ge=0)
    cost_yuan: float = Field(..., ge=0)

    @field_validator("provider")
    @classmethod
    def p_ok(cls, v):
        if v not in ("deepseek", "doubao", "openai", "anthropic", "minimax", "mock"):
            raise ValueError("provider ∈ 6 类")
        return v

    @field_validator("date")
    @classmethod
    def d_ok(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date 必须是 YYYY-MM-DD")
        return v


class TokenReconInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    month: str  # YYYY-MM
    daily_usage: List[DailyUsage] = Field(..., min_length=1, max_length=1000)
    fx_usd_yuan: float = Field(default=7.2, ge=1, le=20)
    anomaly_pct: float = Field(default=50.0, ge=10, le=200)
    workflow_id: str = Field(default="WF-G-022", pattern=r"^WF-G-\d{3}$")

    @field_validator("month")
    @classmethod
    def m_ok(cls, v):
        try:
            datetime.strptime(v, "%Y-%m")
        except ValueError:
            raise ValueError("month 必须是 YYYY-MM")
        return v


class ProviderTotal(BaseModel):
    provider: str
    tokens: int
    cost_yuan: float
    cost_usd: float


class TokenReconOutput(BaseModel):
    month: str
    by_provider: List[ProviderTotal]
    total_tokens: int
    total_cost_yuan: float
    total_cost_usd: float
    anomalies: List[str]


@run_workflow(workflow_id="WF-G-022", tenant_field="tenant_id")
def run_token_recon(inp: TokenReconInput) -> TokenReconOutput:
    by_p: dict = defaultdict(lambda: {"tokens": 0, "cost_yuan": 0.0})
    by_day_p: dict = defaultdict(list)
    for d in inp.daily_usage:
        by_p[d.provider]["tokens"] += d.tokens
        by_p[d.provider]["cost_yuan"] += d.cost_yuan
        by_day_p[d.provider].append(d.cost_yuan)
    rows = []
    total_tokens = 0
    total_yuan = 0.0
    for provider, agg in by_p.items():
        rows.append(ProviderTotal(
            provider=provider,
            tokens=agg["tokens"],
            cost_yuan=round(agg["cost_yuan"], 2),
            cost_usd=round(agg["cost_yuan"] / inp.fx_usd_yuan, 2),
        ))
        total_tokens += agg["tokens"]
        total_yuan += agg["cost_yuan"]

    # anomalies: provider 内部某日 cost > 均值 * (1 + anomaly_pct/100)
    anomalies: List[str] = []
    for provider, costs in by_day_p.items():
        if len(costs) < 3:
            continue
        avg = sum(costs) / len(costs)
        if avg == 0:
            continue
        for i, c in enumerate(costs):
            if c > avg * (1 + inp.anomaly_pct / 100.0):
                anomalies.append(f"{provider} day#{i} cost {c:.2f} (avg {avg:.2f}, +{((c-avg)/avg*100):.0f}%)")

    return TokenReconOutput(
        month=inp.month,
        by_provider=rows,
        total_tokens=total_tokens,
        total_cost_yuan=round(total_yuan, 2),
        total_cost_usd=round(total_yuan / inp.fx_usd_yuan, 2),
        anomalies=anomalies,
    )


validate_json = lambda s: validate_workflow_json(s, TokenReconInput)
validate_yaml = lambda s: validate_workflow_yaml(s, TokenReconInput)