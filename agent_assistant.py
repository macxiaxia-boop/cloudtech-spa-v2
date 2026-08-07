"""
AI Agent 助手 — CloudTech Agent
===============================
对标筷子科技「小K」：对话式 AI 助手，集成知识库和工具调用

能力:
- 装修咨询: 基于装企知识库回答用户问题
- 内容生成: 一键生成各平台内容
- 任务执行: 自然语言驱动视频生成/发布
- 智能推荐: 根据用户画像推荐内容策略
"""
import json, os, re, time
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE = Path(__file__).parent

# ═══════════════════════════════════
# Agent 工具注册
# ═══════════════════════════════════

AGENT_TOOLS = {
    "generate_content": {
        "name": "内容生成",
        "description": "生成小红书图文/抖音脚本/公众号文章",
        "params": ["platform", "topic", "style", "length"],
        "handler": "_tool_generate_content",
    },
    "generate_video": {
        "name": "视频生成",
        "description": "AI生成视频或混剪方案",
        "params": ["topic", "template", "provider"],
        "handler": "_tool_generate_video",
    },
    "publish_content": {
        "name": "内容发布",
        "description": "发布内容到指定平台",
        "params": ["platform", "title", "content", "images"],
        "handler": "_tool_publish_content",
    },
    "estimate_budget": {
        "name": "预算估算",
        "description": "估算装修预算和工期",
        "params": ["area", "style", "level"],
        "handler": "_tool_estimate_budget",
    },
    "search_knowledge": {
        "name": "知识搜索",
        "description": "搜索装企知识库（小区/材料/工价/政策）",
        "params": ["query", "category"],
        "handler": "_tool_search_knowledge",
    },
    "competitor_analysis": {
        "name": "竞品分析",
        "description": "分析竞争对手内容策略",
        "params": ["competitor_name", "platform"],
        "handler": "_tool_competitor_analysis",
    },
    "batch_produce": {
        "name": "批量生产",
        "description": "批量生成内容+视频+发布",
        "params": ["topics", "platforms", "count"],
        "handler": "_tool_batch_produce",
    },
}

# ═══════════════════════════════════
# Agent 提示词系统
# ═══════════════════════════════════

SYSTEM_PROMPTS = {
    "default": """你是云数科技AI助手「小云」，专门服务装修行业。
你的能力:
- 🏠 装修咨询: 回答装修设计/材料/预算/工艺等问题
- 📝 内容生成: 一键生成小红书/抖音/公众号内容
- 🎬 视频制作: AI生成装修视频方案
- 📊 数据分析: 竞品分析/趋势洞察/预算估算

回复风格: 专业但不啰嗦，实用且接地气。说人话，不讲术语。

{tools_description}

当前用户: {user_context}""",

    "renovation_expert": """你是资深装修顾问，有15年装修行业经验。
你能:
- 根据户型/预算/风格给出具体建议
- 识别装修中的常见坑点
- 推荐漳州本地靠谱材料和工价
- 解释装修流程和注意事项

说话风格: 像个有经验的老师傅，直接给干货。
{knowledge_context}""",

    "content_creator": """你是装修内容创作专家，精通各平台内容逻辑。
你能:
- 生成符合平台算法的小红书图文
- 撰写抖音爆款口播脚本
- 编辑公众号装修科普长文
- 优化标题和关键词

知道每个平台的流量密码，但不造假，不吹牛。
{platform_tips}""",
}

# ═══════════════════════════════════
# 对话记忆系统
# ═══════════════════════════════════

