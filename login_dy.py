"""抖音登录 — 简化版：打开浏览器，等3分钟，保存状态"""
import os, sys, time
os.chdir(os.path.dirname(__file__))
print("当前目录:", os.getcwd(), flush=True)

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print(f"Playwright导入失败: {e}", flush=True)
    input("按Enter退出...")
    sys.exit(1)

state_dir = os.path.join(os.path.dirname(__file__), 'data', 'browser_profiles')
os.makedirs(state_dir, exist_ok=True)
state_path = os.path.join(state_dir, 'douyin_state.json')

print("启动Chromium浏览器...", flush=True)
try:
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 800},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    page = ctx.new_page()
    print("打开抖音...", flush=True)
    page.goto('https://www.douyin.com/', timeout=30000)
    print("浏览器已打开！请在浏览器中扫码登录抖音", flush=True)

    # Wait up to 3 minutes, checking for login
    logged_in = False
    for i in range(180):
        time.sleep(1)
        try:
            url = page.url
            if i % 15 == 0:
                print(f"  等待中...{i}秒 (当前: {url[:80]})", flush=True)
            # Login success indicators
            if '/recommend' in url or '/follow' in url or page.query_selector('[data-e2e="user-avatar"]') or page.query_selector('.avatar'):
                print(f"检测到登录成功！", flush=True)
                logged_in = True
                time.sleep(2)
                break
        except:
            break

    print("保存登录态...", flush=True)
    ctx.storage_state(path=state_path)
    browser.close()
    p.stop()

    size = os.path.getsize(state_path)
    print(f"✅ 抖音登录态已保存: {size/1024:.1f}KB", flush=True)
    print(f"   文件: {state_path}", flush=True)

except Exception as e:
    print(f"错误: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("\n按Enter退出...", flush=True)
try:
    input()
except:
    pass
