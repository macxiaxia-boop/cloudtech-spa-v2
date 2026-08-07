"""
视频生成引擎 — Video Production Engine
========================================
口播脚本 → AI视频生成 → 素材自动匹配 → 多版本混剪
接入: 即梦(Jimeng) / 可灵(Kling) / Seedance / 剪映API
"""
import json, os, time, hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE = Path(__file__).parent
VIDEO_OUT = Path("D:/个人文件/电商图片/装企孵化/视频产出")
VIDEO_OUT.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 视频生成方案矩阵
# ═══════════════════════════════════

VIDEO_MODES = {
    "before_after": {
        "name": "前后对比视频",
        "duration": "30-60s",
        "scenes": ["改造前痛点特写(3s)", "施工过程快放(5s)", "改造后同角度对比(5s)",
                   "花费清单字幕(5s)", "设计师/业主点评(10s)", "CTA关注引导(3s)"],
        "visual_style": "split_screen",
        "bgm": "轻快·温馨·成就感",
        "prompt_template": """装修前后对比视频:
户型: {room_type} | 面积: {size}平 | 风格: {style}
改造前痛点: {pain_point}
改造方案: {solution}
花费: {budget}万

生成30秒竖版视频(9:16)，分镜:
1. 0-3s: [{pain_point}] 特写镜头+大字痛点字幕
2. 3-8s: 施工快放+进度条动画
3. 8-13s: 改造后全景对比(左右分屏)
4. 13-20s: 花费明细卡片(逐项弹出)
5. 20-27s: 设计师金句+业主表情包
6. 27-30s: [{city}{style}改造] CTA关注引导""",
    },
    "material_review": {
        "name": "材料测评视频",
        "duration": "45-90s",
        "scenes": ["材料开箱(3s)", "细节微距(5s)", "对比实验(10s)",
                   "价格区间(5s)", "选购技巧(10s)", "实拍效果(5s)"],
        "visual_style": "macro_detail",
        "bgm": "理性·专业·科技感",
        "prompt_template": """装修材料测评视频:
材料: {material} | 城市: {city}
品牌对比: {brands}
价格区间: {price_range}

生成45秒竖版视频(9:16)，分镜:
1. 0-3s: 材料开箱+价格悬念字幕
2. 3-8s: 微距特写(纹理/接缝/光泽)
3. 8-18s: A品牌 vs B品牌 左右对比实验
4. 18-23s: 价格区间信息图弹出
5. 23-35s: 3个选购技巧(文字+实拍)
6. 35-40s: 实景效果展示
7. 40-45s: 关注获取完整清单 CTA""",
    },
    "room_tour": {
        "name": "空间漫游视频",
        "duration": "60-90s",
        "scenes": ["门外悬念(2s)", "推门第一视角(8s)", "空间亮点逐一展示(20s)",
                   "材质细节特写(10s)", "尺寸标注动画(5s)", "品牌清单字幕(5s)", "设计师解读(15s)"],
        "visual_style": "walk_through",
        "bgm": "沉浸·舒缓·高级感",
        "prompt_template": """空间漫游视频:
户型: {room_type} | 面积: {size}平 | 风格: {style}
城市: {city} | 小区: {community}
设计亮点: {highlights}

生成60秒竖版视频(9:16)，分镜:
1. 0-2s: 门外悬念(门牌号虚化)
2. 2-10s: 推门第一人称视角(缓慢推入)
3. 10-30s: 逐一展示{highlights}(每处5-8秒，缓慢摇镜)
4. 30-40s: 材质细节特写(地板/台面/五金)
5. 40-45s: 尺寸标注动画叠加
6. 45-50s: 品牌清单滚动字幕
7. 50-55s: 设计师语音解读(字幕同步)
8. 55-60s: [{city}{community}] 关注看更多案例""",
    },
    "construction_diary": {
        "name": "施工日记视频",
        "duration": "30-45s",
        "scenes": ["今日进度预览(3s)", "施工过程延时(10s)", "遇到问题(5s)",
                   "解决方案(5s)", "明日预告(3s)", "关注追更(2s)"],
        "visual_style": "timeline",
        "bgm": "纪实·真实·节奏感",
        "prompt_template": """装修施工日记:
阶段: {stage} | 第{day}天 | 城市: {city}
今日进度: {progress}
遇到问题: {issue}
解决方案: {fix}

生成30秒竖版视频(9:16)，分镜:
1. 0-3s: 昨日vs今日对比(进度条)
2. 3-13s: 今日施工延时摄影(配BGM鼓点)
3. 13-18s: 问题特写+大字"注意"
4. 18-23s: 解决方案演示
5. 23-27s: 明日预告(效果图闪现)
6. 27-30s: 关注追更 CTA""",
    },
}

