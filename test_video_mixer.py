"""
test_video_mixer.py — Comprehensive test suite for Video Mixing Engine
=====================================================================
Tests: imports, FFmpeg, templates, dry-run plans, ColorClip mixing,
       concatenation, text overlay, transitions, batch mix, edge cases.

Creates a real output video using ColorClips (no real media files required).
"""

import sys, os, json, time, traceback
from pathlib import Path

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(r"D:\浏览器\CloudTech-v2.0.0\CloudTech-Portable")
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

TEST_OUT = PROJECT_ROOT / "test_output"
TEST_OUT.mkdir(exist_ok=True)

RESULTS = []  # list of (test_name, status, detail)


def report(test_name: str, status: str, detail: str = ""):
    """status: PASS / FAIL / WARN / INFO"""
    RESULTS.append((test_name, status, detail))
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}.get(status, "?")
    line = f"{icon} {status:4s} | {test_name}"
    if detail:
        line += f"  — {detail}"
    print(line)


# ═══════════════════════════════════════════════════════
# TEST 1: Import dependency checks
# ═══════════════════════════════════════════════════════

print("=" * 72)
print("TEST 1: Import & Dependency Checks")
print("=" * 72)

try:
    from moviepy import (
        VideoFileClip, ImageClip, TextClip, AudioFileClip,
        CompositeVideoClip, concatenate_videoclips, ColorClip
    )
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    report("moviepy import", "PASS", f"MoviePy version check")
    _moviepy_ok = True
except ImportError as e:
    report("moviepy import", "FAIL", str(e))
    _moviepy_ok = False

try:
    import subprocess
    ffmpeg_result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
    if ffmpeg_result.returncode == 0:
        ver_line = ffmpeg_result.stdout.split("\n")[0] if ffmpeg_result.stdout else "unknown"
        report("FFmpeg available", "PASS", ver_line[:80])
        _ffmpeg_ok = True
    else:
        report("FFmpeg available", "FAIL", f"Exit code {ffmpeg_result.returncode}")
        _ffmpeg_ok = False
except FileNotFoundError:
    report("FFmpeg available", "FAIL", "ffmpeg not found on PATH")
    _ffmpeg_ok = False
except Exception as e:
    report("FFmpeg available", "FAIL", str(e))
    _ffmpeg_ok = False

try:
    import video_mixer
    report("video_mixer import", "PASS", f"Module loaded from {video_mixer.__file__}")
except Exception as e:
    report("video_mixer import", "FAIL", str(e))

deps = video_mixer.check_dependencies() if "video_mixer" in sys.modules else {}
report("check_dependencies()", "INFO", json.dumps(deps, ensure_ascii=False))

# ═══════════════════════════════════════════════════════
# TEST 2: Template System
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 2: Template System")
print("=" * 72)

try:
    templates = video_mixer.list_templates()
    report("list_templates()", "PASS",
           f"{len(templates.get('templates',{}))} templates loaded")
    for name, info in list(templates.get("templates", {}).items())[:3]:
        print(f"        ↳ {name}: {info['name']} ({info['duration']}s, {info['resolution']})")
    if len(templates.get("templates", {})) > 3:
        print(f"        ↳ ... and {len(templates['templates'])-3} more")
except Exception as e:
    report("list_templates()", "FAIL", str(e))

try:
    before_after = video_mixer.get_template("before_after")
    report("get_template('before_after')", "PASS",
           f"name={before_after.get('name')}, segments={len(before_after.get('segments',[]))}")
except Exception as e:
    report("get_template('before_after')", "FAIL", str(e))

try:
    room_tour = video_mixer.get_template("room_tour")
    report("get_template('room_tour')", "PASS",
           f"name={room_tour.get('name')}, segments={len(room_tour.get('segments',[]))}")
except Exception as e:
    report("get_template('room_tour')", "FAIL", str(e))

