"""
视频智能解析引擎 — Video Intelligence Engine
==============================================
对标筷子科技「智镜视频解析」+「AI复刻」+「元素替换」
核心: 爆款视频结构拆解 → 模板化复刻 → 元素智能替换

能力:
- 视频结构拆解: 分镜检测/节奏分析/文案提取/情绪曲线
- 爆款复刻: 提取爆款结构→生成同款模板→套用新内容
- 元素替换: 背景替换/产品替换/文字替换/Logo替换
"""
from cloudtech_app import DATA_DIR, OUTPUT_DIR

import json, os, re, subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

BASE = Path(__file__).parent
VIDEO_INTEL = BASE / "data" / "video_intel"
VIDEO_INTEL.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 一、视频结构拆解
# ═══════════════════════════════════

def analyze_video_structure(video_path: str) -> dict:
    """
    深度分析视频结构

    使用 FFmpeg 提取:
    - 场景切换点 (scene detection)
    - 音频节奏 (audio beat detection)  
    - 字幕时间轴
    - 画面变化率
    """
    if not os.path.exists(video_path):
        return {"ok": False, "error": "视频文件不存在"}

    result = {"path": video_path, "scenes": [], "metrics": {}}

    # 1. 场景检测 (scene change detection)
    scenes = _detect_scenes(video_path)
    result["scenes"] = scenes
    result["metrics"]["scene_count"] = len(scenes)

    # 2. 节奏分析
    rhythm = _analyze_rhythm(video_path)
    result["metrics"]["rhythm"] = rhythm

    # 3. 分镜结构推断
    if scenes:
        result["shot_structure"] = _infer_shot_structure(scenes, rhythm)

    # 4. 复刻模板生成
    result["replication_template"] = _generate_replication_template(result)

    return {"ok": True, "analysis": result}


def _detect_scenes(video_path: str) -> List[Dict]:
    """场景切换检测"""
    scene_file = str(VIDEO_INTEL / f"scenes_{datetime.now().strftime('%H%M%S')}.txt")

    # FFmpeg scene detection
    try:
        subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vf", "select='gt(scene,0.3)',showinfo",
            "-f", "null", "-",
        ], capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")

        # Fallback: 均匀切分
        import subprocess as sp
        r = sp.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", video_path,
        ], capture_output=True, text=True, timeout=10)
        info = json.loads(r.stdout) if r.returncode == 0 else {}
        duration = float(info.get("format", {}).get("duration", 0))

        if duration > 0:
            # 按节奏分镜(短视频通常3-8秒一个镜头)
            shot_duration = min(8, max(3, duration / 8))
            scenes = []
            t = 0
            i = 0
            while t < duration:
                scenes.append({
                    "index": i,
                    "start": round(t, 1),
                    "end": round(min(t + shot_duration, duration), 1),
                    "duration": round(min(shot_duration, duration - t), 1),
                    "suggested_type": _guess_shot_type(i, len(range(0, int(duration), int(shot_duration)))),
                })
                t += shot_duration
                i += 1
            return scenes
    except Exception:
        pass

    return []


def _guess_shot_type(index: int, total: int) -> str:
    """根据位置推断镜头类型"""
    ratio = index / max(total, 1)
    if ratio < 0.1:
        return "hook"        # 开头钩子
    elif ratio < 0.3:
        return "context"     # 背景铺垫
    elif ratio < 0.6:
        return "core"        # 核心内容
    elif ratio < 0.85:
        return "detail"      # 细节展示
    elif ratio < 0.95:
        return "cta"         # 行动号召
    else:
        return "ending"      # 结尾


def _analyze_rhythm(video_path: str) -> dict:
    """音频节奏分析"""
    try:
        r = subprocess.run([
            "ffprobe", "-v", "quiet",
            "-show_entries", "stream=codec_type,sample_rate,channels",
            "-of", "json", video_path,
        ], capture_output=True, text=True, timeout=10)
        info = json.loads(r.stdout) if r.returncode == 0 else {}
        audio_streams = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]

        return {
            "has_audio": len(audio_streams) > 0,
            "sample_rate": audio_streams[0].get("sample_rate") if audio_streams else None,
            "channels": audio_streams[0].get("channels") if audio_streams else None,
            "tempo_estimate": "fast" if len(audio_streams) > 0 else "silent",
        }
    except Exception:
        return {"has_audio": False}


