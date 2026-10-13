"""V4 — WorkBuddy connector bridge
把 CloudTech V4 workpath 接到 D:\AIOS\_relinked\workbuddy\ 100+ connector
具体 connector (kling / yihook / tiktok) 是真实可调, 但本桥只暴露 mock 接口
真实 HTTP 调用需 L4 user 拍板 + BudgetGate reserve
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


WORKBUDDY_ROOT = Path("D:/AIOS/_relinked/workbuddy/plugins/marketplaces/workbuddy-connector-plugins-official/connectors")


class WorkBuddyBridge:
    """扫描 + 列出 connector; 调用走 mock 接口 (不直发 HTTP)"""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or WORKBUDDY_ROOT
        self._connectors: Dict[str, Dict[str, Any]] = {}

    def scan(self) -> int:
        """扫描 root 下所有含 mcp.json 的 connector"""
        if not self.root.exists():
            return 0
        count = 0
        for mcp_json in self.root.rglob("mcp.json"):
            try:
                data = json.loads(mcp_json.read_text(encoding="utf-8", errors="ignore"))
                if not isinstance(data, dict):
                    continue
                name = mcp_json.parent.name
                self._connectors[name] = {
                    "path": str(mcp_json.parent),
                    "mcp_config": data,
                    "skills": self._list_skills(mcp_json.parent),
                }
                count += 1
            except Exception:
                continue
        return count

    def _list_skills(self, connector_path: Path) -> List[str]:
        skills_dir = connector_path / "skills"
        if not skills_dir.exists():
            return []
        return [d.name for d in skills_dir.iterdir() if d.is_dir()]

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._connectors.get(name)

    def list_all(self) -> List[str]:
        return sorted(self._connectors.keys())

    def filter_by_skill(self, skill_name: str) -> List[str]:
        """找出含指定 skill 的 connector"""
        return [
            name for name, info in self._connectors.items()
            if skill_name in info.get("skills", [])
        ]

    def call_skill(self, connector_name: str, skill_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Mock 调用 — 真实 HTTP 由 user 拍板后接通
        返回 mock 输出 + 标注"""
        c = self.get(connector_name)
        if c is None:
            return {"ok": False, "error": f"connector '{connector_name}' 未注册", "mock": True}
        if skill_name not in c.get("skills", []):
            return {"ok": False, "error": f"skill '{skill_name}' 不在 '{connector_name}'", "mock": True}
        # mock 输出 (顶层 mock=True 便于断言)
        return {
            "ok": True,
            "connector": connector_name,
            "skill": skill_name,
            "payload_received": payload,
            "result": {"url": "mock://workbuddy/" + connector_name + "/" + skill_name, "mock": True},
            "actual_cost_cents": 0,
            "provider_req_id": f"wb_mock_{connector_name}_{skill_name}",
            "mock": True,
        }


# 已知关键 connector (从 audit report)
KEY_CONNECTORS = {
    "kling-ai-plugin": {
        "endpoint": "https://klingai.com/mcp/plugin",
        "auth": "KLING_ACCESS_KEY + KLING_SECRET_KEY (in mcp_credentials.env)",
        "capabilities": ["video.generate", "video.extend", "video.image_to_video"],
        "v4_relevance": "WP-GROWTH-VIDEO 核心",
    },
    "yihook": {
        "endpoint": "https://app.yihook.cn/api/mcp",
        "auth": "需要 user 拍板",
        "capabilities": ["image.generate (gpt-image-2)", "lipsync-avatar", "photo-avatar", "product-video", "video-enhancement"],
        "v4_relevance": "WP-PRODUCT-MARKETING + WP-RENOVATION-FULL fallback",
    },
    "tiktok": {
        "endpoint": "https://business-api.tiktok.com/open_mcp/tt-ads-mcp-flat",
        "auth": "TikTok Business OAuth",
        "capabilities": ["tiktok-shop-product-extraction"],
        "v4_relevance": "WP-PRODUCT-MARKETING 数据源",
    },
    "douyin": {
        "endpoint": "https://mcp.tikhub.io/douyin/mcp",
        "auth": "TIKHUB_TOKEN (已注册到 .mcp.json)",
        "capabilities": ["公开主页元数据抓取", "公开作品列表"],
        "v4_relevance": "WP-BLOGGER-RESEARCH 真实抓取 (未接通)",
    },
    "xiaohongshu": {
        "endpoint": "https://mcp.tikhub.io/xiaohongshu/mcp",
        "auth": "TIKHUB_TOKEN",
        "capabilities": ["公开笔记元数据"],
        "v4_relevance": "WP-BLOGGER-RESEARCH + WP-ARTICLE-REWRITE",
    },
}
