"""Actual aggregation of supplied platform metrics. No fabricated counters."""
from __future__ import annotations
from typing import Any


def _nonnegative_count(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer from source data")
    return value


class LocalMetrics:
    def fetch_videos(self, author_id: str, records: list[dict] | None = None) -> dict:
        if records is None:
            return {
                "status": "blocked",
                "error_code": "SOURCE_METRICS_REQUIRED",
                "reason": "No attributed video metrics supplied; zero platforms were queried",
                "mock": False,
            }
        if not isinstance(records, list) or len(records) > 10000:
            raise ValueError("records must contain up to 10000 items")
        seen: set[str] = set()
        selected: list[dict] = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("each metrics record must be an object")
            if author_id and record.get("author_id") != author_id:
                continue
            work_id = record.get("work_id")
            if not isinstance(work_id, str) or not work_id:
                raise ValueError("each metrics record must have an attributed work_id")
            if work_id in seen:
                continue
            seen.add(work_id)
            selected.append(record)
        totals = {name: 0 for name in (
            "view_count", "like_count", "comment_count", "share_count",
        )}
        for record in selected:
            for name in totals:
                totals[name] += _nonnegative_count(record.get(name), name)
        n = len(selected)
        engagement = totals["like_count"] + totals["comment_count"] + totals["share_count"]
        return {
            "status": "completed",
            "author_id": author_id,
            "total_videos": n,
            "total_views": totals["view_count"],
            "total_likes": totals["like_count"],
            "total_comments": totals["comment_count"],
            "total_shares": totals["share_count"],
            "average_views": round(totals["view_count"] / n, 2) if n else 0,
            "engagement_rate": round(engagement / totals["view_count"], 6)
                               if totals["view_count"] else 0,
            "source": "caller_supplied_records",
            "provider_called": False,
            "mock": False,
        }
