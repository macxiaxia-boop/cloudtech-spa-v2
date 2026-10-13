"""adapters/platform/catalog_builder.py
对 parse_homepage 输出去重，生成 unique catalog。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .homepage_parser import WorkItem


@dataclass
class CatalogResult:
    unique_items: List[Dict[str, Any]]
    dropped_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unique_items": self.unique_items,
            "dropped_count": self.dropped_count,
        }


def build_catalog(parsed: dict) -> dict:
    """对 parse_homepage 返回的 dict 去重。

    去重逻辑：以 work_id 为主键，保留首次出现的 item；
    同一 work_id 出现多次只保留第一条。

    Args:
        parsed: parse_homepage() 返回的 dict（含 items 列表）

    Returns:
        {
            "unique_items": [WorkItem, ...],
            "dropped_count": int,
        }
    """
    raw_items: List[dict] = parsed.get("items", [])
    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []

    for item in raw_items:
        wid = item.get("work_id", "")
        if wid and wid not in seen:
            seen.add(wid)
            unique.append(item)

    dropped = len(raw_items) - len(unique)
    return CatalogResult(
        unique_items=unique,
        dropped_count=dropped,
    ).to_dict()


class CatalogBuilder:
    """面向对象封装。"""

    @staticmethod
    def build(parsed: dict) -> dict:
        return build_catalog(parsed)
