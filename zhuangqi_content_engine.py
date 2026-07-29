"""
装企内容生产引擎 v1.0 — Decoration Content Engine
=====================================================
脱离财经口播模板。装修行业原生表达方式。
8种内容格式 × 4平台适配 × 4种视觉语言
"""
import json, os, secrets
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

# ═══════════════════════════════════════
# 一、装修内容格式体系 (8种)
# ═══════════════════════════════════════

CONTENT_FORMATS = {
    "before_after": {
        "name": "前后对比",
        "icon": "🔄",
        "structure": ["改造前痛点", "改造方案", "改造后效果", "花费清单"],
        "visual": "split_screen",  # 左右/上下对比图
        "hook_examples": [
            "花{w}万把{old_room}改成{new_room}，邻居都来抄作业",
            "改造前房东说能租{w}是运气，改造后他说亏了",
            "只花了{w}万，{old}变{new}，老公以为换了套房",
        ],
        "platforms": ["xiaohongshu", "douyin", "wechat"],
    },
    "room_tour": {
        "name": "空间漫游",
        "icon": "🏠",
        "structure": ["空间概览", "设计亮点", "材质细节", "尺寸标注", "品牌清单"],
        "visual": "walk_through",  # 第一人称走进去的视角
        "hook_examples": [
            "{size}平{mode}风，进门那一刻我愣住了",
            "看完这套{style}设计，我决定重新装修",
            "{city}一套{size}平的{style}小家，每一处都长在审美上",
        ],
        "platforms": ["xiaohongshu", "douyin"],
    },
    "budget_breakdown": {
        "name": "预算拆解",
        "icon": "💰",
        "structure": ["总预算", "硬装明细", "软装明细", "省钱技巧", "踩坑记录"],
        "visual": "infographic",  # 信息图/表格
        "hook_examples": [
            "{size}平装完花了{w}万，明细全公开",
            "装修公司报价{high}万，我自己装只花了{low}万",
            "预算{w}万装{size}平，每一项花在哪都告诉你",
        ],
        "platforms": ["xiaohongshu", "wechat"],
    },
    "construction_diary": {
        "name": "施工日记",
        "icon": "📋",
        "structure": ["今日进度", "施工照片", "遇到的问题", "解决方案", "明日计划"],
        "visual": "timeline",  # 时间线/进度条
        "hook_examples": [
            "装修第{day}天，{event}，我差点崩溃",
            "水电改造第{day}天，师傅说我家是他见过最{adj}的",
            "瓦工进场第{day}天，{detail}这个细节一定要注意",
        ],
        "platforms": ["xiaohongshu", "douyin"],
    },
    "material_review": {
        "name": "材料测评",
        "icon": "🔍",
        "structure": ["材料介绍", "品牌对比", "价格区间", "选购技巧", "实拍效果"],
        "visual": "macro_detail",  # 微距/细节特写
        "hook_examples": [
            "{material}怎么选？跑了{city}三个建材市场总结的干货",
            "瓷砖/地板/涂料别乱买，{years}年老工头教你挑",
            "同样是{material}，{price_low}和{price_high}的差距有多大",
        ],
        "platforms": ["xiaohongshu", "wechat", "douyin"],
    },
    "style_guide": {
        "name": "风格指南",
        "icon": "🎨",
        "structure": ["风格定义", "色彩搭配", "材质选择", "家具推荐", "案例参考"],
        "visual": "moodboard",  # 情绪板/拼图
        "hook_examples": [
            "202{year}最火的{style}风，这样装不翻车",
            "{style}风装修避坑指南，设计师不会告诉你的{num}个秘密",
            "我家{size}平的{style}风，每一处都是精心设计",
        ],
        "platforms": ["xiaohongshu", "wechat"],
    },
    "mistake_guide": {
        "name": "避坑指南",
        "icon": "⚠️",
        "structure": ["踩坑描述", "为什么会踩", "正确做法", "费用对比", "预防清单"],
        "visual": "comparison",  # 错误 vs 正确对比
        "hook_examples": [
            "装修{num}个最容易踩的坑，我家踩了{count}个",
            "水电改造这{num}个细节没盯住，多花了{w}万",
            "入住{months}个月才发现，{detail}当初做错了",
        ],
        "platforms": ["xiaohongshu", "douyin", "wechat"],
    },
    "local_case": {
        "name": "本地案例",
        "icon": "📍",
        "structure": ["小区/楼盘", "户型面积", "业主需求", "设计方案", "完工实拍"],
        "visual": "real_photo",  # 真实照片（非效果图）
        "hook_examples": [
            "{city}{district}的{size}平小家，装成了理想的样子",
            "给{city}业主设计的{style}风，效果图vs实景",
            "{city}{community}的户型改造，邻居看完也要装",
        ],
        "platforms": ["xiaohongshu", "douyin", "wechat"],
    },
}


