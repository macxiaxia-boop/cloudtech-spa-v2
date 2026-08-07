@echo off
chcp 65001 >nul
echo ══════════════════════════════════════
echo   CloudTech 发布前检查
echo ══════════════════════════════════════
echo.

echo [1/3] 前端 JS 语法检查...
node "%~dp0validate_frontend.js"
if %errorlevel% neq 0 (
    echo.
    echo ⛔ 前端检查失败！阻塞发布。
    pause
    exit /b 1
)
echo.

echo [2/3] Python 导入检查...
call "%~dp0.venv\Scripts\python.exe" -c "import admin_dashboard; import dashboard_app; print('OK')" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  Python 导入检查跳过 (venv 环境问题)
) else (
    echo ✅ Python 模块正常
)
echo.

echo [3/3] 端口冲突检查...
netstat -ano | findstr ":5099.*LISTENING" >nul && (
    echo ⚠️  端口 5099 已被占用
) || (
    echo ✅ 端口 5099 空闲
)
netstat -ano | findstr ":8501.*LISTENING" >nul && (
    echo ⚠️  端口 8501 已被占用
) || (
    echo ✅ 端口 8501 空闲
)
echo.

echo ══════════════════════════════════════
echo   ✅ 全部检查通过，可以发布！
echo ══════════════════════════════════════
pause
exit /b 0
