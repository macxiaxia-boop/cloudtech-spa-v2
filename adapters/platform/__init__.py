"""adapters/platform — WP-BLOGGER-RESEARCH platform adapters
只读 + mock; 不调真实 API。
"""
from .permission_gate import PermissionGate, check
from .homepage_parser import HomepageParser, parse_homepage
from .catalog_builder import CatalogBuilder, build_catalog
from .public_metadata import PublicMetadataExtractor, extract

__all__ = [
    "PermissionGate",
    "check",
    "HomepageParser",
    "parse_homepage",
    "CatalogBuilder",
    "build_catalog",
    "PublicMetadataExtractor",
    "extract",
]
