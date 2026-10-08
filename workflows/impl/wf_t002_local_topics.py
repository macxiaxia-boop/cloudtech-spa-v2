"""WF-T-002 本地客群与选题池 — 装修业务
=====================================
输入: tenant_id, cities, persona_segments, platforms
输出: topics[] 每条含 (topic, angle, persona, hotness_score)
"""
from __future__ import annotations
import hashlib
from typing import List
from pydantic import BaseModel, Field
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError, PLATFORMS_T


class LocalTopicInput(BaseModel):
    tenant_id: str = Field(..., min_length=2, max_length=50)
    cities: List[str] = Field(..., min_length=1, max_length=9)
    persona_segments: List[str] = Field(default_factory=lambda: ["刚需家庭", "改善型", "适老化"])
    platforms: List[str] = Field(default_factory=lambda: ["xiaohongshu", "douyin"])
    industry: str = Field(default="decoration")
    count: int = Field(default=10, ge=1, le=50)
    workflow_id: str = Field(default="WF-T-002", pattern=r"^WF-T-\d{3}$")


class TopicItem(BaseModel):
    topic: str
    angle: str
    persona: str
    platform: str
    hotness_score: float
    city: str


class LocalTopicOutput(BaseModel):
    total: int
    cities_covered: List[str]
    platforms_covered: List[str]
    topics: List[TopicItem]


def _gen_topic(city: str, persona: str, platform: str, idx: int) -> TopicItem:
    angles = ["避坑", "干货", "对比", "故事", "热点"]
    base_titles = [
        f"{city}老破小翻新",
        f"{city}装修预算10万实录",
        f"{city}二手房改造",
        f"{city}软装搭配",
        f"{city}工地验收",
        f"{city}户型优化",
        f"{city}建材探店",
        f"{city}装修日记",
    ]
    title = base_titles[idx % len(base_titles)]
    angle = angles[idx % len(angles)]
    # 确定性 hash → score
    seed = hashlib.md5(f"{city}-{persona}-{platform}-{idx}".encode()).hexdigest()
    score = 60 + (int(seed[:4], 16) % 40)
    return TopicItem(
        topic=title,
        angle=angle,
        persona=persona,
        platform=platform,
        hotness_score=round(float(score), 1),
        city=city,
    )


@run_workflow(workflow_id="WF-T-002", tenant_field="tenant_id")
def run_local_topics(inp: LocalTopicInput) -> LocalTopicOutput:
    for p in inp.platforms:
        if p not in PLATFORMS_T:
            raise WorkflowError("WF-T002-PLAT", f"平台 {p} 不在 {PLATFORMS_T}")
    if not inp.cities:
        raise WorkflowError("WF-T002-CITY", "至少 1 个城市")

    topics: List[TopicItem] = []
    for i in range(inp.count):
        city = inp.cities[i % len(inp.cities)]
        persona = inp.persona_segments[i % len(inp.persona_segments)]
        platform = inp.platforms[i % len(inp.platforms)]
        topics.append(_gen_topic(city, persona, platform, i))

    return LocalTopicOutput(
        total=len(topics),
        cities_covered=inp.cities,
        platforms_covered=inp.platforms,
        topics=topics,
    )


validate_json = lambda s: validate_workflow_json(s, LocalTopicInput)
validate_yaml = lambda s: validate_workflow_yaml(s, LocalTopicInput)