# ═══════════════════════════════════════
# 二、平台适配器
# ═══════════════════════════════════════

PLATFORM_ADAPTERS = {
    "xiaohongshu": {
        "name": "小红书",
        "tone": "亲切分享感，像朋友安利，不硬广",
        "structure": "钩子开头 → 痛点共鸣 → 解决方案 → 干货细节 → 互动引导",
        "length": (400, 800),  # 字数范围
        "hashtags": True,
        "emoji_density": "high",
        "forbidden": ["全网最低", "绝对", "保证", "免费咨询", "包工包料"],  # 限流词
        "visual_note": "竖版3:4封面，首图决定点击率。不要拼图大字报。",
    },
    "douyin": {
        "name": "抖音",
        "tone": "节奏快、信息密度高、前3秒决定留还是划走",
        "structure": "钩子(3秒) → 问题 → 过程 → 结果 → 引导关注",
        "length": None,  # 视频时长，不限字数
        "hashtags": True,
        "emoji_density": "medium",
        "forbidden": ["加微信", "私聊", "免费设计"],
        "visual_note": "9:16竖屏。前3帧决定一切。字幕必须大字。",
    },
    "wechat": {
        "name": "公众号",
        "tone": "专业深度，行业洞察，像设计师在讲方案",
        "structure": "引子故事 → 问题分析 → 方案拆解 → 细节展开 → 总结升华",
        "length": (1200, 2500),
        "hashtags": False,
        "emoji_density": "low",
        "forbidden": [],
        "visual_note": "头部图片宽度900px。正文配图间隔2-3段。",
    },
    "pengyouquan": {
        "name": "朋友圈",
        "tone": "个人化、生活化，像发给自己朋友看",
        "structure": "一句话亮点 → 配图说明 → 互动钩子",
        "length": (50, 200),
        "hashtags": False,
        "emoji_density": "medium",
        "forbidden": ["立即咨询", "限时优惠"],
        "visual_note": "1/4/6/9张图。九宫格中间放logo。",
    },
}


# ═══════════════════════════════════════
# 三、视觉表达方式（不是人物出镜）
# ═══════════════════════════════════════

VISUAL_LANGUAGE = {
    "split_screen": {
        "name": "前后对比",
        "shot": "同角度拍摄，左右或上下拼接",
        "suitable": ["before_after", "mistake_guide"],
        "not_for": ["room_tour"],
    },
    "walk_through": {
        "name": "空间漫游",
        "shot": "第一人称手持，从门口推入，缓慢左→右扫视",
        "suitable": ["room_tour", "local_case"],
        "not_for": ["budget_breakdown"],
    },
    "macro_detail": {
        "name": "材质微距",
        "shot": "近距离特写纹理、接缝、光泽度。手指触摸互动。",
        "suitable": ["material_review", "construction_diary"],
        "not_for": [],
    },
    "infographic": {
        "name": "信息图表",
        "shot": "费用清单、尺寸标注、施工流程的卡片/图表形式",
        "suitable": ["budget_breakdown", "style_guide"],
        "not_for": ["room_tour"],
    },
    "timeline": {
        "name": "时间线",
        "shot": "垂直时间轴 + 每日/每周一张代表性照片",
        "suitable": ["construction_diary"],
        "not_for": [],
    },
    "real_photo": {
        "name": "实景拍摄",
        "shot": "不做后期滤镜，自然光拍摄。展示真实落地效果。",
        "suitable": ["local_case", "before_after"],
        "not_for": [],
    },
}


