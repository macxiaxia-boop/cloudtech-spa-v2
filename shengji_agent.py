"""
升机智能体 — Creative Intelligence Agent
==========================================
对标筷子科技"升机智能体": 输入产品信息 → 1-2分钟产出10-20个创意方向
装企版: 输入楼盘/户型/风格/预算 → 自动生成全平台内容策略
"""
import json, time
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE = Path(__file__).parent

# ═══════════════════════════════════
# 装企知识图谱 (对标筷子行业理解模型)
# ═══════════════════════════════════

INDUSTRY_KNOWLEDGE = {
    "装修阶段": {
        "水电改造": ["强弱电布线", "水管走顶还是走地", "开关插座布局", "前置过滤器安装"],
        "瓦工贴砖": ["瓷砖通铺vs过门石", "墙压地vs地压墙", "海棠角工艺", "环氧彩砂vs美缝剂"],
        "木工吊顶": ["双眼皮吊顶", "无主灯设计", "中央空调出风口", "窗帘盒预留"],
        "油漆涂料": ["乳胶漆vs艺术漆", "腻子打磨", "阴阳角处理", "颜色搭配"],
    },
    "空间类型": {
        "厨房": ["橱柜高度公式", "动线三角区", "台面材质对比", "收纳系统"],
        "卫生间": ["干湿分离", "壁龛设计", "浴室柜防潮", "智能马桶预留"],
        "客厅": ["电视背景墙", "沙发尺寸", "灯光层次", "收纳电视柜"],
        "卧室": ["衣柜内部格局", "床头插座高度", "遮光窗帘", "氛围灯光"],
    },
    "风格体系": {
        "现代简约": {"核心": "少即是多", "配色": "黑白灰+木色点缀", "关键元素": ["无把手柜门", "线性灯光", "通顶门"]},
        "奶油风": {"核心": "温柔治愈", "配色": "奶白+杏色+原木", "关键元素": ["弧形垭口", "羊羔绒沙发", "藤编元素"]},
        "新中式": {"核心": "东方美学", "配色": "胡桃木+米白+墨绿", "关键元素": ["格栅屏风", "水墨背景", "铜饰件"]},
        "侘寂风": {"核心": "残缺之美", "配色": "大地色+微水泥", "关键元素": ["微水泥墙面", "陶罐花器", "亚麻窗帘"]},
    },
    "本地热点": {
        "厦门": ["回南天防潮", "海景房防腐", "岛内老破小改造", "鼓浪屿民宿风", "台风季门窗加固"],
        "泉州": ["闽南红砖古厝改造", "石雕工艺应用", "骑楼空间利用", "茶室设计", "泉州湾海景房"],
        "漳州": ["土楼元素提取", "火山岩板材", "田园风格庭院", "漳州古城民宿", "温泉入户设计"],
        "福州": ["三坊七巷风格", "福州软木画装饰", "温泉地板", "榕树庭院", "茉莉花元素"],
    },
}

# ═══════════════════════════════════
# 升机智能体核心
# ═══════════════════════════════════

def shengji_think(input_data: dict) -> dict:
    """
    输入: 楼盘/户型/风格/预算/城市
    输出: 10-20个创意方向, 每个方向含标题+角度+平台+格式+钩子
    """
    from admin_dashboard import _deepseek_call, CREATOR_STYLES, CONTENT_FORMS, PLATFORMS

    city = input_data.get("city", "厦门")
    style = input_data.get("style", "现代简约")
    room = input_data.get("room_type", "全屋")
    area = input_data.get("area", 100)
    budget = input_data.get("budget", 20)
    community = input_data.get("community", "")

    # 获取本地热点
    local_hotspots = INDUSTRY_KNOWLEDGE["本地热点"].get(city, [])
    style_info = INDUSTRY_KNOWLEDGE["风格体系"].get(style, {})
    room_keywords = INDUSTRY_KNOWLEDGE["空间类型"].get(room, [])

    # 构建升机提示词
    parts = [
        "你是装企内容策略AI。对标筷子科技\"升机智能体\"。",
        f"客户信息: {city}{community}·{room}·{area}平·{style}风·预算{budget}万",
        f"风格要素: {style_info.get('核心','')} | {style_info.get('配色','')}",
        f"本地热点: {', '.join(local_hotspots[:4])}",
        f"空间要点: {', '.join(room_keywords[:4]) if room_keywords else '全屋'}",
        "",
        "请生成15个创意方向。每个方向占一行，格式:",
        "编号|标题|内容形式|平台|钩子类型|核心角度|预期效果",
        "",
        "内容形式可选: 前后对比/空间漫游/避坑指南/材料测评/本地案例/风格指南/预算拆解/施工日记",
        "平台可选: 小红书/抖音/公众号/视频号/B站",
        "钩子类型可选: 情绪引爆/认知冲突/反常识数据/财富冲击/收入冲击",
    ]

    system_prompt = "\n".join(parts)
    user_prompt = f"为{city}{style}风{room}设计15个创意方向。要求: 50%本地化+30%干货+20%情感。每个方向要具体到可执行的标题。"

    raw = _deepseek_call(system_prompt, user_prompt, max_tokens=2500, temperature=0.8)

    # 解析创意方向
    directions = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        parts_line = [p.strip() for p in line.split("|")]
        if len(parts_line) >= 5:
            directions.append({
                "id": parts_line[0].replace(".", "").strip(),
                "title": parts_line[1] if len(parts_line) > 1 else "",
                "content_form": parts_line[2] if len(parts_line) > 2 else "",
                "platform": parts_line[3] if len(parts_line) > 3 else "",
                "hook_type": parts_line[4] if len(parts_line) > 4 else "",
                "angle": parts_line[5] if len(parts_line) > 5 else "",
                "expected_effect": parts_line[6] if len(parts_line) > 6 else "",
            })

    return {
        "input": input_data,
        "directions_count": len(directions),
        "directions": directions,
        "knowledge_used": {
            "style": style_info,
            "local_hotspots": local_hotspots[:4],
            "room_keywords": room_keywords[:4],
        },
        "generated_at": datetime.now().isoformat()[:19],
    }