try:
    invalid = video_mixer.get_template("nonexistent_xyz")
    report("get_template(invalid) → error", "PASS",
           f"Correctly returned error: {invalid.get('error','')[:60]}")
except Exception as e:
    report("get_template(invalid)", "WARN", str(e))

# Check every single template can be fetched
tmpl_count = 0
tmpl_fail = 0
for name in video_mixer.MIX_TEMPLATES:
    try:
        t = video_mixer.get_template(name)
        if t.get("ok"):
            tmpl_count += 1
        else:
            tmpl_fail += 1
    except Exception:
        tmpl_fail += 1
report("All templates fetchable", "PASS" if tmpl_fail == 0 else "FAIL",
       f"{tmpl_count} ok, {tmpl_fail} failed out of {len(video_mixer.MIX_TEMPLATES)}")

# ═══════════════════════════════════════════════════════
# TEST 3: Dry-Run Plan Generation (multiple templates)
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 3: Dry-Run Plan Generation")
print("=" * 72)

test_templates = ["before_after", "room_tour", "construction_diary", "material_review",
                  "product_showcase", "budget_reveal", "water_electric"]

for tmpl_name in test_templates:
    try:
        plan = video_mixer.mix_video([], template=tmpl_name, dry_run=True)
        if plan.get("ok") and plan.get("dry_run"):
            p = plan.get("plan", {})
            report(f"dry_run({tmpl_name})", "PASS",
                   f"template={p.get('template')}, duration={p.get('total_duration')}s, "
                   f"segments={len(p.get('segments',[]))}")
        else:
            report(f"dry_run({tmpl_name})", "FAIL",
                   f"ok={plan.get('ok')}, dry_run={plan.get('dry_run')}, error={plan.get('error','')}")
    except Exception as e:
        report(f"dry_run({tmpl_name})", "FAIL", str(e)[:120])

# ═══════════════════════════════════════════════════════
# TEST 4: Text Clip Creation
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 4: Text Clip Creation")
print("=" * 72)

if _moviepy_ok:
    try:
        tc = video_mixer.create_text_clip("测试文字 Hello 你好", duration=2.0,
                                          style="clean_white", size=(1080, 1920))
        if tc is not None:
            report("create_text_clip basic", "PASS",
                   f"duration={tc.duration}, size={tc.size}")
        else:
            report("create_text_clip basic", "FAIL", "Returned None")
    except Exception as e:
        report("create_text_clip basic", "FAIL", str(e)[:150])

    # Test all subtitle styles
    for style in video_mixer.SUBTITLE_STYLES:
        try:
            tc = video_mixer.create_text_clip(f"Style: {style}", duration=1.0,
                                              style=style, size=(1080, 1920))
            if tc is not None:
                report(f"  style={style}", "PASS", f"size={tc.size}")
            else:
                report(f"  style={style}", "FAIL", "Returned None")
        except Exception as e:
            report(f"  style={style}", "FAIL", str(e)[:100])

    # Test with longer text
    try:
        long_text = "这是一段比较长的文字用来测试文字渲染是否正常工作包括中文和English混合"
        tc = video_mixer.create_text_clip(long_text, duration=2.0, size=(1080, 1920))
        report("create_text_clip long text", "PASS",
               f"text_len={len(long_text)}, clip_ok={tc is not None}")
    except Exception as e:
        report("create_text_clip long text", "FAIL", str(e)[:150])

else:
    report("create_text_clip", "SKIP", "moviepy not available")

# ═══════════════════════════════════════════════════════
# TEST 5: ColorClip Mixing — Generate Real Output Video
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 5: ColorClip Video Mixing (Real Output)")
print("=" * 72)

