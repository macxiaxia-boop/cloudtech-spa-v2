"""
视频混剪引擎 — Video Mixer Engine
==================================
对标筷子科技「短视频智能混剪」：批量混剪、模板系统、字幕叠加、转场特效
依赖: moviepy, pillow, numpy (需 pip install)

功能:
1. 批量混剪 — 从素材库自动生成N条变体
2. 模板系统 — 前后对比/空间漫游/施工日记/材料测评
3. 字幕叠加 — 自动时间轴字幕
4. 转场特效 — 淡入淡出/滑动/缩放
5. 背景音乐 — 自动配乐+音量调节
"""
from cloudtech_app import DATA_DIR, OUTPUT_DIR

import json, os, random, hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

BASE = Path(__file__).parent
MIXER_OUT = OUTPUT_DIR / "zhuangqi" /"mixer"
MIXER_OUT.mkdir(parents=True, exist_ok=True)

# 延迟导入，避免未安装时崩溃
_moviepy_available = False
try:
    from moviepy import (
        VideoFileClip, ImageClip, TextClip, AudioFileClip,
        CompositeVideoClip, concatenate_videoclips, ColorClip
    )
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    _moviepy_available = True
except ImportError:
    pass

# ═══════════════════════════════════
# 混剪模板系统
# ═══════════════════════════════════

