"""adapters/platform/public_metadata.py
从单个作品 URL 拉取公开元数据（mock）。
view_count 强制标注 'mock-not-real'；rights_status 强制 unknown。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .permission_gate import check


@dataclass
class MetadataResult:
    source_url: str
    source_platform: str
    title: str
    author: str
    published_at: str
    media_meta: Dict[str, Any]
    rights_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_url":       self.source_url,
            "source_platform": self.source_platform,
            "title":           self.title,
            "author":          self.author,
            "published_at":   self.published_at,
            "media_meta":      self.media_meta,
            "rights_status":   self.rights_status,
        }


def extract(work_url: str) -> dict:
    """从作品 URL 提取公开元数据。

    所有字段均为 mock：
    - view_count 强制为 'mock-not-real'
    - duration_sec 固定为 0（未知）
    - rights_status 强制为 'unknown'

    Args:
        work_url: 单个作品的 URL

    Returns:
        {
            "source_url": str,
            "source_platform": str,
            "title": str,
            "author": str,
            "published_at": str,
            "media_meta": {"duration_sec": 0, "view_count": "mock-not-real"},
            "rights_status": "unknown",
        }
    """
    perm = check(work_url)
    platform = perm["source_platform"]

    # 从 URL 中尝试提取 work_id
    work_id = "unknown"
    if "/work/" in work_url:
        parts = work_url.rstrip("/").split("/work/")
        if len(parts) == 2:
            work_id = parts[1].split("/")[0]

    title_map = {
        "douyin":       "[MOCK] 抖音作品",
        "xiaohongshu":  "[MOCK] 小红书笔记",
        "weibo":        "[MOCK] 微博动态",
        "video_weixin": "[MOCK] 视频号内容",
        "kuaishou":     "[MOCK] 快手视频",
        "wechat_mp":    "[MOCK] 公众号图文",
        "bilibili":     "[MOCK] B站视频",
        "example":      "[MOCK] 示例作品",
    }
    title = title_map.get(platform, "[MOCK] 未知平台作品")

    return MetadataResult(
        source_url=work_url,
        source_platform=platform,
        title=title,
        author=f"mock_author_{platform}",
        published_at="2026-10-10T00:00:00Z",
        media_meta={
            "duration_sec": 0,
            "view_count": "mock-not-real",
        },
        rights_status="unknown",
    ).to_dict()


class PublicMetadataExtractor:
    """面向对象封装。"""

    @staticmethod
    def extract(url: str) -> dict:
        return extract(url)
