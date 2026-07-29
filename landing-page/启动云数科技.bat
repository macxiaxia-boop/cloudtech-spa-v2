@echo off
chcp 65001 >nul
title 云数科技 CloudTech v2.0

:: ═══════════════════════════════════════
::  云数科技 — 一键启动
::  前端永远可用（静态HTML直开）
::  AI仪表盘按需启动
:: ═══════════════════════════════════════

cd /d "%~dp0"

echo.
echo   ╔══════════════════════════════════════╗
echo   ║   云数科技 CloudTech v2.0           ║
echo   ║   AI数字营销中台 · 23工具·6引擎      ║
echo   ╚══════════════════════════════════════╝
echo.
echo   [1] 打开官网首页 (秒开，不需要服务器)
echo   [2] 打开AI操作仪表盘 (Streamlit)
echo   [3] 全部启动 + 打开
echo   [4] 系统健康检查
echo   [0] 退出
echo.

set /p choice="  请选择: "

if "%choice%"=="1" goto frontend
if "%choice%"=="2" goto dashboard
if "%choice%"=="3" goto all
if "%choice%"=="4" goto health
if "%choice%"=="0" exit
goto end

:frontend
echo   正在打开官网...
start "" "%~dp0index.html"
goto end

:dashboard
echo   检查AI仪表盘...
curl -s -m 2 http://localhost:8501 >nul 2>&1
if errorlevel 1 (
    echo   仪表盘未启动，正在启动...
    start "CloudTech-Dashboard" cmd /c "cd /d D:\浏览器\CloudTech-v2.0.0\CloudTech-Portable && python -m streamlit run dashboard_app.py --server.port 8501 --server.headless true"
    echo   等待启动 (约10秒)...
    timeout /t 8 /nobreak >nul
)
start "" http://localhost:8501
goto end

:all
echo   打开官网...
start "" "%~dp0index.html"
echo   检查并启动AI仪表盘...
curl -s -m 2 http://localhost:8501 >nul 2>&1
if errorlevel 1 (
    start "CloudTech-Dashboard" cmd /c "cd /d D:\浏览器\CloudTech-v2.0.0\CloudTech-Portable && python -m streamlit run dashboard_app.py --server.port 8501 --server.headless true"
    timeout /t 8 /nobreak >nul
)
start "" http://localhost:8501
goto end

:health
echo   正在检查系统健康...
curl -s -m 2 http://localhost:18792/health >nul 2>&1 && echo   ✅ Gateway 正常 || echo   ❌ Gateway 未运行
curl -s -m 2 http://localhost:5000/health >nul 2>&1 && echo   ✅ 管理后台 正常 || echo   ❌ 管理后台 未运行
curl -s -m 2 http://localhost:8501 >nul 2>&1 && echo   ✅ AI仪表盘 正常 || echo   ❌ AI仪表盘 未运行
curl -s -m 2 http://localhost:8188 >nul 2>&1 && echo   ✅ ComfyUI 正常 || echo   ❌ ComfyUI 未运行
echo.
pause
goto end

:end
