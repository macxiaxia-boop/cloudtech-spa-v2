"""Deterministic, auditable text analysis for user-provided articles.

No language-model claim, invented marketing copy, content rewriting or
unverified metrics. All evidence is calculated from the actual parsed text.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import re

# These are explicit lexical signals, not sentiment classification or AI.
CTA_WORDS = ("关注", "评论", "私信", "联系", "点击", "订阅", "购买", "报名", "咨询")
QUESTION_WORDS = ("什么", "为什么", "如何", "怎么", "是否", "吗", "呢", "?","？")


def analyze_user_article(parsed: dict) -> dict:
    if not isinstance(parsed, dict) or parsed.get("mock") is not False:
        raise ValueError("only verified user-provided HTML extraction is accepted")
    text = parsed.get("text")
    source_hash = parsed.get("content_sha256")
    if not isinstance(text, str) or not text.strip() or len(text) > 250_000:
        raise ValueError("actual article text missing or beyond limit")
    if not isinstance(source_hash, str) or re.fullmatch("[0-9a-f]{64}", source_hash) is None:
        raise ValueError("source HTML SHA256 is missing")
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    if not paragraphs:
        raise ValueError("no non-empty paragraphs")
    plain = "\n".join(paragraphs)
    paragraphs_metrics = [
        {"index": i, "characters": len(part)}
        for i, part in enumerate(paragraphs)
    ]
    cta_candidates = [
        {"paragraph_index": i, "matched_terms": [word for word in CTA_WORDS if word in part]}
        for i, part in enumerate(paragraphs)
        if any(word in part for word in CTA_WORDS)
    ]
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,8}", plain)
    counter = Counter(word.lower() for word in words)
    return {
        "source_html_sha256": source_hash,
        "text_sha256": sha256(text.encode("utf-8")).hexdigest(),
        "title": parsed.get("title") if isinstance(parsed.get("title"), str) else "",
        "characters": len(text),
        "paragraph_count": len(paragraphs),
        "paragraphs": paragraphs_metrics,
        "opening_excerpt": paragraphs[0][:160],
        "closing_excerpt": paragraphs[-1][-160:],
        "question_marks": text.count("?") + text.count("？"),
        "question_term_matches": [w for w in QUESTION_WORDS if w in plain],
        "cta_term_matches": cta_candidates,
        "lexical_counts": [
            {"term": term, "count": count}
            for term, count in sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:15]
        ],
        "media_reference_counts": {
            "images": len(parsed.get("images", [])) if isinstance(parsed.get("images"), list) else 0,
            "videos": len(parsed.get("videos", [])) if isinstance(parsed.get("videos"), list) else 0,
        },
        "analysis_method": "deterministic_lexical_counts_v1",
        "ai_model_used": False,
        "subjective_quality_rating_provided": False,
        "mock": False,
    }