MIX_TEMPLATES = {
    "before_after": {
        "name": "前后对比混剪",
        "duration": 30,
        "resolution": (1080, 1920),  # 9:16 竖版
        "fps": 30,
        "segments": [
            {"type": "title", "text": "改造前 vs 改造后", "duration": 3, "effect": "zoom_in"},
            {"type": "before", "duration": 5, "label": "改造前", "effect": "crossfade"},
            {"type": "transition", "duration": 1, "text": "→"},
            {"type": "after", "duration": 5, "label": "改造后", "effect": "crossfade"},
            {"type": "details", "duration": 8, "text": "花费/工期/材料", "effect": "slide_up"},
            {"type": "contact", "duration": 5, "text": "关注获取报价", "effect": "fade_in"},
            {"type": "logo", "duration": 3, "effect": "fade"},
        ],
        "bgm_style": "upbeat_warm",
    },
    "room_tour": {
        "name": "空间漫游混剪",
        "duration": 45,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{size}平{style}风，进门那一刻我愣住了", "duration": 3},
            {"type": "panorama", "duration": 5, "label": "全屋概览"},
            {"type": "detail_1", "duration": 8, "label": "客厅亮点"},
            {"type": "detail_2", "duration": 8, "label": "厨房/卫生间"},
            {"type": "detail_3", "duration": 8, "label": "卧室/书房"},
            {"type": "price", "duration": 6, "text": "硬装{w}万+软装{s}万"},
            {"type": "cta", "duration": 4, "text": "{city}装修找我们"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "ambient_calm",
    },
    "construction_diary": {
        "name": "施工日记混剪",
        "duration": 35,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "progress", "text": "装修第{day}天", "duration": 3},
            {"type": "timelapse", "duration": 8, "label": "今日施工"},
            {"type": "detail", "duration": 8, "label": "施工细节"},
            {"type": "tip", "duration": 8, "text": "装修避坑: {tip}"},
            {"type": "preview", "duration": 5, "text": "明天: {next_stage}"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "rhythmic_real",
    },
    "material_review": {
        "name": "材料测评混剪",
        "duration": 40,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{material}怎么选？别再被坑了", "duration": 3},
            {"type": "unboxing", "duration": 5, "label": "开箱实拍"},
            {"type": "compare", "duration": 12, "label": "品牌对比测试"},
            {"type": "price", "duration": 8, "text": "价格区间+避坑"},
            {"type": "tips", "duration": 8, "text": "3个选购技巧"},
            {"type": "logo", "duration": 4},
        ],
        "bgm_style": "tech_professional",
    },
    "product_showcase": {
        "name": "产品展示混剪",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{product_name}", "duration": 2},
            {"type": "showcase", "duration": 10, "label": "产品特写"},
            {"type": "features", "duration": 8, "text": "核心卖点"},
            {"type": "cta", "duration": 5, "text": "限时优惠"},
        ],
        "bgm_style": "energetic_pop",
    },
    # ═══ P2 扩展模板 (50+) ═══
    "budget_reveal": {
        "name": "预算公开混剪",
        "duration": 40,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{size}平装完花了{w}万，每笔都公开", "duration": 3},
            {"type": "hard_cost", "duration": 10, "label": "硬装明细"},
            {"type": "soft_cost", "duration": 10, "label": "软装+家电"},
            {"type": "save_tips", "duration": 8, "text": "我省钱的3个方法"},
            {"type": "mistakes", "duration": 6, "text": "这{w}万不该花"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "honest_calm",
    },
    "style_comparison": {
        "name": "风格对比混剪",
        "duration": 35,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "title", "text": "{style_a} vs {style_b}", "duration": 3},
            {"type": "style_a_show", "duration": 10, "label": "风格A效果"},
            {"type": "style_b_show", "duration": 10, "label": "风格B效果"},
            {"type": "price_compare", "duration": 5, "text": "价格对比"},
            {"type": "verdict", "duration": 4, "text": "结论+推荐"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "balanced",
    },
    "small_space_hack": {
        "name": "小户型改造",
        "duration": 35,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "problem", "text": "{size}平小户型怎么装", "duration": 3},
            {"type": "before_pain", "duration": 5, "label": "改造前痛点"},
            {"type": "solution_1", "duration": 8, "label": "方案1: 空间复用"},
            {"type": "solution_2", "duration": 8, "label": "方案2: 视觉扩容"},
            {"type": "result", "duration": 5, "label": "改造后效果"},
            {"type": "tips", "duration": 4, "text": "3个小户型秘诀"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "creative_light",
    },
    "kitchen_reno": {
        "name": "厨房改造专题",
        "duration": 35,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "厨房这样装，做饭变成享受", "duration": 3},
            {"type": "layout", "duration": 6, "label": "布局方案"},
            {"type": "storage", "duration": 8, "label": "收纳系统"},
            {"type": "appliance", "duration": 6, "label": "嵌入式电器"},
            {"type": "countertop", "duration": 6, "label": "台面材质对比"},
            {"type": "tips", "duration": 4, "text": "厨房避坑指南"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "warm_kitchen",
    },
    "bathroom_spa": {
        "name": "卫生间改造",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "dream", "text": "把酒店SPA搬回家", "duration": 3},
            {"type": "waterproof", "duration": 5, "label": "防水工艺"},
            {"type": "wet_dry", "duration": 5, "label": "干湿分离"},
            {"type": "lighting", "duration": 5, "label": "灯光氛围"},
            {"type": "storage", "duration": 5, "label": "收纳设计"},
            {"type": "price", "duration": 5, "text": "改造花费"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "spa_calm",
    },
    "balcony_garden": {
        "name": "阳台花园改造",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "before", "duration": 3, "label": "改造前: 杂物阳台"},
            {"type": "plan", "duration": 5, "label": "设计方案"},
            {"type": "plants", "duration": 7, "label": "植物选择"},
            {"type": "furniture", "duration": 5, "label": "阳台家具"},
            {"type": "after", "duration": 4, "label": "改造后效果"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "nature_light",
    },
    "before_rental": {
        "name": "出租房改造",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{amount}元改造出租房", "duration": 3},
            {"type": "before", "duration": 4, "label": "改造前"},
            {"type": "diy", "duration": 8, "label": "DIY过程"},
            {"type": "after", "duration": 5, "label": "改造后"},
            {"type": "cost", "duration": 3, "text": "总花费{amount}元"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "budget_happy",
    },
    "smart_home": {
        "name": "智能家居安装",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{size}平全屋智能花了{w}万", "duration": 3},
            {"type": "devices", "duration": 8, "label": "智能设备清单"},
            {"type": "install", "duration": 5, "label": "安装过程"},
            {"type": "demo", "duration": 8, "label": "场景演示"},
            {"type": "tips", "duration": 4, "text": "避坑提醒"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "tech_future",
    },
    "kids_room": {
        "name": "儿童房设计",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "儿童房这样装，用到18岁", "duration": 3},
            {"type": "safety", "duration": 6, "label": "安全设计"},
            {"type": "growth", "duration": 6, "label": "成长性设计"},
            {"type": "storage", "duration": 5, "label": "玩具收纳"},
            {"type": "study", "duration": 5, "label": "学习区"},
            {"type": "tips", "duration": 3, "text": "3个设计原则"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "playful",
    },
    "elderly_home": {
        "name": "适老化改造",
        "duration": 35,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "给父母装修，这5点最重要", "duration": 3},
            {"type": "anti_slip", "duration": 6, "label": "防滑地面"},
            {"type": "handrail", "duration": 6, "label": "扶手系统"},
            {"type": "lighting", "duration": 5, "label": "照明设计"},
            {"type": "smart", "duration": 7, "label": "紧急呼叫+智能"},
            {"type": "tips", "duration": 5, "text": "适老化改造补贴"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "warm_care",
    },
    "office_reno": {
        "name": "办公室装修",
        "duration": 30,
        "resolution": (1920, 1080),  # 横版
        "fps": 30,
        "segments": [
            {"type": "before", "duration": 4, "label": "改造前"},
            {"type": "design", "duration": 8, "label": "设计方案"},
            {"type": "construction", "duration": 6, "label": "施工过程"},
            {"type": "result", "duration": 8, "label": "完工效果"},
            {"type": "logo", "duration": 4},
        ],
        "bgm_style": "professional",
    },
    "shop_reno": {
        "name": "店铺装修",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "brand", "text": "{shop_name}形象升级", "duration": 3},
            {"type": "before", "duration": 4, "label": "装修前"},
            {"type": "facade", "duration": 6, "label": "门头设计"},
            {"type": "interior", "duration": 6, "label": "店内设计"},
            {"type": "after", "duration": 4, "label": "完工效果"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "energetic",
    },
    "season_tips": {
        "name": "季节装修Tips",
        "duration": 20,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "season", "text": "{season}装修注意事项", "duration": 3},
            {"type": "tip_1", "duration": 5, "text": "要点1"},
            {"type": "tip_2", "duration": 5, "text": "要点2"},
            {"type": "tip_3", "duration": 5, "text": "要点3"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "light_info",
    },
    "client_testimonial": {
        "name": "客户见证",
        "duration": 35,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "intro", "text": "{name}的家装完了", "duration": 3},
            {"type": "before_show", "duration": 5, "label": "装修前"},
            {"type": "interview", "duration": 10, "label": "业主采访"},
            {"type": "after_show", "duration": 8, "label": "装修后"},
            {"type": "rating", "duration": 5, "text": "满意度: ⭐⭐⭐⭐⭐"},
            {"type": "cta", "duration": 4, "text": "你也想要这样的家?"},
        ],
        "bgm_style": "warm_story",
    },
    "designer_intro": {
        "name": "设计师介绍",
        "duration": 20,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "name", "text": "{designer_name}", "duration": 2},
            {"type": "work", "duration": 8, "label": "代表作品"},
            {"type": "style", "duration": 5, "label": "设计风格"},
            {"type": "contact", "duration": 3, "text": "预约设计"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "elegant",
    },
    "promo_flash": {
        "name": "限时活动",
        "duration": 15,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{offer}限时优惠", "duration": 3},
            {"type": "details", "duration": 8, "text": "活动详情"},
            {"type": "urgency", "duration": 3, "text": "仅限{deadline}"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "urgent",
    },
    "water_electric": {
        "name": "水电工艺展示",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "importance", "text": "水电做不好，全屋白装修", "duration": 3},
            {"type": "pipe", "duration": 6, "label": "水管工艺"},
            {"type": "wire", "duration": 6, "label": "电路工艺"},
            {"type": "detail", "duration": 6, "label": "细节特写"},
            {"type": "test", "duration": 5, "label": "打压测试"},
            {"type": "tips", "duration": 3, "text": "验收标准"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "professional",
    },
    "waterproof": {
        "name": "防水工艺",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "防水做3遍，10年不漏水", "duration": 3},
            {"type": "clean", "duration": 4, "label": "基层清理"},
            {"type": "coat_1", "duration": 4, "label": "第一遍防水"},
            {"type": "coat_2", "duration": 4, "label": "第二遍防水"},
            {"type": "test", "duration": 5, "label": "48h闭水试验"},
            {"type": "protect", "duration": 3, "label": "保护层"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "detailed",
    },
    "tile_laying": {
        "name": "瓷砖铺贴",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "prep", "duration": 4, "label": "基层找平"},
            {"type": "layout", "duration": 4, "label": "排砖放线"},
            {"type": "paste", "duration": 6, "label": "铺贴过程"},
            {"type": "level", "duration": 4, "label": "水平检验"},
            {"type": "gap", "duration": 4, "label": "缝隙控制"},
            {"type": "grout", "duration": 5, "label": "美缝效果"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "craft",
    },
    "painting": {
        "name": "油漆工艺",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "putty", "duration": 5, "label": "批腻子"},
            {"type": "sand", "duration": 4, "label": "打磨"},
            {"type": "prime", "duration": 4, "label": "底漆"},
            {"type": "topcoat", "duration": 4, "label": "面漆"},
            {"type": "check", "duration": 4, "label": "验收检查"},
            {"type": "tips", "duration": 3, "text": "油漆避坑"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "smooth",
    },
    "custom_cabinet": {
        "name": "定制柜安装",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "design", "duration": 5, "label": "设计图纸"},
            {"type": "material", "duration": 5, "label": "板材展示"},
            {"type": "assembly", "duration": 8, "label": "组装过程"},
            {"type": "install", "duration": 6, "label": "安装效果"},
            {"type": "tips", "duration": 4, "text": "定制柜避坑"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "craft",
    },
    "lighting_design": {
        "name": "灯光设计",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "before", "duration": 3, "label": "只有主灯的效果"},
            {"type": "layers", "duration": 6, "label": "无主灯设计"},
            {"type": "scene", "duration": 7, "label": "场景模式"},
            {"type": "temp", "duration": 5, "label": "色温对比"},
            {"type": "before_after", "duration": 5, "label": "灯光改造前后"},
            {"type": "tips", "duration": 3, "text": "灯光布局原则"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "atmospheric",
    },
    "curtain_blind": {
        "name": "窗帘选购",
        "duration": 20,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "窗帘选错，全屋毁一半", "duration": 3},
            {"type": "type", "duration": 5, "label": "窗帘类型对比"},
            {"type": "fabric", "duration": 4, "label": "面料选择"},
            {"type": "install", "duration": 4, "label": "安装方式"},
            {"type": "tips", "duration": 3, "text": "3个省钱秘诀"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "home_warm",
    },
    "furniture_arrange": {
        "name": "家具布局",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "problem", "text": "{size}平家具怎么摆", "duration": 3},
            {"type": "flow", "duration": 5, "label": "动线设计"},
            {"type": "size", "duration": 5, "label": "尺寸选择"},
            {"type": "layout", "duration": 5, "label": "布局对比"},
            {"type": "result", "duration": 4, "label": "最佳方案"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "clean",
    },
    "greenery": {
        "name": "绿植搭配",
        "duration": 20,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "这5种植物，让你家高级10倍", "duration": 3},
            {"type": "plant_1", "duration": 4, "label": "推荐1"},
            {"type": "plant_2", "duration": 4, "label": "推荐2"},
            {"type": "plant_3", "duration": 4, "label": "推荐3"},
            {"type": "care", "duration": 3, "text": "养护技巧"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "nature",
    },
    "house_inspection": {
        "name": "收房验房",
        "duration": 35,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "收房不验这10项，入住就后悔", "duration": 3},
            {"type": "door_window", "duration": 5, "label": "门窗检查"},
            {"type": "wall", "duration": 5, "label": "墙面空鼓"},
            {"type": "floor", "duration": 5, "label": "地面水平"},
            {"type": "water", "duration": 5, "label": "水电检查"},
            {"type": "tools", "duration": 4, "label": "验房工具"},
            {"type": "checklist", "duration": 5, "text": "验房清单"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "alert_info",
    },
    "fengshui": {
        "name": "装修风水",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "闽南人装修必看的3个风水", "duration": 3},
            {"type": "door", "duration": 5, "label": "大门朝向"},
            {"type": "kitchen", "duration": 5, "label": "厨房布局"},
            {"type": "bedroom", "duration": 5, "label": "卧室安床"},
            {"type": "modern", "duration": 4, "text": "现代科学解释"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "traditional",
    },
    "color_matching": {
        "name": "色彩搭配",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "装修配色万能公式", "duration": 3},
            {"type": "rule_631", "duration": 5, "label": "6:3:1法则"},
            {"type": "palette", "duration": 6, "label": "配色方案"},
            {"type": "mistake", "duration": 5, "label": "常见翻车"},
            {"type": "tips", "duration": 4, "text": "配色工具推荐"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "artsy",
    },
    "storage_hack": {
        "name": "收纳技巧",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "{size}平收纳量翻倍的秘密", "duration": 3},
            {"type": "vertical", "duration": 5, "label": "垂直收纳"},
            {"type": "hidden", "duration": 5, "label": "隐藏收纳"},
            {"type": "multi", "duration": 5, "label": "多功能家具"},
            {"type": "before_after", "duration": 4, "label": "收纳前后对比"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "organized",
    },
    "air_quality": {
        "name": "除甲醛指南",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "新房除甲醛，90%的人都做错了", "duration": 3},
            {"type": "source", "duration": 4, "label": "甲醛来源"},
            {"type": "myth", "duration": 5, "label": "常见误区"},
            {"type": "method", "duration": 6, "label": "正确方法"},
            {"type": "test", "duration": 4, "label": "检测标准"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "health_alert",
    },
    "floor_heating": {
        "name": "地暖安装",
        "duration": 30,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "南方装地暖，到底值不值", "duration": 3},
            {"type": "type", "duration": 5, "label": "水暖vs电暖"},
            {"type": "install", "duration": 7, "label": "安装过程"},
            {"type": "cost", "duration": 5, "label": "费用分析"},
            {"type": "experience", "duration": 5, "label": "使用体验"},
            {"type": "verdict", "duration": 3, "text": "结论+建议"},
            {"type": "logo", "duration": 2},
        ],
        "bgm_style": "tech_warm",
    },
    "ac_choice": {
        "name": "空调选购",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "空调买错，电费翻倍", "duration": 3},
            {"type": "type", "duration": 5, "label": "中央vs挂机vs风管"},
            {"type": "size", "duration": 4, "label": "匹数计算"},
            {"type": "brand", "duration": 5, "label": "品牌对比"},
            {"type": "install", "duration": 4, "label": "安装注意"},
            {"type": "tips", "duration": 3, "text": "省钱建议"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "info_clean",
    },
    "door_selection": {
        "name": "室内门选购",
        "duration": 20,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "室内门怎么选？看懂这4点不踩坑", "duration": 3},
            {"type": "material", "duration": 5, "label": "材质对比"},
            {"type": "style", "duration": 4, "label": "风格搭配"},
            {"type": "hardware", "duration": 4, "label": "五金件"},
            {"type": "tips", "duration": 3, "text": "砍价技巧"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "home_tips",
    },
    "window_selection": {
        "name": "窗户选购",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "importance", "text": "窗户选错，噪音+漏水", "duration": 3},
            {"type": "aluminum", "duration": 5, "label": "铝合金vs断桥铝"},
            {"type": "glass", "duration": 5, "label": "玻璃选择"},
            {"type": "install", "duration": 5, "label": "安装工艺"},
            {"type": "price", "duration": 4, "label": "价格参考"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "practical",
    },
    "wall_treatment": {
        "name": "墙面处理",
        "duration": 20,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "options", "text": "乳胶漆vs墙布vs硅藻泥", "duration": 3},
            {"type": "paint", "duration": 5, "label": "乳胶漆"},
            {"type": "wallpaper", "duration": 4, "label": "墙布"},
            {"type": "diatom", "duration": 4, "label": "硅藻泥"},
            {"type": "verdict", "duration": 3, "text": "推荐方案"},
            {"type": "logo", "duration": 1},
        ],
        "bgm_style": "compare",
    },
    "floor_selection": {
        "name": "地板选购",
        "duration": 25,
        "resolution": (1080, 1920),
        "fps": 30,
        "segments": [
            {"type": "hook", "text": "瓷砖还是木地板？看完不纠结", "duration": 3},
            {"type": "tile", "duration": 5, "label": "瓷砖"},
            {"type": "wood", "duration": 5, "label": "木地板"},
            {"type": "spc", "duration": 4, "label": "SPC石塑"},
            {"type": "recommend", "duration": 5, "text": "闽南推荐方案"},
            {"type": "logo", "duration": 3},
        ],
        "bgm_style": "compare",
    },
}

