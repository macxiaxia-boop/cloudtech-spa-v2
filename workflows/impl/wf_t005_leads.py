"""WF-T-005 线索导入去重与分配 — 装修业务
=========================================
输入: tenant_id, leads[] (含 name+phone+city+source), strategy (round_robin/by_load/by_skill)
输出: deduped_leads[], assigned_leads[], dedup_count, duplicates[]
"""
from __future__ import annotations
import hashlib
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class Lead(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    phone: str = Field(..., min_length=5, max_length=30)
    city: str = Field(..., min_length=1, max_length=40)
    source: str = Field(default="unknown")
    intent_score: float = Field(default=50.0, ge=0, le=100)
    budget: Optional[float] = None


class LeadsInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    leads: List[Lead] = Field(..., min_length=1, max_length=2000)
    sales_team: List[str] = Field(..., min_length=1, max_length=50)
    strategy: str = Field(default="round_robin")
    workflow_id: str = Field(default="WF-T-005", pattern=r"^WF-T-\d{3}$")

    @field_validator("strategy")
    @classmethod
    def strat_ok(cls, v):
        if v not in ("round_robin", "by_load", "by_skill", "by_intent"):
            raise ValueError("strategy ∈ {round_robin, by_load, by_skill, by_intent}")
        return v


class AssignedLead(BaseModel):
    name: str
    phone_hash: str  # 隐私: 不返回明文
    city: str
    assigned_to: str
    priority: str  # hot/warm/cold


class LeadsOutput(BaseModel):
    input_count: int
    deduped_count: int
    duplicates: List[str]
    assigned: List[AssignedLead]
    load_distribution: dict


def _phash(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()[:12]


@run_workflow(workflow_id="WF-T-005", tenant_field="tenant_id")
def run_leads(inp: LeadsInput) -> LeadsOutput:
    if not inp.sales_team:
        raise WorkflowError("WF-T005-TEAM", "sales_team 不能为空")
    if not inp.leads:
        raise WorkflowError("WF-T005-LEADS", "leads 不能为空")

    # 去重 (phone)
    seen = {}
    duplicates: List[str] = []
    deduped: List[Lead] = []
    for l in inp.leads:
        h = _phash(l.phone)
        if h in seen:
            duplicates.append(l.phone[:3] + "***")
        else:
            seen[h] = l.name
            deduped.append(l)

    # 分配
    load_count = {m: 0 for m in inp.sales_team}
    assigned: List[AssignedLead] = []
    for i, l in enumerate(deduped):
        if inp.strategy == "by_intent" or inp.strategy == "by_skill":
            # 高 intent 给销售 #0
            member = inp.sales_team[0] if l.intent_score >= 70 else inp.sales_team[i % len(inp.sales_team)]
        elif inp.strategy == "by_load":
            member = min(load_count, key=lambda m: load_count[m])
        else:  # round_robin
            member = inp.sales_team[i % len(inp.sales_team)]
        load_count[member] += 1
        priority = "hot" if l.intent_score >= 80 else ("warm" if l.intent_score >= 50 else "cold")
        assigned.append(AssignedLead(
            name=l.name, phone_hash=_phash(l.phone),
            city=l.city, assigned_to=member, priority=priority,
        ))

    return LeadsOutput(
        input_count=len(inp.leads),
        deduped_count=len(deduped),
        duplicates=duplicates,
        assigned=assigned,
        load_distribution=load_count,
    )


validate_json = lambda s: validate_workflow_json(s, LeadsInput)
validate_yaml = lambda s: validate_workflow_yaml(s, LeadsInput)