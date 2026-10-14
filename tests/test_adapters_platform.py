"""tests/test_adapters_platform.py
WP-BLOGGER-RESEARCH platform adapters — 全 mock 测试套件。
不调任何真实 API。
"""
from __future__ import annotations

import unittest
from adapters.platform.permission_gate import (
    PermissionGate,
    check,
    WHITELIST_DOMAINS,
    BLACKLIST_PATTERNS,
)
from adapters.platform.homepage_parser import (
    HomepageParser,
    parse_homepage,
    WorkItem,
    MOCK_TITLES,
)
from adapters.platform.catalog_builder import CatalogBuilder, build_catalog
from adapters.platform.public_metadata import PublicMetadataExtractor, extract


# ---------------------------------------------------------------------------
# T1: permission_gate — 白名单放行
# ---------------------------------------------------------------------------
class TestPermissionGateAllowlist(unittest.TestCase):
    def test_douyin_allowed(self):
        r = check("https://www.douyin.com/user/abc123")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["reason"], "OK")
        self.assertEqual(r["source_platform"], "douyin")
        self.assertEqual(r["rate_limit_remaining"], 100)

    def test_xiaohongshu_allowed(self):
        r = check("https://www.xiaohongshu.com/user/profile/xxx")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["source_platform"], "xiaohongshu")

    def test_bilibili_allowed(self):
        r = check("https://space.bilibili.com/123456")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["source_platform"], "bilibili")

    def test_example_domain_allowed(self):
        r = check("https://example.com/creator/page1")
        self.assertTrue(r["allowed"])
        self.assertEqual(r["source_platform"], "example")


# ---------------------------------------------------------------------------
# T2: permission_gate — 黑名单拦截
# ---------------------------------------------------------------------------
class TestPermissionGateBlacklist(unittest.TestCase):
    def test_private_url_blocked(self):
        r = check("https://example.com/private/video")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["reason"], "BLOCKED_PRIVATE_OR_DRM")
        self.assertEqual(r["rate_limit_remaining"], 0)

    def test_paywall_url_blocked(self):
        r = check("https://example.com/paywall/article")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["reason"], "BLOCKED_PRIVATE_OR_DRM")

    def test_drm_url_blocked(self):
        r = check("https://example.com/drm/content")
        self.assertFalse(r["allowed"])


# ---------------------------------------------------------------------------
# T3: permission_gate — 非白名单平台
# ---------------------------------------------------------------------------
class TestPermissionGateFallback(unittest.TestCase):
    def test_unknown_platform_denied_not_falsely_authorized(self):
        r = check("https://www.someunknownplatform.com/user/123")
        self.assertFalse(r["allowed"])
        self.assertEqual(r["reason"], "PLATFORM_NOT_CONNECTED_OR_INVALID_URL")

    def test_lookalike_platform_domain_denied(self):
        for url in (
            "https://douyin.com.evil.example/user/abc",
            "https://evil.example/path/douyin.com/user/abc",
            "https://xiaohongshu.com.attacker.example/profile",
            "https://user:pass@evil.example/redirect?to=douyin.com",
            "file:///etc/passwd",
            "http://127.0.0.1/private",
        ):
            with self.subTest(url=url):
                self.assertFalse(check(url)["allowed"])

    def test_real_subdomain_still_detected(self):
        self.assertEqual(
            check("https://www.douyin.com/user/abc")["source_platform"],
            "douyin",
        )

    def test_permission_gate_class(self):
        r = PermissionGate.check("https://www.douyin.com/user/test")
        self.assertTrue(r["allowed"])


# ---------------------------------------------------------------------------
# T4: permission_gate — 速率限制 mock
# ---------------------------------------------------------------------------
class TestPermissionGateRateLimit(unittest.TestCase):
    def test_rate_limit_remaining_is_100_for_allowed(self):
        for url in [
            "https://www.douyin.com/user/abc",
            "https://www.bilibili.com/video/BV123",
            "https://example.com/public",
        ]:
            with self.subTest(url=url):
                r = check(url)
                self.assertEqual(r["rate_limit_remaining"], 100)

    def test_rate_limit_zero_for_blocked(self):
        r = check("https://example.com/private")
        self.assertEqual(r["rate_limit_remaining"], 0)


# ---------------------------------------------------------------------------
# T5: homepage_parser — 输出符合 typed contract
# ---------------------------------------------------------------------------
class TestHomepageParserContract(unittest.TestCase):
    def test_parse_returns_required_keys(self):
        result = parse_homepage("https://www.douyin.com/user/test")
        for key in ("source_platform", "source_url", "source_author", "items", "retrieved_policy"):
            self.assertIn(key, result)

    def test_retrieved_policy_is_mock(self):
        result = parse_homepage("https://www.bilibili.com/video BV1")
        self.assertEqual(result["retrieved_policy"], "mock")

    def test_items_count_limited(self):
        result = parse_homepage("https://www.douyin.com/user/test", limit=3)
        self.assertLessEqual(len(result["items"]), 3)

    def test_rights_status_unknown_for_all_items(self):
        result = parse_homepage("https://www.xiaohongshu.com/user/profile/xxx")
        for item in result["items"]:
            self.assertEqual(item["rights_status"], "unknown_need_user_confirm")

    def test_work_ids_are_unique(self):
        result = parse_homepage("https://www.douyin.com/user/test")
        ids = [item["work_id"] for item in result["items"]]
        self.assertEqual(sorted(ids), sorted(set(ids)))

    def test_homepage_parser_class(self):
        r = HomepageParser.parse("https://www.kuaishou.com/user/test")
        self.assertIn("items", r)