# ═══════════════════════════════════
# 字幕叠加系统
# ═══════════════════════════════════

SUBTITLE_STYLES = {
    "bold_yellow": {
        "font_size": 48, "color": "yellow", "stroke_color": "black",
        "stroke_width": 3, "position": ("center", 0.85),
    },
    "clean_white": {
        "font_size": 42, "color": "white", "stroke_color": "rgba(0,0,0,0.6)",
        "stroke_width": 2, "position": ("center", 0.82),
    },
    "minimal_bottom": {
        "font_size": 36, "color": "white", "stroke_color": "rgba(0,0,0,0.5)",
        "stroke_width": 1, "position": ("center", 0.92),
    },
}

# ═══════════════════════════════════
# 批量混剪核心引擎
# ═══════════════════════════════════

def check_dependencies() -> dict:
    """检查视频处理依赖"""
    return {
        "moviepy": _moviepy_available,
        "ffmpeg": _check_ffmpeg(),
        "available": _moviepy_available and _check_ffmpeg(),
    }

def _check_ffmpeg() -> bool:
    import subprocess
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def create_text_clip(
    text: str, duration: float, style: str = "clean_white",
    size: tuple = (1080, 1920)
) -> "ImageClip":
    """创建文字片段（带背景渐变）"""
    if not _moviepy_available:
        return None

    sty = SUBTITLE_STYLES.get(style, SUBTITLE_STYLES["clean_white"])
    font_size = sty["font_size"]

    # 用 PIL 渲染文字
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 尝试加载中文字体
    font = None
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                pass

    if font is None:
        font = ImageFont.load_default()

    # 文字阴影 + 主文字
    x_pos = size[0] // 2
    y_pos = int(size[1] * sty["position"][1])

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    # 半透明背景条
    padding = 30
    bg_rect = [
        x_pos - tw//2 - padding, y_pos - th//2 - padding//2,
        x_pos + tw//2 + padding, y_pos + th//2 + padding//2,
    ]
    draw.rectangle(bg_rect, fill=(0, 0, 0, 160))

    # 描边效果
    for dx in [-2, 2]:
        for dy in [-2, 2]:
            draw.text(
                (x_pos + dx, y_pos + dy), text,
                font=font, fill=(0, 0, 0, 255), anchor="mm"
            )

    draw.text((x_pos, y_pos), text, font=font, fill=(255, 255, 255, 255), anchor="mm")

    import numpy as np
    return ImageClip(np.array(img), duration=duration)


