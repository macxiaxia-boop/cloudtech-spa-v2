"""CloudTech V4 — 转写结构拆解 (mock-only)"""
import re
from typing import TypedDict


class HookDict(TypedDict):
    text: str
    score: float


class CTADict(TypedDict):
    text: str
    score: float


class BodySegment(TypedDict):
    text: str
    score: float
    keywords: list[str]


class AnalyzeResult(TypedDict):
    hook: HookDict
    body_segments: list[BodySegment]
    cta: CTADict
    duration_sec: float
    structure_template: str
    mock: bool


_PROBLEM_KEYWORDS = ["问题", "痛点", "困难", "烦恼", "困扰", "挑战", "压力", "焦虑"]
_SOLUTION_KEYWORDS = ["解决", "方法", "方案", "技巧", "秘诀", "攻略", "教你", "如何"]
_LISTICLE_KEYWORDS = ["第一", "第二", "第三", "第四", "第五", "六点", "七招", "八个"]
_STORY_KEYWORDS = ["曾经", "后来", "有一天", "故事", "经历", "那时候", "回忆"]


def _heuristic_template(transcript_text: str) -> str:
    """根据关键词启发式判断结构模板"""
    text = transcript_text
    p_score = sum(1 for k in _PROBLEM_KEYWORDS if k in text)
    s_score = sum(1 for k in _SOLUTION_KEYWORDS if k in text)
    l_score = sum(1 for k in _LISTICLE_KEYWORDS if k in text)
    st_score = sum(1 for k in _STORY_KEYWORDS if k in text)

    if l_score >= 3:
        return "listicle"
    if p_score >= 2 and s_score >= 2:
        return "problem-solution-cta"
    if st_score >= 2:
        return "story-arc"
    return "unknown"


def _extract_hook(text: str) -> tuple[str, float]:
    """提取 hook：取前 30 字，评分按感叹/疑问/数字前缀提高"""
    raw = text[:60].strip()
    score = 0.5
    if re.search(r"[!?。]", raw):
        score += 0.1
    if re.search(r"^[\d零一二三四五六七八九十]+", raw):
        score += 0.15
    return raw, min(score, 1.0)


def _extract_cta(text: str) -> tuple[str, float]:
    """提取 CTA：取末 40 字，关键词加权"""
    raw = text[-80:].strip()
    score = 0.5
    cta_keywords = ["关注", "点赞", "评论", "分享", "联系我们", "立即", "现在", "赶紧"]
    score += 0.05 * sum(1 for k in cta_keywords if k in raw)
    return raw, min(score, 1.0)


def _split_body(text: str, template: str) -> list[BodySegment]:
    """按模板启发式切分 body segments"""
    if template == "listicle":
        pattern = r"[\d零一二三四五六七八九十]+[、，,．].{5,}"
    elif template == "problem-solution-cta":
        pattern = r".{20,}?"
    else:
        pattern = r".{40,}?"

    matches = re.findall(pattern, text[30:-80] if len(text) > 160 else text)
    segments: list[BodySegment] = []
    for m in matches[:8]:
        keywords = [k for k in _SOLUTION_KEYWORDS + _PROBLEM_KEYWORDS if k in m]
        segments.append({"text": m.strip(), "score": 0.5 + 0.05 * len(keywords), "keywords": keywords})
    return segments


def analyze(segments: list, transcript_text: str) -> AnalyzeResult:
    """输入转写片段列表 + 原文 → 结构拆解结果

    Args:
        segments: 分段列表 (每段 dict含 text/speaker/timestamp)
        transcript_text: 完整转写文本

    Returns:
        含 hook / body_segments / cta / duration_sec / structure_template / mock=True
    """
    if not transcript_text or not transcript_text.strip():
        raise ValueError("transcript_text 不能为空")

    template = _heuristic_template(transcript_text)
    hook_text, hook_score = _extract_hook(transcript_text)
    cta_text, cta_score = _extract_cta(transcript_text)
    body = _split_body(transcript_text, template)

    # duration 启发式：中文约 400字/分钟
    char_count = len(transcript_text)
    duration_sec = round(char_count / 400 * 60)

    return AnalyzeResult(
        hook={"text": hook_text, "score": hook_score},
        body_segments=body,
        cta={"text": cta_text, "score": cta_score},
        duration_sec=duration_sec,
        structure_template=template,
        mock=True,
    )


class StructureAnalyzer:
    """结构分析器封装"""

    def analyze(self, segments: list, transcript_text: str) -> AnalyzeResult:
        return analyze(segments, transcript_text)
