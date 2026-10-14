"""adapters/platform/permission_gate.py
平台权限门控 — 白名单/黑名单判断。
所有判断为 mock 数据，不调真实 API。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

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


def _safe_hostname(url: str) -> str:
    """Require a real HTTP(S) host; never classify domains by substring."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname:
            return ""
        if parsed.username is not None or parsed.password is not None:
            return ""
        return parsed.hostname.lower().rstrip(".")
    except (ValueError, TypeError, AttributeError):
        return ""


def _is_subdomain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _detect_platform(url: str) -> str:
    host = _safe_hostname(url)
    if not host:
        return "unknown"
    for domain, platform in (
        ("channels.weixin.qq.com", "video_weixin"),
        ("mp.weixin.qq.com", "wechat_mp"),
        ("douyin.com", "douyin"),
        ("xiaohongshu.com", "xiaohongshu"),
        ("weibo.com", "weibo"),
        ("kuaishou.com", "kuaishou"),
        ("bilibili.com", "bilibili"),
        ("example.com", "example"),
    ):
        if _is_subdomain(host, domain):
            return platform
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

    # Unknown hosts or invalid URLs cannot be treated as authorized.
    return PermissionResult(
        allowed=False,
        reason="PLATFORM_NOT_CONNECTED_OR_INVALID_URL",
        source_platform=detected,
        rate_limit_remaining=0,
    ).to_dict()


class PermissionGate:
    """面向对象封装。"""

    @staticmethod
    def check(url: str, platform_hint: Optional[str] = None) -> dict:
        return check(url, platform_hint)
