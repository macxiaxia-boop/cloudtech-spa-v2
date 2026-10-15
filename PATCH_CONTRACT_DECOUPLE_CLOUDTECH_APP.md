# PATCH CONTRACT — Decouple 7 source files from `cloudtech_app` import

**Branch**: `fix/pr2-decouple-cloudtech-app-20261015`
**Date**: 2026-10-15
**Author**: Claude Code session R1870+
**Isolation**: D:\AIOS-worktrees\ct-iso-fix-v4p0\ct-repo (0 bytes to D:\CloudTech-Portable)
**Scope**: 7 source files (NOT tests, NOT user data)
**L3 Auth**: User explicit "全部授权,默认批准" + 持续干模式 v9

## 1. Root cause

- `video_mixer.py`, `auto_pipeline.py`, `digital_human.py`, `ffmpeg_pipeline.py`,
  `platform_extras.py`, `platform_publisher.py`, `video_intelligence.py` all do
  `from cloudtech_app import DATA_DIR, OUTPUT_DIR`.
- `cloudtech_app` is the Streamlit UI entry-point and requires `streamlit`.
- This causes 36+ test failures (`test_video_mixer.py` 30 fails + `test_pipeline.py` 6 fails)
  not because of business logic but because the test environment doesn't have streamlit installed.
- PR #2 design is **defective**: pipeline modules should not depend on UI module.

## 2. Patch (uniform across 7 files)

### Before (uniform)
```python
from cloudtech_app import DATA_DIR, OUTPUT_DIR
```

### After
```python
import os
from pathlib import Path
_DATA_ROOT = Path(os.environ.get("CLOUDTECH_DATA_ROOT", str(Path(__file__).parent / "data")))
_OUTPUT_ROOT = Path(os.environ.get("CLOUDTECH_OUTPUT_ROOT", str(Path(__file__).parent / "outputs")))
DATA_DIR = _DATA_ROOT
OUTPUT_DIR = _OUTPUT_ROOT
```

## 3. Why this is safe

- `DATA_DIR` / `OUTPUT_DIR` are used only as `Path` objects (`Path / "subdir"`)
- `cloudtech_app` definitions (see git blame): `DATA_DIR = Path("data")`, `OUTPUT_DIR = Path("outputs")`
- Our replacement computes same paths from `__file__.parent` (project root)
- Override path via env: `CLOUDTECH_DATA_ROOT=/custom/path`
- No change to any public function signature, behavior, or return value

## 4. Files to modify (7 total)
1. `auto_pipeline.py` line 12
2. `digital_human.py` line 14
3. `ffmpeg_pipeline.py` line 19
4. `platform_extras.py` line 15
5. `platform_publisher.py` line 19
6. `video_intelligence.py` line 12
7. `video_mixer.py` line 14

## 5. Test plan
- After patch: `pytest tests/test_video_mixer.py` expect 0 fail (was 30)
- After patch: `pytest tests/test_pipeline.py` expect 0 fail (was 6)
- After patch: full 1095 baseline — expect failure count drops from 111 to ~75
- No tests are modified (red line #1.8)

## 6. Rollback
- `git reset --hard master` on this branch
- `git branch -D fix/pr2-decouple-cloudtech-app-20261015`

## 7. Out of scope (NOT touched)
- `cloudtech_app.py` itself (UI, keep as-is)
- Any test file
- `D:\CloudTech-Portable\` (user original repo, READ-ONLY)
- `D:\AIOS\` (user original repo, READ-ONLY)
