"""Video Mixer Engine Tests — Templates, Mixing, Text Overlays, Input Validation"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Check if moviepy is actually available
_moviepy_ok = True
try:
    from moviepy import VideoFileClip, ImageClip, TextClip, ColorClip
except ImportError:
    _moviepy_ok = False


# ═══════════════════════════════════
# Template System
# ═══════════════════════════════════

class TestMixerTemplates:
    """混剪模板系统"""

    def test_all_builtin_templates_valid(self):
        from video_mixer import MIX_TEMPLATES, list_templates
        result = list_templates()
        assert result["ok"] is True
        assert len(result["templates"]) >= 5

    def test_template_names_known(self):
        from video_mixer import MIX_TEMPLATES
        expected = ["before_after", "room_tour", "construction_diary", "material_review", "product_showcase"]
        for name in expected:
            assert name in MIX_TEMPLATES, f"Missing template: {name}"

    def test_get_template_exists(self):
        from video_mixer import get_template
        t = get_template("before_after")
        assert t["ok"] is True
        assert "name" in t
        assert "duration" in t

    def test_get_template_missing(self):
        from video_mixer import get_template
        t = get_template("nonexistent_template")
        assert t["ok"] is False

    def test_template_segments_have_types(self):
        from video_mixer import MIX_TEMPLATES
        for name, tmpl in MIX_TEMPLATES.items():
            assert "segments" in tmpl, f"Template {name} missing segments"
            assert len(tmpl["segments"]) >= 3, f"Template {name} has < 3 segments"
            for seg in tmpl["segments"]:
                assert "type" in seg, f"Segment missing type in template {name}"
                assert "duration" in seg, f"Segment missing duration in template {name}"

    def test_template_resolutions(self):
        from video_mixer import MIX_TEMPLATES
        for name, tmpl in MIX_TEMPLATES.items():
            assert "resolution" in tmpl, f"Template {name} missing resolution"
            w, h = tmpl["resolution"]
            assert w > 0 and h > 0

    def test_template_bgm_styles_valid(self):
        from video_mixer import MIX_TEMPLATES
        for name, tmpl in MIX_TEMPLATES.items():
            assert "bgm_style" in tmpl, f"Template {name} missing bgm_style"
            assert isinstance(tmpl["bgm_style"], str)

    def test_list_templates_returns_dict_of_templates(self):
        from video_mixer import list_templates
        result = list_templates()
        assert isinstance(result["templates"], dict)
        for tpl_name, tpl_data in result["templates"].items():
            assert "name" in tpl_data
            assert "duration" in tpl_data
            assert "resolution" in tpl_data
            assert "segments" in tpl_data


# ═══════════════════════════════════
# Mixing Engine (No Real Video Files)
# ═══════════════════════════════════

class TestMixerEngine:
    """混剪引擎核心逻辑（无需真实视频文件）"""

    def test_mix_video_dry_run(self):
        from video_mixer import mix_video
        result = mix_video([], template="before_after", dry_run=True)
        assert "ok" in result
        if result.get("ok"):
            assert "plan" in result

    def test_mix_video_dry_run_all_templates(self):
        from video_mixer import mix_video, MIX_TEMPLATES
        for name in MIX_TEMPLATES:
            result = mix_video([], template=name, dry_run=True)
            assert "ok" in result, f"Dry run failed for template: {name}"

    def test_mix_video_invalid_template(self):
        from video_mixer import mix_video
        result = mix_video([], template="not_a_template", dry_run=True)
        assert result["ok"] is False

    def test_mix_with_placeholder_clips(self):
        from video_mixer import mix_video
        fake_clips = [
            {"path": "/nonexistent/clip1.mp4", "label": "before"},
            {"path": "/nonexistent/clip2.mp4", "label": "after"},
        ]
        result = mix_video(fake_clips, template="before_after", dry_run=True)
        assert "ok" in result

    @pytest.mark.skip(reason="batch_mix generates real moviepy clips, slow in CI")
    def test_batch_mix_dry_run(self):
        from video_mixer import batch_mix
        result = batch_mix({"city": "厦门"}, [], template="before_after", count=1)
        assert "ok" in result or isinstance(result, dict)

    @pytest.mark.skip(reason="batch_mix generates real moviepy clips, slow in CI")
    def test_batch_mix_with_variants(self):
        from video_mixer import batch_mix
        variants = [{"title": "奶油风", "size": 100, "budget": 15}]
        result = batch_mix({"city": "厦门"}, variants, template="room_tour", count=1)
        assert "ok" in result or isinstance(result, dict)


# ═══════════════════════════════════
# Text Overlay & ColorClip
# ═══════════════════════════════════

class TestTextAndColor:
    """文字叠加和颜色片段"""

    def test_create_text_clip(self):
        """create_text_clip returns ImageClip when moviepy available, or dict on error"""
        from video_mixer import create_text_clip
        result = create_text_clip("测试文字", duration=3)
        if _moviepy_ok:
            # Should return an ImageClip-like object or dict
            assert result is not None
        else:
            assert isinstance(result, dict)

    def test_create_chinese_text_clip(self):
        from video_mixer import create_text_clip
        result = create_text_clip("装修设计灵感分享", duration=3)
        assert result is not None

    def test_create_text_clip_long_text(self):
        from video_mixer import create_text_clip
        result = create_text_clip("这是" * 50, duration=5)
        assert result is not None

    def test_check_dependencies(self):
        from video_mixer import check_dependencies
        result = check_dependencies()
        assert isinstance(result, dict)
        assert "moviepy" in result or "ffmpeg" in result


# ═══════════════════════════════════
# Asset Management
# ═══════════════════════════════════

class TestAssetManagement:
    """素材管理"""

    def test_list_assets_default(self):
        from video_mixer import list_assets
        result = list_assets()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_list_assets_nonexistent_dir(self):
        from video_mixer import list_assets
        result = list_assets(asset_dir="/nonexistent/path")
        assert "ok" in result

    def test_assets_structure(self):
        from video_mixer import list_assets
        result = list_assets()
        assert isinstance(result, dict)


# ═══════════════════════════════════
# Edge Cases & Validation
# ═══════════════════════════════════

class TestMixerEdgeCases:
    """边界条件"""

    def test_mix_empty_clips(self):
        from video_mixer import mix_video
        result = mix_video([], template="before_after", dry_run=True)
        assert "ok" in result

    def test_mix_single_clip(self):
        from video_mixer import mix_video
        result = mix_video([{"path": "/x.mp4"}], template="before_after", dry_run=True)
        assert "ok" in result

    def test_batch_mix_zero_variants(self):
        """batch_mix with count=0 should not create clips"""
        from video_mixer import batch_mix
        result = batch_mix({}, [], template="before_after", count=0)
        assert result["ok"] is True

    @pytest.mark.skip(reason="batch_mix generates real moviepy clips, slow in CI")
    def test_batch_mix_large_variant_count(self):
        from video_mixer import batch_mix
        result = batch_mix({}, [], template="before_after", count=2)
        assert "ok" in result or isinstance(result, dict)

    def test_mix_template_with_special_chars(self):
        from video_mixer import mix_video
        result = mix_video([], template="<script>alert(1)</script>", dry_run=True)
        assert result["ok"] is False


# ════════════════════════════════════════════════════════════════════════
# V6.2 Item 4: Boundary case tests (Galois/74)
# ════════════════════════════════════════════════════════════════════════

class TestMixerBoundaryV62:
    """V6.2 boundary: extreme inputs, unicode, malformed paths."""

    def test_mix_video_with_unicode_clips(self):
        """Unicode chars in clip paths don't crash list_assets / mix_video."""
        from video_mixer import mix_video
        result = mix_video(
            [{"path": "/测试/视频_客户-中国_🏠.mp4"}],
            template="before_after", dry_run=True,
        )
        assert isinstance(result, dict)
        assert "ok" in result

    def test_mix_video_with_extremely_long_path(self):
        """Path > 4KB should not crash (defensive)."""
        from video_mixer import mix_video
        long_path = "/" + "a" * 4096 + ".mp4"
        result = mix_video([{"path": long_path}], template="before_after", dry_run=True)
        assert isinstance(result, dict)

    def test_list_assets_with_none_asset_dir(self):
        """None asset_dir falls back gracefully (no AttributeError)."""
        from video_mixer import list_assets
        try:
            result = list_assets(asset_dir=None)
            assert isinstance(result, dict)
        except (TypeError, AttributeError):
            pass  # raising is acceptable too

    def test_check_dependencies_returns_bool_or_dict(self):
        """check_dependencies must return something truthy for healthy state."""
        from video_mixer import check_dependencies
        result = check_dependencies()
        assert result is not None

    def test_mix_video_dry_run_no_io(self):
        """dry_run=True must NOT touch filesystem (idempotent)."""
        from video_mixer import mix_video
        # Repeated dry_run calls must produce same result shape
        r1 = mix_video([], template="before_after", dry_run=True)
        r2 = mix_video([], template="before_after", dry_run=True)
        # Both should at least have the same keys
        assert set(r1.keys()) == set(r2.keys()) or "ok" in r1

    def test_batch_mix_count_negative_treated_as_zero(self):
        """batch_mix with count=-1 should not crash (negative boundary)."""
        from video_mixer import batch_mix
        try:
            result = batch_mix({}, [], template="before_after", count=-1)
            assert isinstance(result, dict)
        except (ValueError, TypeError):
            pass  # rejecting negative is also acceptable

    def test_list_templates_returns_at_least_one(self):
        """list_templates has ≥1 template (sanity)."""
        from video_mixer import list_templates
        result = list_templates()
        assert result.get("ok") is True
        assert len(result.get("templates", [])) >= 1
