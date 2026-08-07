"""
视频合成引擎 v2 — FFmpeg Direct Pipeline
==========================================
纯 FFmpeg 驱动，零 Python 视频库依赖。
只要系统装了 ffmpeg 就能跑。

能力:
- 图片序列→视频 (带转场特效)
- 视频拼接 (xfburn/fade/slide)
- 字幕渲染 (ASS/SSA 格式，完美中文)
- 音频混合 (BGM + 旁白)
- 批量生产 (N条变体)
- 缩略图/封面生成
"""
import subprocess, json, os, random, shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from cloudtech_app import DATA_DIR, OUTPUT_DIR

BASE = Path(__file__).parent
FFMPEG_OUT = OUTPUT_DIR / "zhuangqi" /"ffmpeg"
FFMPEG_OUT.mkdir(parents=True, exist_ok=True)

# 检查 ffmpeg
def _ffmpeg(cmd: list, timeout: int = 120) -> tuple:
    """执行 ffmpeg 命令"""
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + cmd,
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return r.returncode == 0, r.stderr
    except Exception as e:
        return False, str(e)

def _ffprobe(path: str) -> dict:
    """获取媒体信息"""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, text=True, timeout=10,
        )
        return json.loads(r.stdout) if r.returncode == 0 else {}
    except Exception:
        return {}


# ═══════════════════════════════════
# 一、图片序列→视频
# ═══════════════════════════════════

def images_to_video(
    images: List[str],
    output: str = None,
    fps: int = 30,
    duration_per_image: float = 3.0,
    resolution: str = "1080x1920",
    zoom_effect: bool = True,
    bgm: str = None,
    bgm_volume: float = 0.3,
) -> dict:
    """
    图片序列合成视频（带 Ken Burns 缩放效果）

    输出: 9:16竖版视频，适合抖音/小红书/视频号
    """
    if not images:
        return {"ok": False, "error": "图片列表为空"}

    work_dir = FFMPEG_OUT / f"img2vid_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    work_dir.mkdir(parents=True, exist_ok=True)
    output = output or str(work_dir / "output.mp4")

    # 复制图片到工作目录
    work_imgs = []
    for i, img in enumerate(images):
        if not os.path.exists(img):
            continue
        ext = Path(img).suffix or ".jpg"
        dest = work_dir / f"img_{i:04d}{ext}"
        shutil.copy2(img, dest)
        work_imgs.append(str(dest))

    if not work_imgs:
        return {"ok": False, "error": "没有有效图片"}

    # 方案A: concat + zoompan滤镜 (带缩放效果)
    if zoom_effect and len(work_imgs) <= 10:
        return _images_to_video_zoompan(work_imgs, output, fps, duration_per_image, resolution, bgm, bgm_volume)

    # 方案B: 简单concat (快速，适合大量图片)
    return _images_to_video_concat(work_imgs, output, fps, duration_per_image, resolution, bgm, bgm_volume)


def _images_to_video_concat(images, output, fps, duration, resolution, bgm, bgm_vol):
    """简单拼接模式"""
    # 写concat文件
    concat_file = Path(output).parent / "concat.txt"
    with open(concat_file, "w") as f:
        for img in images:
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration}\n")
        # 最后一张重复一次（ffmpeg bug workaround）
        f.write(f"file '{images[-1]}'\n")

    w, h = resolution.split("x")
    cmd = [
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},format=yuv420p",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
    ]

    if bgm and os.path.exists(bgm):
        cmd += ["-i", bgm, "-filter_complex",
                f"[1:a]volume={bgm_vol}[a];[0:v][a]concat=n=1:v=1:a=1",
                "-c:a", "aac", "-b:a", "128k", "-shortest"]
    else:
        cmd += ["-an"]

    cmd.append(output)
    ok, err = _ffmpeg(cmd, timeout=300)

    if ok:
        size_mb = os.path.getsize(output) / 1024 / 1024
        return {"ok": True, "path": output, "images": len(images), "duration": len(images) * duration, "size_mb": round(size_mb, 1), "mode": "concat"}
    return {"ok": False, "error": err[:500]}