def mix_video(
    clips_data: List[Dict],
    output_name: str = None,
    template: str = "before_after",
    bgm_path: str = None,
    subtitles: List[Dict] = None,
    resolution: tuple = (1080, 1920),
    fps: int = 30,
    dry_run: bool = False,
) -> dict:
    """
    核心混剪函数

    clips_data: [
        {"type": "image", "path": "...", "duration": 3, "effect": "zoom_in"},
        {"type": "video", "path": "...", "start": 0, "end": 5, "effect": "crossfade"},
        {"type": "text", "text": "标题文字", "duration": 3, "style": "bold_yellow"},
    ]

    返回: {"ok": True, "path": "...", "duration": 30, "size_mb": 5.2}
    """
    # Validate template (reject unknown templates instead of silent fallback)
    if template not in MIX_TEMPLATES:
        print(f"[WARNING] Unknown template '{template}'. Available: {list(MIX_TEMPLATES.keys())}")
        return {
            "ok": False,
            "error": f"Unknown template '{template}'. Available: {list(MIX_TEMPLATES.keys())}",
        }

    if dry_run or not clips_data:
        # 生成视频方案（无需实际素材）
        tpl = MIX_TEMPLATES[template]
        plan = _generate_mix_plan(tpl, clips_data)
        return {
            "ok": True,
            "dry_run": True,
            "plan": plan,
            "message": "视频方案已生成。提供素材后自动合成。",
        }

    if not _moviepy_available:
        return {
            "ok": False,
            "error": "moviepy 未安装。请运行: pip install moviepy pillow numpy",
            "hint": "dry_run 模式仍可生成视频方案",
        }

    try:
        clips = []
        total_duration = 0

        for cd in clips_data:
            ctype = cd.get("type", "image")
            duration = cd.get("duration", 3)
            effect = cd.get("effect", "fade")

            if ctype == "image" and cd.get("path"):
                try:
                    clip = ImageClip(cd["path"], duration=duration)
                    clip = clip.resized(resolution)
                    if effect == "zoom_in":
                        clip = clip.resized(lambda t: 1 + 0.05 * t / duration)
                    clips.append(clip)
                except Exception as e:
                    print(f"[WARNING] Skipping image {cd['path']}: {e}")

            elif ctype == "video" and cd.get("path"):
                try:
                    vc = VideoFileClip(cd["path"])
                    if cd.get("start") or cd.get("end"):
                        vc = vc.subclipped(cd.get("start", 0), cd.get("end", vc.duration))
                    vc = vc.resized(resolution)
                    if duration > 0:
                        vc = vc.with_duration(duration)
                    clips.append(vc)
                except Exception as e:
                    print(f"[WARNING] Skipping video {cd['path']}: {e}")

            elif ctype == "text" and cd.get("text"):
                tc = create_text_clip(cd["text"], duration, cd.get("style", "clean_white"), resolution)
                if tc:
                    clips.append(tc)

            elif ctype == "color":
                color = cd.get("color", (0, 0, 0))
                clips.append(ColorClip(resolution, color=color, duration=duration))

            total_duration += duration

        if not clips:
            return {"ok": False, "error": "没有可用的素材片段"}

        # 拼接 + 转场
        final = concatenate_videoclips(clips, method="compose")

        # 添加背景音乐
        if bgm_path and os.path.exists(bgm_path):
            audio = AudioFileClip(bgm_path)
            if audio.duration > final.duration:
                audio = audio.subclipped(0, final.duration)
            audio = audio.with_effects([lambda a: a * 0.3])  # 30% 音量
            final = final.with_audio(audio)

        # 输出
        if not output_name:
            output_name = f"mix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        output_path = MIXER_OUT / output_name
        final.write_videofile(
            str(output_path), fps=fps,
            codec="libx264", audio_codec="aac",
            temp_audiofile=str(MIXER_OUT / "temp_audio.mp3"),
            logger=None,
        )

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)

        return {
            "ok": True,
            "path": str(output_path),
            "duration": round(total_duration, 1),
            "size_mb": round(file_size_mb, 2),
            "clips_count": len(clips_data),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}


