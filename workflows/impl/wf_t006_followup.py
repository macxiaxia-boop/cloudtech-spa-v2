"""WF-T-006 线索跟进提醒 — 装修业务
==================================
输入: tenant_id, leads[] (跟进历史), sla_hours
输出: overdue[], due_soon[], reminders[]
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class FollowupEntry(BaseModel):
    lead_name: str
    last_contact_at: str  # ISO 8601
    assigned_to: str
    status: str = "open"  # open/closed/lost
    stage: str = "awareness"  # awareness/consideration/decision/closed


class FollowupInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    leads: List[FollowupEntry] = Field(..., min_length=1, max_length=2000)
    sla_hours: int = Field(default=24, ge=1, le=240)
    now_iso: Optional[str] = None  # 测试用, 默认 UTC now
    workflow_id: str = Field(default="WF-T-006", pattern=r"^WF-T-\d{3}$")


class Reminder(BaseModel):
    lead_name: str
    assigned_to: str
    reminder_type: str  # overdue/due_soon/on_track
    hours_since: float
    stage: str
    suggested_action: str


class FollowupOutput(BaseModel):
    total: int
    overdue: int
    due_soon: int
    on_track: int
    reminders: List[Reminder]


@run_workflow(workflow_id="WF-T-006", tenant_field="tenant_id")
def run_followup(inp: FollowupInput) -> FollowupOutput:
    if not inp.leads:
        raise WorkflowError("WF-T006-LEADS", "leads 不能为空")
    now = inp.now_iso or datetime.now(timezone.utc).isoformat()
    try:
        now_dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except Exception:
        raise WorkflowError("WF-T006-NOW", "now_iso 格式错误")

    reminders: List[Reminder] = []
    overdue_count = 0
    due_soon_count = 0
    on_track_count = 0

    for l in inp.leads:
        try:
            last = datetime.fromisoformat(l.last_contact_at.replace("Z", "+00:00"))
            # pydantic v2 / datetime compat: 如果 ISO 字符串无 tz, 默认按 UTC 处理
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if l.status != "open":
            continue
        hours = (now_dt - last).total_seconds() / 3600.0
        if hours > inp.sla_hours:
            reminders.append(Reminder(
                lead_name=l.lead_name,
                assigned_to=l.assigned_to,
                reminder_type="overdue",
                hours_since=round(hours, 1),
                stage=l.stage,
                suggested_action="立即电话回访 (已超时)",
            ))
            overdue_count += 1
        elif hours > inp.sla_hours * 0.75:
            reminders.append(Reminder(
                lead_name=l.lead_name,
                assigned_to=l.assigned_to,
                reminder_type="due_soon",
                hours_since=round(hours, 1),
                stage=l.stage,
                suggested_action="预约 24h 内回访",
            ))
            due_soon_count += 1
        else:
            on_track_count += 1

    return FollowupOutput(
        total=overdue_count + due_soon_count + on_track_count,
        overdue=overdue_count,
        due_soon=due_soon_count,
        on_track=on_track_count,
        reminders=reminders,
    )


validate_json = lambda s: validate_workflow_json(s, FollowupInput)
validate_yaml = lambda s: validate_workflow_yaml(s, FollowupInput)