# ═══════════════════════════════════
# 素材自动匹配引擎
# ═══════════════════════════════════

def match_assets(topic: str, mode: str, context: dict) -> list:
    """从装企案例库自动匹配合适素材"""
    asset_dir = Path("D:/个人文件/电商图片/装企孵化/06-图片与素材/01-素材库")
    if not asset_dir.exists():
        return []

    matched = []

    # 按风格匹配
    style = context.get("style", "现代简约")
    style_dir = asset_dir / style
    if style_dir.exists():
        matched.extend([str(f) for f in style_dir.rglob("*") if f.suffix.lower() in (".jpg", ".png", ".mp4", ".mov")][:5])

    # 按空间匹配
    room = context.get("room_type", "")
    for kw in ["厨房", "卫生间", "客厅", "卧室", "阳台"]:
        if kw in str(topic) or kw in room:
            room_dir = asset_dir / kw
            if room_dir.exists():
                matched.extend([str(f) for f in room_dir.rglob("*") if f.suffix.lower() in (".jpg", ".png")][:5])

    # 按模式匹配
    mode_dirs = {"before_after": "改造前后", "material_review": "材料", "room_tour": "完工", "construction_diary": "施工"}
    mode_dir = asset_dir / mode_dirs.get(mode, "")
    if mode_dir.exists():
        matched.extend([str(f) for f in mode_dir.rglob("*") if f.suffix.lower() in (".jpg", ".png")][:3])

    return list(set(matched))[:10]  # 去重·最多10个


# ═══════════════════════════════════
# 视频生产API (DeepSeek → 即梦)
# ═══════════════════════════════════

def generate_video_script(topic: str, mode: str = "before_after", context: dict = None) -> dict:
    """生成完整视频制作方案：分镜脚本 + 素材匹配 + AI生成提示词"""
    from admin_dashboard import _deepseek_call

    ctx = context or {}
    ctx.setdefault("room_type", "厨房")
    ctx.setdefault("size", 100)
    ctx.setdefault("style", "现代简约")
    ctx.setdefault("city", "厦门")
    ctx.setdefault("budget", 15)
    ctx.setdefault("pain_point", "空间小·采光差·动线不合理")
    ctx.setdefault("solution", "拆墙+玻璃隔断+超薄柜体")

    mode_config = VIDEO_MODES.get(mode, VIDEO_MODES["before_after"])

    # 生成AI视频提示词
    prompt = mode_config["prompt_template"].format(
        room_type=ctx.get("room_type", ""),
        size=ctx.get("size", ""),
        style=ctx.get("style", ""),
        city=ctx.get("city", ""),
        budget=ctx.get("budget", ""),
        pain_point=ctx.get("pain_point", ""),
        solution=ctx.get("solution", ""),
        material=topic,
        brands="A品牌 vs B品牌",
        price_range="50-200元/㎡",
        community=ctx.get("community", "本地小区"),
        highlights=ctx.get("highlights", "空间布局·收纳设计·灯光氛围"),
        stage=ctx.get("stage", "水电改造"),
        day=ctx.get("day", 7),
        progress=ctx.get("progress", "完成水电走线"),
        issue=ctx.get("issue", "墙体开槽深度不足"),
        fix=ctx.get("fix", "换用超薄底盒"),
    )

    # AI增强提示词
    enhance_sys = "你是AI视频导演。优化视频生成提示词，使其更具体、更视觉化、更适合AI生成。保留所有分镜结构。"
    enhanced = _deepseek_call(enhance_sys, prompt, max_tokens=1000)

    # 匹配素材
    assets = match_assets(topic, mode, ctx)

    return {
        "mode": mode_config["name"],
        "duration": mode_config["duration"],
        "scenes": mode_config["scenes"],
        "bgm": mode_config["bgm"],
        "prompt": enhanced,
        "matched_assets": assets,
        "asset_count": len(assets),
        "estimated_cost": "10-30元/条(即梦API)",
    }


