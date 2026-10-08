"""WF-G-017 长流程与人工批准 — 通用
================================
输入: tenant_id, steps[] (含 name, status, approver), checkpoints[]
输出: progress_pct, awaiting_approval[], approval_summary, next_actions[]
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class Step(BaseModel):
    name: str = Field(..., min_length=1)
    status: str = "pending"  # pending/running/done/blocked/waiting_approval
    approver: Optional[str] = None


class Checkpoint(BaseModel):
    step: str
    needs_approval: bool = True
    approved: Optional[bool] = None
    note: str = ""


class LongFlowInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    steps: List[Step] = Field(..., min_length=1, max_length=200)
    checkpoints: List[Checkpoint] = Field(..., min_length=0, max_length=200)
    workflow_id: str = Field(default="WF-G-017", pattern=r"^WF-G-\d{3}$")


class LongFlowOutput(BaseModel):
    total_steps: int
    done_steps: int
    progress_pct: float
    awaiting_approval: List[str]
    approval_summary: dict
    next_actions: List[str]


@run_workflow(workflow_id="WF-G-017", tenant_field="tenant_id")
def run_long_flow(inp: LongFlowInput) -> LongFlowOutput:
    if not inp.steps:
        raise WorkflowError("WF-G017-STEPS", "steps 不能为空")
    done = sum(1 for s in inp.steps if s.status == "done")
    pct = round(done / len(inp.steps) * 100, 1)

    awaiting = []
    approved_total = 0
    rejected_total = 0
    pending_approval_total = 0
    step_names = {s.name for s in inp.steps}

    for ck in inp.checkpoints:
        if ck.step not in step_names:
            raise WorkflowError("WF-G017-ORPHAN", f"checkpoint 引用未注册 step: {ck.step}")
        if not ck.needs_approval:
            continue
        if ck.approved is True:
            approved_total += 1
        elif ck.approved is False:
            rejected_total += 1
            awaiting.append(f"{ck.step} 已被驳回 ({ck.note})")
        else:
            pending_approval_total += 1
            awaiting.append(f"{ck.step} 等待批准")

    # 找下一个阻塞的 step
    blocked = next((s for s in inp.steps if s.status in ("blocked", "waiting_approval")), None)
    next_actions = []
    if blocked:
        next_actions.append(f"处理 {blocked.name} (status={blocked.status})")
    if rejected_total:
        next_actions.append(f"复盘 {rejected_total} 个被驳回 checkpoint")
    if pct < 100 and not next_actions:
        next_actions.append("继续执行剩余步骤")

    return LongFlowOutput(
        total_steps=len(inp.steps),
        done_steps=done,
        progress_pct=pct,
        awaiting_approval=awaiting,
        approval_summary={
            "approved": approved_total,
            "rejected": rejected_total,
            "pending": pending_approval_total,
        },
        next_actions=next_actions,
    )


validate_json = lambda s: validate_workflow_json(s, LongFlowInput)
validate_yaml = lambda s: validate_workflow_yaml(s, LongFlowInput)