"""Media Extractor — 从 HTML 中提取图片/视频引用 (mock-only)"""
import re
from typing import Literal

MediaRef = dict  # {url, alt, width, height, license}


def extract(html: str, base_url: str = "") -> dict:
    """
    返回 {
        images: list[dict],   # [{url, alt, width, height, license}]
        videos: list[dict],   # [{url, alt, width, height, license}]
    }

    - 所有 license 默认 'unknown_need_user_confirm'
    - 只做正则提取，不做网络请求
    """
    images: list[MediaRef] = []
    videos: list[MediaRef] = []

    # <img ... src="..." alt="...">
    for img_match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE):
        url = img_match.group(1)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', img_match.group(0), re.IGNORECASE)
        alt = alt_match.group(1) if alt_match else ""
        # 解析 width/height (简化)
        w_match = re.search(r'width=["\']?(\d+)["\']?', img_match.group(0))
        h_match = re.search(r'height=["\']?(\d+)["\']?', img_match.group(0))
        images.append({
            "url": url,
            "alt": alt,
            "width": int(w_match.group(1)) if w_match else None,
            "height": int(h_match.group(1)) if h_match else None,
            "license": "unknown_need_user_confirm",
        })

    # <video ... src="..."> 或 <source src="...">
    for vid_match in re.finditer(r'<video[^>]*>(?:.*?<source[^>]+src=["\']([^"\']+)["\'][^>]*>)?.*?</video>', html, re.IGNORECASE | re.DOTALL):
        src = vid_match.group(1) if vid_match.group(1) else ""
        if not src:
            src_match = re.search(r'src=["\']([^"\']+)["\']', vid_match.group(0))
            src = src_match.group(1) if src_match else ""
        if src:
            videos.append({
                "url": src,
                "alt": "",
                "width": None,
                "height": None,
                "license": "unknown_need_user_confirm",
            })

    # 独立 <source> 标签
    for src_match in re.finditer(r'<source[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE):
        videos.append({
            "url": src_match.group(1),
            "alt": "",
            "width": None,
            "height": None,
            "license": "unknown_need_user_confirm",
        })

    return {"images": images, "videos": videos}


class MediaExtractor:
    def run(self, html: str, base_url: str = "") -> dict:
        return extract(html, base_url)
