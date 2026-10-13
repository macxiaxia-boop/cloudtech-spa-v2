@echo off
REM ============================================================
REM CloudTech V4 — Production Ready 一键脚本
REM 在能访问 github.com + 媒体 API + Postgres 的机器上跑
REM 红线 #60: 不替你假装完成 — 所有步骤都需你显式确认
REM ============================================================

setlocal enabledelayedexpansion

echo ============================================================
echo CloudTech V4 — Production Ready
echo ============================================================
echo.

REM Step 1: 检查本地 commit 状态
echo [1/7] 检查本地 commit 状态
git log --oneline -3
echo.

REM Step 2: 推送 remote
echo [2/7] 推送 remote (github.com)
set /p push_confirm=确认推送? (yes/no):
if /i not "%push_confirm%"=="yes" goto :skip_push
git push origin master
echo.
:skip_push

REM Step 3: 设置 env vars
echo [3/7] 设置 env vars (从 D:\AIOS\_workzone\mcp_credentials.env 读取)
echo 如已有 env var, 跳过此步
echo 需要:
echo   V4_JWT_SECRET=... (HS256 密钥)
echo   DOUBAO_API_KEY=... (火山方舟)
echo   TIKHUB_TOKEN=... (公开数据)
echo   DATABASE_URL=postgresql://user:pass@host/db
echo.

REM Step 4: 跑 Postgres migration
echo [4/7] 跑 Postgres migration (L5 不可逆, 需你确认)
set /p db_confirm=确认跑真实 DB migration? (yes/no):
if /i not "%db_confirm%"=="yes" goto :skip_db
set DATABASE_URL=%DATABASE_URL%
python scripts/run_v4_migration.py --execute
echo.
:skip_db

REM Step 5: 跑全部 V4 测试
echo [5/7] 跑全部 V4 测试
python -m pytest tests/test_v4_*.py tests/test_adapters_*.py tests/test_workbuddy_*.py tests/test_real_provider_clients.py -q
echo.

REM Step 6: 写真实 doubao 调用 (需 DOUBAO_API_KEY 注入)
echo [6/7] 启真实 doubao_seedream (需 __enable_real=True)
echo 仅当你确认:
echo   - DOUBAO_API_KEY 已注入
echo   - 测试 cap 上限 1000 cents
echo   - 接受失败后果 (真扣费)
echo.
set /p real_doubao=启真实 doubao? (yes/no):
if /i not "%real_doubao%"=="yes" goto :skip_doubao
python -c "import os; os.environ['DOUBAO_API_KEY'] = input('DOUBAO_API_KEY: '); from adapters.media.real_providers import get_real_client; from adapters.media.types import MediaRequest; r = get_real_client('doubao_seedream')._call(MediaRequest(operation='image.generate', inputs={'prompt': 'test', '__enable_real': True}, tenant_id='t_test_v4_001', idempotency_key='k_test_001', estimated_cost_cents=20, cost_class='METERED_MEDIA'), 'token'); print('real result:', r.mock, r.output_assets[0].get('url'))"
echo.
:skip_doubao

REM Step 7: 启动 FastAPI 服务
echo [7/7] 启动 FastAPI 服务 (后台)
echo uvicorn api.v4:app --host 0.0.0.0 --port 8000
echo 然后 vite-spa (npm run dev) 调用 /v4/*
echo.
pause