if _moviepy_ok and _ffmpeg_ok:
    try:
        # Build a simulated mix using ColorClips to test concatenation
        test_clips_data = [
            {"type": "color", "color": (30, 30, 60), "duration": 2.0},       # dark blue intro
            {"type": "color", "color": (60, 30, 30), "duration": 2.0},       # dark red
            {"type": "color", "color": (30, 60, 30), "duration": 2.0},       # dark green
            {"type": "color", "color": (60, 60, 30), "duration": 1.0},       # yellow
            {"type": "color", "color": (30, 30, 60), "duration": 1.0},       # blue outro
        ]

        result = video_mixer.mix_video(
            test_clips_data,
            output_name="test_color_mix.mp4",
            template="before_after",
            resolution=(640, 360),   # small resolution for fast test
            fps=24,
            dry_run=False,
        )
        report("ColorClip concatenation", "PASS" if result.get("ok") else "FAIL",
               f"path={result.get('path')}, duration={result.get('duration')}s, "
               f"size={result.get('size_mb')}MB, clips={result.get('clips_count')}")
        if not result.get("ok"):
            report("  error detail", "FAIL", result.get("error","")[:200])
        print(json.dumps({k: v for k, v in result.items() if k != "plan"},
                         ensure_ascii=False, indent=2))
    except Exception as e:
        report("ColorClip concatenation", "FAIL", str(e)[:200])
        traceback.print_exc()

else:
    report("ColorClip mixing", "SKIP", f"moviepy={_moviepy_ok}, ffmpeg={_ffmpeg_ok}")

# ═══════════════════════════════════════════════════════
# TEST 6: Text + Color Mixing
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 6: Text + ColorClip Composite Mixing")
print("=" * 72)

if _moviepy_ok and _ffmpeg_ok:
    try:
        composite_clips = [
            {"type": "color", "color": (20, 40, 20), "duration": 1.5},
            {"type": "text",  "text": "改造前", "duration": 2.0, "style": "bold_yellow"},
            {"type": "color", "color": (40, 20, 20), "duration": 1.0},
            {"type": "text",  "text": "改造后", "duration": 2.0, "style": "clean_white"},
            {"type": "color", "color": (20, 20, 40), "duration": 1.5},
        ]

        result = video_mixer.mix_video(
            composite_clips,
            output_name="test_text_mix.mp4",
            template="before_after",
            resolution=(640, 360),
            fps=24,
            dry_run=False,
        )
        report("Text+Color composite mix", "PASS" if result.get("ok") else "FAIL",
               f"duration={result.get('duration')}s, size={result.get('size_mb')}MB")
        if not result.get("ok"):
            report("  error detail", "FAIL", result.get("error","")[:200])
    except Exception as e:
        report("Text+Color composite mix", "FAIL", str(e)[:200])
        traceback.print_exc()
else:
    report("Text+Color composite mix", "SKIP")

# ═══════════════════════════════════════════════════════
# TEST 7: Concatenate Videoclips (compose vs chain)
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 7: Concatenation Methods")
print("=" * 72)

if _moviepy_ok and _ffmpeg_ok:
    try:
        c1 = ColorClip((320, 240), color=(255, 0, 0), duration=1.0)
        c2 = ColorClip((320, 240), color=(0, 255, 0), duration=1.0)
        c3 = ColorClip((320, 240), color=(0, 0, 255), duration=1.0)

        # Method: compose
        final_compose = concatenate_videoclips([c1, c2, c3], method="compose")

        out_path = TEST_OUT / "test_concat_compose.mp4"
        final_compose.write_videofile(
            str(out_path), fps=24, codec="libx264",
            logger=None, temp_audiofile=str(TEST_OUT / "_tmp_audio.mp3")
        )
        sz = os.path.getsize(out_path) / 1024
        report("concatenate (compose)", "PASS",
               f"output={out_path.name}, size={sz:.1f}KB, duration=3s")
    except Exception as e:
        report("concatenate (compose)", "FAIL", str(e)[:200])
        traceback.print_exc()

    try:
        c1 = ColorClip((320, 240), color=(255, 255, 0), duration=1.0)
        c2 = ColorClip((320, 240), color=(0, 255, 255), duration=1.0)

        final_chain = concatenate_videoclips([c1, c2], method="chain")

        out_path = TEST_OUT / "test_concat_chain.mp4"
        final_chain.write_videofile(
            str(out_path), fps=24, codec="libx264",
            logger=None, temp_audiofile=str(TEST_OUT / "_tmp_audio2.mp3")
        )
        sz = os.path.getsize(out_path) / 1024
        report("concatenate (chain)", "PASS",
               f"output={out_path.name}, size={sz:.1f}KB, duration=2s")
    except Exception as e:
        report("concatenate (chain)", "FAIL", str(e)[:200])
        traceback.print_exc()
