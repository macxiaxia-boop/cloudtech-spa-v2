"""Search authors from a caller-supplied, attributed catalog only.

This is deterministic local filtering, NOT live Douyin/XHS scraping.
The V4 registry returns an explicit block if no source catalog is provided.
"""
from __future__ import annotations
from typing import Any


class LocalAuthorSearch:
    def search_authors(self, keywords: list[str], *, platform: str = "",
                       catalog: list[dict[str, Any]] | None = None) -> dict:
        if catalog is None:
            return {
                "status": "blocked", "error_code": "AUTHOR_CATALOG_REQUIRED",
                "reason": "No authorized source catalog supplied; no platform was queried",
                "mock": False,
            }
        if not isinstance(catalog, list) or len(catalog) > 5000:
            raise ValueError("catalog must be a list of at most 5000 items")
        terms = [term.casefold().strip() for term in keywords
                 if isinstance(term, str) and term.strip()]
        if not terms:
            raise ValueError("at least one non-empty keyword required")
        matching: list[dict[str, Any]] = []
        for entry in catalog:
            if not isinstance(entry, dict):
                continue
            if platform and entry.get("platform") != platform:
                continue
            searchable = " ".join(
                str(entry.get(k, "")) for k in ("name", "handle", "bio", "category")
            ).casefold()
            if any(term in searchable for term in terms):
                matching.append(entry)
        return {
            "status": "completed",
            "items": matching,
            "total": len(matching),
            "source": "caller_supplied_catalog",
            "provider_called": False,
            "mock": False,
        }
