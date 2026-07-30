"""
视频生成引擎 — Video Production Engine
========================================
口播脚本 → AI视频生成 → 素材自动匹配 → 多版本混剪
接入: 即梦(Jimeng) / Seedance / 剪映API
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
