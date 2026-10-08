"""WF-T-004 内容计划排期与人工发布 — 装修业务
============================================
输入: tenant_id, scripts[] (含 topic + platform + scheduled_at), approval_required
输出: schedule[] 每条含 (script_id, scheduled_at, status, approver)
"""
from __future__ import annotations
from datetime import datetime
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError, PLATFORMS_T


class ScriptSlot(BaseModel):
    script_id: str
    topic: str
    platform: str
    scheduled_at: str  # ISO 8601
    approver: str = "human"

    @field_validator("platform")
    @classmethod
    def plat_ok(cls, v):
        if v not in PLATFORMS_T:
            raise ValueError(f"平台必须 ∈ {PLATFORMS_T}")
        return v


class ContentPlanInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    scripts: List[ScriptSlot] = Field(..., min_length=1, max_length=50)
    approval_required: bool = Field(default=True)
    workflow_id: str = Field(default="WF-T-004", pattern=r"^WF-T-\d{3}$")


class ScheduledItem(BaseModel):
    script_id: str
    topic: str
    platform: str
    scheduled_at: str
    status: str  # pending_approval / approved / published / failed
    approver: str
    publish_window: str  # morning/noon/evening


class ContentPlanOutput(BaseModel):
    total: int
    pending_approval: int
    approved: int
    schedule: List[ScheduledItem]
    conflicts: List[str]


def _classify_window(iso: str) -> str:
    try:
        h = datetime.fromisoformat(iso.replace("Z", "+00:00")).hour
    except Exception:
        h = 12
    if h < 11:
        return "morning"
    if h < 17:
        return "noon"
    return "evening"


@run_workflow(workflow_id="WF-T-004", tenant_field="tenant_id")
def run_content_plan(inp: ContentPlanInput) -> ContentPlanOutput:
    if not inp.scripts:
        raise WorkflowError("WF-T004-EMPTY", "scripts 不能为空")

    schedule: List[ScheduledItem] = []
    conflicts: List[str] = []
    pending = 0
    approved = 0

    # 同平台同时段冲突检测
    seen = {}
    for s in inp.scripts:
        key = (s.platform, s.scheduled_at)
        if key in seen:
            conflicts.append(f"{s.platform}@{s.scheduled_at} 冲突: {seen[key]} vs {s.script_id}")
        else:
            seen[key] = s.script_id
        status = "pending_approval" if inp.approval_required else "approved"
        if status == "pending_approval":
            pending += 1
        else:
            approved += 1
        schedule.append(ScheduledItem(
            script_id=s.script_id,
            topic=s.topic,
            platform=s.platform,
            scheduled_at=s.scheduled_at,
            status=status,
            approver=s.approver,
            publish_window=_classify_window(s.scheduled_at),
        ))

    return ContentPlanOutput(
        total=len(schedule),
        pending_approval=pending,
        approved=approved,
        schedule=schedule,
        conflicts=conflicts,
    )


validate_json = lambda s: validate_workflow_json(s, ContentPlanInput)
validate_yaml = lambda s: validate_workflow_yaml(s, ContentPlanInput)