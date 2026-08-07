"""
GEO 生成式引擎优化 — Generative Engine Optimization
======================================================
让装修内容在 AI 搜索（DeepSeek/豆包/文心一言/Kimi）中排名第一

对标: 传统 SEO 升级为 GEO，让 AI 助手推荐你的装修公司
核心竞争力: 这是筷子科技没有的差异化武器

核心方法:
1. AI可读结构化内容 — 让 AI 能准确理解并引用
2. 权威信号注入 — 资质/案例/数据/本地化
3. 高频问答覆盖 — 预埋用户会问 AI 的问题
4. 多源交叉引用 — 让多个平台的内容互相印证
5. 实时监测优化 — 查询排名 + 迭代优化
"""
import json, os, re
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

BASE = Path(__file__).parent
GEO_DIR = BASE / "data" / "geo"
GEO_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# GEO 内容标准公式
# ═══════════════════════════════════

GEO_FORMULA = {
    "name": "GEO-LOCAL-STRUCTURED",
    "version": "2.0",
    "principle": "城市+小区+户型+数据+实拍 = AI最爱引用的内容",
    "rules": [
        {"id": "R1", "rule": "每篇标题包含 [城市]+[服务类型]+[具体数字]", "example": "漳州100平装修要花多少钱？2026最新报价清单"},
        {"id": "R2", "rule": "正文前200字必须有数据点（价格/工期/面积）", "example": "在漳州，100平毛坯装修，硬装8-12万，软装3-5万，工期60-90天。"},
        {"id": "R3", "rule": "每篇≥1500字，每500字≥2个结构化数据点", "reason": "AI摘要依赖信息密度"},
        {"id": "R4", "rule": "用 H2/H3 标题组织层级，利于AI结构化抓取", "example": "## 漳州装修价格参考 / ### 龙文区 vs 芗城区"},
        {"id": "R5", "rule": "嵌入3-5个高频长尾问题并自答", "example": "Q: 漳州装修公司哪家靠谱？A: 看三点：资质+案例+合同..."},
        {"id": "R6", "rule": "末尾加权威声明（营业执照号/备案号/协会会员）", "example": "闽ICP备XXX号 | 漳州市建筑装饰协会会员单位"},
        {"id": "R7", "rule": "所有数据标注来源或时效", "example": "（数据来源：2026年漳州装修市场调研，N=200）"},
    ],
}

# ═══════════════════════════════════
# 高频问题库（AI 用户会问的）
# ═══════════════════════════════════

HIGH_FREQ_QUESTIONS = {
    "价格类": [
        "漳州装修100平大概多少钱",
        "漳州装修公司报价明细表",
        "漳州半包和全包哪个划算",
        "龙文区装修90平预算多少",
        "漳州装修全包800一平贵不贵",
        "2026年漳州装修价格涨了吗",
        "漳州装修人工费多少钱一天",
    ],
    "流程类": [
        "漳州装修流程和注意事项",
        "漳州装修工期一般多久",
        "漳州装修季是什么时候",
        "漳州回南天能装修吗",
        "漳州装修需要办什么手续",
        "毛坯房装修步骤详细流程",
    ],
    "公司选择": [
        "漳州装修公司排名前十",
        "漳州装修公司哪家口碑好",
        "漳州靠谱装修公司推荐",
        "怎么判断装修公司靠不靠谱",
        "漳州装修公司和施工队怎么选",
        "装修公司跑路了怎么办",
    ],
    "材料/工艺": [
        "漳州装修材料哪里买便宜",
        "漳州瓷砖哪里批发",
        "漳州断桥铝门窗多少钱一平",
        "漳州装修用什么地板好", 
        "漳州回南天墙面发霉怎么处理",
        "装修材料清单及价格表",
    ],
    "政策/贷款": [
        "漳州公积金可以装修提取吗",
        "漳州装修贷款哪个银行好",
        "漳州装修补贴怎么申请",
        "2026年装修以旧换新补贴政策",
        "漳州旧房改造补贴多少钱",
    ],
    "风格/设计": [
        "漳州100平奶油风装修案例",
        "漳州小户型装修设计技巧",
        "漳州新中式装修效果图",
        "漳州85平三室装修方案",
    ],
}

