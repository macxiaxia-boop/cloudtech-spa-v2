"""
多平台发布引擎 — Platform Publisher
====================================
对标筷子科技「矩阵宝」：多平台内容分发与调度

支持平台:
- 小红书 (Xiaohongshu) — 图文/视频笔记发布
- 抖音 (Douyin) — 视频上传+标题+话题
- 视频号 (WeChat Channels) — 视频发布
- 公众号 (WeChat Official) — 图文素材

实现方式:
- 真实 API 对接（需开发者账号）
- 本地模拟模式（开发测试用）
- Cookie 注入模式（已有 social_scraper 的 cookie）

架构: 统一发布接口 → 平台适配器 → API调用/模拟
"""
from cloudtech_app import DATA_DIR, OUTPUT_DIR

import json, os, time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field

BASE = Path(__file__).parent
PUBLISH_LOG = DATA_DIR / "publish_log"
PUBLISH_LOG.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 平台配置
# ═══════════════════════════════════

@dataclass
class PlatformConfig:
    name: str
    api_base: str
    auth_type: str  # "oauth" | "cookie" | "api_key" | "mock"
    rate_limit_per_hour: int
    supported_types: List[str]  # "image" | "video" | "article"

PLATFORMS = {
    "xiaohongshu": PlatformConfig(
        name="小红书",
        api_base="https://edith.xiaohongshu.com/api",
        auth_type="cookie",
        rate_limit_per_hour=20,
        supported_types=["image", "video"],
    ),
    "douyin": PlatformConfig(
        name="抖音",
        api_base="https://open.douyin.com",
        auth_type="oauth",
        rate_limit_per_hour=30,
        supported_types=["video"],
    ),
    "shipinhao": PlatformConfig(
        name="视频号",
        api_base="https://channels.weixin.qq.com",
        auth_type="cookie",
        rate_limit_per_hour=10,
        supported_types=["video", "image"],
    ),
    "wechat_mp": PlatformConfig(
        name="公众号",
        api_base="https://api.weixin.qq.com",
        auth_type="api_key",
        rate_limit_per_hour=5,
        supported_types=["article"],
    ),
}

# ═══════════════════════════════════
# 统一发布接口
# ═══════════════════════════════════

@dataclass
class PublishTask:
    """发布任务"""
    id: str
    platform: str
    content_type: str  # "image" | "video" | "article"
    title: str
    content: str
    images: List[str] = field(default_factory=list)
    video_path: str = None
    tags: List[str] = field(default_factory=list)
    topic: str = None
    location: str = None
    scheduled_at: str = None
    status: str = "pending"
    result: dict = field(default_factory=dict)


def publish(
    platform: str,
    content_type: str,
    title: str,
    content: str,
    images: List[str] = None,
    video_path: str = None,
    tags: List[str] = None,
    topic: str = None,
    location: str = None,
    scheduled_at: str = None,
    dry_run: bool = False,
) -> dict:
    """
    统一发布入口

    参数:
        platform: xiaohongshu/douyin/shipinhao/wechat_mp
        content_type: image/video/article
        title: 标题
        content: 正文（支持 Markdown 的部分格式）
        images: 图片路径列表
        video_path: 视频文件路径
        tags: 话题标签
        topic: 所属话题
        location: 地理位置（城市/门店）
        scheduled_at: 定时发布时间 (ISO格式)
        dry_run: True=仅模拟不发
    """
    if platform not in PLATFORMS:
        return {"ok": False, "error": f"不支持的平台: {platform}. 可用: {list(PLATFORMS.keys())}"}

    cfg = PLATFORMS[platform]
    if content_type not in cfg.supported_types:
        return {"ok": False, "error": f"{platform} 不支持 {content_type}. 支持: {cfg.supported_types}"}

    task = PublishTask(
        id=f"pub-{platform}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        platform=platform,
        content_type=content_type,
        title=title,
        content=content,
        images=images or [],
        video_path=video_path,
        tags=tags or [],
        topic=topic,
        location=location,
        scheduled_at=scheduled_at,
    )

    if dry_run:
        task.status = "simulated"
        task.result = {
            "message": f"模拟发布成功 [{cfg.name}]",
            "platform": platform,
            "mode": "dry_run",
        }
        _log_task(task)
        return {"ok": True, "task": task.__dict__, "mode": "dry_run"}

    # 真实发布
    result = _execute_publish(task, cfg)
    task.status = "published" if result.get("ok") else "failed"
    task.result = result
    _log_task(task)

    return {"ok": result.get("ok", False), "task": task.__dict__, **result}