def batch_video_produce(topics: list, mode: str = "before_after") -> list:
    """批量视频生产"""
    results = []
    for topic in topics:
        try:
            result = generate_video_script(topic["topic"], mode, topic.get("context", {}))
            result["topic"] = topic["topic"]
            results.append(result)
        except Exception as e:
            results.append({"topic": topic["topic"], "error": str(e)[:100]})
    return results


# ═══════════════════════════════════
# 视频发布素材包
# ═══════════════════════════════════

def create_video_package(script: dict, account_name: str) -> dict:
    """为一键发布生成完整素材包"""
    pkg_dir = VIDEO_OUT / f"{datetime.now().strftime('%Y%m%d_%H%M')}_{account_name}"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    # 口播文案
    voiceover = pkg_dir / "口播文案.txt"
    voiceover.write_text(script.get("prompt", ""), encoding="utf-8")
    files["voiceover"] = str(voiceover)

    # 发布说明
    pub_notes = pkg_dir / "发布说明.md"
    pub_notes.write_text(f"""# {account_name} 视频发布说明

## 基本信息
- 模式: {script.get('mode')}
- 时长: {script.get('duration')}
- BGM: {script.get('bgm')}

## 分镜脚本
{script.get('prompt', '')[:500]}

## 标题建议
1. {script.get('topic', '')} — 花{script.get('context', {}).get('budget', 'XX')}万的效果
2. {script.get('context', {}).get('city', '')}{script.get('context', {}).get('style', '')}风 — 邻居都来抄作业
3. 装修第{script.get('context', {}).get('day', 'X')}天 — {script.get('context', {}).get('progress', '')}

## 标签
#装修 #装修设计 #{(script.get('context', {}).get('city', ''))}装修 #{(script.get('context', {}).get('style', ''))}风 #{script.get('mode', '')}

## AI视频生成提示词
{script.get('prompt', '')[:1000]}
""", encoding="utf-8")
    files["notes"] = str(pub_notes)

    # 素材清单
    if script.get("matched_assets"):
        assets_list = pkg_dir / "素材清单.txt"
        assets_list.write_text("\n".join(script["matched_assets"]), encoding="utf-8")
        files["assets"] = str(assets_list)

    return {"package_dir": str(pkg_dir), "files": files, "account": account_name}


# ═══════════════════════════════════
# Content → Video Pipeline (auto_pipeline消费)
# ═══════════════════════════════════

