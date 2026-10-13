r"""V4 — TikHub MCP 真实 connector
5 端点 LIVE 在 C:\Users\xinzh\.claude\.mcp.json
真实调用需 L4 user 拍 TIKHUB_TOKEN (BETA tier 免费额度有限)
本文件只写真实 HTTP 客户端代码, 默认 mock
"""
from __future__ import annotations
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


TIKHUB_ENDPOINTS = {
    "douyin": "https://mcp.tikhub.io/douyin/mcp",
    "xiaohongshu": "https://mcp.tikhub.io/xiaohongshu/mcp",
    "wechat": "https://mcp.tikhub.io/wechat/mcp",
    "weibo": "https://mcp.tikhub.io/weibo/mcp",
    "kuaishou": "https://mcp.tikhub.io/kuaishou/mcp",
}


@dataclass
class TikHubConnector:
    """TikHub 5 平台 MCP connector (streamable-http)
    默认 mock; 真实调用需 enable_real=True + TIKHUB_TOKEN env
    """
    enable_real: bool = False
    timeout_sec: int = 60

    def _get_token(self) -> str:
        token = os.environ.get("TIKHUB_TOKEN")
        if not token:
            raise PermissionError("[TIK] TIKHUB_TOKEN 未设置; 真实调用需 L4 user 拍 (R61 实证: BETA tier)")
        return token

    def _call(self, platform: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if platform not in TIKHUB_ENDPOINTS:
            raise ValueError(f"[TIK] 未知平台 {platform}")
        if not self.enable_real:
            # mock 输出 — 真实公开元数据样板
            return self._mock_response(platform, method, params)
        try:
            import httpx
        except ImportError:
            raise RuntimeError("[TIK] httpx 未安装")
        # TikHub 真实 endpoint: api.tikhub.io/api/v1/{platform}/web/...
        # Cloudflare UA 拦截 → 必须带 browser-like UA
        import os
        token = os.environ.get("TIKHUB_TOKEN") or self._get_token()
        url = self._tikhub_url(platform, method)
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": "https://www.tikhub.io",
            "Referer": "https://www.tikhub.io/",
        }
        t0 = time.time()
        r = httpx.get(url, headers=headers, params=params, timeout=self.timeout_sec)
        if r.status_code != 200:
            raise RuntimeError(f"[TIK] {platform} HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    def _tikhub_url(self, platform: str, method: str) -> str:
        """TikHub v1 endpoint 映射"""
        METHOD_TO_ENDPOINT = {
            "douyin": "douyin/web/handler_user_profile",
            "xiaohongshu": "xiaohongshu/web/fetch_user_info",
            "wechat": "wechat/web/fetch_search_result",
            "weibo": "weibo/web/fetch_user_statuses",
            "kuaishou": "kuaishou/web/fetch_user_photo",
        }
        ep = METHOD_TO_ENDPOINT.get(platform)
        if not ep:
            raise ValueError(f"[TIK] 无 endpoint 映射 for {platform}")
        return f"https://api.tikhub.io/api/v1/{ep}"

    def _mock_response(self, platform: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """模拟 TikHub 返回 — 标注 mock"""
        url = params.get("url", params.get("homepage_url", ""))
        # 5 个样本 work_id (mock)
        return {
            "ok": True,
            "platform": platform,
            "method": method,
            "source_url": url,
            "items": [
                {"work_id": f"w_{i:03d}", "title": f"{platform}_mock_title_{i}",
                 "published_at": "2026-10-01T00:00:00Z",
                 "url": f"https://{platform}.example.com/w_{i:03d}",
                 "view_count": 1000 + i * 100, "mock": True}
                for i in range(1, 6)
            ],
            "retrieved_at": time.time(),
            "rate_limit_remaining": 95,
            "mock": True,
        }

    # === 5 平台特定方法 ===

    def douyin_homepage(self, url: str, limit: int = 30) -> Dict[str, Any]:
        # TikHub 需要 sec_user_id (uid), 尝试从 URL 提取或硬编码测试
        sec_user_id = self._extract_sec_user_id(url) or "MS4wLjABAAAA"
        return self._call("douyin", "fetch_user_homepage", {"sec_user_id": sec_user_id, "max_cursor": 0, "count": limit})

    def xiaohongshu_homepage(self, url: str, limit: int = 30) -> Dict[str, Any]:
        return self._call("xiaohongshu", "fetch_user_homepage", {"url": url, "limit": limit})

    def wechat_video_account(self, url: str, limit: int = 30) -> Dict[str, Any]:
        return self._call("wechat", "fetch_account_videos", {"url": url, "limit": limit})

    def weibo_homepage(self, url: str, limit: int = 30) -> Dict[str, Any]:
        return self._call("weibo", "fetch_user_posts", {"url": url, "limit": limit})

    def kuaishou_homepage(self, url: str, limit: int = 30) -> Dict[str, Any]:
        return self._call("kuaishou", "fetch_user_videos", {"url": url, "limit": limit})

    @staticmethod
    def _extract_sec_user_id(url: str) -> Optional[str]:
        """从抖音 URL 提取 sec_user_id (无 → None)"""
        import re
        # 形如 https://www.douyin.com/user/MS4wLjABAAAA
        m = re.search(r"/user/([A-Za-z0-9_-]+)", url)
        if m:
            return m.group(1)
        return None


# === 接入 V4 HomepageParser ===

def homepage_via_tikhub(url: str, platform_hint: Optional[str] = None, enable_real: bool = False) -> Dict[str, Any]:
    """V4 接入: 平台 URL → TikHub → catalog
    platform_hint: 'douyin' / 'xiaohongshu' / 'wechat' / 'weibo' / 'kuaishou' / None=auto
    enable_real: 默认 False (mock); 真实需 L4 user 拍 + TIKHUB_TOKEN
    """
    if platform_hint is None:
        # 简单启发式 — 真实应 URL pattern 匹配
        if "douyin.com" in url:
            platform_hint = "douyin"
        elif "xiaohongshu.com" in url or "xhs" in url:
            platform_hint = "xiaohongshu"
        elif "weixin.qq.com" in url or "channels.weixin" in url:
            platform_hint = "wechat"
        elif "weibo.com" in url or "weibo.cn" in url:
            platform_hint = "weibo"
        elif "kuaishou.com" in url or "gifshow.com" in url:
            platform_hint = "kuaishou"
        else:
            platform_hint = "douyin"  # 默认 fallback
    connector = TikHubConnector(enable_real=enable_real)
    method = {
        "douyin": connector.douyin_homepage,
        "xiaohongshu": connector.xiaohongshu_homepage,
        "wechat": connector.wechat_video_account,
        "weibo": connector.weibo_homepage,
        "kuaishou": connector.kuaishou_homepage,
    }.get(platform_hint)
    if method is None:
        raise ValueError(f"[TIK-V4] 不支持平台 {platform_hint}")
    return method(url)