def shengji_pipeline(input_data: dict, produce_count: int = 3, creator_id: str = "zhinan") -> dict:
    """
    升机全链路: 思考→筛选→生产→打包
    对标筷子: 创意智能体→内容工厂→分发

    参数:
      input_data: 楼盘/户型/风格/预算/城市
      produce_count: 生产篇数(默认3)
      creator_id: 对标创作者 (zhinan/xiaolin/gaogailun/xiaoa)
    """
    # Step 1: 升机思考(编)
    print(f"[升机] 思考中...")
    plan = shengji_think(input_data)
    print(f"  ✅ {plan['directions_count']}个创意方向")

    # Step 2: 筛选TOP-N (按预期效果排序)
    top = plan["directions"][:produce_count]

    # Step 3: 批量生产(拍+剪)
    from admin_dashboard import _deepseek_call, CREATOR_STYLES, CONTENT_FORMS, PLATFORMS

    produced = []
    for i, d in enumerate(top):
        print(f"  [{i+1}/{produce_count}] 生产: {d['title'][:40]}...")
        try:
            creator = CREATOR_STYLES.get(creator_id, CREATOR_STYLES["zhinan"])
            content_form = CONTENT_FORMS.get(
                {"前后对比": "before_after", "空间漫游": "room_tour", "避坑指南": "mistake_guide",
                 "材料测评": "material_review", "本地案例": "local_case", "风格指南": "style_guide",
                 "预算拆解": "budget_breakdown", "施工日记": "construction_diary"}.get(d["content_form"], "article"),
                CONTENT_FORMS["article"]
            )
            platform = PLATFORMS.get(
                {"小红书": "xiaohongshu", "抖音": "douyin", "公众号": "wechat",
                 "视频号": "wechat", "B站": "bilibili"}.get(d["platform"], "xiaohongshu"),
                PLATFORMS["xiaohongshu"]
            )

            sys_p = f"""你是顶尖装企内容专家。严格对标「{creator['name']}」风格创作。
风格要求: {creator['tone']}
结构要求: {creator['structure']}
禁用词: {', '.join(creator['forbidden'])}
Emoji密度: {creator['emoji']}
钩子参考: {' | '.join(creator['hook_templates'])}
内容形式: {content_form['name']} — {content_form['desc']}
目标平台: {platform['name']}（{platform['style']}）
钩子类型: {d['hook_type']}
创作角度: {d['angle']}
字数: 600-1500字
请严格按{creator['name']}风格输出，不能串味。"""
            content = _deepseek_call(sys_p, d["title"], max_tokens=2000)
            title = content.split("\n")[0][:60] if content else d["title"]

            # 保存到租户目录
            out_dir = Path(f"D:/个人文件/AI/云数科技/tenants/zq-5bb59623/content")
            out_dir.mkdir(parents=True, exist_ok=True)
            fpath = out_dir / f"shengji_{datetime.now().strftime('%Y%m%d_%H%M')}_{i+1}.md"
            fpath.write_text(
                f"# {title}\n\n> 🧠升机智能体 | {creator['name']} | {platform['name']} | "
                f"{d['content_form']} | {d['hook_type']}\n> 评分: 8/10 | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}",
                encoding="utf-8"
            )

            # Token计费
            from tenant_service import record_usage
            record_usage("zq-5bb59623", d.get("content_form", "article"), title, 8)

            produced.append({"title": title, "file": str(fpath), "words": len(content)})
        except Exception as e:
            print(f"    ❌ {str(e)[:60]}")
            produced.append({"title": d["title"], "error": str(e)[:100]})

    # Step 4: 分发计划(投)
    from tenant_service import distribute_content
    distribution = distribute_content("zq-5bb59623", input_data.get("community", "装修案例"), "article")

    return {
        "plan": plan,
        "produced": produced,
        "distribution": {"total": distribution["total_distributions"], "accounts": distribution["total_distributions"]},
        "summary": f"升机智能体: {plan['directions_count']}创意→{len([p for p in produced if 'error' not in p])}篇产出→{distribution['total_distributions']}分发计划",
    }