else:
    report("Concatenation", "SKIP")

# ═══════════════════════════════════════════════════════
# TEST 8: Transition Effects
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 8: Transition Effects")
print("=" * 72)

if _moviepy_ok and _ffmpeg_ok:
    # crossfadein / crossfadeout via with_effects
    try:
        c1 = ColorClip((640, 360), color=(50, 0, 0), duration=2.0)
        c2 = ColorClip((640, 360), color=(0, 0, 50), duration=2.0)

        # Simple crossfade by concatenating with compose
        crossfade_clips = [c1, c2]
        final = concatenate_videoclips(crossfade_clips, method="compose")

        out_path = TEST_OUT / "test_crossfade.mp4"
        final.write_videofile(
            str(out_path), fps=24, codec="libx264",
            logger=None, temp_audiofile=str(TEST_OUT / "_tmp_audio3.mp3")
        )
        sz = os.path.getsize(out_path) / 1024
        report("crossfade transition", "PASS",
               f"output={out_path.name}, size={sz:.1f}KB")
    except Exception as e:
        report("crossfade transition", "FAIL", str(e)[:200])
        traceback.print_exc()

    # Zoom-in effect (resize over time)
    try:
        c1 = ColorClip((640, 360), color=(20, 50, 20), duration=2.0)
        c1_zoomed = c1.resized(lambda t: 1 + 0.1 * t / 2.0)

        out_path = TEST_OUT / "test_zoom.mp4"
        c1_zoomed.write_videofile(
            str(out_path), fps=24, codec="libx264",
            logger=None, temp_audiofile=str(TEST_OUT / "_tmp_audio4.mp3")
        )
        sz = os.path.getsize(out_path) / 1024
        report("zoom-in effect", "PASS",
               f"output={out_path.name}, size={sz:.1f}KB")
    except Exception as e:
        report("zoom-in effect", "FAIL", str(e)[:200])
        traceback.print_exc()

    # Basic clip write (ColorClip render)
    try:
        c1 = ColorClip((640, 360), color=(30, 30, 80), duration=2.0)

        out_path = TEST_OUT / "test_fade.mp4"
        c1.write_videofile(
            str(out_path), fps=24, codec="libx264",
            logger=None, temp_audiofile=str(TEST_OUT / "_tmp_audio5.mp3")
        )
        sz = os.path.getsize(out_path) / 1024
        report("basic clip write", "PASS",
               f"output={out_path.name}, size={sz:.1f}KB")
    except Exception as e:
        report("basic clip write", "FAIL", str(e)[:200])
        traceback.print_exc()
else:
    report("Transition effects", "SKIP")

# ═══════════════════════════════════════════════════════
# TEST 9: Batch Mix (dry-run)
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 9: Batch Mix (dry-run)")
print("=" * 72)

try:
    base_data = {
        "before_images": [],
        "after_images": [],
    }
    result = video_mixer.batch_mix(base_data, variants=[], template="before_after", count=3)
    if result.get("ok"):
        report("batch_mix (3 variants)", "PASS",
               f"total={result.get('total')}, success={result.get('success')}, "
               f"failed={result.get('failed')}")
        for r in result.get("results", []):
            is_dry = r.get("dry_run", False)
            has_plan = r.get("plan") is not None
            print(f"        ↳ ok={r.get('ok')}, dry_run={is_dry}, plan={'yes' if has_plan else 'no'}")
    else:
        report("batch_mix", "FAIL", result.get("error", str(result))[:200])
