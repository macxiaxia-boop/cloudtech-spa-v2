"""License Checker — 评估媒体引用 License (mock-only, 禁止调用真实版权 API)"""
from typing import Literal

MediaRef = dict  # {url, alt, width, height, license}

# 明确无版权或开放许可的平台域名白名单
PUBLIC_DOMAIN_PATTERNS = [
    "commons.wikimedia.org",
    "upload.wikimedia.org",
    "pixabay.com",
    "pexels.com",
    "unsplash.com",
    "github.com",         # 代码截图等
]

CC_BY_PATTERNS = []  # 暂不列入，需 user 拍板

LICENSE_RESULT = Literal["public_domain", "cc-by", "unknown", "commercial_unknown"]


def check(media_ref: MediaRef, source_platform: str = "") -> dict:
    """
    返回 {
        media_url: str,
        license: LICENSE_RESULT,
        notes: str,
        mock: True,
    }

    严格策略:
    - 默认 license = 'unknown' (需 user 确认)
    - 只在明确白名单域名上标 public_domain
    - commercial_unknown: 明确是商业平台但无 license 声明
    """
    url: str = media_ref.get("url", "")

    # 优先判断 public_domain
    for pattern in PUBLIC_DOMAIN_PATTERNS:
        if pattern in url:
            return {
                "media_url": url,
                "license": "public_domain",
                "notes": f"匹配白名单域名: {pattern}",
                "mock": True,
            }

    # 商业平台常见默认 commercial_unknown
    commercial_platforms = ["weixin.qq.com", "bilibili.com", "hdslb.com",
                             "douyin.com", "xiaohongshu.com", "kuaishou.com",
                             "youtube.com", "vip.com", "iqiyi.com", "youku.com"]
    for plat in commercial_platforms:
        if plat in url:
            return {
                "media_url": url,
                "license": "commercial_unknown",
                "notes": f"商业平台资源，license 未知，需用户自行确认: {plat}",
                "mock": True,
            }

    # 默认 unknown
    return {
        "media_url": url,
        "license": "unknown",
        "notes": "未匹配白名单，无法确认 license，请用户自行判断",
        "mock": True,
    }


class LicenseChecker:
    def run(self, media_ref: MediaRef, source_platform: str = "") -> dict:
        return check(media_ref, source_platform)
