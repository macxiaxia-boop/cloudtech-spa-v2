"""
浏览器认证工具 — 登录一次，自动保存Cookie，后续headless复用
用法:
  登录(可见浏览器): python browser_auth.py --login xiaohongshu
  搜索(复用Cookie):  python browser_auth.py --search xiaohongshu "厦门装修"
"""
import json, sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data" / "browser_profiles"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PLATFORM_CONFIG = {
    "xiaohongshu": {
        "login_url": "https://www.xiaohongshu.com/login",
        "search_url": "https://www.xiaohongshu.com/search_result?keyword={keyword}&sort=general",
        "note_selector": ".note-item, .search-result-item, [class*=note], [class*=card]",
        "title_selector": ".title, .note-title, [class*=title]",
        "desc_selector": ".desc, .note-desc, [class*=desc]",
        "tag_selector": ".tag, .hashtag, [class*=tag]",
    },
    "douyin": {
        "login_url": "https://www.douyin.com/",
        "search_url": "https://www.douyin.com/search/{keyword}",
        "note_selector": "[class*=video-card], [class*=search-result]",
        "title_selector": "[class*=title]",
        "desc_selector": "[class*=desc]",
        "tag_selector": "[class*=tag]",
    },
}

def login_and_save(platform_name: str):
    """打开可见浏览器 → 用户手动扫码登录 → 自动保存Cookie和存储状态"""
    from playwright.sync_api import sync_playwright

    cfg = PLATFORM_CONFIG[platform_name]
    state_file = DATA_DIR / f"{platform_name}_state.json"

    print(f"\n{'='*50}")
    print(f"  登录 {platform_name}")
    print(f"  浏览器窗口即将打开 → 请手动扫码登录")
    print(f"  登录成功后回到此处按 Enter 保存状态")
    print(f"{'='*50}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 可见浏览器
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(cfg["login_url"], timeout=30000)

        input("\n👆 请在浏览器中完成登录，然后按 Enter 保存...")

        # Save browser state (cookies, localStorage, etc.)
        context.storage_state(path=str(state_file))
        browser.close()

    print(f"\n✅ 登录态已保存到: {state_file}")
    print(f"   文件大小: {state_file.stat().st_size/1024:.1f} KB")
    return state_file

def search_with_saved_state(platform_name: str, keyword: str, count: int = 10):
    """使用已保存的登录态进行搜索（支持headless）"""
    from playwright.sync_api import sync_playwright

    cfg = PLATFORM_CONFIG[platform_name]
    state_file = DATA_DIR / f"{platform_name}_state.json"

    if not state_file.exists():
        print(f"❌ 未找到登录态: {state_file}")
        print(f"   请先运行: python browser_auth.py --login {platform_name}")
        return []

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            storage_state=str(state_file),  # 复用Cookie
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        search_url = cfg["search_url"].format(keyword=keyword)
        print(f"🔍 搜索: {search_url}")
        page.goto(search_url, timeout=30000)
        page.wait_for_timeout(3000)

        # Scroll to load more
        for _ in range(3):
            page.keyboard.press("PageDown")
            page.wait_for_timeout(1000)

        # Parse results
        cards = page.query_selector_all(cfg["note_selector"])
        print(f"  找到 {len(cards)} 个卡片")

        for card in cards[:count]:
            try:
                title_el = card.query_selector(cfg["title_selector"])
                desc_el = card.query_selector(cfg["desc_selector"])
                tag_els = card.query_selector_all(cfg["tag_selector"])

                title = title_el.inner_text().strip() if title_el else ""
                desc = desc_el.inner_text().strip() if desc_el else ""
                tags = [t.inner_text().replace("#","").strip() for t in tag_els if t.inner_text()]

                if title or desc:
                    results.append({"title": title[:100], "desc": desc[:200], "tags": tags[:5], "url": page.url})
            except Exception:
                continue

        browser.close()

    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法:")
        print("  登录:  python browser_auth.py --login <平台名>")
        print("  搜索:  python browser_auth.py --search <平台名> <关键词>")
        print("  状态:  python browser_auth.py --status")
        print("\n支持平台: xiaohongshu, douyin")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "--login":
        platform = sys.argv[2] if len(sys.argv) > 2 else "xiaohongshu"
        login_and_save(platform)

    elif cmd == "--search":
        platform = sys.argv[2] if len(sys.argv) > 2 else "xiaohongshu"
        keyword = sys.argv[3] if len(sys.argv) > 3 else "装修"
        results = search_with_saved_state(platform, keyword)
        print(f"\n📊 搜索结果 ({len(results)}条):")
        for r in results:
            print(f"  📌 {r['title']}")
            if r['desc']: print(f"     {r['desc'][:100]}")
            if r['tags']: print(f"     🏷 {', '.join(r['tags'])}")

    elif cmd == "--status":
        for platform in ["xiaohongshu", "douyin"]:
            state_file = DATA_DIR / f"{platform}_state.json"
            if state_file.exists():
                mtime = datetime.fromtimestamp(state_file.stat().st_mtime)
                print(f"  ✅ {platform}: {state_file.stat().st_size/1024:.1f}KB (登录于 {mtime.strftime('%m-%d %H:%M')})")
            else:
                print(f"  ⬜ {platform}: 未登录")

    else:
        print(f"未知命令: {cmd}")
