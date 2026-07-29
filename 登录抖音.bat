@echo off
chcp 65001
cd /d D:\浏览器\CloudTech-v2.0.0\CloudTech-Portable
echo 正在启动浏览器...
echo 请在浏览器中扫码登录抖音
echo 登录成功后脚本会自动检测并保存
echo.
.venv\Scripts\python login_dy.py
echo.
echo 完成！按任意键关闭...
pause >nul
