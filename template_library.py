"""
内容模板库 — Content Template Library
对标: HeyGen 300+ / Biteable 7000+ / InVideo 7000+ templates
"""
import json, secrets
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
TEMPLATE_DIR = Path("D:/个人文件/AI/云数科技/templates")
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# 预置模板(对标HeyGen 300+ / Biteable 7000+)
PRESET_TEMPLATES = {
    "social_xhs": [
        {"name": "避坑指南", "structure": "痛点钩子→3个坑→解决方案→CTA", "platforms": ["xiaohongshu"], "word_range": (500, 800), "category": "装修知识"},
        {"name": "前后对比", "structure": "改造前痛点→改造方案→花费清单→改造后效果→CTA", "platforms": ["xiaohongshu"], "word_range": (400, 700), "category": "案例展示"},
        {"name": "好物推荐", "structure": "种草开场→产品亮点(3点)→使用体验→购买建议", "platforms": ["xiaohongshu"], "word_range": (300, 600), "category": "产品推广"},
        {"name": "亲情故事", "structure": "人物亮相→一个具体故事→专业细节→父辈金句→实用价值", "platforms": ["xiaohongshu", "公众号"], "word_range": (800, 2500), "category": "人设IP"},
    ],
    "social_douyin": [
        {"name": "口播科普", "structure": "Scene0-3s钩子→痛点共鸣→解决方案→效果展示→CTA", "platforms": ["抖音"], "word_range": (800, 1500), "category": "知识科普"},
        {"name": "改造纪实", "structure": "改造前→施工延时→遇到问题→解决方案→明日预告", "platforms": ["抖音"], "word_range": (400, 800), "category": "施工日记"},
        {"name": "材料测评", "structure": "开箱→微距特写→对比实验→价格区间→选购技巧", "platforms": ["抖音"], "word_range": (600, 1200), "category": "产品测评"},
    ],
    "social_wechat": [
        {"name": "深度拆解", "structure": "引子故事→问题分析→方案拆解→细节展开→总结", "platforms": ["公众号"], "word_range": (1500, 3000), "category": "专业知识"},
        {"name": "案例复盘", "structure": "项目背景→设计挑战→解决方案→完工交付→经验总结", "platforms": ["公众号"], "word_range": (1200, 2500), "category": "案例展示"},
    ],
    "video_modes": [
        {"name": "空间漫游", "duration": "60-90s", "scenes": 7, "platforms": ["抖音", "B站"], "category": "视频"},
        {"name": "施工延时", "duration": "30-45s", "scenes": 6, "platforms": ["抖音"], "category": "视频"},
        {"name": "材料开箱", "duration": "45-90s", "scenes": 7, "platforms": ["抖音", "B站"], "category": "视频"},
    ],
}

def list_templates(category: str = "", platform: str = "") -> list:
    """列出所有模板"""
    all_templates = []
    for cat, templates in PRESET_TEMPLATES.items():
        for t in templates:
            t["category_key"] = cat
            if category and t.get("category") != category: continue
            if platform and platform not in t.get("platforms", []): continue
            all_templates.append(t)
    return all_templates

def get_template_categories() -> list:
    cats = set()
    for templates in PRESET_TEMPLATES.values():
        for t in templates:
            cats.add(t.get("category", ""))
    return sorted(cats)

def apply_template(template_name: str, variables: dict) -> dict:
    """应用模板: 填充变量→AI生成完整内容"""
    for cat, templates in PRESET_TEMPLATES.items():
        for t in templates:
            if t["name"] == template_name:
                structure = t["structure"]
                city = variables.get("城市", "厦门")
                topic = variables.get("topic", "装修")

                # AI生成完整内容
                content = ""
                try:
                    from admin_dashboard import _deepseek_call
                    sys_p = f"""你是顶尖内容创作者。严格按照以下结构创作:
模板: {t['name']}
结构: {structure}
平台: {'/'.join(t.get('platforms',['通用']))}
字数: {t.get('word_range',(500,1000))[0]}-{t.get('word_range',(500,1000))[1]}字
城市: {city}
要求: 口语化·本地化细节·emoji适度·拒绝AI腔"""
                    content = _deepseek_call(sys_p, f"创作主题: {topic}", max_tokens=2000, temperature=0.8)
                except Exception:
                    content = f"# {topic}\n\n> 按{t['name']}模板生成\n> 结构: {structure}"

                return {"ok": True, "template": t, "structure": structure,
                        "generated_content": content, "variables": variables}
    return {"ok": False, "error": "模板不存在"}