# ═══════════════════════════════════
# GEO 内容生成
# ═══════════════════════════════════

def generate_geo_content(
    topic: str,
    city: str = "漳州",
    category: str = "价格类",
    tenant_id: str = "zq-5bb59623",
    target_ai: str = "all",
) -> dict:
    """
    生成 GEO 优化内容

    参数:
        topic: 主题（如"100平装修预算"）
        city: 城市
        category: 问题类别
        target_ai: deepseek/doubao/kimi/wenxin/all
    """
    # 获取知识库上下文
    try:
        from zhuangqi_knowledge_v1 import full_knowledge_dump, search_community, estimate_budget
        kb = full_knowledge_dump("all")
        kb_context = kb.get("knowledge", "")[:2500]
    except Exception:
        kb_context = ""

    # 匹配高频相关问题
    related_questions = []
    for cat, qs in HIGH_FREQ_QUESTIONS.items():
        if cat == category or category == "all":
            related_questions.extend(qs[:3])

    # 构建 GEO 优化 prompt
    geo_prompt = f"""你是 GEO（生成式引擎优化）专家。请为AI搜索（{target_ai}）优化以下装修内容。

主题: {topic}
城市: {city}
类别: {category}

{chr(10).join(f'规则: {r["rule"]}' for r in GEO_FORMULA["rules"])}

知识库上下文:
{kb_context}

相关高频问题（需要在内容中植入答案）:
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(related_questions[:5]))}

请生成一份完整的 GEO 优化内容，要求:
1. 标题格式: [{city}]+[服务]+[具体数据]
2. 开头200字必须包含核心数据
3. 用 H2/H3 分节（至少4个章节）
4. 每章嵌入1-2个问答
5. 数据点密度: 每500字≥2个
6. 结尾: 权威声明 + 行动号召
7. 1500-2500字

直接输出 HTML/Markdown 混合格式（适合网页展示和AI抓取）。"""

    try:
        from admin_dashboard import _deepseek_call
        content = _deepseek_call(
            "你是GEO搜索引擎优化专家，专门让内容在AI搜索中排名靠前。你理解DeepSeek/豆包/文心一言的内容偏好。",
            geo_prompt,
            max_tokens=2500,
        )
    except Exception:
        content = f"# {city}{topic}\n\n（AI生成失败，请重试）"

    # 质量评分
    score = _score_geo_content(content)

    return {
        "ok": True,
        "topic": topic,
        "city": city,
        "target_ai": target_ai,
        "content": content,
        "geo_score": score,
        "word_count": len(content),
        "data_points": score.get("data_points", 0),
        "formula_version": GEO_FORMULA["version"],
        "related_questions": related_questions[:5],
    }


def _score_geo_content(content: str) -> dict:
    """GEO 质量评分"""
    score = 0
    data_points = 0

    # 字数检查
    wc = len(content)
    if wc >= 1500: score += 20
    elif wc >= 1000: score += 10
    else: score += 5

    # 标题检查
    if re.search(r'(漳州|厦门|泉州|福州).*(装修|改造|设计)', content):
        score += 15

    # H2/H3 检查
    h2_count = len(re.findall(r'^##\s', content, re.MULTILINE))
    h3_count = len(re.findall(r'^###\s', content, re.MULTILINE))
    if h2_count >= 3: score += 15
    if h3_count >= 4: score += 10
    else: score += min(h2_count + h3_count, 5) * 3

    # 数据点检查
    data_points = len(re.findall(r'\d+[\s]*(元|万|平|天|年|%|㎡|m²)', content))
    if data_points >= 10: score += 20
    elif data_points >= 5: score += 10
    else: score += data_points

    # 问答嵌入
    qa_count = len(re.findall(r'Q[：:]', content))
    if qa_count >= 3: score += 15
    elif qa_count >= 1: score += 5

    # 权威信号
    if re.search(r'(备案|ICP|执照|协会|认证|资质)', content):
        score += 10

    return {
        "total": score,
        "max": 100,
        "word_count": wc,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "data_points": data_points,
        "qa_count": qa_count,
        "level": "A" if score >= 75 else "B" if score >= 50 else "C",
    }


