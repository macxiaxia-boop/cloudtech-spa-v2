"""tests/test_adapters_article.py — CloudTech V4 WP-ARTICLE-REWRITE adapter 测试"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.article.article_parser import parse, ArticleParser
from adapters.article.media_extractor import extract, MediaExtractor
from adapters.article.license_checker import check, LicenseChecker


# ─── Article Parser ───────────────────────────────────────────────────────────

class TestArticleParser:
    def test_parse_returns_typed_contract(self):
        result = parse("https://mp.weixin.qq.com/s/example")
        assert isinstance(result, dict)
        for field in ["source_url", "source_platform", "title", "author",
                       "published_at", "html", "text", "media_refs",
                       "retrieval_policy"]:
            assert field in result
        assert result["mock"] is True

    def test_parse_generates_1000_chars_text(self):
        result = parse("https://mp.weixin.qq.com/s/example")
        assert len(result["text"]) >= 500  # 约 1000 字的样本

    def test_parse_includes_media_refs(self):
        result = parse("https://mp.weixin.qq.com/s/example")
        assert isinstance(result["media_refs"], list)
        assert len(result["media_refs"]) == 3

    def test_parse_platform_detection(self):
        result = parse("https://www.xiaohongshu.com/explore/abc")
        assert result["source_platform"] == "小红书"

        result2 = parse("https://www.bilibili.com/video/BV123")
        assert result2["source_platform"] == "哔哩哔哩"

    def test_parse_html_contains_title(self):
        result = parse("https://juejin.cn/post/123")
        assert "<h1>" in result["html"]
        assert "AI 技术如何赋能现代企业运营" in result["html"]


# ─── Media Extractor ─────────────────────────────────────────────────────────

class TestMediaExtractor:
    def test_extract_images(self):
        html = '<img src="https://example.com/a.jpg" alt="图片A" width="800" height="600">'
        result = extract(html)
        assert len(result["images"]) == 1
        assert result["images"][0]["url"] == "https://example.com/a.jpg"
        assert result["images"][0]["alt"] == "图片A"
        assert result["images"][0]["width"] == 800
        assert result["images"][0]["height"] == 600

    def test_extract_videos(self):
        html = '<video><source src="https://example.com/v.mp4"></video>'
        result = extract(html)
        assert len(result["videos"]) >= 1

    def test_media_license_defaults_unknown(self):
        html = '<img src="https://example.com/photo.png">'
        result = extract(html)
        assert result["images"][0]["license"] == "unknown_need_user_confirm"

    def test_multiple_images(self):
        html = """
        <img src="http://a.com/1.jpg">
        <img src="http://b.com/2.png" alt="截图">
        <img src="http://c.com/3.gif">
        """
        result = extract(html)
        assert len(result["images"]) == 3

    def test_empty_html(self):
        result = extract("")
        assert result["images"] == []
        assert result["videos"] == []


# ─── License Checker ──────────────────────────────────────────────────────────

class TestLicenseChecker:
    def test_wikimedia_public_domain(self):
        ref = {"url": "https://commons.wikimedia.org/wiki/File:Example.png",
               "alt": "", "width": 100, "height": 100, "license": ""}
        result = check(ref)
        assert result["license"] == "public_domain"
        assert result["mock"] is True

    def test_pixabay_public_domain(self):
        ref = {"url": "https://pixabay.com/photos/cat-silhouette-123456/",
               "alt": "", "width": None, "height": None, "license": ""}
        result = check(ref)
        assert result["license"] == "public_domain"

    def test_bilibili_commercial_unknown(self):
        ref = {"url": "https://i0.hdslb.com/bfs/repo/abc.jpg",
               "alt": "", "width": None, "height": None, "license": ""}
        result = check(ref)
        assert result["license"] == "commercial_unknown"

    def test_douyin_commercial_unknown(self):
        ref = {"url": "https://v.douyin.com/abc123",
               "alt": "", "width": None, "height": None, "license": ""}
        result = check(ref)
        assert result["license"] == "commercial_unknown"

    def test_unknown_url_is_unknown(self):
        ref = {"url": "https://random-site.com/image.png",
               "alt": "", "width": None, "height": None, "license": ""}
        result = check(ref)
        assert result["license"] == "unknown"

    def test_commercial_not_mislabeled_ccby(self):
        """严格性: commercial_unknown 不应误标 cc-by"""
        ref = {"url": "https://v.douyin.com/abc123", "alt": "", "width": None, "height": None, "license": ""}
        result = check(ref)
        assert result["license"] != "cc-by"

        ref2 = {"url": "https://i0.hdslb.com/bfs/repo/abc.jpg",
                "alt": "", "width": None, "height": None, "license": ""}
        result2 = check(ref2)
        assert result2["license"] != "cc-by"

    def test_check_returns_mock_true(self):
        ref = {"url": "https://example.com/img.jpg", "alt": "", "width": None, "height": None, "license": ""}
        result = check(ref)
        assert result["mock"] is True

    def test_source_platform_passed_to_check(self):
        ref = {"url": "https://example.com/video.mp4",
               "alt": "视频", "width": 1920, "height": 1080, "license": ""}
        result = check(ref, source_platform="微信公众平台")
        assert result["media_url"] == "https://example.com/video.mp4"