class AgentMemory:
    """Agent 短期记忆（单次会话）"""
    def __init__(self, max_turns=20):
        self.history = []
        self.max_turns = max_turns
        self.user_profile = {}
        self.current_topic = None

    def add(self, role: str, content: str):
        self.history.append({"role": role, "content": content, "time": datetime.now().isoformat()[:19]})
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

    def get_context(self, turns: int = 5) -> str:
        """获取最近N轮对话上下文"""
        recent = self.history[-(turns * 2):]
        return "\n".join([f"{m['role']}: {m['content'][:200]}" for m in recent])

    def extract_user_info(self):
        """从对话中提取用户画像"""
        all_text = " ".join([m["content"] for m in self.history if m["role"] == "user"])
        profile = {}
        # 面积
        area_match = re.search(r'(\d+)\s*平', all_text)
        if area_match: profile["area"] = int(area_match.group(1))
        # 预算
        budget_match = re.search(r'(\d+)\s*万', all_text)
        if budget_match: profile["budget"] = int(budget_match.group(1))
        # 风格
        for style in ["现代简约", "奶油风", "新中式", "侘寂风", "轻法式", "工业风"]:
            if style in all_text: profile["style"] = style; break
        # 城市
        for city in ["漳州", "厦门", "泉州", "福州", "龙海"]:
            if city in all_text: profile["city"] = city; break
        self.user_profile.update(profile)


# ═══════════════════════════════════
# Agent 核心引擎
# ═══════════════════════════════════

global_memory = AgentMemory()


def chat(
    message: str,
    mode: str = "default",
    tenant_id: str = "zq-5bb59623",
    context: dict = None,
) -> dict:
    """
    Agent 对话入口

    参数:
        message: 用户消息
        mode: default/renovation_expert/content_creator
        tenant_id: 租户ID
        context: 额外上下文（小区/面积/预算等）
    """
    global_memory.add("user", message)
    global_memory.extract_user_info()

    # 意图识别
    intent = _detect_intent(message)
    profile = global_memory.user_profile

    # 如果是工具类意图，直接执行
    if intent.get("tool"):
        tool_result = _execute_tool(intent["tool"], intent.get("params", {}), tenant_id)
        response = tool_result.get("response", str(tool_result))
        global_memory.add("assistant", response)
        return {
            "ok": True,
            "message": response,
            "intent": intent,
            "tool_called": intent["tool"],
            "tool_result": tool_result,
            "profile": profile,
        }

    # 构建知识上下文
    knowledge_ctx = ""
    try:
        from zhuangqi_knowledge_v1 import full_knowledge_dump
        kb = full_knowledge_dump("all")
        knowledge_ctx = kb.get("knowledge", "")[:2000]
    except Exception:
        import logging; logging.getLogger(__name__).warning("Suppressed exception", exc_info=True)

    # 构建 prompt
    sp = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["default"])
    tools_desc = "\n".join([f"- {v['name']}: {v['description']}" for v in AGENT_TOOLS.values()])
    system_prompt = sp.format(
        tools_description=f"可用工具:\n{tools_desc}",
        user_context=f"面积:{profile.get('area','?')}平, 预算:{profile.get('budget','?')}万, 风格:{profile.get('style','?')}, 城市:{profile.get('city','漳州')}",
        knowledge_context=knowledge_ctx,
        platform_tips=_get_platform_tips(),
    )

    # 调用 AI
    from admin_dashboard import _deepseek_call
    conversation_history = global_memory.get_context(5)
    full_prompt = f"{system_prompt}\n\n对话历史:\n{conversation_history}\n\n用户: {message}\n助手:"
    ai_response = _deepseek_call(system_prompt, full_prompt, max_tokens=800)

    global_memory.add("assistant", ai_response)
    return {
        "ok": True,
        "message": ai_response,
        "intent": intent,
        "mode": mode,
        "profile": profile,
    }


def _detect_intent(message: str) -> dict:
    """意图识别"""
    msg = message.lower()

    intents = [
        (["生成", "写", "创作", "文案", "脚本", "文章", "发布"], "generate_content", {"topic": message}),
        (["视频", "做视频", "生成视频", "混剪"], "generate_video", {"topic": message}),
        (["发布", "发送", "publish"], "publish_content", {}),
        (["预算", "多少钱", "花费", "费用"], "estimate_budget", {}),
        (["小区", "楼盘", "材料", "工价", "政策", "公积金"], "search_knowledge", {"query": message}),
        (["竞品", "对手", "同行", "competitor"], "competitor_analysis", {}),
        (["批量", "一键", "全部生成", "自动化"], "batch_produce", {}),
    ]

    for keywords, tool, params in intents:
        if any(kw in msg for kw in keywords):
            # 提取参数
            area_match = re.search(r'(\d+)\s*平', message)
            budget_match = re.search(r'(\d+)\s*万', message)
            if area_match and tool == "estimate_budget":
                params["area"] = int(area_match.group(1))
            if budget_match:
                params["budget"] = int(budget_match.group(1))
            return {"tool": tool, "params": params, "confidence": 0.8}

    return {"tool": None, "type": "conversation"}


