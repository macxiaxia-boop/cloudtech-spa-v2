"""
内容二创管线 v1.0 — Content Repurpose Pipeline
==============================================
粘贴笔记链接 → 自动提取内容 → AI二创改写 → 下载原始图片
支持: 小红书 / 公众号 / 知乎 / 抖音 / 通用网页
"""
import os, sys, re, json, hashlib, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).parent
ROOT_OUTPUT = Path("D:/装修素材")
ROOT_OUTPUT.mkdir(parents=True, exist_ok=True)

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ─── Platform Detection ───────────────────────────────

def detect_platform(url: str) -> str:
    u = url.lower()
    if any(d in u for d in ["xiaohongshu.com", "xhslink.com", "xhs.cn"]):
        return "小红书"
    if any(d in u for d in ["mp.weixin.qq.com", "weixin.qq.com"]):
        return "公众号"
    if any(d in u for d in ["zhihu.com", "zhuanlan.zhihu.com"]):
        return "知乎"
    if any(d in u for d in ["douyin.com", "v.douyin"]):
        return "抖音"
    if any(d in u for d in ["bilibili.com", "b23.tv"]):
        return "B站"
    return "通用网页"

# ─── Content Extraction ───────────────────────────────

def extract_content(url: str, save_to_disk: bool = True) -> dict:
    """Extract title, text, images, author from any URL"""
    platform = detect_platform(url)
    result = {"url": url, "platform": platform, "title": "", "text": "", "author": "", "images": [], "error": None, "folder": ""}

    # Create output folder: D:\装修素材\{平台}\{日期}_{标题}
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "未命名"
    folder_name = f"{date_str}_{safe_title}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except Exception as e:
        result["error"] = f"无法访问页面: {e}"
        return result

    soup = BeautifulSoup(html, "html.parser")

    # Title
    title_tag = soup.find("h1") or soup.find("title")
    if title_tag:
        result["title"] = title_tag.get_text(strip=True)[:200]
        # 用标题做文件夹名的一部分
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', result["title"])[:40].strip()

    # Create per-link folder
    platform_dir = {"小红书":"小红书","公众号":"公众号","知乎":"知乎","抖音":"抖音","B站":"B站"}.get(platform, "通用网页")
    folder_name = f"{date_str}_{safe_title}" if safe_title else date_str
    result["folder"] = str(ROOT_OUTPUT / platform_dir / folder_name)
    img_dir = Path(result["folder"]) / "images"

    # Platform-specific extraction
    extractors = {
        "小红书": _extract_xhs,
        "公众号": _extract_wechat,
        "知乎": _extract_zhihu,
        "通用网页": _extract_generic,
    }

    func = extractors.get(platform, _extract_generic)
    func(soup, result, url)

    # Fallback: generic extraction
    if not result["text"]:
        _extract_generic(soup, result, url)

    # Clean text
    result["text"] = re.sub(r'\n{3,}', '\n\n', result["text"]).strip()
    result["text"] = re.sub(r'\s{3,}', '  ', result["text"])

    # Download images to per-link folder
    if result["images"] and save_to_disk:
        result["downloaded_images"] = _download_images(result["images"], img_dir, url)

    # Save original text to folder
    if save_to_disk and result["text"]:
        img_dir.mkdir(parents=True, exist_ok=True)
        txt_path = Path(result["folder"]) / "原始内容.txt"
        meta = f"来源: {result['platform']}\n链接: {url}\n作者: {result['author']}\n标题: {result['title']}\n提取时间: {datetime.now()}\n{'='*50}\n\n"
        txt_path.write_text(meta + result["text"], encoding="utf-8")

    return result

def _extract_xhs(soup, result, url):
    # 小红书 note content
    for sel in [{"class": "note-content"}, {"class": "note-text"}, {"id": "detail-desc"}, {"class": "desc"}]:
        div = soup.find("div", sel) or soup.find("span", sel) or soup.find("p", sel)
        if div:
            result["text"] = div.get_text(separator="\n", strip=True)
            break

    # Author
    author_el = soup.find("span", {"class": "username"}) or soup.find("a", {"class": "name"})
    if author_el:
        result["author"] = author_el.get_text(strip=True)

    # Images
    for sel in [{"class": "note-image"}, {"class": "swiper-slide"}, {"class": "slide"}]:
        for img in soup.find_all("img", sel):
            src = img.get("src") or img.get("data-src")
            if src:
                result["images"].append(_full_url(src, url))

def _extract_wechat(soup, result, url):
    # 公众号文章
    content = soup.find("div", {"id": "js_content"}) or soup.find("div", {"class": "rich_media_content"})
    if content:
        # Remove hidden elements
        for h in content.find_all(style=re.compile("display:\s*none")):
            h.decompose()
        result["text"] = content.get_text(separator="\n", strip=True)

    author_el = soup.find("span", {"id": "js_author_name"}) or soup.find("strong", {"class": "rich_media_meta_text"})
    if author_el:
        result["author"] = author_el.get_text(strip=True)

    if content:
        for img in content.find_all("img"):
            src = img.get("data-src") or img.get("src")
            if src:
                result["images"].append(_full_url(src, url))