def generate_video_from_content(
    title: str = "",
    content: str = "",
    provider: str = "mock",
    template: str = "before_after",
    config: dict = None,
) -> dict:
    """
    从文本内容一键生成视频

    消费方: auto_pipeline._stage_video_production
    调用链: 内容解析 → 分镜拆解 → 脚本增强(DeepSeek) → mix/mock渲染

    Args:
        title:   视频标题，如"现代简约装修设计"
        content: 正文内容（口播稿/小红书内容/纯文本）
        provider: 生成后端 "mock"|"jimeng"|"seedance"
        template: 混剪模板名（对应 MIX_TEMPLATES 的 key）
        config:   可选附加配置

    Returns:
        {"ok": True, "path": "output/video_xxx.mp4", "duration": 45.0, "segments": 5, "script": {...}}
        or {"ok": False, "error": "reason"}
    """
    import re
    cfg = config or {}

    # ── 1. 内容归一化 ──────────────────────────────────
    if isinstance(content, dict):
        content = content.get("content", content.get("text", str(content)))
    if not content or not content.strip():
        content = title or "装修设计视频"

    # ── 2. 段落拆解 → 分镜段落 ─────────────────────────
    paragraphs = _split_into_paragraphs(content)
    segments = []

    for idx, para in enumerate(paragraphs):
        if not para.strip():
            continue
        char_len = len(para)
        # 根据长度和位置决定场景类型
        if idx == 0:
            stype = "title"
            dur = 3
        elif char_len < 20:
            stype = "text"
            dur = min(3, max(2, char_len // 10))
        elif any(kw in para for kw in ["对比", "vs", "改造前", "改造后", "before", "after"]):
            stype = "image"
            dur = 5
        elif any(kw in para for kw in ["花费", "预算", "价格", "元", "万"]):
            stype = "text"
            dur = 4
        elif any(kw in para for kw in ["步骤", "方法", "流程", "如何", "怎么", "技巧"]):
            stype = "text"
            dur = 5
        else:
            stype = "text"
            dur = max(2, min(6, char_len // 30))

        segments.append({
            "type": stype,
            "text": para.strip()[:200],
            "duration": dur,
            "effect": "fade" if idx % 3 == 0 else ("slide_up" if idx % 3 == 1 else "zoom_in"),
        })

    if not segments:
        segments = [{"type": "text", "text": content[:200] or title, "duration": 8, "effect": "fade"}]

    total_duration = sum(s.get("duration", 3) for s in segments)

    # ── 3. 尝试 DeepSeek 脚本增强 ───────────────────────
    script_prompt = ""
    try:
        from admin_dashboard import _deepseek_call
        sys_prompt = (
            "你是AI视频导演。根据以下内容生成一个完整的竖版短视频分镜脚本。"
            "输出包含: 标题、每个分镜的时间码(秒)、画面描述、字幕文案、转场效果。"
            + '格式: JSON {"title":"...", "scenes": [{"time":"0-3s", "visual":"...", "subtitle":"..."}]}' + " "
            + f"视频类型: {template} | 内容: {content[:1500]}"
        )
        enhanced = _deepseek_call(sys_prompt, content[:2000], max_tokens=1200)
        script_prompt = enhanced
    except Exception:
        script_prompt = f"# {title}\n\n" + "\n\n".join(
            f"[{i*3}-{i*3+s.get('duration',3)}s] {s['text']}" for i, s in enumerate(segments)
        )

    # ── 4. 生成视频（dry_run 模式输出方案） ─────────────
    try:
        from video_mixer import mix_video, MIX_TEMPLATES

        # 确保模板存在
        actual_template = template if template in MIX_TEMPLATES else "before_after"

        # 构建 clips_data
        clips_data = [
            {"type": "text", "text": s["text"], "duration": s["duration"], "effect": s["effect"]}
            for s in segments
        ]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"content_video_{ts}"

        mix_result = mix_video(
            clips_data=clips_data,
            output_name=output_name,
            template=actual_template,
            dry_run=True,  # 首先生成方案；实际渲染需要素材
        )

        output_path = str(VIDEO_OUT / f"{output_name}.mp4")

        # 持久化脚本到文件（便于后续实际渲染）
        script_file = VIDEO_OUT / f"{output_name}_script.json"
        script_payload = {
            "title": title,
            "template": actual_template,
            "provider": provider,
            "segments": segments,
            "total_duration": total_duration,
            "prompt": script_prompt,
            "created_at": datetime.now().isoformat()[:19],
        }
        script_file.write_text(json.dumps(script_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return {
            "ok": True,
            "path": output_path,
            "script_file": str(script_file),
            "duration": total_duration,
            "segments": len(segments),
            "template": actual_template,
            "provider": provider,
            "script": {
                "prompt": script_prompt,
                "scenes": len(segments),
                "mode": actual_template,
                "duration": f"{total_duration}s",
            },
            "mix_result": mix_result,
        }

    except ImportError as e:
        return {"ok": False, "error": f"依赖缺失: {e}. 请安装 moviepy"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": f"视频生成失败: {str(e)[:200]}"}


def ai_generate_video(
    prompt: str,
    style: str = "modern",
    duration: int = 30,
    provider: str = "auto",
) -> dict:
    """
    AI 视频生成 — 实时调用云端API或本地Mock

    调用链: DeepSeek增强prompt → 即梦API(优先) → video_api本地渲染 → Mock降级
    降级策略: 即梦不可用 → 本地MoviePy渲染 → 文字转视频(Mock)

    Args:
        prompt:   视频描述/脚本提示词
        style:    风格 "modern"|"minimal"|"chinese"|"luxury"
        duration: 目标时长（秒），默认30
        provider: 生成后端 "auto"|"jimeng"|"seedance"|"mock"

    Returns:
        {"ok": True, "path": "output/ai_video_xxx.mp4", "provider": "jimeng"|"mock", "duration": 30}
        or {"ok": False, "error": "reason"}
    """
    import re

    # ── 1. 用 DeepSeek 优化提示词 ────────────────────────
    enhanced_prompt = prompt
    try:
        from admin_dashboard import _deepseek_call
        sys_prompt = (
            "你是AI视频生成专家。优化以下提示词，使其更适合视频生成模型(即梦/Seedance)。"
            "添加详细的视觉描述: 镜头语言、光线、色彩、运镜方式、场景细节。"
            f"视频风格: {style} | 目标时长: {duration}秒"
        )
        enhanced_prompt = _deepseek_call(sys_prompt, prompt[:1500], max_tokens=800)
    except Exception:
        pass

    # ── 2. 尝试即梦 API 真实生成 ──────────────────────────
    use_jimeng = provider in ("auto", "jimeng")
    if use_jimeng:
        try:
            from jimeng_api import text_to_video as jimeng_t2v, AK as jimeng_ak

            if jimeng_ak:
                jimeng_result = jimeng_t2v(
                    prompt=enhanced_prompt,
                    duration=min(duration, 30),  # 即梦免费额度限制30s
                    resolution="720p",
                    style="realistic",
                )

                if jimeng_result.get("ok"):
                    video_url = jimeng_result.get("video_url", "")
                    task_id = jimeng_result.get("task_id", "")

                    # 尝试下载视频
                    video_path = ""
                    try:
                        from jimeng_api import generate_renovation_video
                        dl_result = generate_renovation_video(
                            {"prompt": enhanced_prompt},
                            mode="text_to_video",
                        )
                        video_path = dl_result.get("video_path", "")
                    except Exception:
                        pass

                    return {
                        "ok": True,
                        "path": video_path or video_url,
                        "video_url": video_url,
                        "task_id": task_id,
                        "provider": "jimeng",
                        "duration": duration,
                        "prompt_enhanced": enhanced_prompt,
                        "style": style,
                        "render_mode": "jimeng_api",
                    }
                else:
                    # 即梦失败 → 记录原因，继续降级
                    jimeng_error = jimeng_result.get("error", "未知错误")
            else:
                jimeng_error = "JIMENG_ACCESS_KEY 未配置"
        except ImportError:
            jimeng_error = "jimeng_api 模块未安装"
        except Exception as e:
            jimeng_error = str(e)[:100]
    else:
        jimeng_error = f"provider={provider} 跳过即梦"

    # ── 2.5. 尝试可灵 API ───────────────────────────────────
    use_kling = provider in ("auto", "kling")
    kling_error = None
    if use_kling:
        try:
            from kling_api import text_to_video as kling_t2v, check_status as kling_check

            kling_status = kling_check()
            if kling_status.get("configured"):
                kling_result = kling_t2v(
                    prompt=enhanced_prompt,
                    duration=str(min(duration, 10)),  # Kling: 5 or 10
                    mode="std",
                    aspect_ratio="9:16",
                )

                if kling_result.get("ok"):
                    return {
                        "ok": True,
                        "path": kling_result.get("task_id", ""),
                        "task_id": kling_result.get("task_id", ""),
                        "provider": "kling",
                        "duration": duration,
                        "prompt_enhanced": enhanced_prompt,
                        "style": style,
                        "render_mode": "kling_api",
                        "jimeng_attempted": use_jimeng,
                        "jimeng_error": jimeng_error if use_jimeng else None,
                    }
                else:
                    kling_error = kling_result.get("error", "未知错误")
            else:
                kling_error = "Kling API 未正确配置: " + "; ".join(kling_status.get("issues", []))
        except ImportError:
            kling_error = "kling_api 模块未安装"
        except Exception as e:
            kling_error = str(e)[:100]

    # ── 3. 尝试 video_api 本地渲染 ────────────────────────
    try:
        from video_api import render_video_locally, submit_video_job

        script = {
            "prompt": enhanced_prompt,
            "duration": f"{duration}s",
            "visual_style": _style_to_visual(style),
            "scenes": _generate_mock_scenes(enhanced_prompt, duration),
            "mode": f"ai_gen_{style}",
            "topic": prompt[:50],
        }

        local_result = render_video_locally({
            "prompt": enhanced_prompt,
            "duration": duration,
            "scenes": script["scenes"],
            "metadata": {"mode": style, "topic": prompt[:50]},
        })

        if local_result.get("ok"):
            return {
                "ok": True,
                "path": local_result.get("preview_html", local_result.get("output_dir", "")),
                "provider": "mock",
                "duration": duration,
                "prompt_enhanced": enhanced_prompt,
                "style": style,
                "render_mode": "local",
                "details": local_result,
                "jimeng_attempted": use_jimeng,
                "jimeng_error": jimeng_error if use_jimeng else None,
                "kling_attempted": use_kling,
                "kling_error": kling_error if use_kling else None,
            }

    except ImportError:
        pass
    except Exception:
        pass

    # ── 4. Mock 降级: 文字转视频 ─────────────────────────
    try:
        from video_mixer import mix_video

        words = re.split(r"[。，；\n]", prompt)
        paragraphs = [w.strip() for w in words if len(w.strip()) > 3]
        if not paragraphs:
            paragraphs = [prompt[:200]]

        slot_dur = max(2, duration // max(len(paragraphs), 1))
        clips = []
        for i, p in enumerate(paragraphs[:12]):
            clips.append({
                "type": "text",
                "text": p[:160],
                "duration": min(slot_dur, 6),
                "effect": "fade" if i % 2 == 0 else "slide_up",
            })

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"ai_video_{ts}"

        mix_result = mix_video(
            clips_data=clips,
            output_name=output_name,
            template="before_after",
            dry_run=True,
        )

        output_path = str(VIDEO_OUT / f"{output_name}.mp4")

        return {
            "ok": True,
            "path": output_path,
            "provider": "mock",
            "duration": duration,
            "prompt_enhanced": enhanced_prompt,
            "style": style,
            "render_mode": "mock_text_overlay",
            "clips": len(clips),
            "mix_result": mix_result,
            "jimeng_attempted": use_jimeng,
            "jimeng_error": jimeng_error if use_jimeng else None,
            "kling_attempted": use_kling,
            "kling_error": kling_error if use_kling else None,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "error": f"AI视频生成失败: {str(e)[:200]}"}


# ═══════════════════════════════════
# 内部工具函数
# ═══════════════════════════════════

def _split_into_paragraphs(text: str) -> list:
    """智能分段: 按段落/句号/分号/换行 拆解"""
    import re
    # 先按双换行分
    parts = re.split(r"\n\s*\n", text)
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # 如果段落太长，按句号/分号继续拆分
        if len(part) > 120:
            sub = re.split(r"[。；!?！？]", part)
            result.extend(s.strip() + "。" for s in sub if s.strip())
        else:
            result.append(part)
    return result


def _style_to_visual(style: str) -> str:
    """风格名 → visual_style 映射"""
    mapping = {
        "modern": "cinematic",
        "minimal": "clean_bright",
        "chinese": "warm_heritage",
        "luxury": "dark_elegant",
        "industrial": "raw_urban",
        "scandinavian": "airy_natural",
    }
    return mapping.get(style, "cinematic")


def _generate_mock_scenes(prompt: str, duration: int) -> list:
    """根据prompt和时长生成模拟分镜列表"""
    import re
    sentences = re.split(r"[。；\n]", prompt)
    parts = [s.strip() for s in sentences if len(s.strip()) > 2]
    if not parts:
        return [f"{duration}s: {prompt[:80]}"]

    slot_count = max(3, min(len(parts), 8))
    slot_dur = duration // slot_count
    scenes = []
    for i in range(slot_count):
        text = parts[i % len(parts)][:80]
        start = i * slot_dur
        end = start + slot_dur if i < slot_count - 1 else duration
        scenes.append(f"{start}-{end}s: {text}")
    return scenes