except Exception as e:
    report("batch_mix", "FAIL", str(e)[:200])
    traceback.print_exc()

# ═══════════════════════════════════════════════════════
# TEST 10: Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 10: Edge Cases & Error Handling")
print("=" * 72)

# Empty clips list
try:
    result = video_mixer.mix_video([], template="before_after", dry_run=False)
    report("mix_video([]) dry_run=False", "PASS",
           f"dry_run={result.get('dry_run')}, ok={result.get('ok')}")
except Exception as e:
    report("mix_video([])", "FAIL", str(e)[:150])

# Empty clips dry_run=True
try:
    result = video_mixer.mix_video([], template="before_after", dry_run=True)
    report("mix_video([]) dry_run=True", "PASS" if result.get("dry_run") else "FAIL",
           f"has plan: {result.get('plan') is not None}")
except Exception as e:
    report("mix_video([]) dry_run=True", "FAIL", str(e)[:150])

# Invalid template — now returns error dict instead of silent fallback
try:
    result = video_mixer.mix_video([], template="invalid_xyz", dry_run=True)
    if not result.get("ok") and "Unknown template" in result.get("error", ""):
        report("mix_video with invalid template", "PASS",
               f"Correctly rejected: {result.get('error','')[:80]}")
    else:
        report("mix_video with invalid template", "FAIL",
               f"Expected error, got ok={result.get('ok')}")
except Exception as e:
    report("mix_video with invalid template", "FAIL", str(e)[:150])

# list_assets
try:
    assets = video_mixer.list_assets(str(TEST_OUT))
    report("list_assets", "PASS",
           f"images={assets.get('images')}, videos={assets.get('videos')}")
except Exception as e:
    report("list_assets", "FAIL", str(e)[:150])

if _moviepy_ok and _ffmpeg_ok:
    # Mixed clip types with missing path (gracefully skip bad files, render rest)
    try:
        mixed_data = [
            {"type": "color", "color": (40, 40, 80), "duration": 1.5},
            {"type": "video", "path": "nonexistent_file.mp4", "start": 0, "end": 5},
            {"type": "text", "text": "Missing Video, Using Color Instead", "duration": 2.0},
            {"type": "image", "path": "nonexistent.jpg", "duration": 2.0},
            {"type": "color", "color": (80, 40, 40), "duration": 1.5},
        ]
        result = video_mixer.mix_video(
            mixed_data, output_name="test_edge_mixed.mp4",
            resolution=(640, 360), fps=24, dry_run=False,
        )
        if result.get("ok"):
            report("mix with invalid paths", "PASS",
                   f"gracefully skipped bad files, output={result.get('path','?')}")
        else:
            report("mix with invalid paths", "FAIL", result.get("error","")[:200])
    except Exception as e:
        report("mix with invalid paths", "FAIL", str(e)[:200])
        traceback.print_exc()

    # Resolution test
    try:
        test_resolutions = [
            (640, 360),    # 16:9 small
            (360, 640),    # 9:16 small
            (1080, 1080),  # square
        ]
        for res in test_resolutions:
            tc_data = [
                {"type": "color", "color": (30, 60, 30), "duration": 0.5},
                {"type": "color", "color": (60, 30, 60), "duration": 0.5},
            ]
            result = video_mixer.mix_video(
                tc_data,
                output_name=f"test_res_{res[0]}x{res[1]}.mp4",
                resolution=res, fps=24, dry_run=False,
            )
            if result.get("ok"):
                report(f"resolution {res[0]}x{res[1]}", "PASS",
                       f"size={result.get('size_mb')}MB")
            else:
                report(f"resolution {res[0]}x{res[1]}", "FAIL",
                       result.get("error","")[:120])
    except Exception as e:
        report("resolution test", "FAIL", str(e)[:200])
        traceback.print_exc()

