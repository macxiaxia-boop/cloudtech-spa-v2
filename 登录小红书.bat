@echo off
chcp 65001 >nul
cd /d "D:\浏览器\CloudTech-v2.0.0\CloudTech-Portable"
echo.
echo   ╔══════════════════════════════════════╗
echo   ║   小红书浏览器登录                   ║
echo   ║   浏览器窗口将打开 → 请扫码登录       ║
echo   ║   登录成功后回到此处按任意键保存     ║
echo   ╚══════════════════════════════════════╝
echo.
.venv\Scripts\python -c "from playwright.sync_api import sync_playwright; import os; os.makedirs('data/browser_profiles',exist_ok=True); p=sync_playwright().start(); b=p.chromium.launch(headless=False); ctx=b.new_context(viewport={'width':1280,'height':800},user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'); page=ctx.new_page(); page.goto('https://www.xiaohongshu.com/login',timeout=30000); print('浏览器已打开。'); print('登录完成后回到这里按任意键...'); import msvcrt; msvcrt.getch(); ctx.storage_state(path='data/browser_profiles/xiaohongshu_state.json'); b.close(); p.stop(); print(f'已保存: {os.path.getsize(\"data/browser_profiles/xiaohongshu_state.json\")/1024:.1f}KB')"
echo.
echo   ✅ 登录态已保存！
pause
