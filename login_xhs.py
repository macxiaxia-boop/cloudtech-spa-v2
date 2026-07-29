"""小红书自动登录 — 打开浏览器 → 检测登录完成 → 自动保存"""
from playwright.sync_api import sync_playwright
import os, time

state_dir = os.path.join(os.path.dirname(__file__), 'data', 'browser_profiles')
os.makedirs(state_dir, exist_ok=True)
state_path = os.path.join(state_dir, 'xiaohongshu_state.json')

print('启动浏览器...')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 800},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0.0.0 Safari/537.36'
    )
    page = ctx.new_page()
    page.goto('https://www.xiaohongshu.com/explore', timeout=30000)

    # Wait up to 3 min for user to login (detect redirect to explore feed)
    print('请在浏览器中扫码登录（最多等3分钟）...')
    for i in range(36):
        time.sleep(5)
        url = page.url
        if '/explore' in url or '/feed' in url:
            print(f'检测到登录成功！(当前URL: {url})')
            break
        if i % 6 == 0:
            print(f'  等待中... ({i*5}秒)')

    time.sleep(2)
    ctx.storage_state(path=state_path)
    browser.close()

size_kb = os.path.getsize(state_path) / 1024
print(f'\n✅ 小红书登录态已保存: {size_kb:.1f}KB')
print(f'   文件: {state_path}')
