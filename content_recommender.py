"""
内容推荐引擎 — Content Recommendation Engine
基于表现数据·历史产出·GEO趋势 自动推荐选题
"""
import json
from pathlib import Path
from datetime import datetime
from collections import Counter

BASE = Path(__file__).parent


def recommend_topics(tid: str, city: str = "厦门", count: int = 5) -> dict:
    """基于多维数据推荐选题"""
    recommendations = []

    # 维度1: 历史高表现话题
    from content_analytics import get_content_performance
    perf = get_content_performance(tid, 90)
    high_perf_keywords = _extract_keywords(perf.get("entries", []))

    # 维度2: 本地GEO热点
    geo_keywords = _get_geo_trends(city)

    # 维度3: 内容日历缺口
    calendar_gaps = _get_calendar_gaps(tid)

    # 维度4: 竞争对手分析
    competitor_topics = _get_competitor_topics(city)

    # 综合推荐
    all_topics = high_perf_keywords + geo_keywords + calendar_gaps + competitor_topics
    topic_scores = Counter(all_topics)

    for topic, score in topic_scores.most_common(count):
        recommendations.append({
            "topic": topic, "score": score,
            "sources": _trace_sources(topic, high_perf_keywords, geo_keywords, calendar_gaps, competitor_topics),
        })

    return {
        "tenant_id": tid, "city": city,
        "recommendations": recommendations,
        "generated_at": datetime.now().isoformat()[:19],
    }


def _extract_keywords(entries: list) -> list:
    """从高表现内容提取关键词"""
    words = []
    for e in entries:
        metrics = e.get("metrics", {})
        engagement = metrics.get("likes", 0) + metrics.get("shares", 0) * 2 + metrics.get("saves", 0) * 3
        if engagement > 10:
            words.append(f"装修风格_{e.get('platform', '')}")
            words.append(f"装修预算_{e.get('platform', '')}")
    return words if words else ["厨房改造", "卫生间翻新", "老房改造"]


def _get_geo_trends(city: str) -> list:
    """本地GEO趋势关键词"""
    base = ["旧房翻新", "厨房改造", "卫生间改造", "全屋定制", "适老化改造"]
    return [f"{city}{t}" for t in base[:3]]


def _get_calendar_gaps(tid: str) -> list:
    """内容日历缺口"""
    from content_scheduler import get_calendar
    cal = get_calendar(tid, 7)
    gaps = []
    for day in cal.get("calendar", []):
        if not day["scheduled"]:
            gaps.append(f"{day['date']}缺内容")
    return gaps[:3] if gaps else ["周末内容", "工作日避坑"]


def _get_competitor_topics(city: str) -> list:
    """竞品热门话题"""
    return [f"{city}装修避坑", f"{city}装修预算", f"{city}装修案例"]


def _trace_sources(topic: str, *sources) -> list:
    """追溯推荐来源"""
    result = []
    names = ["历史高表现", "GEO趋势", "日历缺口", "竞品分析"]
    for i, src in enumerate(sources):
        if topic in src:
            result.append(names[i])
    return result
