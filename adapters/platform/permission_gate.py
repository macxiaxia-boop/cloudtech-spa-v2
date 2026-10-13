"""adapters/platform/permission_gate.py
平台权限门控 — 白名单/黑名单判断。
所有判断为 mock 数据，不调真实 API。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# 已知的公开创作平台白名单（大小写不敏感）
WHITELIST_DOMAINS: set[str] = {
    "douyin.com",          # 抖音
    "xiaohongshu.com",     # 小红书
    "weibo.com",           # 微博
    "channels.weixin.qq.com",  # 视频号
    "kuaishou.com",        # 快手
    "mp.weixin.qq.com",    # 微信公众号
    "bilibili.com",        # B 站
}

# 明确私域 / DRM / 付费墙黑名单
BLACKLIST_PATTERNS: set[str] = {
    "private",
    "drm",
    "paywall",
    "membership",
    "subscription",
}


@dataclass
class PermissionResult:
    allowed: bool
    reason: str
    source_platform: str
    rate_limit_remaining: int

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "source_platform": self.source_platform,
            "rate_limit_remaining": self.rate_limit_remaining,
        }


def _detect_platform(url: str) -> str:
    """根据 URL 推断平台名称。"""
    u = url.lower()
    if "douyin.com" in u:
        return "douyin"
    if "xiaohongshu.com" in u:
        return "xiaohongshu"
    if "weibo.com" in u:
        return "weibo"
    if "channels.weixin.qq.com" in u:
        return "video_weixin"
    if "kuaishou.com" in u:
        return "kuaishou"
    if "mp.weixin.qq.com" in u:
        return "wechat_mp"
    if "bilibili.com" in u:
        return "bilibili"
    if "example.com" in u:
        return "example"
    return "unknown"


def _is_blacklisted(url: str) -> bool:
    """检查是否匹配黑名单 pattern。"""
    u = url.lower()
    return any(pat in u for pat in BLACKLIST_PATTERNS)


def check(
    homepage_url: str,
    platform_hint: Optional[str] = None,
) -> dict:
    """检查 homepage_url 是否允许抓取。

    规则：
    - example.com / 公开测试域 → allowed=True, reason=OK
    - 白名单平台 → allowed=True, reason=OK
    - 黑名单 pattern → allowed=False, reason=BLOCKED_PRIVATE_OR_DRM
    - 其它平台 → allowed=True, reason=NEED_OAUTH_FALLBACK_PLACEHOLDER
    - rate_limit_remaining 全部 mock 为 100

    Returns:
        dict with keys: allowed, reason, source_platform, rate_limit_remaining
    """
    if _is_blacklisted(homepage_url):
        return PermissionResult(
            allowed=False,
            reason="BLOCKED_PRIVATE_OR_DRM",
            source_platform=_detect_platform(homepage_url),
            rate_limit_remaining=0,
        ).to_dict()

    detected = _detect_platform(homepage_url)

    # 白名单直接放行
    if detected in (
        "douyin",
        "xiaohongshu",
        "weibo",
        "video_weixin",
        "kuaishou",
        "wechat_mp",
        "bilibili",
        "example",
    ):
        return PermissionResult(
            allowed=True,
            reason="OK",
            source_platform=detected,
            rate_limit_remaining=100,
        ).to_dict()

    # 其它平台允许但标注需 OAuth fallback
    return PermissionResult(
        allowed=True,
        reason="NEED_OAUTH_FALLBACK_PLACEHOLDER",
        source_platform=detected,
        rate_limit_remaining=100,
    ).to_dict()


class PermissionGate:
    """面向对象封装。"""

    @staticmethod
    def check(url: str, platform_hint: Optional[str] = None) -> dict:
        return check(url, platform_hint)
