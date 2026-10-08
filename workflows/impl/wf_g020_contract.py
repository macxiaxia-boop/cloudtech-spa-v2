"""WF-G-020 合同陪跑验收 — 通用
=============================
输入: tenant_id, contract_id, clauses[] (含 text, type), milestones[]
输出: clause_checks[] (含 risk_level), milestone_progress, total_risk_score, verdict
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class Clause(BaseModel):
    cid: str
    text: str = Field(..., min_length=1)
    type: str = Field(default="payment")  # payment/delivery/penalty/warranty/termination/other

    @field_validator("type")
    @classmethod
    def t_ok(cls, v):
        if v not in ("payment", "delivery", "penalty", "warranty", "termination", "confidentiality", "other"):
            raise ValueError("type ∈ 7 类")
        return v


class Milestone(BaseModel):
    mid: str
    name: str
    due_date: str  # YYYY-MM-DD
    completed: bool = False
    completed_at: Optional[str] = None


class ContractInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    contract_id: str
    clauses: List[Clause] = Field(..., min_length=1, max_length=200)
    milestones: List[Milestone] = Field(default_factory=list)
    workflow_id: str = Field(default="WF-G-020", pattern=r"^WF-G-\d{3}$")


class ClauseCheck(BaseModel):
    cid: str
    type: str
    risk_level: str  # low/medium/high
    note: str


class ContractOutput(BaseModel):
    contract_id: str
    clause_checks: List[ClauseCheck]
    milestone_progress: dict
    total_risk_score: int  # 0-100
    verdict: str  # pass/conditional/reject


_HIGH_RISK_TYPES = {"penalty", "termination"}
_MED_RISK_TYPES = {"payment", "warranty", "confidentiality"}


def _risk_for(clause: Clause) -> ClauseCheck:
    txt = clause.text.lower()
    if clause.type in _HIGH_RISK_TYPES and ("违约金" in txt or "解除" in txt):
        return ClauseCheck(cid=clause.cid, type=clause.type, risk_level="high", note="高风险条款")
    if clause.type in _MED_RISK_TYPES and not any(k in txt for k in ["明确", "约定", "协商"]):
        return ClauseCheck(cid=clause.cid, type=clause.type, risk_level="medium", note="措辞含糊")
    return ClauseCheck(cid=clause.cid, type=clause.type, risk_level="low", note="可接受")


@run_workflow(workflow_id="WF-G-020", tenant_field="tenant_id")
def run_contract(inp: ContractInput) -> ContractOutput:
    if not inp.clauses:
        raise WorkflowError("WF-G020-CLAUSES", "clauses 不能为空")
    checks = [_risk_for(c) for c in inp.clauses]
    score = sum(20 if x.risk_level == "high" else (10 if x.risk_level == "medium" else 0) for x in checks)

    # milestones
    completed = sum(1 for m in inp.milestones if m.completed)
    pending = sum(1 for m in inp.milestones if not m.completed)
    overdue = 0
    import re
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date().isoformat()
    for m in inp.milestones:
        if not m.completed and m.due_date < today:
            overdue += 1

    verdict = "pass" if score < 20 else ("conditional" if score < 50 else "reject")
    return ContractOutput(
        contract_id=inp.contract_id,
        clause_checks=checks,
        milestone_progress={"completed": completed, "pending": pending, "overdue": overdue},
        total_risk_score=score,
        verdict=verdict,
    )


validate_json = lambda s: validate_workflow_json(s, ContractInput)
validate_yaml = lambda s: validate_workflow_yaml(s, ContractInput)