def _generate_mix_plan(template: dict, clips_data: List[Dict]) -> dict:
    """生成混剪方案"""
    segments = []
    for seg in template["segments"]:
        segments.append({
            "type": seg["type"],
            "duration": seg.get("duration", 5),
            "label": seg.get("label", seg.get("text", "")),
            "effect": seg.get("effect", "fade"),
            "needs_image": seg["type"] in ("before", "after", "panorama", "detail_1", "detail_2", "detail_3"),
            "needs_text": seg["type"] in ("title", "hook", "price", "tip", "preview", "cta"),
        })

    return {
        "template": template["name"],
        "total_duration": template["duration"],
        "resolution": f"{template['resolution'][0]}x{template['resolution'][1]}",
        "bgm_style": template["bgm_style"],
        "segments": segments,
        "required_assets": _list_required_assets(segments),
    }


def _list_required_assets(segments: List[Dict]) -> List[str]:
    assets = []
    for s in segments:
        if s.get("needs_image"):
            assets.append(f"图片: {s['label']} ({s['duration']}s)")
        if s.get("needs_text"):
            assets.append(f"文案: {s['label']}")
    return assets


# ═══════════════════════════════════
# 批量混剪 — 一键生成 N 条变体
# ═══════════════════════════════════

def batch_mix(
    base_data: Dict,
    variants: List[Dict],
    template: str = "before_after",
    count: int = 10,
) -> dict:
    """
    批量混剪：从一组素材+变体参数生成多条视频

    base_data: {"before_images": [...], "after_images": [...], "bgm": "..."}
    variants: [{"title": "变体1", "subtitles": [...]}, ...]
    或自动生成 count 条变体
    """
    results = []

    if not variants:
        # 自动生成变体（轮换素材组合）
        before_imgs = base_data.get("before_images", [])
        after_imgs = base_data.get("after_images", [])
        for i in range(min(count, max(len(before_imgs), 1) * max(len(after_imgs), 1))):
            variants.append({
                "title": f"变体{i+1}",
                "before_idx": i % max(len(before_imgs), 1),
                "after_idx": i % max(len(after_imgs), 1),
            })

    for v in variants[:count]:
        # 构建混剪数据
        clips_data = _build_clips_from_variant(base_data, v, template)
        result = mix_video(
            clips_data,
            output_name=f"batch_{template}_{v.get('title','var')}.mp4",
            template=template,
            bgm_path=base_data.get("bgm"),
            dry_run=not _moviepy_available,
        )
        results.append(result)

    return {
        "ok": True,
        "total": len(results),
        "success": sum(1 for r in results if r.get("ok")),
        "failed": sum(1 for r in results if not r.get("ok")),
        "results": results,
    }


