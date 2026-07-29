@echo off
chcp 65001 >nul
echo ===================================
echo   云数科技 CloudTech v2.0
echo   AI数字营销中台
echo ===================================
echo.
echo 启动选项:
echo   [1] 管理后台  (http://localhost:5000/admin)
echo   [2] AI仪表盘  (http://localhost:8501)
echo   [3] 系统健康检查
echo.
set /p choice="请选择 (1/2/3): "

if "%choice%"=="1" (
    start "CloudTech Admin" cmd /c "python admin_dashboard.py"
    start "" "landing-page/index.html"
)
if "%choice%"=="2" (
    start "AI Dashboard" cmd /c "python -m streamlit run dashboard_app.py --server.port 8501"
)
if "%choice%"=="3" (
    python integration_hub.py --health
    pause
)
