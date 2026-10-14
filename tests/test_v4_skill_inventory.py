"""Skill inventory tests use local temporary assets only, never real private files."""
import importlib.util
from pathlib import Path
import hashlib


def _load():
    path = Path(__file__).resolve().parents[1] / "scripts" / "cloudtech_skill_inventory.py"
    spec = importlib.util.spec_from_file_location("ct_skill_inventory", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_inventory_reports_hashes_without_skill_text(tmp_path):
    src = tmp_path / "decoration-1-0"
    src.mkdir()
    content = "my sensitive training text that must remain private"
    (src / "SKILL.md").write_text(content, encoding="utf-8")
    report = _load().inventory(tmp_path)
    assert report["status"] == "INDEXED"
    assert report["file_count"] == 1
    assert report["entries"][0]["sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert report["operation_groups"] == {"decoration": 1}
    assert content not in str(report)
    assert report["entries"][0]["relative_path"] == "decoration-1-0/SKILL.md"


def test_missing_private_asset_root_blocks_without_inventing_files(tmp_path):
    missing = tmp_path / "not-mounted"
    result = _load().inventory(missing)
    assert result["status"] == "BLOCKED"
    assert result["file_count"] == 0
    assert result["error"] == "SKILL_ROOT_UNAVAILABLE"
    assert not missing.exists()


def test_empty_mount_is_not_claimed_loadable(tmp_path):
    result = _load().inventory(tmp_path)
    assert result["status"] == "BLOCKED"
    assert result["error"] == "NO_SKILL_FILES"
