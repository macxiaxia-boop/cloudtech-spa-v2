"""WF-G-016 Provider 真实调用与对账 — 通用
========================================
输入: tenant_id, calls[] (provider + model + tokens_in + tokens_out + unit_price)
输出: reconciled[] (含 cost_yuan, cost_usd, drift_pct), total_cost, audit_disputes[]
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class ProviderCall(BaseModel):
    call_id: str
    provider: str
    model: str
    tokens_in: int = Field(..., ge=0)
    tokens_out: int = Field(..., ge=0)
    unit_price_in: float = Field(..., ge=0)   # ¥ / 1k tokens
    unit_price_out: float = Field(..., ge=0)
    reported_cost_yuan: float = Field(default=0.0, ge=0)

    @field_validator("provider")
    @classmethod
    def p_ok(cls, v):
        if v not in ("deepseek", "doubao", "openai", "anthropic", "minimax", "mock"):
            raise ValueError("provider ∈ {deepseek, doubao, openai, anthropic, minimax, mock}")
        return v


class ProviderInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    calls: List[ProviderCall] = Field(..., min_length=1, max_length=5000)
    fx_usd_yuan: float = Field(default=7.2, ge=1, le=20)
    drift_threshold_pct: float = Field(default=5.0, ge=0.5, le=50)
    workflow_id: str = Field(default="WF-G-016", pattern=r"^WF-G-\d{3}$")


class ReconciledRow(BaseModel):
    call_id: str
    expected_cost_yuan: float
    reported_cost_yuan: float
    drift_pct: float
    dispute: bool


class ProviderOutput(BaseModel):
    total_calls: int
    total_expected_yuan: float
    total_reported_yuan: float
    total_cost_usd: float
    reconciled: List[ReconciledRow]
    audit_disputes: List[str]


def _expected_cost(c: ProviderCall) -> float:
    return (c.tokens_in / 1000.0) * c.unit_price_in + (c.tokens_out / 1000.0) * c.unit_price_out


@run_workflow(workflow_id="WF-G-016", tenant_field="tenant_id")
def run_provider(inp: ProviderInput) -> ProviderOutput:
    if not inp.calls:
        raise WorkflowError("WF-G016-CALLS", "calls 不能为空")
    rows: List[ReconciledRow] = []
    disputes: List[str] = []
    total_expected = 0.0
    total_reported = 0.0
    for c in inp.calls:
        exp = _expected_cost(c)
        rep = c.reported_cost_yuan
        total_expected += exp
        total_reported += rep
        drift = ((rep - exp) / exp * 100.0) if exp > 0 else 0.0
        is_dispute = abs(drift) > inp.drift_threshold_pct
        rows.append(ReconciledRow(
            call_id=c.call_id,
            expected_cost_yuan=round(exp, 4),
            reported_cost_yuan=round(rep, 4),
            drift_pct=round(drift, 2),
            dispute=is_dispute,
        ))
        if is_dispute:
            disputes.append(f"{c.call_id}: drift {drift:.1f}% (expected {exp:.4f} vs {rep:.4f})")
    return ProviderOutput(
        total_calls=len(rows),
        total_expected_yuan=round(total_expected, 2),
        total_reported_yuan=round(total_reported, 2),
        total_cost_usd=round(total_expected / inp.fx_usd_yuan, 2),
        reconciled=rows,
        audit_disputes=disputes,
    )


validate_json = lambda s: validate_workflow_json(s, ProviderInput)
validate_yaml = lambda s: validate_workflow_yaml(s, ProviderInput)