def _build_clips_from_variant(base_data: Dict, variant: Dict, template: str) -> List[Dict]:
    """根据变体参数构建素材列表"""
    tpl = MIX_TEMPLATES.get(template, MIX_TEMPLATES["before_after"])
    clips = []
    before_imgs = base_data.get("before_images", [])
    after_imgs = base_data.get("after_images", [])

    for seg in tpl["segments"]:
        stype = seg["type"]
        dur = seg.get("duration", 3)

        if stype == "before" and before_imgs:
            idx = variant.get("before_idx", 0)
            clips.append({"type": "image", "path": before_imgs[idx % len(before_imgs)], "duration": dur, "effect": "crossfade"})
        elif stype == "after" and after_imgs:
            idx = variant.get("after_idx", 0)
            clips.append({"type": "image", "path": after_imgs[idx % len(after_imgs)], "duration": dur, "effect": "crossfade"})
        elif seg.get("text"):
            text = seg["text"].format(**variant.get("format_data", {}))
            clips.append({"type": "text", "text": text, "duration": dur})
        elif stype == "transition":
            clips.append({"type": "color", "color": (20, 20, 30), "duration": dur})

    return clips


# ═══════════════════════════════════
# 简易素材管理
# ═══════════════════════════════════

def list_assets(asset_dir: str = None) -> dict:
    """列出可用素材"""
    if not asset_dir:
        asset_dir = OUTPUT_DIR / "zhuangqi"
    path = Path(asset_dir)
    if not path.exists():
        return {"ok": False, "error": f"目录不存在: {asset_dir}"}

    images, videos = [], []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        images.extend([str(p) for p in path.rglob(ext)])
    for ext in ["*.mp4", "*.mov", "*.avi"]:
        videos.extend([str(p) for p in path.rglob(ext)])

    return {
        "ok": True,
        "dir": str(path),
        "images": len(images),
        "videos": len(videos),
        "sample_images": images[:5],
        "sample_videos": videos[:3],
    }


def get_template(template_name: str) -> dict:
    """获取混剪模板详情"""
    tpl = MIX_TEMPLATES.get(template_name)
    if not tpl:
        return {"ok": False, "error": f"模板不存在。可选: {list(MIX_TEMPLATES.keys())}"}
    return {"ok": True, **tpl}


def list_templates() -> dict:
    """列出所有混剪模板"""
    templates = {}
    for name, tpl in MIX_TEMPLATES.items():
        templates[name] = {
            "name": tpl["name"],
            "duration": tpl["duration"],
            "resolution": f"{tpl['resolution'][0]}x{tpl['resolution'][1]}",
            "segments": len(tpl["segments"]),
            "bgm_style": tpl["bgm_style"],
        }
    return {"ok": True, "templates": templates}


# ═══════════════════════════════════
# CLI 测试
# ═══════════════════════════════════

if __name__ == "__main__":
    deps = check_dependencies()
    print(f"依赖检查: {deps}")

    # 生成混剪方案
    plan = mix_video([], template="before_after", dry_run=True)
    print(json.dumps(plan, ensure_ascii=False, indent=2))

    # 列模板
    print(json.dumps(list_templates(), ensure_ascii=False, indent=2))