def _execute_tool(tool_name: str, params: dict, tenant_id: str) -> dict:
    """执行工具调用"""
    tool = AGENT_TOOLS.get(tool_name)
    if not tool:
        return {"error": f"未知工具: {tool_name}", "response": f"抱歉，我还没有学会{tool_name}这个能力。"}

    handler_name = tool["handler"]
    # 调用内部处理方法
    if handler_name == "_tool_generate_content":
        return _tool_generate_content(params, tenant_id)
    elif handler_name == "_tool_generate_video":
        return _tool_generate_video(params, tenant_id)
    elif handler_name == "_tool_publish_content":
        return _tool_publish_content(params, tenant_id)
    elif handler_name == "_tool_estimate_budget":
        return _tool_estimate_budget(params, tenant_id)
    elif handler_name == "_tool_search_knowledge":
        return _tool_search_knowledge(params, tenant_id)
    elif handler_name == "_tool_competitor_analysis":
        return _tool_competitor_analysis(params, tenant_id)
    elif handler_name == "_tool_batch_produce":
        return _tool_batch_produce(params, tenant_id)
    return {"error": f"工具未实现: {tool_name}"}


# ═══════════════════════════════════
# 工具实现
# ═══════════════════════════════════

def _tool_generate_content(params: dict, tenant_id: str) -> dict:
    topic = params.get("topic", "装修建议")
    platform = params.get("platform", "xiaohongshu")
    from admin_dashboard import _deepseek_call

    platform_guides = {
        "xiaohongshu": "小红书图文风格：标题要抓眼球+emoji，正文用短句+分段，结尾加话题标签。控制在500字以内。",
        "douyin": "抖音口播脚本：开头3秒钩子，中间干货，结尾引导关注。口语化、有节奏感。",
        "wechat": "公众号长文：标题党+小标题分段+干货满满。1500-3000字。",
    }

    guide = platform_guides.get(platform, "")
    prompt = f"""请根据以下主题生成{platform}内容:

主题: {topic}
{guide}

输出完整的内容（含标题和正文），可直接发布。"""

    content = _deepseek_call(platform_guides.get(platform, ""), prompt, max_tokens=1500)
    return {"ok": True, "response": content, "content": content, "platform": platform}


def _tool_generate_video(params: dict, tenant_id: str) -> dict:
    topic = params.get("topic", "")
    template = params.get("template", "before_after")
    from video_engine import generate_video_from_content
    result = generate_video_from_content(topic, "", provider="mock", template=template)
    response = f"已生成视频方案：{result['script'].get('mode','')}，{result['script'].get('duration','')}。"
    return {"ok": True, "response": response, "result": result}


def _tool_publish_content(params: dict, tenant_id: str) -> dict:
    platform = params.get("platform", "xiaohongshu")
    title = params.get("title", "")
    content = params.get("content", "")
    from platform_publisher import publish
    result = publish(platform, "image", title, content, dry_run=True)
    return {"ok": True, "response": f"内容已准备发布到{platform}（模拟模式）", "result": result}


def _tool_estimate_budget(params: dict, tenant_id: str) -> dict:
    area = params.get("area", 100)
    style = params.get("style", "现代简约")
    level = params.get("level", "舒适型")
    from zhuangqi_knowledge_v1 import estimate_budget, get_timeline
    budget = estimate_budget(area, level, style)
    timeline = get_timeline()
    response = f"""**{area}平{style}{level}装修预算估算：**

💰 总预算：{budget['total_range'][0]/10000:.1f}-{budget['total_range'][1]/10000:.1f}万
📐 单价：{budget['unit_price_range'][0]}-{budget['unit_price_range'][1]}元/平
⏱ 预计工期：{timeline['total_days_range'][0]}-{timeline['total_days_range'][1]}天

建议找3家装修公司对比报价，差价通常在15-20%。"""
    return {"ok": True, "response": response, "budget": budget}