# ═══════════════════════════════════════
# 四、核心引擎
# ═══════════════════════════════════════

class ZhuangqiContentEngine:
    """装企内容生产引擎"""

    def __init__(self):
        self.formats = CONTENT_FORMATS
        self.platforms = PLATFORM_ADAPTERS
        self.visuals = VISUAL_LANGUAGE

    def generate_brief(self, content_type: str, platform: str, context: dict) -> dict:
        """Generate a content brief (提纲) for any format × platform combination"""
        fmt = self.formats.get(content_type)
        plat = self.platforms.get(platform)

        if not fmt or not plat:
            return {"error": f"Unknown type={content_type} or platform={platform}"}

        # Select a hook and fill in context values
        import random
        hook_template = random.choice(fmt["hook_examples"])
        try:
            hook = hook_template.format(**context)
        except KeyError:
            hook = hook_template  # Use as-is if context doesn't match

        # Get visual recommendation
        visual = self.visuals.get(fmt["visual"], {})

        return {
            "brief_id": secrets.token_hex(6),
            "content_type": content_type,
            "type_name": fmt["name"],
            "platform": platform,
            "platform_name": plat["name"],
            "tone": plat["tone"],
            "hook": hook,
            "structure": fmt["structure"],
            "visual_style": fmt["visual"],
            "visual_instructions": visual.get("shot", ""),
            "platform_structure": plat["structure"],
            "target_length": f"{plat['length'][0]}-{plat['length'][1]}字" if plat["length"] else "视频脚本",
            "forbidden_words": plat["forbidden"],
            "visual_note": plat["visual_note"],
            "emoji_density": plat["emoji_density"],
            "context": context,
        }

    def generate_content(self, brief: dict) -> dict:
        """Generate full content from a brief — ready to publish"""
        fmt = self.formats.get(brief["content_type"])
        plat = self.platforms.get(brief["platform"])

        if not fmt or not plat:
            return {"error": "Invalid brief"}

        # Build content sections
        sections = []
        for i, step in enumerate(fmt["structure"]):
            sections.append({
                "step": i + 1,
                "title": step,
                "instruction": self._section_prompt(step, brief),
            })

        # Generate hashtags for platforms that need them
        hashtags = []
        if plat["hashtags"]:
            hashtags = self._generate_hashtags(brief)

        return {
            "brief": brief,
            "hook": brief["hook"],
            "sections": sections,
            "hashtags": hashtags,
            "closing": self._generate_closing(plat),
            "do_nots": plat["forbidden"],
        }

    def _section_prompt(self, step_name: str, brief: dict) -> str:
        """Generate writing instruction for each section"""
        prompts = {
            "改造前痛点": "描述装修前的具体状态，用数字和细节强化对比效果。不要笼统说'很旧'，要说'墙皮掉了3块/厨房只有4平米/卫生间没有干湿分离'。",
            "改造方案": "说明做了什么改动。拆了哪面墙/换了什么材料/加了什么功能。配改造前后户型图。",
            "改造后效果": "用空间漫游的视角描述。从进门→客厅→厨房→卧室→阳台的顺序。每个空间2-3句。",
            "花费清单": "表格形式。硬装/软装/家电三大类。每项标注品牌和价格。最后算总价。",
            "空间概览": "从玄关开始，按进入动线描述。每个空间：面积+风格+亮点设计。",
            "设计亮点": "挑3个最特别的设计点展开。为什么这样设计？解决了什么问题？",
            "材质细节": "瓷砖/地板/墙面/台面/五金。每种材质：品牌+型号+价格+使用感受。",
            "省钱技巧": "说具体数字。'瓷砖去佛山买省了3000' 比 '瓷砖可以省钱' 有用100倍。",
            "踩坑记录": "踩了什么坑→为什么踩→多花了多少钱→正确做法是什么。",
            "今日进度": "今天做了什么(拍照)→花了多少钱→遇到什么问题→明天做什么。像日记一样。",
            "品牌对比": "至少对比3个品牌。价格/质量/售后。用表格。",
            "选购技巧": "带具体判断标准。'敲一敲听声音'这种。配实拍对比图。",
            "风格定义": "这个风格的核心特征(3个关键词)。适合什么样的户型/预算/人群。",
            "色彩搭配": "主色+辅色+点缀色。给色号。配案例图。",
            "设计灵感": "从哪看到的灵感→怎么改造成适合自己家。附灵感来源图。",
        }
        return prompts.get(step_name, f"展开描述{step_name}，用具体数字和细节，避免抽象形容词。")

    def _generate_hashtags(self, brief: dict) -> list:
        """Generate platform-appropriate hashtags"""
        base_tags = {
            "before_after": ["装修前后", "老房改造", "装修日记", "改造案例"],
            "room_tour": ["roomtour", "装修灵感", "家居设计", "理想的家"],
            "budget_breakdown": ["装修预算", "装修费用", "装修省钱", "全屋装修"],
            "construction_diary": ["装修日记", "装修记录", "施工现场", "装修ing"],
            "material_review": ["装修材料", "装修避坑", "建材选购", "装修干货"],
            "style_guide": ["装修风格", "风格设计", "色彩搭配", "软装设计"],
            "mistake_guide": ["装修避坑", "装修经验", "装修小白", "装修避雷"],
            "local_case": ["装修案例", "全屋定制", "实景拍摄", "装修设计"],
        }
        ct = brief.get("content_type", "")
        city = brief.get("context", {}).get("city", "")
        tags = base_tags.get(ct, ["装修", "家居"])[:6]
        if city:
            tags.insert(0, f"{city}装修")
        return tags

    def _generate_closing(self, plat: dict) -> str:
        """Generate platform-appropriate closing"""
        closings = {
            "xiaohongshu": "💬 有什么问题评论区问我，看到都会回～",
            "douyin": "关注我，每天分享一个装修干货！",
            "wechat": "— END —",
            "pengyouquan": "🏠 自己的家，每一处都要用心",
        }
        return closings.get(plat["name"], "")