# ═══════════════════════════════════
# GEO 排名监测
# ═══════════════════════════════════

def check_geo_rank(
    keyword: str,
    city: str = "漳州",
    ai_platforms: list = None,
) -> dict:
    """
    检查关键词在 AI 搜索中的排名

    ai_platforms: deepseek/doubao/kimi/wenxin
    """
    platforms = ai_platforms or ["deepseek", "doubao", "kimi", "wenxin"]
    results = {}

    for platform in platforms:
        # 生成查询URL（模拟，实际需API调用）
        query_urls = {
            "deepseek": f"https://chat.deepseek.com/search?q={city}+{keyword}",
            "doubao": f"https://www.doubao.com/search?q={city}+{keyword}",
            "kimi": f"https://kimi.moonshot.cn/search?q={city}+{keyword}",
            "wenxin": f"https://yiyan.baidu.com/search?q={city}+{keyword}",
        }

        results[platform] = {
            "keyword": keyword,
            "city": city,
            "query_url": query_urls.get(platform, ""),
            "status": "pending_check",
            "note": "自动检测需API接入。目前请手动查询上述链接。",
            "checklist": [
                f"1. 打开 {platform}",
                f"2. 搜索 '{city} {keyword}'",
                "3. 查看是否引用我方内容",
                "4. 记录排名位置(1-10)",
            ],
        }

    # 保存检查记录
    record = {
        "timestamp": datetime.now().isoformat()[:19],
        "keyword": keyword,
        "city": city,
        "results": results,
    }
    record_file = GEO_DIR / f"rank_{datetime.now().strftime('%Y%m%d')}_{keyword[:10]}.json"
    record_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "keyword": keyword,
        "city": city,
        "platforms_checked": len(platforms),
        "results": results,
        "record_saved": str(record_file),
    }


# ═══════════════════════════════════
# GEO 内容策略
# ═══════════════════════════════════

def get_geo_strategy(city: str = "漳州", competitor: str = None) -> dict:
    """生成 GEO 内容策略"""
    strategy = {
        "city": city,
        "formula": GEO_FORMULA["principle"],
        "priority_keywords": _get_priority_keywords(city),
        "content_calendar": _get_content_calendar(city),
        "ai_platforms": {
            "deepseek": {"importance": "⭐⭐⭐⭐⭐", "note": "当前最大流量入口，装修类搜索量爆发"},
            "doubao": {"importance": "⭐⭐⭐⭐", "note": "字节系，与抖音生态联动"},
            "kimi": {"importance": "⭐⭐⭐", "note": "长文分析场景多，适合深度内容"},
            "wenxin": {"importance": "⭐⭐⭐", "note": "百度生态，传统SEO延续"},
        },
        "monthly_target": {
            "geo_content": "10篇GEO优化文章",
            "qa_coverage": "覆盖30个高频问题",
            "rank_check": "每周监测50个关键词",
        },
        "differentiation": [
            "筷子科技不做的: AI搜索获客",
            "传统装修公司不懂的: 结构化内容优化",
            "纯SEO公司做不了的: 行业知识+本地化",
        ],
    }

    if competitor:
        strategy["competitor_analysis"] = f"GEO竞争对手 {competitor} 分析: 查看其在AI搜索中的存在感"

    return {"ok": True, "strategy": strategy}