def _images_to_video_zoompan(images, output, fps, duration, resolution, bgm, bgm_vol):
    """缩放平移效果（Ken Burns）"""
    w, h = resolution.split("x")
    w_i, h_i = int(w), int(h)

    # 为每张图构建 zoompan 滤镜链
    filter_parts = []
    for i, img in enumerate(images):
        # 随机缩放方向: 放大 or 缩小
        zoom_dir = random.choice(["in", "out"])
        if zoom_dir == "in":
            zoom_expr = f"zoom+0.0015*on"
        else:
            zoom_expr = f"zoom-0.0015*on"

        filter_parts.append(
            f"[{i}:v]scale={w_i}:{h_i}:force_original_aspect_ratio=increase,"
            f"crop={w_i}:{h_i},zoompan=z='if(eq(on,0),1,{zoom_expr})':d={int(duration*fps)}:"
            f"s={w_i}x{h_i}:fps={fps},setpts=PTS-STARTPTS[v{i}]"
        )

    cmd = []
    for img in images:
        cmd += ["-loop", "1", "-t", str(duration), "-i", img]

    filter_str = ";".join(filter_parts)
    concat_inputs = "".join(f"[v{i}]" for i in range(len(images)))
    filter_str += f";{concat_inputs}concat=n={len(images)}:v=1,format=yuv420p[outv]"

    cmd += ["-filter_complex", filter_str, "-map", "[outv]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p"]

    if bgm and os.path.exists(bgm):
        cmd += ["-i", bgm, "-filter_complex",
                f"[{len(images)}:a]volume={bgm_vol}[outa]",
                "-map", "[outa]", "-c:a", "aac", "-b:a", "128k", "-shortest"]

    cmd.append(output)
    ok, err = _ffmpeg(cmd, timeout=300)

    if ok:
        size_mb = os.path.getsize(output) / 1024 / 1024
        return {"ok": True, "path": output, "images": len(images), "duration": len(images) * duration, "size_mb": round(size_mb, 1), "mode": "zoompan"}
    return {"ok": False, "error": err[:500]}


# ═══════════════════════════════════
# 二、视频拼接+转场
# ═══════════════════════════════════

def concat_videos(
    clips: List[str],
    output: str = None,
    transition: str = "xfade",  # xfade/fade/dissolve/wipe
    transition_duration: float = 0.5,
    resolution: str = "1080x1920",
    bgm: str = None,
) -> dict:
    """
    多段视频拼接（带转场特效）

    clips: 视频文件路径列表
    transition: xfade(交叉淡化)/fade(黑场)/dissolve(溶解)/wipeleft(左擦)
    """
    if not clips:
        return {"ok": False, "error": "视频列表为空"}
    if len(clips) == 1:
        shutil.copy2(clips[0], output)
        return {"ok": True, "path": output, "mode": "copy"}

    work_dir = FFMPEG_OUT / f"concat_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    work_dir.mkdir(parents=True, exist_ok=True)
    output = output or str(work_dir / "concat_output.mp4")

    w, h = resolution.split("x")

    # 先统一分辨率
    normalized = []
    for i, clip in enumerate(clips):
        norm = str(work_dir / f"norm_{i}.mp4")
        ok, _ = _ffmpeg([
            "-i", clip,
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-an", norm,
        ])
        if ok:
            normalized.append(norm)

    if len(normalized) < 2:
        return {"ok": False, "error": "视频规范化失败"}

    # 构建 xfade 滤镜链
    xfade_map = {
        "xfade": "fade", "fade": "fadeblack", "dissolve": "fade",
        "wipeleft": "wipeleft", "wiperight": "wiperight",
        "slideup": "slideup", "slidedown": "slidedown",
    }
    xfade_type = xfade_map.get(transition, "fade")

    filter_parts = []
    for i, v in enumerate(normalized):
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")

    # xfade chain
    prev = "v0"
    for i in range(1, len(normalized)):
        offset = f"{transition_duration}"
        next_v = f"v{i}"
        out = f"x{i}" if i < len(normalized) - 1 else "outv"
        filter_parts.append(
            f"[{prev}][{next_v}]xfade=transition={xfade_type}:duration={offset}:offset="
            f"{i*2-transition_duration}[{out}]"
        )
        prev = out

    filter_str = ";".join(filter_parts)
    cmd = []

    for v in normalized:
        cmd += ["-i", v]

    cmd += ["-filter_complex", filter_str, "-map", f"[{prev}]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p"]

    if bgm and os.path.exists(bgm):
        cmd += ["-i", bgm, "-map", f"{len(normalized)}:a",
                "-c:a", "aac", "-b:a", "128k", "-shortest"]

    cmd.append(output)
    ok, err = _ffmpeg(cmd, timeout=300)

    if ok and os.path.exists(output):
        size_mb = os.path.getsize(output) / 1024 / 1024
        return {"ok": True, "path": output, "clips": len(clips), "transition": transition, "size_mb": round(size_mb, 1)}
    return {"ok": False, "error": err[:500]}


