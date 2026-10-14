"""adapters/platform/homepage_parser.py
解析平台创作者主页，生成 mock catalog。
严禁假装版权清晰；所有 rights_status 必须是 unknown_need_user_confirm。
"""
from __future__ import annotations
import os

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .permission_gate import check


MOCK_AUTHORS: Dict[str, str] = {
    "douyin":       "douyin_creator_001",
    "xiaohongshu":  "xhs_author_001",
    "weibo":        "weibo_user_001",
    "video_weixin": "video_weixin_001",
    "kuaishou":     "kuaishou_creator_001",
    "wechat_mp":    "wechat_mp_001",
    "bilibili":     "bilibili_up_001",
    "example":      "example_author",
}


MOCK_TITLES: List[str] = [
    "AI 时代内容创作方法论",
    "短视频爆款标题公式分享",
    "私域引流全链路拆解",
    "从 0 到 1 打造个人 IP",
    "内容复利：自动化生产秘籍",
]


@dataclass
class WorkItem:
    work_id: str
    title: str
    published_at: str
    url: str
    transcript_url: Optional[str]
    cover_url: Optional[str]
    frame_urls: List[str]
    rights_status: str = "unknown_need_user_confirm"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "work_id":        self.work_id,
            "title":          self.title,
            "published_at":   self.published_at,
            "url":            self.url,
            "transcript_url": self.transcript_url,
            "cover_url":      self.cover_url,
            "frame_urls":     self.frame_urls,
            "rights_status": self.rights_status,
        }


@dataclass
class HomepageResult:
    source_platform: str
    source_url: str
    source_author: str
    items: List[WorkItem]
    retrieved_policy: str = "mock"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_platform": self.source_platform,
            "source_url":     self.source_url,
            "source_author":  self.source_author,
            "items":          [i.to_dict() for i in self.items],
            "retrieved_policy": self.retrieved_policy,
        }


def parse_homepage(url: str, limit: int = 30) -> dict:
    """解析创作者主页 URL，返回 mock catalog dict。

    Args:
        url: 创作者主页 URL
        limit: 最大返回条数（默认 30）

    Returns:
        {
            "source_platform": str,
            "source_url": str,
            "source_author": str,
            "items": [WorkItem, ...],
            "retrieved_policy": "mock",
        }

    注意：
    - 所有 rights_status 强制为 'unknown_need_user_confirm'
    - 永不返回 'rights_cleared' / 'likely_fair_use' 等模糊状态
    """
    if not (
        os.environ.get("CLOUDTECH_ENV", "").lower() in {"test", "development"}
        and os.environ.get("CLOUDTECH_ALLOW_MOCK_PLATFORM") == "1"
    ):
        raise RuntimeError(
            "[PLATFORM-MOCK-403] Public homepage connector not linked; "
            "refusing to fabricate author works"
        )
    perm = check(url)
    if not perm["allowed"]:
        raise PermissionError(f"[PLATFORM-403] {perm['reason']}")
    platform = perm["source_platform"]
    author = MOCK_AUTHORS.get(platform, f"{platform}_unknown")

    n = min(limit, 5)
    items: List[WorkItem] = []
    for i in range(n):
        idx = i + 1
        wid = f"w{idx:03d}"
        base = url.rstrip("/")
        items.append(
            WorkItem(
                work_id=wid,
                title=f"[MOCK] {MOCK_TITLES[i % len(MOCK_TITLES)]} #{idx}",
                published_at=f"2026-10-{10 - i:02d}T08:00:00Z",
                url=f"{base}/work/{wid}",
                transcript_url=f"{base}/work/{wid}/transcript",
                cover_url=f"{base}/work/{wid}/cover.jpg",
                frame_urls=[
                    f"{base}/work/{wid}/frame_0001.jpg",
                    f"{base}/work/{wid}/frame_0002.jpg",
                ],
                rights_status="unknown_need_user_confirm",
            )
        )

    return HomepageResult(
        source_platform=platform,
        source_url=url,
        source_author=author,
        items=items,
        retrieved_policy="mock",
    ).to_dict()


class HomepageParser:
    """面向对象封装。"""

    @staticmethod
    def parse(url: str, limit: int = 30) -> dict:
        return parse_homepage(url, limit)
