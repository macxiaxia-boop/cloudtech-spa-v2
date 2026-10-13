"""CloudTech V4 — 相似性审查 (mock-only, 基于 difflib)"""
import difflib
import re
from typing import TypedDict


class FlaggedPhrase(TypedDict):
    phrase: str
    start: int
    end: int


class ReviewResult(TypedDict):
    similarity_score: float
    ngram_overlap: float
    flagged_phrases: list[FlaggedPhrase]
    verdict: str
    notes: str
    mock: bool


def _tokenize(text: str) -> list[str]:
    """简单分词：中文按单字，英文按空格；限制最大 token 数"""
    if not text:
        return []
    MAX_TOKENS = 3000
    tokens: list[str] = []
    words = text.split()
    for word in words:
        if len(tokens) >= MAX_TOKENS:
            break
        for ch in word:
            if len(tokens) >= MAX_TOKENS:
                break
            tokens.append(ch)
    return tokens


def _ngram_overlap(a: str, b: str, n: int = 3) -> float:
    """计算 n-gram 重叠率 Jaccard"""
    if not a or not b:
        return 0.0
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    ng_a = set(tuple(tokens_a[i : i + n]) for i in range(len(tokens_a) - n + 1))
    ng_b = set(tuple(tokens_b[i : i + n]) for i in range(len(tokens_b) - n + 1))
    if not ng_a or not ng_b:
        return 0.0
    inter = len(ng_a & ng_b)
    union = len(ng_a | ng_b)
    return inter / union if union > 0 else 0.0


def _sequence_similarity(a: str, b: str) -> float:
    """difflib.SequenceMatcher 相似度"""
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _flagged_phrases(original: str, derivative: str) -> list[FlaggedPhrase]:
    """标记 derivative 中与 original 高度相似的连续片段 (>=0.85)"""
    flagged: list[FlaggedPhrase] = []
    if not original or not derivative or len(original) < 5:
        return flagged

    matcher = difflib.SequenceMatcher(None, original, derivative)
    for block in matcher.get_matching_blocks():
        # Python 3.13+ returns 3-tuple (size, i, j); older returns 5-tuple (a, i1, i2, j1, j2)
        if len(block) == 5:
            _, i1, i2, j1, j2 = block
        else:
            size, i1, j1 = block
            i2 = i1 + size
            j2 = j1 + size
        if (i2 - i1) >= 5:
            flagged.append(
                FlaggedPhrase(
                    phrase=derivative[j1:j2],
                    start=j1,
                    end=j2,
                )
            )
    return flagged


def review(original: str, derivative: str, structure: dict) -> ReviewResult:
    """输入原文 vs 原创脚本 → 相似性审查

    Args:
        original: 原始转写文本
        derivative: 生成的原创脚本 (script_text)
        structure: 结构字典 (仅作参考，不影响评分)

    Returns:
        similarity_score / ngram_overlap / flagged_phrases / verdict / notes / mock=True

    threshold:
        < 0.30 → pass
        0.30–0.60 → revise
        > 0.60 → reject

    严禁把高相似度说成低相似度！
    """
    if not original or not derivative:
        raise ValueError("original 和 derivative 都不能为空")

    seq_sim = _sequence_similarity(original, derivative)
    ng_ov = _ngram_overlap(original, derivative)
    flagged = _flagged_phrases(original, derivative)

    # 综合评分：序列相似度为主，ngram 作参考
    similarity_score = round(seq_sim, 3)
    ngram_overlap = round(ng_ov, 3)

    if similarity_score < 0.30:
        verdict = "pass"
        notes = "相似度低，脚本原创性良好"
    elif similarity_score <= 0.60:
        verdict = "revise"
        notes = f"相似度中等 ({similarity_score})，建议润色后使用"
    else:
        verdict = "reject"
        notes = f"相似度过高 ({similarity_score})，需要大幅重写"

    return ReviewResult(
        similarity_score=similarity_score,
        ngram_overlap=ngram_overlap,
        flagged_phrases=flagged,
        verdict=verdict,
        notes=notes,
        mock=True,
    )


class SimilarityQC:
    """相似性审查器封装"""

    def review(self, original: str, derivative: str, structure: dict) -> ReviewResult:
        return review(original, derivative, structure)
