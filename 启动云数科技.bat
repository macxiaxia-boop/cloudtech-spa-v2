@echo off
chcp 65001 >nul
echo ===================================
echo   CloudTech 启动器 (R345 治本版)
echo   V22 Unified Gateway: http://127.0.0.1:5099
echo ===================================
echo.
echo   [1] V22 Gateway - 全局python  (http://localhost:5099)   [默认]
echo   [2] V22 Gateway - venv python   (推荐治本)
echo   [3] 老管理后台   (http://localhost:5000/admin)            [已弃用]
echo   [4] 老 AI 仪表盘 (http://localhost:8501)                 [已弃用]
echo   [5] 健康检查 (curl /health)
echo   [6] 仅打开浏览器到 V22
echo.
set /p choice="请选择 (1-6): "
if "%choice%"=="" set choice=1

if "%choice%"=="1" goto v22_default
if "%choice%"=="2" goto v22_venv
if "%choice%"=="3" goto legacy_admin
if "%choice%"=="4" goto legacy_dashboard
if "%choice%"=="5" goto health
if "%choice%"=="6" goto browser_only
echo 无效选项
pause
exit /b 1

:v22_default
cd /d D:\CloudTech-Portable
start "CloudTech V22" cmd /c "python -m uvicorn gateway_v22:app --host 127.0.0.1 --port 5099"
timeout /t 3 >nul
start "" "http://127.0.0.1:5099/"
goto end

:v22_venv
cd /d D:\CloudTech-Portable
start "CloudTech V22 venv" cmd /c "D:\CloudTech-Portable\.venv\Scripts\python.exe -m uvicorn gateway_v22:app --host 127.0.0.1 --port 5099"
timeout /t 3 >nul
start "" "http://127.0.0.1:5099/"
goto end

:legacy_admin
echo [警告] 老版管理后台端口 5000 已弃用,大概率启动失败
cd /d D:\CloudTech-Portable
start "CloudTech Admin (老)" cmd /c "python admin_dashboard.py"
timeout /t 3 >nul
start "" "http://localhost:5000/admin"
goto end

:legacy_dashboard
echo [警告] 老版 AI 仪表盘端口 8501 已弃用,大概率启动失败
cd /d D:\CloudTech-Portable
start "CloudTech Dashboard (老)" cmd /c "python -m streamlit run dashboard_app.py --server.port 8501"
goto end

:health
curl http://127.0.0.1:5099/health
echo.
pause
goto end

:browser_only
start "" "http://127.0.0.1:5099/"
goto end

:end