# ═══════════════════════════════════════
# 五、批量生产调度
# ═══════════════════════════════════════

class ContentScheduler:
    """内容排期引擎 — 矩阵号 × 多格式 × 多平台"""

    def __init__(self, engine: ZhuangqiContentEngine):
        self.engine = engine

    def generate_week_plan(self, accounts: list, week_start: str = None) -> list:
        """Generate a week's content plan for multiple accounts"""
        import random

        # Content mix ratio (装修行业最优配比)
        MIX_RATIO = {
            "before_after": 0.20,
            "room_tour": 0.15,
            "budget_breakdown": 0.10,
            "construction_diary": 0.15,
            "material_review": 0.10,
            "style_guide": 0.10,
            "mistake_guide": 0.10,
            "local_case": 0.10,
        }

        plan = []
        for account in accounts:
            daily_count = account.get("posts_per_day", 1)
            for day in range(7):
                for slot in range(daily_count):
                    ct = random.choices(list(MIX_RATIO.keys()), weights=list(MIX_RATIO.values()))[0]
                    brief = self.engine.generate_brief(
                        ct, account["platform"], account.get("context", {})
                    )
                    plan.append({
                        "day": day + 1,
                        "account": account["name"],
                        "platform": account["platform"],
                        "slot": slot + 1,
                        "brief": brief,
                    })
        return plan


# ═══════════════════════════════════════
# 六、Flask API 接口
# ═══════════════════════════════════════

engine = ZhuangqiContentEngine()

def api_generate_brief(data: dict) -> dict:
    return engine.generate_brief(
        data.get("content_type", "before_after"),
        data.get("platform", "xiaohongshu"),
        data.get("context", {}),
    )

def api_generate_content(brief: dict) -> dict:
    return engine.generate_content(brief)

def api_generate_week_plan(data: dict) -> list:
    scheduler = ContentScheduler(engine)
    return scheduler.generate_week_plan(data.get("accounts", []))

def api_list_formats() -> list:
    return [
        {"id": k, "name": v["name"], "icon": v["icon"], "structures": v["structure"]}
        for k, v in CONTENT_FORMATS.items()
    ]

def api_list_visuals() -> list:
    return [
        {"id": k, "name": v["name"], "shot": v["shot"], "suitable": v["suitable"]}
        for k, v in VISUAL_LANGUAGE.items()
    ]
