"""
数字人/虚拟角色注册中心 — Digital Human & Avatar Registry
对标: HeyGen 700-1100+ avatars·Synthesia 230+ avatars·AI Twins·LiveAvatar

新增 v2:
  - create_avatar(name, voice, style) — 快速创建数字人
  - generate_digital_human_video(avatar_name, script, config) — 生成数字人视频
    · 真实API: HeyGen > D-ID 逐级降级
    · Mock回退: FFmpeg静帧+文字合成
"""
import json, secrets, os, subprocess, time
from pathlib import Path
from datetime import datetime
from cloudtech_app import DATA_DIR, OUTPUT_DIR

BASE = Path(__file__).parent
AVATAR_DIR = Path("D:/个人文件/AI/云数科技/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# 简化的头像注册表（create_avatar 使用）
AVATAR_REGISTRY = AVATAR_DIR / "_registry.json"

AVATAR_TYPES = {
    "stock": "平台内置", "custom": "定制数字人", "clone": "真人克隆",
    "character": "虚拟角色", "mascot": "品牌吉祥物",
}

VOICE_TYPES = {
    "default":      {"name": "默认（通用）",   "accent": "标准"},
    "male_zh":      {"name": "男声-标准",     "accent": "标准"},
    "female_zh":    {"name": "女声-标准",     "accent": "标准"},
    "gentle":       {"name": "女声-温柔",     "accent": "温柔"},
    "professional": {"name": "男声-专业",     "accent": "沉稳"},
}

STYLE_TYPES = ["realistic", "cartoon", "3d"]

DH_VIDEO_DIR = OUTPUT_DIR / "digital_human"
DH_VIDEO_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════
# 核心 CRUD
# ═══════════════════════════════════

def register_avatar(tid: str, name: str, avatar_type: str, config: dict = None) -> dict:
    """注册数字人/虚拟角色（企业版）"""
    if avatar_type not in AVATAR_TYPES: return {"ok": False, "error": f"无效类型: {avatar_type}"}
    aid = f"av-{secrets.token_hex(6)}"
    avatar = {
        "id": aid, "tenant_id": tid, "name": name, "type": avatar_type,
        "type_name": AVATAR_TYPES[avatar_type],
        "config": config or {},
        "appearances": [],
        "voices": [],
        "gestures": [],
        "status": "active", "created_at": datetime.now().isoformat()[:19],
        "usage_count": 0,
    }
    af = AVATAR_DIR / f"{aid}.json"
    af.write_text(json.dumps(avatar, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "avatar": avatar}


def create_avatar(name: str, voice: str = "default", style: str = "realistic") -> dict:
    """
    快速创建数字人头像

    Args:
        name:  数字人名称
        voice: 声音类型 (default|male_zh|female_zh|gentle|professional)
        style: 外观风格 (realistic|cartoon|3d)

    Returns:
        {"ok": True, "id": "av-...", "name": "...", "voice": "...", "style": "..."}
    """
    if voice not in VOICE_TYPES:
        voice = "default"
    if style not in STYLE_TYPES:
        style = "realistic"

    aid = f"av-{secrets.token_hex(6)}"
    voice_info = VOICE_TYPES[voice]

    avatar = {
        "id": aid,
        "name": name,
        "voice": voice,
        "voice_name": voice_info["name"],
        "voice_accent": voice_info["accent"],
        "style": style,
        "status": "active",
        "created_at": datetime.now().isoformat()[:19],
        "usage_count": 0,
    }

    # 写入独立文件
    af = AVATAR_DIR / f"{aid}.json"
    af.write_text(json.dumps(avatar, ensure_ascii=False, indent=2), encoding="utf-8")

    # 同步注册表
    _update_registry(aid, avatar)

    return {
        "ok": True,
        "id": aid,
        "name": name,
        "voice": voice,
        "style": style,
    }


def _update_registry(aid: str, avatar: dict):
    """维护 _registry.json 索引"""
    reg = {}
    if AVATAR_REGISTRY.exists():
        try:
            reg = json.loads(AVATAR_REGISTRY.read_text(encoding="utf-8"))
        except Exception:
            reg = {}
    reg[aid] = {
        "id": aid,
        "name": avatar["name"],
        "voice": avatar.get("voice", "default"),
        "style": avatar.get("style", "realistic"),
        "created_at": avatar.get("created_at", ""),
    }
    AVATAR_REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def add_voice(avatar_id: str, voice_name: str, voice_uri: str, language: str = "zh-CN") -> dict:
    """为数字人添加声音"""
    af = AVATAR_DIR / f"{avatar_id}.json"
    if not af.exists(): return {"ok": False, "error": "数字人不存在"}
    a = json.loads(af.read_text(encoding="utf-8"))
    vid = f"vc-{secrets.token_hex(4)}"
    voice = {"id": vid, "name": voice_name, "uri": voice_uri, "language": language, "added_at": datetime.now().isoformat()[:19]}
    a["voices"].append(voice)
    af.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "voice": voice}


def list_avatars(tid: str = "", avatar_type: str = "") -> list:
    """
    列出所有数字人

    Args:
        tid:         可选，按企业ID过滤
        avatar_type: 可选，按类型过滤 (stock|custom|clone|character|mascot)

    Returns:
        [{"id": "av-...", "name": "...", "voice": "...", "style": "...", ...}, ...]
    """
    avatars = []
    for f in sorted(AVATAR_DIR.glob("av-*.json")):
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
            # 跳过注册表文件
            if f.name == "_registry.json":
                continue
            if tid and a.get("tenant_id", "") != tid:
                continue
            if avatar_type and a.get("type", "") != avatar_type:
                continue
            avatars.append(a)
        except Exception:
            pass
    return avatars


def get_avatar_stats(tid: str = "") -> dict:
    avatars = list_avatars(tid)
    by_type = {}
    for a in avatars:
        t = a.get("type", "stock")
        by_type[t] = by_type.get(t, 0) + 1
    return {"total": len(avatars), "by_type": by_type, "total_usage": sum(a.get("usage_count", 0) for a in avatars)}


# ═══════════════════════════════════
# 数字人视频生成
# ═══════════════════════════════════

def generate_digital_human_video(
    avatar_name: str = None,
    script: str = "",
    config: dict = None,
    **kwargs,
) -> dict:
    """
    生成数字人视频 — 真实API(Mock降级)

    调用方式兼容两种:
      新: generate_digital_human_video("小云", "你好...", {"provider": "heygen"})
      旧: generate_digital_human_video(script="...", avatar_id="av-xxx", provider="mock")

    Args:
        avatar_name: 数字人名称或ID（必填）
        script:      口播脚本文本
        config:      可选配置 {"provider": "heygen|did|mock", "bg": "#000000", "resolution": "1080x1920"}

    Keyword Args (兼容旧调用):
        avatar_id:  数字人ID（旧参数名）
        provider:   视频生成提供商

    Returns:
        {"ok": True, "path": "output/...mp4", "provider": "heygen|did|mock", "duration": 15.0}
        失败: {"ok": False, "error": "reason"}
    """
    # ── 参数归一化 ──
    cfg = config or {}
    provider = cfg.get("provider") or kwargs.get("provider", "auto")
    avatar_id = avatar_name or kwargs.get("avatar_id", "")
    resolution = cfg.get("resolution", "1080x1920")
    bg_color = cfg.get("bg", "#1a1a2e")

    if not avatar_id:
        return {"ok": False, "error": "缺少 avatar_name 或 avatar_id 参数"}

    # 解析 avatar_id → 加载头像信息
    avatar = _find_avatar(avatar_id)
    if not avatar:
        # 宽松模式：不存在就创建
        create_result = create_avatar(name=avatar_id)
        avatar = _find_avatar(create_result["id"])
        if not avatar:
            return {"ok": False, "error": f"数字人不存在且无法自动创建: {avatar_id}"}

    avatar_name_resolved = avatar.get("name", avatar_id)
    voice_type = avatar.get("voice", "default")

    # ── 真实API尝试 ──
    if provider in ("auto", "heygen"):
        result = _generate_via_heygen(avatar, script, cfg)
        if result.get("ok"):
            return result

    if provider in ("auto", "did"):
        result = _generate_via_did(avatar, script, cfg)
        if result.get("ok"):
            return result

    # ── Mock 回退 (FFmpeg) ──
    return _generate_mock_video(avatar, script, resolution, bg_color, voice_type)


def _find_avatar(identifier: str) -> dict:
    """通过 id 或 name 查找数字人"""
    # 先精确匹配 id
    f = AVATAR_DIR / f"{identifier}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 再按 name 模糊匹配
    for f in sorted(AVATAR_DIR.glob("av-*.json")):
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
            if a.get("name") == identifier or a.get("id") == identifier:
                return a
        except Exception:
            pass

    return None


# ═══════════════════════════════════
# HeyGen API
# ═══════════════════════════════════

def _generate_via_heygen(avatar: dict, script: str, cfg: dict) -> dict:
    """
    HeyGen API: https://docs.heygen.com/reference/create-an-avatar-video

    需要: HEYGEN_API_KEY 环境变量
    """
    api_key = os.environ.get("HEYGEN_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "HEYGEN_API_KEY 未配置"}

    try:
        import urllib.request, urllib.error

        url = "https://api.heygen.com/v2/video/generate"
        payload = json.dumps({
            "video_name": f"digital_human_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": cfg.get("heygen_avatar_id", "default"),
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "voice_id": cfg.get("heygen_voice_id", "default"),
                    "input_text": script[:5000],
                },
            }],
            "dimension": {"width": 1080, "height": 1920} if cfg.get("resolution") == "1080x1920" else {},
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        })

        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode("utf-8"))

        video_id = data.get("data", {}).get("video_id", "")
        if video_id:
            # 轮询等待生成完成
            video_url = _poll_heygen_video(api_key, video_id, timeout=300)
            if video_url:
                # 下载到本地
                local_path = _download_video(video_url, "heygen")
                if local_path:
                    return {
                        "ok": True,
                        "path": local_path,
                        "provider": "heygen",
                        "duration": _get_video_duration(local_path),
                        "heygen_video_id": video_id,
                    }
            return {"ok": False, "error": "HeyGen视频生成超时或下载失败"}
        return {"ok": False, "error": f"HeyGen API 返回异常: {json.dumps(data, ensure_ascii=False)[:200]}"}

    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        return {"ok": False, "error": f"HeyGen HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"ok": False, "error": f"HeyGen调用异常: {str(e)[:200]}"}


def _poll_heygen_video(api_key: str, video_id: str, timeout: int = 300) -> str:
    """轮询 HeyGen 直到视频就绪"""
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(
                f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
                headers={"X-Api-Key": api_key},
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
            status = data.get("data", {}).get("status", "")
            if status == "completed":
                return data["data"].get("video_url", "")
            elif status == "failed":
                return ""
        except Exception:
            pass
        time.sleep(5)
    return ""


# ═══════════════════════════════════
# D-ID API
# ═══════════════════════════════════

def _generate_via_did(avatar: dict, script: str, cfg: dict) -> dict:
    """
    D-ID API: https://docs.d-id.com/reference/create-a-talk

    需要: DID_API_KEY 环境变量
    """
    api_key = os.environ.get("DID_API_KEY", "")
    if not api_key:
        return {"ok": False, "error": "DID_API_KEY 未配置"}

    try:
        import urllib.request, urllib.error

        url = "https://api.d-id.com/talks"
        payload = json.dumps({
            "script": {
                "type": "text",
                "input": script[:2000],
                "provider": {
                    "type": "microsoft",
                    "voice_id": "zh-CN-XiaoxiaoNeural",
                },
            },
            "config": {
                "fluent": "true",
                "pad_audio": "0.0",
            },
            "source_url": cfg.get("did_source_url", ""),
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json",
        })

        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read().decode("utf-8"))

        talk_id = data.get("id", "")
        if talk_id:
            video_url = _poll_did_talk(api_key, talk_id, timeout=300)
            if video_url:
                local_path = _download_video(video_url, "did")
                if local_path:
                    return {
                        "ok": True,
                        "path": local_path,
                        "provider": "did",
                        "duration": _get_video_duration(local_path),
                        "did_talk_id": talk_id,
                    }
            return {"ok": False, "error": "D-ID视频生成超时或下载失败"}
        return {"ok": False, "error": f"D-ID API 返回异常: {json.dumps(data, ensure_ascii=False)[:200]}"}

    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        return {"ok": False, "error": f"D-ID HTTP {e.code}: {err_body}"}
    except Exception as e:
        return {"ok": False, "error": f"D-ID调用异常: {str(e)[:200]}"}


def _poll_did_talk(api_key: str, talk_id: str, timeout: int = 300) -> str:
    """轮询 D-ID 直到视频就绪"""
    import urllib.request

    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(
                f"https://api.d-id.com/talks/{talk_id}",
                headers={"Authorization": f"Basic {api_key}"},
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode("utf-8"))
            status = data.get("status", "")
            if status == "done":
                return data.get("result_url", "")
            elif status in ("error", "rejected"):
                return ""
        except Exception:
            pass
        time.sleep(5)
    return ""


# ═══════════════════════════════════
# Mock 生成 (FFmpeg)
# ═══════════════════════════════════

def _generate_mock_video(
    avatar: dict,
    script: str,
    resolution: str = "1080x1920",
    bg_color: str = "#1a1a2e",
    voice_type: str = "default",
) -> dict:
    """
    Mock数字人视频：FFmpeg静帧+文字合成

    生成一个带头像占位、口播文字、声波动画的视频。
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = str(DH_VIDEO_DIR / f"dh_mock_{ts}.mp4")

    w_str, h_str = resolution.split("x")
    w, h = int(w_str), int(h_str)

    # 估算时长：中文约4字/秒
    char_count = len(script.replace("\n", "").replace(" ", ""))
    duration = max(3.0, char_count / 4.0)

    # 文本分行（每行约18个字，适合竖屏）
    wrapped_lines = _wrap_text(script, 18)
    num_lines = len(wrapped_lines)

    # — 构建 FFmpeg drawtext 滤镜链 —
    # 背景渐变 + 头像圆 + 文字逐行显示 + 底部波浪动画
    drawtexts = []

    # 标题：数字人名称
    name = avatar.get("name", "AI数字人")
    voice_display = VOICE_TYPES.get(voice_type, VOICE_TYPES["default"])["name"]
    header_text = f"{name}  ·  {voice_display}"
    # 字体路径（Windows ffmpeg 兼容）
    font_cn = "C\\:/Windows/Fonts/msyh.ttc"
    font_emoji = "C\\:/Windows/Fonts/seguiemj.ttf"

    drawtexts.append(
        f"drawtext=fontfile='{font_cn}':"
        f"text='{_escape_ass(header_text)}':"
        f"fontsize=28:fontcolor=white@0.9:"
        f"x=(w-text_w)/2:y=h*0.05"
    )

    # 头像占位（圆形 + 文字）
    avatar_size = min(w, h) // 3
    cx, cy = w // 2, h // 3
    drawtexts.append(
        f"drawtext=fontfile='{font_emoji}':"
        f"text='🤖':fontsize={avatar_size}:"
        f"x=(w-text_w)/2:y={cy - avatar_size // 2}"
    )

    # 口播文字（滚动/分页显示在下方）
    y_text_start = h * 0.58
    line_height = 42
    line_duration = duration / max(num_lines, 1)

    for i, line in enumerate(wrapped_lines):
        line_start = i * line_duration
        line_end = line_start + line_duration + 0.5
        y_pos = y_text_start + i * line_height
        drawtexts.append(
            f"drawtext=fontfile='{font_cn}':"
            f"text='{_escape_ass(line)}':"
            f"fontsize=30:fontcolor=white@0.95:"
            f"borderw=2:bordercolor=black@0.5:"
            f"x=(w-text_w)/2:y={y_pos}:"
            f"enable='between(t,{max(0, line_start - 0.3):.1f},{line_end:.1f})'"
        )

    # 底部提示
    drawtexts.append(
        f"drawtext=fontfile='{font_cn}':"
        f"text='—— AI 数字人 Mock ——':"
        f"fontsize=22:fontcolor=white@0.5:"
        f"x=(w-text_w)/2:y=h*0.92"
    )

    # 滤镜链
    vf = ",".join(drawtexts)

    # 构建命令：颜色背景 + 文字
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"color=c={bg_color}:s={resolution}:r=24:d={duration:.1f}",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest", "-t", f"{duration:.1f}",
        out_path,
    ]

    ok, err = _run_ffmpeg(cmd)
    if ok and os.path.exists(out_path):
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        _increment_usage(avatar.get("id", ""))
        return {
            "ok": True,
            "path": out_path,
            "provider": "mock",
            "duration": round(duration, 1),
            "size_mb": round(size_mb, 1),
            "avatar": avatar.get("name", "unknown"),
            "chars": char_count,
        }

    return {"ok": False, "error": f"Mock视频生成失败: {err[:300]}"}


def _wrap_text(text: str, max_chars: int) -> list:
    """简单中文文本换行"""
    lines = []
    current = ""
    for ch in text.replace("\n", ""):
        current += ch
        if len(current) >= max_chars:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines if lines else ["无口播内容"]


def _escape_ass(text: str) -> str:
    """转义 FFmpeg drawtext 中的特殊字符"""
    return (text
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("&", "\\&")
        .replace("#", "\\#")
    )


def _run_ffmpeg(cmd: list, timeout: int = 120) -> tuple:
    """执行 ffmpeg 命令"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return r.returncode == 0, r.stderr
    except Exception as e:
        return False, str(e)


def _get_video_duration(path: str) -> float:
    """用 ffprobe 获取视频时长"""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", path],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        return round(float(data.get("format", {}).get("duration", 0)), 1)
    except Exception:
        return 0.0


def _download_video(url: str, provider: str) -> str:
    """下载远程视频到本地"""
    import urllib.request

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = str(DH_VIDEO_DIR / f"dh_{provider}_{ts}.mp4")
    try:
        urllib.request.urlretrieve(url, out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
            return out_path
    except Exception:
        pass
    return ""


def _increment_usage(avatar_id: str):
    """递增数字人使用计数"""
    if not avatar_id:
        return
    af = AVATAR_DIR / f"{avatar_id}.json"
    if af.exists():
        try:
            a = json.loads(af.read_text(encoding="utf-8"))
            a["usage_count"] = a.get("usage_count", 0) + 1
            af.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