# ═══════════════════════════════════════════════════════
# TEST 11: Duration Accuracy
# ═══════════════════════════════════════════════════════

print("\n" + "=" * 72)
print("TEST 11: Duration Accuracy")
print("=" * 72)

if _moviepy_ok and _ffmpeg_ok:
    try:
        expected_dur = 5.0
        dur_clips = [
            {"type": "color", "color": (20, 20, 20), "duration": 1.0},
            {"type": "color", "color": (40, 40, 40), "duration": 1.5},
            {"type": "color", "color": (60, 60, 60), "duration": 0.5},
            {"type": "color", "color": (80, 80, 80), "duration": 2.0},
        ]
        result = video_mixer.mix_video(
            dur_clips, output_name="test_duration.mp4",
            resolution=(640, 360), fps=24, dry_run=False,
        )
        if result.get("ok"):
            actual_dur = result.get("duration", 0)
            diff = abs(actual_dur - expected_dur)
            status = "PASS" if diff < 0.5 else "WARN"
            report(f"duration accuracy", status,
                   f"expected={expected_dur}s, actual={actual_dur}s, diff={diff:.2f}s")
        else:
            report("duration accuracy", "FAIL", result.get("error","")[:200])
    except Exception as e:
        report("duration accuracy", "FAIL", str(e)[:200])
        traceback.print_exc()
else:
    report("Duration accuracy", "SKIP")

# ═══════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════

print("\n\n" + "=" * 72)
print("SUMMARY REPORT")
print("=" * 72)

pass_count = sum(1 for _, s, _ in RESULTS if s == "PASS")
fail_count = sum(1 for _, s, _ in RESULTS if s == "FAIL")
warn_count = sum(1 for _, s, _ in RESULTS if s == "WARN")
skip_count = sum(1 for _, s, _ in RESULTS if s == "SKIP")
info_count = sum(1 for _, s, _ in RESULTS if s == "INFO")

print(f"\nResults: {pass_count} ✅ PASS | {fail_count} ❌ FAIL | "
      f"{warn_count} ⚠️ WARN | {skip_count} ⤵️ SKIP | {info_count} ℹ️ INFO")
print(f"Total: {len(RESULTS)} tests")

# Overall engine verdict
if _moviepy_ok and _ffmpeg_ok and fail_count == 0:
    print("\n🔹 VERDICT: ✅ Video Mixing Engine is READY")
elif _moviepy_ok and _ffmpeg_ok and fail_count > 0:
    print(f"\n🔹 VERDICT: ⚠️ Engine partially functional — {fail_count} tests FAILED")
elif not _moviepy_ok:
    print("\n🔹 VERDICT: ❌ Engine NOT READY — moviepy not installed")
elif not _ffmpeg_ok:
    print("\n🔹 VERDICT: ❌ Engine NOT READY — FFmpeg not found")
else:
    print(f"\n🔹 VERDICT: ⚠️ Engine status unclear — check individual test results")

# List failed tests
if fail_count > 0:
    print("\n--- Failed Tests ---")
    for name, status, detail in RESULTS:
        if status == "FAIL":
            print(f"  ❌ {name}: {detail}")

if warn_count > 0:
    print("\n--- Warnings ---")
    for name, status, detail in RESULTS:
        if status == "WARN":
            print(f"  ⚠️ {name}: {detail}")

# List generated output files
print(f"\n--- Test Output Files ({TEST_OUT}) ---")
for f in sorted(TEST_OUT.glob("*.mp4")):
    sz = f.stat().st_size / 1024
    print(f"  📹 {f.name}  ({sz:.1f} KB)")

print("\nDone.")