def _tool_search_knowledge(params: dict, tenant_id: str) -> dict:
    query = params.get("query", "")
    category = params.get("category", "all")
    from zhuangqi_knowledge_v1 import search_community, get_material_guide, get_policies, get_local_issues

    results = []
    if "小区" in query or "楼盘" in query:
        r = search_community(query)
        results.append(f"找到 {r['total']} 个相关小区")
        for c in r["results"][:3]:
            results.append(f"- {c['name']} | {c['type']} | {c['year']}年 | 均价{c['avg_price']}元")

    if "材料" in query or "价格" in query:
        m = get_material_guide()
        results.append(f"可用材料类型: {', '.join(m.get('materials', []))}")

    if "政策" in query or "公积金" in query:
        p = get_policies()
        for name, info in p["policies"].items():
            results.append(f"- {name}: {info.get('额度', info.get('利率', info.get('补贴', '')))}")

    if "回南天" in query or "台风" in query or "高温" in query:
        i = get_local_issues()
        for name, info in i["issues"].items():
            results.append(f"- {name}({info['months']}): {info['解决方案'][0]}")

    response = "\n".join(results) if results else "未找到相关信息，请尝试更具体的搜索词。"
    return {"ok": True, "response": response, "results": results}


def _tool_competitor_analysis(params: dict, tenant_id: str) -> dict:
    name = params.get("competitor_name", "本地竞品")
    response = f"""**{name}竞品速览（模拟数据）：**

📊 内容对比:
- 小红书: 月发布约15篇，平均互动200+
- 抖音: 月发布约8条，平均播放5000+
- 公众号: 周更1-2篇

💡 差距机会:
- 对方小红书更新频率高但内容同质化
- 抖音缺乏真人出镜内容
- 可以做差异化: 施工过程实拍+预算公开

🔍 深入分析请使用完整竞品分析工具。"""
    return {"ok": True, "response": response}


def _tool_batch_produce(params: dict, tenant_id: str) -> dict:
    topics = params.get("topics", ["装修攻略", "材料选购"])
    count = params.get("count", 3)
    response = f"🚀 批量生产 {count} 条内容已启动：\n"
    for i, topic in enumerate(topics[:count]):
        response += f"{i+1}. {topic} → 生成中...\n"
    response += "\n完成后自动通知。当前为模拟模式。"
    return {"ok": True, "response": response, "jobs": len(topics[:count])}


# ═══════════════════════════════════
# 辅助函数
# ═══════════════════════════════════

def _get_platform_tips() -> str:
    return """各平台内容要点:
- 小红书: 封面要好看，标题加emoji，正文分点，话题标签5-8个
- 抖音: 前3秒决定生死，用悬念/痛点/冲突开篇
- 公众号: 深度内容，排版舒适，适合长文科普
- 视频号: 真实>精致，真人出镜>画外音"""


def get_agent_status() -> dict:
    return {
        "ok": True,
        "tools": list(AGENT_TOOLS.keys()),
        "tools_count": len(AGENT_TOOLS),
        "memory_turns": len(global_memory.history),
        "user_profile": global_memory.user_profile,
        "modes": list(SYSTEM_PROMPTS.keys()),
    }


def clear_memory():
    global global_memory
    global_memory = AgentMemory()
    return {"ok": True, "message": "记忆已清除"}


# ═══════════════════════════════════
# CLI 测试
# ═══════════════════════════════════

if __name__ == "__main__":
    # 测试对话
    print("=== 云数科技 AI Agent 测试 ===\n")

    # 装修咨询
    r = chat("我家100平，想装奶油风，大概多少钱？")
    print(f"装修咨询: {r['message'][:200]}...\n")

    # 工具调用
    r2 = chat("帮我生成一篇小红书装修文案")
    print(f"内容生成: {r2.get('tool_called')} - {r2.get('ok')}\n")

    # 知识搜索
    r3 = chat("碧湖万达广场什么户型")
    print(f"知识搜索: {r3.get('tool_called')} - {r3.get('ok')}\n")

    # Agent状态
    print(json.dumps(get_agent_status(), ensure_ascii=False, indent=2))