def _execute_publish(task: PublishTask, cfg: PlatformConfig) -> dict:
    """执行真实发布（按平台分发）"""
    if task.platform == "xiaohongshu":
        return _publish_xiaohongshu(task)
    elif task.platform == "douyin":
        return _publish_douyin(task)
    elif task.platform == "shipinhao":
        return _publish_shipinhao(task)
    elif task.platform == "wechat_mp":
        return _publish_wechat_mp(task)
    return {"ok": False, "error": "未知平台"}


# ═══════════════════════════════════
# 小红书发布适配器
# ═══════════════════════════════════

def _publish_xiaohongshu(task: PublishTask) -> dict:
    """
    小红书笔记发布

    方案A: Cookie注入（已有 social_scraper 的 cookie）
    方案B: 官方API（需企业认证）
    方案C: 模拟（开发测试）
    """
    # 检查是否有可用 cookie
    cookie_file = BASE / "cookies_xiaohongshu.json"
    if not cookie_file.exists():
        return {
            "ok": False,
            "error": "小红书 Cookie 未配置",
            "hint": "请先运行: python login_xhs.py 登录小红书账号",
            "setup_steps": [
                "1. 运行 python login_xhs.py 完成扫码登录",
                "2. Cookie 将保存到 cookies_xiaohongshu.json",
                "3. 重新运行发布命令",
            ],
        }

    try:
        cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
        import requests

        session = requests.Session()
        for c in cookies:
            session.cookies.set(c["name"], c["value"])

        # 小红书发布笔记 API (非官方，基于逆向)
        payload = {
            "title": task.title,
            "desc": task.content[:300],  # 小红书正文限制
            "type": task.content_type,
            "topics": task.tags,
            "topic": task.topic,
            "location": task.location,
        }

        # 图片上传
        if task.images:
            image_ids = []
            for img_path in task.images[:9]:  # 小红书最多9张图
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        upload_resp = session.post(
                            "https://edith.xiaohongshu.com/api/sns/upload",
                            files={"file": f},
                            timeout=30,
                        )
                        if upload_resp.ok:
                            image_ids.append(upload_resp.json().get("data", {}).get("id"))
            payload["image_ids"] = image_ids

        # 视频上传
        if task.video_path and os.path.exists(task.video_path):
            with open(task.video_path, "rb") as f:
                video_resp = session.post(
                    "https://edith.xiaohongshu.com/api/sns/upload/video",
                    files={"file": f},
                    timeout=120,
                )
                if video_resp.ok:
                    payload["video_id"] = video_resp.json().get("data", {}).get("id")

        # 发布
        resp = session.post(
            "https://edith.xiaohongshu.com/api/sns/v2/note",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Origin": "https://creator.xiaohongshu.com",
            },
            timeout=30,
        )

        result = resp.json()
        return {
            "ok": resp.ok and result.get("success", False),
            "platform": "xiaohongshu",
            "note_id": result.get("data", {}).get("id"),
            "response": result,
        }

    except Exception as e:
        return {"ok": False, "error": f"小红书发布失败: {str(e)}"}


# ═══════════════════════════════════
# 抖音发布适配器
# ═══════════════════════════════════

