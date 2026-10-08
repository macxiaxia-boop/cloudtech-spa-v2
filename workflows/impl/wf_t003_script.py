"""WF-T-003 脚本生成与审核 — 装修业务
====================================
输入: topic, angle, persona, platform, word_count, creator
输出: script (title + hook + body + cta + hashtags), review_score, review_notes[]
"""
from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError, PLATFORMS_T


class ScriptInput(BaseModel):
    tenant_id: str = Field(..., min_length=2, max_length=50)
    topic: str = Field(..., min_length=2, max_length=200)
    angle: str = Field(default="避坑", min_length=1, max_length=40)
    persona: str = Field(default="刚需家庭")
    platform: str = Field(default="xiaohongshu")
    word_count: int = Field(default=800, ge=100, le=5000)
    creator: str = Field(default="zhinan")
    workflow_id: str = Field(default="WF-T-003", pattern=r"^WF-T-\d{3}$")

    @field_validator("platform")
    @classmethod
    def plat_ok(cls, v):
        if v not in PLATFORMS_T:
            raise ValueError(f"平台必须 ∈ {PLATFORMS_T}")
        return v


class ScriptReviewNote(BaseModel):
    severity: str  # info/warn/error
    note: str


class ScriptOutput(BaseModel):
    title: str
    hook: str
    body: str
    cta: str
    hashtags: List[str]
    review_score: int  # 0-100
    review_notes: List[ScriptReviewNote]
    word_count: int
    approved: bool


def _build_script(inp: ScriptInput) -> str:
    paragraphs = [
        f"## 开场钩子\n{inp.topic} — 你踩过的坑,我都帮你列了。",
        f"## 核心观点\n1. {inp.angle}第一原则: 找到最贵的那一项, 先优化它。\n2. 第二原则: 不要被样板间忽悠。",
        f"## 案例拆解\n案例 A: 老破小改造 50 平, 预算 12 万, 客户最满意的是收纳。\n案例 B: 三房两厅, 拆改节省 1.8 万。",
        f"## 行动建议\n- 立刻做: 户型图先复盘, 再报价。\n- 立刻避免: 一次性签全包, 留 30% 尾款。",
        f"## 互动\n你装修踩过哪些坑?评论区聊聊 👇",
    ]
    return "\n\n".join(paragraphs)


@run_workflow(workflow_id="WF-T-003", tenant_field="tenant_id")
def run_script(inp: ScriptInput) -> ScriptOutput:
    if inp.word_count < 100:
        raise WorkflowError("WF-T003-LEN", "word_count 太小")
    body = _build_script(inp)
    review_notes: List[ScriptReviewNote] = []
    score = 95
    if len(body) < 200:
        review_notes.append(ScriptReviewNote(severity="warn", note="脚本偏短"))
        score -= 10
    if "踩" not in body and "避坑" in inp.angle:
        review_notes.append(ScriptReviewNote(severity="info", note="缺少'踩'关键字,可强化"))
        score -= 5
    if "#" not in inp.topic:
        review_notes.append(ScriptReviewNote(severity="warn", note="话题缺 hashtag"))
        score -= 3

    return ScriptOutput(
        title=f"【{inp.angle}】{inp.topic} — 必看 10 条经验",
        hook=f"为什么 90% 的人都在 {inp.topic} 上踩坑? 真相来了",
        body=body,
        cta="关注我, 下期拆解 10 个真实户型",
        hashtags=[f"#{inp.topic}", f"#{inp.angle}", f"#{inp.persona}", f"#{inp.platform}"],
        review_score=max(0, score),
        review_notes=review_notes,
        word_count=len(body),
        approved=score >= 70,
    )


validate_json = lambda s: validate_workflow_json(s, ScriptInput)
validate_yaml = lambda s: validate_workflow_yaml(s, ScriptInput)