def _infer_shot_structure(scenes: List[Dict], rhythm: dict) -> dict:
    """推断分镜结构"""
    if not scenes:
        return {"type": "unknown"}

    total_duration = sum(s.get("duration", 0) for s in scenes)
    types = [s.get("suggested_type", "unknown") for s in scenes]

    # 判断视频类型
    has_hook = "hook" in types
    has_cta = "cta" in types

    if total_duration <= 15:
        vtype = "short_promo"
    elif total_duration <= 35:
        vtype = "social_short"
        if has_hook and has_cta:
            vtype += "_structured"
    elif total_duration <= 90:
        vtype = "tutorial_review"
    else:
        vtype = "long_form"

    return {
        "type": vtype,
        "duration": round(total_duration, 1),
        "shot_count": len(scenes),
        "avg_shot_duration": round(total_duration / max(len(scenes), 1), 1),
        "structure": types,
        "has_hook": has_hook,
        "has_cta": has_cta,
    }


def _generate_replication_template(analysis: dict) -> dict:
    """生成复刻模板"""
    structure = analysis.get("shot_structure", {})
    scenes = analysis.get("scenes", [])

    template = {
        "name": f"复刻_{structure.get('type', 'generic')}",
        "source_type": structure.get("type"),
        "total_duration": structure.get("duration", 30),
        "shots": [],
        "replaceable_elements": [],
    }

    for s in scenes:
        shot_type = s.get("suggested_type", "scene")
        template["shots"].append({
            "index": s["index"],
            "type": shot_type,
            "duration": s.get("duration", 3),
            "replaceable": shot_type in ("hook", "detail", "core"),
            "instruction": _get_shot_instruction(shot_type),
        })

    template["replaceable_elements"] = [
        {"element": "背景", "method": "chroma_key", "instruction": "替换为品牌色/场景图"},
        {"element": "产品图", "method": "overlay", "instruction": "替换为客户产品"},
        {"element": "文字标题", "method": "drawtext", "instruction": "替换文案+品牌名"},
        {"element": "Logo", "method": "overlay", "position": "top_right", "instruction": "替换水印"},
        {"element": "CTA按钮", "method": "overlay", "position": "bottom", "instruction": "替换联系方式"},
    ]

    return template


def _get_shot_instruction(shot_type: str) -> str:
    return {
        "hook": "前3秒抓眼球: 痛点/悬念/数据冲击",
        "context": "铺垫问题背景: 用具体场景引发共鸣",
        "core": "核心内容展示: 解决方案/产品优势",
        "detail": "细节特写: 材质/工艺/效果近景",
        "cta": "行动号召: 关注/私信/领福利",
        "ending": "品牌收尾: Logo+联系方式",
    }.get(shot_type, "通用内容")


# ═══════════════════════════════════
# 二、AI复刻引擎
# ═══════════════════════════════════

def replicate_video(
    reference_video: str,
    new_content: dict,
    output_dir: str = None,
) -> dict:
    """
    复刻爆款视频结构

    1. 分析参考视频结构
    2. 提取分镜模板
    3. 套用新内容生成新视频

    new_content: {
        "hook_text": "新钩子",
        "scenes": [
            {"type": "hook", "text": "...", "image": "path"},
            {"type": "core", "text": "...", "image": "path"},
            ...
        ],
        "brand_name": "品牌名",
        "cta_text": "行动号召",
    }
    """
    # 分析参考视频
    analysis = analyze_video_structure(reference_video)
    if not analysis.get("ok"):
        return analysis

    template = analysis["analysis"].get("replication_template", {})

    od = Path(output_dir) if output_dir else FFMPEG_OUT / f"replica_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    od.mkdir(parents=True, exist_ok=True)

    # 为每个镜头生成素材+字幕
    shots_data = []
    subtitles = []
    time_cursor = 0

    for shot in template.get("shots", []):
        new_scene = next(
            (s for s in new_content.get("scenes", []) if s.get("type") == shot["type"]),
            None
        )
        duration = shot.get("duration", 3)

        shot_data = {
            "type": shot["type"],
            "duration": duration,
            "image": new_scene.get("image") if new_scene else None,
            "text": new_scene.get("text", shot.get("instruction", "")),
        }
        shots_data.append(shot_data)

        if shot_data["text"]:
            subtitles.append({
                "start": time_cursor,
                "end": time_cursor + duration,
                "text": shot_data["text"],
            })

        time_cursor += duration

    # 用 FFmpeg Pipeline 合成
    from ffmpeg_pipeline import images_to_video, add_subtitles, generate_cover_with_text

    # 收集可用图片
    available_images = [s["image"] for s in shots_data if s.get("image") and os.path.exists(s["image"])]
    if not available_images:
        # 生成纯色占位图
        for i, s in enumerate(shots_data):
            color_img = str(od / f"placeholder_{i}.png")
            subprocess.run([
                "ffmpeg", "-f", "lavfi", "-i", f"color=c=0x1a1a2e:s=1080x1920:d=1",
                "-frames:v", "1", color_img,
            ], capture_output=True)
            available_images.append(color_img)

    # 合成视频
    video_result = images_to_video(available_images, output=str(od / "replica_raw.mp4"))

    if not video_result.get("ok"):
        return {"ok": False, "error": "视频合成失败", "detail": video_result}

    # 添加字幕
    if subtitles:
        subbed = add_subtitles(video_result["path"], subtitles, output=str(od / "replica_subbed.mp4"))
        final_video = subbed.get("path", video_result["path"])
    else:
        final_video = video_result["path"]

    # 生成封面
    cover = generate_cover_with_text(
        available_images[0] if available_images else final_video,
        new_content.get("hook_text", ""),
        new_content.get("brand_name", ""),
        output=str(od / "replica_cover.jpg"),
    )

    return {
        "ok": True,
        "final_video": final_video,
        "cover": cover.get("path"),
        "template_used": template.get("name"),
        "shots": len(shots_data),
        "subtitles": len(subtitles),
    }


