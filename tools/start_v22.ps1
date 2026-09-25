# CloudTech V22 backend startup (port 5000) - QualityAwareRouter enabled (RC2)
# 2026-09-25: switched from _venv312 (no uvicorn) to aios_venv (uvicorn 0.53)
# Bridge on :5099 expects v2 backend on :5000
# 2026-09-25 fix v2: PYTHONPATH must be src\ (parent of cloudtech/)
$ErrorActionPreference = 'Stop'
$env:CLOUDTECH_RC2_USE_QUALITY_AWARE = '1'
$env:PYTHONPATH = 'D:\CloudTech-Portable\src'
$env:CLOUDTECH_RC2_USE_FAKE = '0'
$py = 'D:\AIOS\aios_venv\Scripts\pythonw.exe'
Set-Location 'D:\CloudTech-Portable'
& $py -m cloudtech.live_migration.start_cloudtech --port 5000 --host 127.0.0.1