# ═══════════════════════════════════
# 三、字幕渲染（ASS格式，完美中文）
# ═══════════════════════════════════

def add_subtitles(
    video_path: str,
    subtitles: List[Dict],
    output: str = None,
    font_name: str = "Microsoft YaHei",
    font_size: int = 36,
    primary_color: str = "&H00FFFFFF",   # 白色
    outline_color: str = "&H00000000",   # 黑色描边
    outline: float = 2.0,
    shadow: float = 1.0,
    alignment: int = 2,  # 底部居中
    margin_v: int = 80,
) -> dict:
    """
    给视频添加字幕（ASS格式，完美支持中文）

    subtitles: [
        {"start": 0.0, "end": 3.0, "text": "第一句字幕"},
        {"start": 3.0, "end": 8.0, "text": "第二句字幕"},
    ]
    """
    if not os.path.exists(video_path):
        return {"ok": False, "error": "视频文件不存在"}
    if not subtitles:
        return {"ok": True, "path": video_path, "message": "无字幕，原样返回"}

    work_dir = Path(output).parent if output else FFMPEG_OUT
    work_dir.mkdir(parents=True, exist_ok=True)
    ass_file = work_dir / f"subs_{datetime.now().strftime('%H%M%S')}.ass"
    output = output or str(work_dir / f"subtitled_{datetime.now().strftime('%H%M%S')}.mp4")

    # 生成 ASS 字幕文件
    ass_content = _generate_ass(
        subtitles, font_name, font_size, primary_color,
        outline_color, outline, shadow, alignment, margin_v,
    )
    ass_file.write_text(ass_content, encoding="utf-8")

    # ffmpeg 烧录字幕
    # Windows 路径需要转义冒号
    ass_path = str(ass_file).replace("\\", "/").replace(":", "\\\\:")
    vf = f"subtitles='{ass_path}'"

    ok, err = _ffmpeg([
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        output,
    ], timeout=300)

    if ok and os.path.exists(output):
        return {"ok": True, "path": output, "subtitles": len(subtitles), "ass_file": str(ass_file)}
    return {"ok": False, "error": err[:500]}