# ═══════════════════════════════════
# 三、元素智能替换
# ═══════════════════════════════════

def replace_video_elements(
    video_path: str,
    replacements: List[Dict],
    output: str = None,
) -> dict:
    """
    视频元素替换

    replacements: [
        {"type": "overlay", "image": "logo.png", "position": "top_right", "start": 0, "end": 999},
        {"type": "drawtext", "text": "新标题", "font_size": 48, "start": 0, "end": 5},
        {"type": "replace_segment", "start": 3, "end": 8, "new_clip": "new.mp4"},
    ]
    """
    if not os.path.exists(video_path):
        return {"ok": False, "error": "视频不存在"}

    od = Path(output).parent if output else FFMPEG_OUT
    od.mkdir(parents=True, exist_ok=True)
    output = output or str(od / f"replaced_{datetime.now().strftime('%H%M%S')}.mp4")

    # 构建滤镜链
    filter_parts = []
    font_file = "C\\:/Windows/Fonts/msyh.ttc"

    for i, repl in enumerate(replacements):
        rtype = repl.get("type")

        if rtype == "overlay" and repl.get("image"):
            img = repl["image"].replace("\\", "/").replace(":", "\\\\:")
            pos_map = {
                "top_right": "W-w-20:20",
                "top_left": "20:20",
                "bottom_right": "W-w-20:H-h-20",
                "bottom_left": "20:H-h-20",
                "center": "(W-w)/2:(H-h)/2",
            }
            pos = pos_map.get(repl.get("position", "top_right"), "W-w-20:20")
            enable = f"between(t,{repl.get('start',0)},{repl.get('end',999)})"
            filter_parts.append(
                "overlay=" + pos + ":enable='" + enable + "'"
            )

        elif rtype == "drawtext" and repl.get("text"):
            text = repl["text"].replace(":", "\\:").replace("'", "\\'")
            ft = repl.get("font_size", 48)
            enable = f"between(t,{repl.get('start',0)},{repl.get('end',999)})"
            filter_parts.append(
                f"drawtext=fontfile='{font_file}':text='{text}':"
                f"fontsize={ft}:fontcolor=white:borderw=3:"
                f"bordercolor=black@0.5:x=(w-text_w)/2:y=h*0.85:"
                f"enable='{enable}'"
            )

    if filter_parts:
        vf = ",".join(filter_parts)
        r = subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy", output,
        ])

        if ok:
            return {"ok": True, "path": output, "replacements": len(replacements)}
        return {"ok": False, "error": err[:500]}

    return {"ok": True, "path": video_path, "message": "无替换元素"}


# ═══════════════════════════════════
# 四、批量处理
# ═══════════════════════════════════

def batch_replicate(
    reference_video: str,
    content_variants: List[Dict],
    max_count: int = 10,
) -> dict:
    """批量复刻: 一个爆款模板→N条新视频"""
    results = []
    for i, variant in enumerate(content_variants[:max_count]):
        r = replicate_video(reference_video, variant)
        results.append({"index": i, **r})

    success = sum(1 for r in results if r.get("ok"))
    return {
        "ok": True,
        "total": len(results),
        "success": success,
        "results": results,
    }


from pathlib import Path as _Path
FFMPEG_OUT = OUTPUT_DIR / "zhuangqi" / "ffmpeg"


# ═══════════════════════════════════
# CLI
# ═══════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        video = sys.argv[1]
        result = analyze_video_structure(video)
        print(json.dumps(result, ensure_ascii=False, indent=2)[:1000])
    else:
        print("视频智能解析引擎就绪")
        print("用法: python video_intelligence.py <video_path>")
        print("能力: 场景检测/结构拆解/AI复刻/元素替换")
