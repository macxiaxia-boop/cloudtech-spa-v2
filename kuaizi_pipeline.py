"""
筷子科技对标 — 装企版统一流水线
================================
一条命令完成 编→拍→剪→投 全链路。
输入: 楼盘/户型/风格/预算/城市
输出: 小红书图文 + 抖音口播脚本 + 公众号长文 + 视频方案 + 分发计划 + Token计费

对标: 筷子科技丽帧引擎 + 升机智能体 + Kuaizi AI平台
"""
import json, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent

def kuaizi(input_data: dict) -> dict:
    """
    筷子科技装企版 — 一站式流水线

    输入:
      city: 城市 (厦门/泉州/漳州/福州...)
      style: 风格 (现代简约/奶油风/新中式/侘寂风...)
      room_type: 空间 (全屋/厨房/卫生间/客厅/卧室...)
      area: 面积(平)
      budget: 预算(万)
      community: 小区名(可选)
      pain_point: 痛点(可选)
      account: 发布账号名(可选)

    输出:
      creative_brief: 创意简报(升机智能体)
      xiaohongshu: 小红书图文
      douyin_script: 抖音口播脚本(含分镜)
      wechat_article: 公众号长文
      video_plan: 视频制作方案
      distribute: 分发计划
      tokens: Token消耗
      cost: 预估费用
    """
    from admin_dashboard import _deepseek_call, CREATOR_STYLES, CONTENT_FORMS, PLATFORMS
    from shengji_agent import INDUSTRY_KNOWLEDGE

    t0 = time.time()
    city = input_data.get("city", "厦门")
    style = input_data.get("style", "现代简约")
    room = input_data.get("room_type", "全屋")
    area = input_data.get("area", 100)
    budget = input_data.get("budget", 20)
    community = input_data.get("community", "")
    pain = input_data.get("pain_point", "")
    account = input_data.get("account", f"{city}装修号")

    # 行业知识注入
    local = INDUSTRY_KNOWLEDGE["本地热点"].get(city, [])[:3]
    style_info = INDUSTRY_KNOWLEDGE["风格体系"].get(style, {})

    output = {
        "input": input_data,
        "generated_at": datetime.now().isoformat()[:19],
    }

    # ═══ 筷子核心: 一个System Prompt驱动全链路 ═══
    master_prompt = f"""你是装企AI内容工厂。对标筷子科技Kuaizi AI平台。

## 客户档案
- 城市: {city} | 小区: {community or '未指定'}
- 空间: {room} | 面积: {area}平 | 风格: {style} | 预算: {budget}万
- 痛点: {pain or '未指定'}
- 本地热点: {', '.join(local)}
- 风格要素: {style_info.get('核心','')} | {style_info.get('配色','')}

## 要求: 一次性输出以下全部内容，用 ===SECTION=== 分隔

===XHS===
小红书图文(600-800字): 口语化·emoji·话题标签·第一人称视角·像朋友安利
钩子: 前3句必须制造认知冲突或情绪共鸣

===DY===
抖音口播脚本(含Scene标注): 3秒钩子→痛点共鸣→解决方案→效果展示→CTA
格式: [Scene X·时长] 画面描述 | 口播文案 | [Visual]画面提示

===WX===
公众号长文(1500-2500字): 专业深度·有数据有案例·结构化·可读性强
含: 引子故事→问题分析→方案拆解→细节展开→总结

===VIDEO===
视频方案: 分镜脚本(6-8个分镜)·BGM建议·字幕风格·预计时长
格式: 分镜N [时长] 画面 | 文案 | 特效

===TAGS===
话题标签(5-8个): #{city}装修 #{style} #{room}改造 等

请直接输出，不要额外解释。"""

    try:
        raw = _deepseek_call(master_prompt, f"为{city}{community}{room}{style}风装修创作全平台内容", max_tokens=4000, temperature=0.8)
    except Exception as e:
        return {"error": f"AI调用失败: {e}", "input": input_data}

    # 解析各section
    sections = {}
    current = None
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("===XHS==="):
            current = "xiaohongshu"; continue
        if line.startswith("===DY==="):
            current = "douyin"; continue
        if line.startswith("===WX==="):
            current = "wechat"; continue
        if line.startswith("===VIDEO==="):
            current = "video"; continue
        if line.startswith("===TAGS==="):
            current = "tags"; continue
        if current and line:
            sections.setdefault(current, []).append(line)

    output["xiaohongshu"] = "\n".join(sections.get("xiaohongshu", []))
    output["douyin_script"] = "\n".join(sections.get("douyin", []))
    output["wechat_article"] = "\n".join(sections.get("wechat", []))
    output["video_plan"] = "\n".join(sections.get("video", []))
    output["tags"] = "\n".join(sections.get("tags", []))

    # Token计费(对标筷子Token化)
    tokens_used = 80  # 全平台内容≈80 Token
    output["tokens"] = {"used": tokens_used, "breakdown": "小红书20T + 抖音25T + 公众号25T + 视频10T"}

    # 预估费用
    plan_rate = 0.2  # enterprise
    output["cost"] = {"total": round(tokens_used * plan_rate), "currency": "¥", "rate_per_token": plan_rate}

    # 分发计划
    from tenant_platform import distribute_content
    dist = distribute_content("zq-5bb59623", f"{city}{community}{room}改造", "article")
    output["distribute"] = {"accounts": dist["total_distributions"], "plan": dist["plan"][:3]}

    # 保存产出
    out_dir = Path(f"D:/个人文件/AI/云数科技/tenants/zq-5bb59623/content")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    pkg = out_dir / f"kuaizi_{ts}_{city}_{room}.md"
    pkg.write_text(f"""# 筷子科技流水线产出

> {city}·{community}·{room}·{style}·{area}平·{budget}万
> 生成: {output['generated_at']} | Token: {tokens_used}T | 费用: ¥{output['cost']['total']}

## 📕 小红书
{output['xiaohongshu']}

## 🎵 抖音口播
{output['douyin_script']}

## 💬 公众号
{output['wechat_article']}

## 🎬 视频方案
{output['video_plan']}

## 🏷️ 标签
{output['tags']}
""", encoding="utf-8")
    output["saved_to"] = str(pkg)

    output["elapsed_seconds"] = round(time.time() - t0, 1)
    output["summary"] = f"筷子流水线: {output['elapsed_seconds']}秒 → 小红书+抖音+公众号+视频+{output['distribute']['accounts']}分发 → {tokens_used}T(¥{output['cost']['total']})"

    return output