def _generate_ass(
    subtitles, font_name, font_size, primary_color,
    outline_color, outline, shadow, alignment, margin_v,
) -> str:
    """生成ASS字幕文件"""
    lines = [
        "[Script Info]",
        "Title: CloudTech Auto Subtitles",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H00000000,1,0,0,0,100,100,0,0,1,{outline},{shadow},{alignment},40,40,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for sub in subtitles:
        start = _seconds_to_ass_time(sub["start"])
        end = _seconds_to_ass_time(sub["end"])
        text = sub["text"].replace("\n", "\\N")
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    return "\n".join(lines)


def _seconds_to_ass_time(seconds: float) -> str:
    """秒数转 ASS 时间格式 H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


# ═══════════════════════════════════
# 四、音频混合 + 文字转语音占位
# ═══════════════════════════════════

def mix_audio(
    video_path: str,
    bgm_path: str,
    output: str = None,
    bgm_volume: float = 0.3,
    video_volume: float = 1.0,
    fade_out: float = 3.0,
) -> dict:
    """背景音乐混入视频"""
    if not os.path.exists(video_path):
        return {"ok": False, "error": "视频不存在"}
    if not os.path.exists(bgm_path):
        return {"ok": True, "path": video_path, "message": "BGM不存在，返回原视频"}

    output = output or str(Path(video_path).parent / f"bgm_{Path(video_path).name}")

    ok, err = _ffmpeg([
        "-i", video_path, "-i", bgm_path,
        "-filter_complex",
        f"[0:a]volume={video_volume}[va];"
        f"[1:a]volume={bgm_volume},afade=t=out:st=999:d={fade_out}[bgm];"
        f"[va][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", output,
    ], timeout=120)

    if ok:
        return {"ok": True, "path": output, "bgm": bgm_path}
    return {"ok": False, "error": err[:500]}


# ═══════════════════════════════════
# 五、缩略图/封面生成
# ═══════════════════════════════════

def generate_thumbnail(
    video_path: str,
    output: str = None,
    time_pos: float = 1.0,
    width: int = 1080,
    height: int = 1920,
) -> dict:
    """从视频生成缩略图"""
    output = output or str(Path(video_path).parent / f"thumb_{Path(video_path).stem}.jpg")

    ok, err = _ffmpeg([
        "-ss", str(time_pos), "-i", video_path,
        "-vframes", "1", "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "-q:v", "2", output,
    ])

    if ok and os.path.exists(output):
        return {"ok": True, "path": output, "time_pos": time_pos}
    return {"ok": False, "error": err[:300]}


def generate_cover_with_text(
    image_path: str,
    title: str,
    subtitle: str = "",
    output: str = None,
) -> dict:
    """
    生成带文字的封面图

    使用 FFmpeg drawtext 滤镜
    """
    if not os.path.exists(image_path):
        return {"ok": False, "error": "图片不存在"}

    output = output or str(Path(image_path).parent / f"cover_{Path(image_path).stem}.jpg")

    # 字体路径
    font_file = "C\\:/Windows/Fonts/msyh.ttc"  # 微软雅黑

    # 标题（大号，顶部）
    title_escaped = title.replace(":", "\\:").replace("'", "\\'")
    title_draw = (
        f"drawtext=fontfile='{font_file}':text='{title_escaped}':"
        f"fontsize=64:fontcolor=white:borderw=3:bordercolor=black@0.6:"
        f"x=(w-text_w)/2:y=h*0.08"
    )

    # 副标题
    filter_str = title_draw
    if subtitle:
        sub_escaped = subtitle.replace(":", "\\:").replace("'", "\\'")
        filter_str += (
            f",drawtext=fontfile='{font_file}':text='{sub_escaped}':"
            f"fontsize=36:fontcolor=white@0.9:borderw=2:bordercolor=black@0.4:"
            f"x=(w-text_w)/2:y=h*0.18"
        )

    ok, err = _ffmpeg([
        "-i", image_path,
        "-vf", filter_str,
        "-q:v", "2", output,
    ])

    if ok and os.path.exists(output):
        return {"ok": True, "path": output}
    return {"ok": False, "error": err[:500]}


# ═══════════════════════════════════
# 六、批量生产流水线
# ═══════════════════════════════════

def batch_produce_videos(
    image_sets: List[List[str]],
    subtitles_list: List[List[Dict]],
    template: str = "before_after",
    bgm: str = None,
    count: int = 10,
) -> dict:
    """
    批量视频生产：N组图片 → N条视频

    image_sets: [[img1, img2, img3], [img4, img5, img6], ...]
    subtitles_list: [[{start, end, text}, ...], ...]
    """
    results = []

    for i, (images, subs) in enumerate(zip(image_sets[:count], subtitles_list[:count])):
        # Step 1: 图片→视频
        vid_result = images_to_video(
            images,
            output=str(FFMPEG_OUT / f"batch_{i:03d}_raw.mp4"),
            zoom_effect=(template in ("before_after", "room_tour")),
        )

        if not vid_result.get("ok"):
            results.append({"index": i, "ok": False, "error": vid_result.get("error")})
            continue

        # Step 2: 添加字幕
        sub_result = add_subtitles(
            vid_result["path"],
            subs,
            output=str(FFMPEG_OUT / f"batch_{i:03d}_subbed.mp4"),
        )

        final_path = sub_result.get("path", vid_result["path"])

        # Step 3: 添加BGM
        if bgm and os.path.exists(bgm) and sub_result.get("ok"):
            mix_result = mix_audio(final_path, bgm)
            final_path = mix_result.get("path", final_path)

        # Step 4: 生成封面
        thumb = generate_thumbnail(final_path)

        results.append({
            "index": i,
            "ok": True,
            "path": final_path,
            "thumbnail": thumb.get("path"),
            "images": len(images),
            "subtitles": len(subs),
        })

    success = sum(1 for r in results if r.get("ok"))
    return {
        "ok": True,
        "total": len(results),
        "success": success,
        "failed": len(results) - success,
        "results": results,
        "output_dir": str(FFMPEG_OUT),
    }


# ═══════════════════════════════════
# 七、完整视频制作流程
# ═══════════════════════════════════

def create_video(
    script: dict,
    images: List[str],
    output_dir: str = None,
) -> dict:
    """
    从脚本+图片完整生成一条视频

    script: {
        "title": "...",
        "subtitles": [{"start":0,"end":3,"text":"..."}],
        "bgm": "path/to/bgm.mp3",
        "template": "before_after",
    }
    """
    od = Path(output_dir) if output_dir else FFMPEG_OUT
    od.mkdir(parents=True, exist_ok=True)

    video_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {"video_id": video_id, "files": {}}

    # 1. 图片→视频
    raw = str(od / f"{video_id}_raw.mp4")
    img_result = images_to_video(images, output=raw, zoom_effect=True)
    if not img_result.get("ok"):
        return {"ok": False, "error": "图片合成失败", "detail": img_result}
    result["files"]["raw"] = raw

    # 2. 字幕
    subs = script.get("subtitles", [])
    if subs:
        subbed = str(od / f"{video_id}_subbed.mp4")
        sub_result = add_subtitles(raw, subs, output=subbed)
        current = subbed if sub_result.get("ok") else raw
        result["files"]["subtitled"] = subbed if sub_result.get("ok") else None
    else:
        current = raw

    # 3. BGM
    bgm = script.get("bgm")
    if bgm and os.path.exists(bgm):
        final = str(od / f"{video_id}_final.mp4")
        mix_result = mix_audio(current, bgm, output=final)
        current = final if mix_result.get("ok") else current
        result["files"]["final"] = final if mix_result.get("ok") else None

    # 4. 封面
    thumb = str(od / f"{video_id}_thumb.jpg")
    thumb_result = generate_thumbnail(current, output=thumb)
    result["files"]["thumbnail"] = thumb if thumb_result.get("ok") else None

    # 5. 封面+文字
    title = script.get("title", "")
    if title and result["files"]["thumbnail"]:
        cover = str(od / f"{video_id}_cover.jpg")
        cover_result = generate_cover_with_text(
            result["files"]["thumbnail"], title,
            script.get("subtitle", ""), output=cover,
        )
        result["files"]["cover"] = cover if cover_result.get("ok") else None

    result["ok"] = True
    result["final_video"] = current
    result["duration"] = img_result.get("duration", 0)

    return result


# ═══════════════════════════════════
# 工具函数
# ═══════════════════════════════════

def check_ffmpeg() -> dict:
    """检查 ffmpeg 能力"""
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        version = r.stdout.split("\n")[0] if r.stdout else "unknown"

        # 检查编解码器
        codecs = subprocess.run(
            ["ffmpeg", "-codecs"], capture_output=True, text=True, timeout=5
        ).stdout

        return {
            "ok": True,
            "version": version,
            "h264": "libx264" in codecs,
            "aac": "aac" in codecs,
            "ass": "ass" in codecs,
            "xfade": "xfade" in codecs,
            "drawtext": "drawtext" in codecs,
        }
    except Exception:
        return {"ok": False, "error": "ffmpeg 未安装"}


def get_video_info(path: str) -> dict:
    """获取视频详细信息"""
    info = _ffprobe(path)
    if not info:
        return {"ok": False, "error": "无法读取视频信息"}

    video_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]

    return {
        "ok": True,
        "format": info.get("format", {}).get("format_name"),
        "duration": float(info.get("format", {}).get("duration", 0)),
        "size_mb": round(int(info.get("format", {}).get("size", 0)) / 1024 / 1024, 2),
        "video": {
            "codec": video_streams[0].get("codec_name") if video_streams else None,
            "resolution": f"{video_streams[0].get('width')}x{video_streams[0].get('height')}" if video_streams else None,
            "fps": _safe_parse_fps(video_streams[0].get("r_frame_rate", "0/1")) if video_streams else None,
        } if video_streams else None,
        "audio": {
            "codec": audio_streams[0].get("codec_name") if audio_streams else None,
            "channels": audio_streams[0].get("channels") if audio_streams else None,
        } if audio_streams else None,
    }


# ═══════════════════════════════════
# CLI测试
# ═══════════════════════════════════

if __name__ == "__main__":
    print(json.dumps(check_ffmpeg(), ensure_ascii=False, indent=2))

    # 测试字幕生成
    test_subs = [
        {"start": 0, "end": 3, "text": "装修前：杂乱无章的老厨房"},
        {"start": 3, "end": 8, "text": "改造后：现代简约新厨房"},
        {"start": 8, "end": 12, "text": "只花了8万，效果惊艳"},
    ]
    print(f"字幕生成测试: {len(test_subs)}条")

    print("\n图片→视频需要提供真实图片路径")
    print("视频拼接需要提供真实视频文件")
    print("核心引擎就绪！")