def _extract_zhihu(soup, result, url):
    # 知乎回答/文章
    content = soup.find("div", {"class": "RichContent-inner"}) or \
              soup.find("div", {"class": "Post-RichText"}) or \
              soup.find("div", {"class": "RichText"})
    if content:
        result["text"] = content.get_text(separator="\n", strip=True)

    author_el = soup.find("a", {"class": "AuthorLink"}) or soup.find("span", {"class": "UserLink-link"})
    if author_el:
        result["author"] = author_el.get_text(strip=True)

    if content:
        for img in content.find_all("img"):
            src = img.get("data-src") or img.get("data-actualsrc") or img.get("src")
            if src:
                result["images"].append(_full_url(src, url))

def _extract_generic(soup, result, url):
    # Generic: article/main content
    for tag in ["article", "main", {"role": "main"}, {"class": "content"}, {"class": "post"}, {"class": "article"}]:
        if isinstance(tag, str):
            el = soup.find(tag)
        else:
            el = soup.find("div", tag) or soup.find("section", tag)
        if el:
            for junk in el.find_all(["script", "style", "nav", "footer", "header"]):
                junk.decompose()
            text = el.get_text(separator="\n", strip=True)
            if len(text) > len(result["text"]):
                result["text"] = text

    # Images from article area
    main = soup.find("article") or soup.find("main") or soup
    for img in main.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        if src and not src.startswith("data:"):
            result["images"].append(_full_url(src, url))

    # Fallback: body text
    if not result["text"]:
        body = soup.find("body")
        if body:
            for junk in body.find_all(["script", "style", "nav", "footer"]):
                junk.decompose()
            result["text"] = body.get_text(separator="\n", strip=True)

def _full_url(src: str, base_url: str) -> str:
    if src.startswith("http"):
        return src
    return urljoin(base_url, src)

# ─── Image Download ───────────────────────────────────

def _download_images(images: list, img_dir: Path, source_url: str) -> list:
    """Download images and return local paths"""
    img_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for i, img_url in enumerate(images[:20]):  # Max 20 images
        try:
            ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
            if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]:
                ext = ".jpg"
            name = f"{i+1:02d}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}{ext}"
            path = img_dir / name
            if path.exists():
                downloaded.append(str(path))
                continue
            r = requests.get(img_url, headers=HEADERS, timeout=20)
            if r.status_code == 200 and len(r.content) > 500:
                path.write_bytes(r.content)
                downloaded.append(str(path))
        except Exception:
            continue
    return downloaded

# ─── AI Rewrite ────────────────────────────────────────

REWRITE_PROMPTS = {
    "去AI腔": "把以下内容用真实人类的口吻重写一遍。去掉所有AI腔、套话、模板化表达。像朋友聊天一样自然。保留核心信息，但换一种表达方式。输出重写后的完整内容，不要加任何说明。",
    "小红书风格": "把以下内容改写成小红书笔记风格：口语化、加emoji、分段落、带个人体验感。保留核心信息。输出完整改写内容。",
    "公众号风格": "把以下内容改写成公众号文章风格：有深度、有观点、结构清晰、可读性强。保留核心信息。输出完整改写内容。",
    "知乎风格": "把以下内容改写成知乎专业回答风格：逻辑清晰、有理有据、有数据支撑。保留核心信息。输出完整改写内容。",
    "抖音口播": "把以下内容改写成抖音口播脚本：开头3秒强钩子、节奏快、有情绪起伏、口语化。保留核心信息。输出完整口播脚本。",
    "缩短精简": "把以下内容缩短到原长度的40-50%，保留最核心的信息和最精彩的表达，去掉冗余和铺垫。输出精简后的完整内容。",
    "扩写丰富": "把以下内容扩写，增加具体案例、数据、细节描写，让内容更丰富更有说服力。输出扩写后的完整内容。",
}

def ai_rewrite(text: str, style: str = "去AI腔", custom_prompt: str = "", save_folder: str = "") -> dict:
    """Rewrite content using AI, optionally save to disk"""
    if not DEEPSEEK_KEY:
        return {"rewritten": text, "error": "未配置 AI API Key"}

    prompt = custom_prompt if custom_prompt else REWRITE_PROMPTS.get(style, REWRITE_PROMPTS["去AI腔"])

    # Truncate if too long (DeepSeek context limit)
    max_input = 8000
    if len(text) > max_input:
        text = text[:max_input] + "\n\n[内容过长，已截断前8000字]"

    try:
        resp = requests.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的内容创作者，擅长将内容改写为不同平台和风格。改写时要保留核心信息，但用全新的表达方式。禁止输出任何解释或说明，只输出改写后的内容。"},
                    {"role": "user", "content": f"{prompt}\n\n---\n原始内容：\n\n{text}"}
                ],
                "temperature": 0.8,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        data = resp.json()
        rewritten = data["choices"][0]["message"]["content"].strip()

        # Save rewritten to disk
        if save_folder:
            Path(save_folder).mkdir(parents=True, exist_ok=True)
            rw_path = Path(save_folder) / f"二创_{style}.txt"
            rw_path.write_text(rewritten, encoding="utf-8")

        return {"rewritten": rewritten, "tokens": data.get("usage", {}).get("total_tokens", 0)}
    except Exception as e:
        return {"rewritten": text, "error": f"AI改写失败: {e}"}