def _publish_douyin(task: PublishTask) -> dict:
    """
    抖音视频发布

    方案A: 抖音开放平台 API（需企业资质 + 审核）
    方案B: Cookie 注入（已有 social_scraper）
    方案C: 模拟
    """
    cookie_file = BASE / "cookies_douyin.json"
    if not cookie_file.exists():
        return {
            "ok": False,
            "error": "抖音 Cookie 未配置",
            "hint": "请先运行: python login_dy.py 登录抖音创作者平台",
            "official_api": {
                "note": "生产环境建议使用抖音开放平台 API",
                "url": "https://open.douyin.com",
                "requirements": ["企业营业执照", "对公账户", "应用审核（1-3工作日）"],
            },
        }

    try:
        cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
        import requests

        session = requests.Session()
        for c in cookies:
            session.cookies.set(c["name"], c["value"])

        # 抖音视频上传（分两步：上传→发布）
        if not task.video_path or not os.path.exists(task.video_path):
            return {"ok": False, "error": "抖音发布需要视频文件"}

        # Step 1: 上传视频
        with open(task.video_path, "rb") as f:
            upload_resp = session.post(
                "https://creator.douyin.com/aweme/v1/upload/video/",
                files={"video": f},
                timeout=120,
            )
            if not upload_resp.ok:
                return {"ok": False, "error": f"视频上传失败: {upload_resp.status_code}"}
            video_id = upload_resp.json().get("video", {}).get("video_id")

        # Step 2: 发布
        post_data = {
            "video_id": video_id,
            "text": f"{task.title}\n{task.content[:500]}",
            "topics": [{"name": t} for t in (task.tags or [])],
            "location": task.location,
        }

        post_resp = session.post(
            "https://creator.douyin.com/aweme/v1/create/",
            json=post_data,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        result = post_resp.json()
        return {
            "ok": post_resp.ok,
            "platform": "douyin",
            "video_id": video_id,
            "item_id": result.get("item_id"),
            "response": result,
        }

    except Exception as e:
        return {"ok": False, "error": f"抖音发布失败: {str(e)}"}


# ═══════════════════════════════════
# 视频号发布适配器
# ═══════════════════════════════════

def _publish_shipinhao(task: PublishTask) -> dict:
    """
    视频号发布

    注意: 视频号当前无公开 API，需要通过企业微信/微信客服接口间接操作。
    当前实现为引导式：输出发布指令供手动操作。
    """
    return {
        "ok": False,
        "mode": "manual_required",
        "platform": "shipinhao",
        "message": "视频号暂不支持自动发布（无公开 API）",
        "manual_steps": [
            "1. 打开视频号助手 https://channels.weixin.qq.com",
            "2. 点击「发表视频」",
            f"3. 上传视频: {task.video_path}",
            f"4. 填写标题: {task.title}",
            f"5. 添加话题: {', '.join(task.tags or [])}",
            "6. 点击发布",
        ],
        "clipboard_content": task.title,
    }


# ═══════════════════════════════════
# 公众号发布适配器
# ═══════════════════════════════════

def _publish_wechat_mp(task: PublishTask) -> dict:
    """
    公众号图文发布

    需要: 微信公众号 AppID + AppSecret (从 .env 读取)
    """
    import requests
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")

    app_id = os.getenv("WECHAT_APP_ID")
    app_secret = os.getenv("WECHAT_APP_SECRET")

    if not app_id or not app_secret:
        return {
            "ok": False,
            "error": "微信公众号未配置",
            "hint": "在 .env 文件中设置 WECHAT_APP_ID 和 WECHAT_APP_SECRET",
        }

    try:
        # 获取 access_token
        token_resp = requests.get(
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": app_id,
                "secret": app_secret,
            },
            timeout=10,
        ).json()

        access_token = token_resp.get("access_token")
        if not access_token:
            return {"ok": False, "error": f"获取 access_token 失败: {token_resp}"}

        # 上传图文素材（草稿）
        draft = {
            "articles": [{
                "title": task.title,
                "content": task.content,
                "content_source_url": "",
                "need_open_comment": 1,
                "only_fans_can_comment": 0,
                "digest": task.content[:100] if len(task.content) > 100 else task.content,
            }]
        }

        draft_resp = requests.post(
            f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={access_token}",
            json=draft,
            timeout=30,
        ).json()

        return {
            "ok": "media_id" in draft_resp,
            "platform": "wechat_mp",
            "media_id": draft_resp.get("media_id"),
            "response": draft_resp,
        }

    except Exception as e:
        return {"ok": False, "error": f"公众号发布失败: {str(e)}"}


# ═══════════════════════════════════
# 批量发布 + 定时调度
# ═══════════════════════════════════

def batch_publish(
    tasks: List[Dict],
    dry_run: bool = True,
) -> dict:
    """
    批量多平台发布

    tasks: [{"platform": "xiaohongshu", "title": "...", "content": "...", ...}, ...]
    """
    results = []
    for t in tasks:
        r = publish(
            platform=t.get("platform", "xiaohongshu"),
            content_type=t.get("content_type", "image"),
            title=t.get("title", ""),
            content=t.get("content", ""),
            images=t.get("images", []),
            video_path=t.get("video_path"),
            tags=t.get("tags", []),
            topic=t.get("topic"),
            location=t.get("location"),
            dry_run=dry_run,
        )
        results.append(r)

    return {
        "ok": True,
        "total": len(tasks),
        "success": sum(1 for r in results if r.get("ok")),
        "failed": sum(1 for r in results if not r.get("ok")),
        "results": results,
    }