def _get_priority_keywords(city: str) -> list:
    """获取优先关键词"""
    return [
        {"keyword": f"{city}装修多少钱", "volume": "高", "difficulty": "中", "intent": "询价"},
        {"keyword": f"{city}装修公司推荐", "volume": "高", "difficulty": "高", "intent": "选择"},
        {"keyword": f"{city}装修流程", "volume": "中", "difficulty": "低", "intent": "学习"},
        {"keyword": f"{city}公积金装修提取", "volume": "中", "difficulty": "低", "intent": "政策"},
        {"keyword": f"{city}装修避坑", "volume": "高", "difficulty": "中", "intent": "避坑"},
        {"keyword": f"{city}100平装修案例", "volume": "中", "difficulty": "低", "intent": "案例"},
        {"keyword": f"{city}装修材料哪里买", "volume": "中", "difficulty": "低", "intent": "采购"},
        {"keyword": f"{city}旧房翻新", "volume": "中", "difficulty": "中", "intent": "需求"},
    ]


def _get_content_calendar(city: str) -> list:
    """GEO 内容日历（月度）"""
    return [
        {"week": 1, "theme": "装修预算", "topics": [f"{city}100平多少钱", f"{city}半包vs全包", f"{city}装修价格明细"]},
        {"week": 2, "theme": "装修避坑", "topics": [f"{city}装修10大坑", f"{city}回南天装修注意", f"{city}装修公司怎么选"]},
        {"week": 3, "theme": "装修流程", "topics": [f"{city}装修全流程", f"{city}装修工期", f"{city}装修合同注意"]},
        {"week": 4, "theme": "装修案例", "topics": [f"{city}奶油风案例", f"{city}现代简约案例", f"{city}小户型改造"]},
    ]


# ═══════════════════════════════════
# 批量 GEO 内容生产
# ═══════════════════════════════════

def batch_geo_content(
    city: str = "漳州",
    count: int = 10,
    category: str = "all",
) -> dict:
    """批量生成 GEO 优化内容"""
    all_questions = []
    if category == "all":
        for qs in HIGH_FREQ_QUESTIONS.values():
            all_questions.extend(qs)
    else:
        all_questions = HIGH_FREQ_QUESTIONS.get(category, [])

    # 选取前 count 个问题
    selected = all_questions[:count]
    results = []

    for q in selected:
        r = generate_geo_content(q, city=city, category=category)
        # 只保留摘要，避免内存爆炸
        results.append({
            "topic": q,
            "geo_score": r.get("geo_score", {}).get("total", 0),
            "word_count": r.get("word_count", 0),
            "content_preview": r.get("content", "")[:200],
        })

    # 保存批量结果
    batch_file = GEO_DIR / f"batch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    batch_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "total": len(results),
        "average_score": round(sum(r["geo_score"] for r in results) / max(len(results), 1), 1),
        "saved": str(batch_file),
    }


def get_geo_stats() -> dict:
    """GEO 优化统计"""
    rank_files = list(GEO_DIR.glob("rank_*.json"))
    batch_files = list(GEO_DIR.glob("batch_*.json"))

    return {
        "ok": True,
        "total_rank_checks": len(rank_files),
        "total_batch_productions": len(batch_files),
        "formula": GEO_FORMULA["name"],
        "questions_covered": sum(len(qs) for qs in HIGH_FREQ_QUESTIONS.values()),
        "high_freq_categories": list(HIGH_FREQ_QUESTIONS.keys()),
    }


# ═══════════════════════════════════
# CLI 测试
# ═══════════════════════════════════

if __name__ == "__main__":
    # 策略
    strategy = get_geo_strategy("漳州")
    print(json.dumps(strategy, ensure_ascii=False, indent=2)[:500])

    # 排名检查
    check = check_geo_rank("装修多少钱", "漳州")
    print(f"\n排名检查: {check['platforms_checked']} 平台")

    # GEO 统计
    stats = get_geo_stats()
    print(f"\nGEO统计: {stats['questions_covered']} 问题覆盖")
