"""WF-G-019 知识问答人工接管 — 通用
=================================
输入: tenant_id, question, user_role, confidence_threshold
输出: answer (mock), confidence, action (auto/handoff/escalate), suggested_responder
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class QAInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    question: str = Field(..., min_length=2, max_length=1000)
    user_role: str = Field(default="user")
    confidence_threshold: float = Field(default=0.75, ge=0.1, le=0.99)
    candidate_answers: List[str] = Field(default_factory=list)
    workflow_id: str = Field(default="WF-G-019", pattern=r"^WF-G-\d{3}$")


class QAOutput(BaseModel):
    question: str
    answer: str
    confidence: float
    action: str  # auto/handoff/escalate
    suggested_responder: Optional[str]
    rationale: str


def _score_answer(q: str, a: str) -> float:
    """基于简单关键词覆盖度的 mock 置信度"""
    q_words = set(q.lower().replace("?", "").replace("？", "").split())
    a_words = set(a.lower().split())
    if not q_words:
        return 0.5
    overlap = len(q_words & a_words)
    return round(min(0.99, overlap / max(len(q_words), 1) + 0.1), 3)


@run_workflow(workflow_id="WF-G-019", tenant_field="tenant_id")
def run_qa(inp: QAInput) -> QAOutput:
    if not inp.question.strip():
        raise WorkflowError("WF-G019-Q", "question 不能为空")
    if not inp.candidate_answers:
        answer = "(无候选答案, 默认回复)"
        confidence = 0.2
    else:
        scored = [(a, _score_answer(inp.question, a)) for a in inp.candidate_answers]
        scored.sort(key=lambda x: x[1], reverse=True)
        answer, confidence = scored[0]

    if confidence >= inp.confidence_threshold:
        action = "auto"
        responder = None
        rationale = f"置信度 {confidence:.2f} ≥ 阈值 {inp.confidence_threshold}, 自动答复"
    elif confidence >= inp.confidence_threshold * 0.5:
        action = "handoff"
        responder = "human_expert"
        rationale = f"置信度 {confidence:.2f} 中等, 转人工专家"
    else:
        action = "escalate"
        responder = "manager"
        rationale = f"置信度 {confidence:.2f} 低, 上报经理"

    return QAOutput(
        question=inp.question,
        answer=answer,
        confidence=confidence,
        action=action,
        suggested_responder=responder,
        rationale=rationale,
    )


validate_json = lambda s: validate_workflow_json(s, QAInput)
validate_yaml = lambda s: validate_workflow_yaml(s, QAInput)