def distribute_content(
    content: Dict,
    platforms: List[str],
    dry_run: bool = True,
) -> dict:
    """
    一条内容多平台分发

    content: {"title": "...", "content": "...", "images": [...], "video": "...", "tags": [...]}
    platforms: ["xiaohongshu", "douyin", "wechat_mp"]
    """
    platform_content_map = {
        "xiaohongshu": {"content_type": "image" if content.get("images") else "video"},
        "douyin": {"content_type": "video"},
        "wechat_mp": {"content_type": "article"},
    }

    tasks = []
    for p in platforms:
        pcm = platform_content_map.get(p, {})
        # 平台特有适配：小红书加emoji，公众号加排版
        adapted_content = content["content"]
        adapted_title = content["title"]

        if p == "xiaohongshu":
            # 小红书风格：加emoji、加话题
            if content.get("tags"):
                adapted_content += "\n\n" + " ".join(f"#{t}" for t in content["tags"])
        elif p == "wechat_mp":
            # 公众号风格：Markdown 排版
            adapted_content = _format_for_wechat(content["title"], content["content"], content.get("images", []))

        tasks.append({
            "platform": p,
            "content_type": pcm.get("content_type", "image"),
            "title": adapted_title,
            "content": adapted_content,
            "images": content.get("images", []),
            "video_path": content.get("video"),
            "tags": content.get("tags", []),
        })

    return batch_publish(tasks, dry_run=dry_run)


def _format_for_wechat(title: str, content: str, images: List[str]) -> str:
    """格式化为公众号排版"""
    img_html = ""
    for img in images:
        img_html += f'\n<img src="{img}" style="max-width:100%;margin:16px 0;">\n'

    return f"""<h1>{title}</h1>
{img_html}
{content}
<p style="color:#999;font-size:14px;margin-top:32px;">— END —</p>
<p style="color:#999;font-size:12px;">本文由云数科技 AI 内容引擎生成</p>"""


# ═══════════════════════════════════
# 发布状态追踪
# ═══════════════════════════════════

def _log_task(task: PublishTask):
    """记录发布任务到日志"""
    log_file = PUBLISH_LOG / f"publish_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(task.__dict__, ensure_ascii=False) + "\n")


def get_publish_stats(date: str = None) -> dict:
    """获取发布统计"""
    if not date:
        date = datetime.now().strftime("%Y%m%d")
    log_file = PUBLISH_LOG / f"publish_{date}.jsonl"

    if not log_file.exists():
        return {"ok": True, "date": date, "total": 0, "by_platform": {}}

    tasks = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))

    by_platform = {}
    for t in tasks:
        p = t.get("platform", "unknown")
        by_platform[p] = by_platform.get(p, 0) + 1

    return {
        "ok": True,
        "date": date,
        "total": len(tasks),
        "published": sum(1 for t in tasks if t.get("status") == "published"),
        "failed": sum(1 for t in tasks if t.get("status") == "failed"),
        "simulated": sum(1 for t in tasks if t.get("status") == "simulated"),
        "by_platform": by_platform,
    }


def get_platform_status() -> dict:
    """检查各平台连接状态"""
    status = {}
    for pid, cfg in PLATFORMS.items():
        cookie_map = {
            "xiaohongshu": "cookies_xiaohongshu.json",
            "douyin": "cookies_douyin.json",
        }
        env_map = {
            "wechat_mp": ["WECHAT_APP_ID", "WECHAT_APP_SECRET"],
        }
        status[pid] = {
            "name": cfg.name,
            "supported_types": cfg.supported_types,
            "rate_limit": f"{cfg.rate_limit_per_hour}/h",
        }

        if pid in cookie_map:
            cookie_file = BASE / cookie_map[pid]
            status[pid]["connected"] = cookie_file.exists()
            status[pid]["auth_method"] = "Cookie"
        elif pid in env_map:
            all_set = all(os.getenv(k) for k in env_map[pid])
            status[pid]["connected"] = all_set
            status[pid]["auth_method"] = "API Key"
        else:
            status[pid]["connected"] = False
            status[pid]["auth_method"] = "待支持"

    return {"ok": True, "platforms": status}


# ═══════════════════════════════════
# CLI 测试
# ═══════════════════════════════════

if __name__ == "__main__":
    # 检查状态
    print(json.dumps(get_platform_status(), ensure_ascii=False, indent=2))

    # 模拟发布
    result = publish(
        platform="xiaohongshu",
        content_type="image",
        title="花12万把85平老房改成奶油风，邻居都来抄作业",
        content="改造前后对比，每一分钱都花在刀刃上。硬装8万，软装4万，明细都在图里。",
        tags=["装修设计", "漳州装修", "奶油风", "老房改造"],
        topic="装修灵感",
        location="漳州",
        dry_run=True,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 批量分发测试
    content = {
        "title": "花12万把85平老房改成奶油风",
        "content": "改造前后对比，硬装8万软装4万...",
        "images": [],
        "tags": ["装修", "奶油风", "漳州装修"],
    }
    distribute_result = distribute_content(
        content,
        platforms=["xiaohongshu", "douyin", "wechat_mp"],
        dry_run=True,
    )
    print(json.dumps(distribute_result, ensure_ascii=False, indent=2))
