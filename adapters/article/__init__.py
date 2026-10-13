"""CloudTech V4 — 文章重写 adapters (mock-only, 禁止调用真实网络 API)"""
from .article_parser import parse, ArticleParser
from .media_extractor import extract, MediaExtractor
from .license_checker import check, LicenseChecker

__all__ = [
    "ArticleParser", "parse",
    "MediaExtractor", "extract",
    "LicenseChecker", "check",
]
