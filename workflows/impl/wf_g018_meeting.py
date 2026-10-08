"""WF-G-018 会议纪要形成任务 — 通用
=================================
输入: tenant_id, meeting_id, transcript (含 speakers + utterances), auto_create
输出: summary, decisions[], action_items[] (含 owner, due, priority), created_task_ids[]
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class Utterance(BaseModel):
    speaker: str
    text: str = Field(..., min_length=1)


class Transcript(BaseModel):
    meeting_id: str
    title: str
    duration_min: int = Field(default=30, ge=1, le=480)
    utterances: List[Utterance] = Field(..., min_length=1)


class MeetingInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    transcript: Transcript
    auto_create: bool = False
    workflow_id: str = Field(default="WF-G-018", pattern=r"^WF-G-\d{3}$")


class Decision(BaseModel):
    text: str
    decided_by: str


class ActionItem(BaseModel):
    text: str
    owner: str
    due: str
    priority: str  # P0/P1/P2


class MeetingOutput(BaseModel):
    meeting_id: str
    summary: str
    decisions: List[Decision]
    action_items: List[ActionItem]
    created_task_ids: List[str]


_DECISION_KW = ("决定", "确认", "拍板", "agreed", "决定是", "结论")
_ACTION_KW = ("需要", "跟进", "落实", "action", "todo", "安排")


def _detect(text: str) -> bool:
    return any(k in text.lower() for k in _DECISION_KW + _ACTION_KW)


@run_workflow(workflow_id="WF-G-018", tenant_field="tenant_id")
def run_meeting(inp: MeetingInput) -> MeetingOutput:
    if not inp.transcript.utterances:
        raise WorkflowError("WF-G018-UTT", "utterances 不能为空")

    decisions: List[Decision] = []
    actions: List[ActionItem] = []
    speakers = []
    for u in inp.transcript.utterances:
        if u.speaker not in speakers:
            speakers.append(u.speaker)
        text_low = u.text.lower()
        if any(k in text_low for k in _DECISION_KW):
            decisions.append(Decision(text=u.text[:120], decided_by=u.speaker))
        elif any(k in text_low for k in _ACTION_KW):
            owner = u.speaker
            priority = "P0" if any(k in u.text for k in ["立刻", "马上", "急"]) else "P1"
            due = "T+3" if priority == "P0" else "T+7"
            actions.append(ActionItem(text=u.text[:200], owner=owner, due=due, priority=priority))

    summary = f"会议 {inp.transcript.title} ({inp.transcript.duration_min} 分钟, {len(speakers)} 位参会者): "
    summary += f"{len(decisions)} 项决议, {len(actions)} 项行动项"

    created = []
    if inp.auto_create:
        for i, a in enumerate(actions):
            created.append(f"task-{inp.transcript.meeting_id}-{i:03d}")

    return MeetingOutput(
        meeting_id=inp.transcript.meeting_id,
        summary=summary,
        decisions=decisions,
        action_items=actions,
        created_task_ids=created,
    )


validate_json = lambda s: validate_workflow_json(s, MeetingInput)
validate_yaml = lambda s: validate_workflow_yaml(s, MeetingInput)