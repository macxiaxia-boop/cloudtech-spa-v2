"""WF-G-023 故障快速人工降级 — 通用
=================================
输入: tenant_id, incident_id, severity (P0/P1/P2/P3), affected_workflows[], degraded_mode
输出: action_plan[], notify_list[], degraded_until, status
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class IncidentInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    incident_id: str
    severity: str = Field(..., pattern=r"^P[0-3]$")
    affected_workflows: List[str] = Field(default_factory=list)
    degraded_mode: str = "auto_only"  # auto_only / half_manual / full_handoff
    detected_at: str = ""
    workflow_id: str = Field(default="WF-G-023", pattern=r"^WF-G-\d{3}$")

    @field_validator("degraded_mode")
    @classmethod
    def m_ok(cls, v):
        if v not in ("auto_only", "half_manual", "full_handoff", "kill_switch"):
            raise ValueError("degraded_mode ∈ 4 类")
        return v


class ActionItem(BaseModel):
    action: str
    owner: str
    eta_min: int


class IncidentOutput(BaseModel):
    incident_id: str
    status: str
    action_plan: List[ActionItem]
    notify_list: List[str]
    degraded_until: str
    affected_count: int
    estimated_impact: str


_SEV_OWNER = {"P0": "tech_lead", "P1": "oncall", "P2": "support", "P3": "support"}


@run_workflow(workflow_id="WF-G-023", tenant_field="tenant_id")
def run_incident(inp: IncidentInput) -> IncidentOutput:
    if inp.severity == "P0" and inp.degraded_mode not in ("half_manual", "kill_switch"):
        raise WorkflowError("WF-G023-P0", "P0 必须立即切换到 half_manual 或 kill_switch")

    eta_min = {"P0": 15, "P1": 60, "P2": 240, "P3": 1440}[inp.severity]
    plan = [
        ActionItem(action=f"切换到 {inp.degraded_mode}", owner="oncall", eta_min=5),
        ActionItem(action="通知相关方 + 拉 Slack 战时频道", owner=_SEV_OWNER[inp.severity], eta_min=eta_min),
        ActionItem(action="写入 post-mortem 草稿", owner="tech_lead", eta_min=eta_min * 4),
    ]
    if inp.affected_workflows:
        plan.append(ActionItem(
            action=f"暂停受影响 workflow ({len(inp.affected_workflows)} 个)",
            owner="oncall", eta_min=10,
        ))

    notify = ["tech_lead", "product_owner", "客户成功 (租户列表)"] if inp.severity in ("P0", "P1") else ["oncall"]

    detected = inp.detected_at or datetime.now(timezone.utc).isoformat()
    try:
        det_dt = datetime.fromisoformat(detected.replace("Z", "+00:00"))
    except Exception:
        det_dt = datetime.now(timezone.utc)
    degraded_until = (det_dt + timedelta(minutes=eta_min)).isoformat()

    impact = f"影响 {len(inp.affected_workflows)} 个 workflow, 预计 {eta_min} 分钟恢复"
    return IncidentOutput(
        incident_id=inp.incident_id,
        status="degraded" if inp.degraded_mode != "kill_switch" else "offline",
        action_plan=plan,
        notify_list=notify,
        degraded_until=degraded_until,
        affected_count=len(inp.affected_workflows),
        estimated_impact=impact,
    )


validate_json = lambda s: validate_workflow_json(s, IncidentInput)
validate_yaml = lambda s: validate_workflow_yaml(s, IncidentInput)