# ---------------------------------------------------------------------------
# T6: catalog_builder — 去重
# ---------------------------------------------------------------------------
class TestCatalogBuilderDedupe(unittest.TestCase):
    def test_no_drop_when_all_unique(self):
        parsed = {
            "items": [
                {"work_id": "w001", "title": "A", "published_at": "2026-10-10T00:00:00Z",
                 "url": "url1", "transcript_url": None, "cover_url": None, "frame_urls": []},
                {"work_id": "w002", "title": "B", "published_at": "2026-10-09T00:00:00Z",
                 "url": "url2", "transcript_url": None, "cover_url": None, "frame_urls": []},
            ]
        }
        result = build_catalog(parsed)
        self.assertEqual(len(result["unique_items"]), 2)
        self.assertEqual(result["dropped_count"], 0)

    def test_duplicates_dropped(self):
        parsed = {
            "items": [
                {"work_id": "w001", "title": "A", "published_at": "2026-10-10T00:00:00Z",
                 "url": "url1", "transcript_url": None, "cover_url": None, "frame_urls": []},
                {"work_id": "w001", "title": "A duplicate", "published_at": "2026-10-10T00:00:00Z",
                 "url": "url1b", "transcript_url": None, "cover_url": None, "frame_urls": []},
                {"work_id": "w002", "title": "B", "published_at": "2026-10-09T00:00:00Z",
                 "url": "url2", "transcript_url": None, "cover_url": None, "frame_urls": []},
            ]
        }
        result = build_catalog(parsed)
        self.assertEqual(len(result["unique_items"]), 2)
        self.assertEqual(result["dropped_count"], 1)
        self.assertEqual(result["unique_items"][0]["work_id"], "w001")

    def test_empty_items(self):
        parsed = {"items": []}
        result = build_catalog(parsed)
        self.assertEqual(len(result["unique_items"]), 0)
        self.assertEqual(result["dropped_count"], 0)

    def test_catalog_builder_class(self):
        r = CatalogBuilder.build({"items": []})
        self.assertIn("unique_items", r)


# ---------------------------------------------------------------------------
# T7: public_metadata — mock 标注
# ---------------------------------------------------------------------------
class TestPublicMetadata(unittest.TestCase):
    def test_view_count_is_mock_not_real(self):
        r = extract("https://www.douyin.com/video/123")
        self.assertEqual(r["media_meta"]["view_count"], "mock-not-real")

    def test_rights_status_is_unknown(self):
        r = extract("https://www.bilibili.com/video/BV123")
        self.assertEqual(r["rights_status"], "unknown")

    def test_platform_detected(self):
        r = extract("https://www.xiaohongshu.com/discovery/item/abc")
        self.assertEqual(r["source_platform"], "xiaohongshu")

    def test_metadata_extractor_class(self):
        r = PublicMetadataExtractor.extract("https://www.kuaishou.com/video/123")
        self.assertIn("media_meta", r)


# ---------------------------------------------------------------------------
# T8: 端到端 integration
# ---------------------------------------------------------------------------
class TestEndToEndIntegration(unittest.TestCase):
    def test_full_pipeline_parse_catalog_metadata(self):
        # Step 1: parse homepage
        homepage_url = "https://www.douyin.com/user/test123"
        parsed = parse_homepage(homepage_url)
        self.assertIn("items", parsed)
        self.assertEqual(parsed["retrieved_policy"], "mock")

        # Step 2: build catalog (dedupe)
        catalog = build_catalog(parsed)
        self.assertIn("unique_items", catalog)
        dropped = catalog["dropped_count"]
        # no duplicates from mock data so dropped should be 0
        self.assertEqual(dropped, 0)

        # Step 3: extract metadata for each unique item
        for item in catalog["unique_items"]:
            meta = extract(item["url"])
            self.assertEqual(meta["source_platform"], parsed["source_platform"])
            self.assertEqual(meta["media_meta"]["view_count"], "mock-not-real")
            self.assertEqual(meta["rights_status"], "unknown")

        # Step 4: final catalog_json shape
        catalog_json = {
            "source_platform": parsed["source_platform"],
            "source_url": parsed["source_url"],
            "unique_count": len(catalog["unique_items"]),
            "dropped_count": catalog["dropped_count"],
            "items": [
                {**item, "meta": extract(item["url"])}
                for item in catalog["unique_items"]
            ],
        }
        self.assertIsInstance(catalog_json["items"], list)
        self.assertEqual(catalog_json["unique_count"], len(catalog_json["items"]))


if __name__ == "__main__":
    unittest.main()
