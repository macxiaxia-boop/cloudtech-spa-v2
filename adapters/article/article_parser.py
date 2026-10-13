"""Article Parser — 解析公开文章元数据 + 正文 (mock-only, 禁止调用真实网络)"""
from datetime import datetime
from typing import Literal


def parse(url: str) -> dict:
    """
    返回 {
        source_url: str,
        source_platform: str,
        title: str,
        author: str,
        published_at: str | None,
        html: str,
        text: str,
        media_refs: list[dict],   # [{url, alt}]
        retrieval_policy: str,
        mock: True,
    }

    Mock: 生成 1000 字样本 + 3 个 media_refs。
    """
    # 从 URL 推断 platform
    platform_map = {
        "weixin": "微信公众平台",
        "xiaohongshu": "小红书",
        "douyin": "抖音",
        "bilibili": "哔哩哔哩",
        "juejin": "掘金",
        "zhihu": "知乎",
    }
    source_platform = "微信公众平台"
    for key, name in platform_map.items():
        if key in url.lower():
            source_platform = name
            break

    text = (
        "在当今数字化浪潮中，人工智能技术正以前所未有的速度渗透到各行各业。\n"
        "无论是内容创作、数据分析，还是用户运营，AI 都在重新定义工作的边界。\n"
        "本文将从技术原理、实践方法、商业价值三个维度，系统性地探讨 AI 如何赋能现代企业。\n\n"
        "首先，我们来看技术原理层面。大语言模型（LLM）的核心是 Transformer 架构，"
        "它通过自注意力机制实现对上下文的长程依赖建模。这意味着模型能够理解文章的完整语义，"
        "而不仅仅是孤立的关键词。\n\n"
        "在实践方法上，企业需要关注数据的质量与标注的准确性。高质量的训练数据是模型效果的前提，"
        "而精细化的数据标注则决定了模型在特定任务上的表现。\n\n"
        "从商业价值角度看，AI 的引入可以显著降低人力成本。以内容审核为例，传统人工审核的效率"
        "约为每日千条级别，而 AI 系统的处理速度可以达到每秒数千条，且成本仅为前者的十分之一。\n\n"
        "数据隐私与安全是另一个关键议题。在训练和应用 AI 模型时，企业必须严格遵守相关法律法规，"
        "对用户数据进行脱敏处理，并建立完善的数据访问权限管理机制。\n\n"
        "综上所述，AI 技术的落地需要技术团队与业务团队的紧密协作。只有深入理解业务场景，"
        "才能真正发挥 AI 的价值，为企业创造可持续的竞争优势。"
    )

    return {
        "source_url": url,
        "source_platform": source_platform,
        "title": "AI 技术如何赋能现代企业运营",
        "author": "云数科技研究员",
        "published_at": "2026-10-01T08:00:00+08:00",
        "html": f"<article><h1>AI 技术如何赋能现代企业运营</h1><p>{text}</p></article>",
        "text": text,
        "media_refs": [
            {"url": "https://example.com/img/ai_framework.png",  "alt": "AI 技术框架图"},
            {"url": "https://example.com/img/llm_arch.png",     "alt": "LLM 结构示意"},
            {"url": "https://example.com/video/ai_demo.mp4",   "alt": "AI 应用演示视频"},
        ],
        "retrieval_policy": "mock_content",
        "mock": True,
    }


class ArticleParser:
    def run(self, url: str) -> dict:
        return parse(url)
