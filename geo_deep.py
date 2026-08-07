"""
GEO 深度引擎 v2 — Real Crawling + Ranking + Optimization
==========================================================
真爬取 AI 搜索排名，真内容优化，真数据驱动

能力:
- AI搜索排名检查: 爬DeepSeek/豆包/文心一言搜索页
- 竞品GEO分析: 分析竞品在AI搜索中的存在感
- 内容缺口分析: 找出竞品覆盖了我们没覆盖的关键词
- 自动优化建议: 基于排名数据给出具体优化方案
- 批量监控: 定时检查N个关键词排名变化
"""
import json, os, re, time, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import defaultdict
import urllib.request
import urllib.parse

BASE = Path(__file__).parent
GEO_DATA = BASE / "data" / "geo"
GEO_DATA.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 一、AI搜索排名爬取
# ═══════════════════════════════════

def check_ai_ranking(
    keyword: str,
    city: str = "漳州",
    platforms: List[str] = None,
    our_domain: str = "cloudtech.ai",
) -> dict:
    """
    真爬取 AI 搜索排名

    使用 web_fetch 检查各AI平台的搜索结果
    """
    platforms = platforms or ["deepseek", "doubao"]
    results = {}

    search_urls = {
        "deepseek": f"https://chat.deepseek.com/search?q={urllib.parse.quote(city + ' ' + keyword)}",
        "doubao": f"https://www.doubao.com/chat/search?query={urllib.parse.quote(city + ' ' + keyword)}",
        "kimi": f"https://kimi.moonshot.cn/search?q={urllib.parse.quote(city + ' ' + keyword)}",
        "wenxin": f"https://yiyan.baidu.com/search?q={urllib.parse.quote(city + ' ' + keyword)}",
    }

    for platform in platforms:
        url = search_urls.get(platform)
        if not url:
            continue

        try:
            # 用 requests 真爬（需要cookie/header伪装）
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }

            resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            html = resp.text[:10000]

            # 分析排名
            ranking = _analyze_ranking(html, our_domain, keyword, platform)

            results[platform] = {
                "keyword": keyword,
                "city": city,
                "url": url,
                "status_code": resp.status_code,
                "ranking": ranking,
                "checked_at": datetime.now().isoformat()[:19],
            }

        except Exception as e:
            results[platform] = {
                "keyword": keyword,
                "error": str(e)[:200],
                "status": "crawl_failed",
            }

    # 保存记录
    record = {
        "timestamp": datetime.now().isoformat()[:19],
        "keyword": keyword,
        "city": city,
        "results": results,
    }
    _save_rank_record(record)

    return {"ok": True, "keyword": keyword, "results": results, "platforms_checked": len(results)}


def _analyze_ranking(html: str, domain: str, keyword: str, platform: str) -> dict:
    """分析HTML中的排名信息"""
    ranking = {"found": False, "position": None, "snippet": "", "competitors": []}

    # 检查我方域名
    if domain in html:
        ranking["found"] = True
        # 估算位置
        pos = html.find(domain)
        ranking["position"] = 1 if pos < 1000 else (2 if pos < 3000 else 3)

    # 提取摘要
    snippet_patterns = [
        r'<div[^>]*class="[^"]*result[^"]*"[^>]*>(.*?)</div>',
        r'<p[^>]*>(.{50,200}?' + re.escape(keyword) + r'.{50,200}?)</p>',
    ]
    for pattern in snippet_patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            ranking["snippet"] = re.sub(r'<[^>]+>', '', match.group(1))[:300]
            break

    # 提取竞品
    competitor_domains = ["kuaizi.cn", "tujia.com", "qijia.com", "zhuxiaobang.com", "tubatu.com"]
    for comp in competitor_domains:
        if comp in html and comp != domain:
            cp_pos = html.find(comp)
            ranking["competitors"].append({
                "domain": comp,
                "found": True,
                "position_estimate": 1 if cp_pos < 3000 else (2 if cp_pos < 6000 else 3),
            })

    return ranking


def _save_rank_record(record: dict):
    """保存排名记录"""
    date_str = datetime.now().strftime("%Y%m%d")
    daily_file = GEO_DATA / f"rankings_{date_str}.jsonl"
    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ═══════════════════════════════════
# 二、批量关键词排名监控
# ═══════════════════════════════════

def batch_rank_check(
    keywords: List[str],
    city: str = "漳州",
    platforms: List[str] = None,
) -> dict:
    """批量检查关键词排名"""
    results = []
    for kw in keywords:
        r = check_ai_ranking(kw, city, platforms)
        results.append(r)
        time.sleep(1)  # 避免请求过快

    found = sum(1 for r in results if any(
        p.get("ranking", {}).get("found") for p in r.get("results", {}).values()
    ))

    return {
        "ok": True,
        "total": len(keywords),
        "found_in_ai": found,
        "not_found": len(keywords) - found,
        "coverage_rate": f"{round(found/max(len(keywords),1)*100)}%",
        "results": results,
    }


# ═══════════════════════════════════
# 三、竞品GEO差距分析
# ═══════════════════════════════════

def competitor_geo_analysis(
    competitor_domain: str,
    keywords: List[str],
    city: str = "漳州",
) -> dict:
    """
    分析竞品在AI搜索中的存在感

    对比我方 vs 竞品在各个关键词上的AI搜索表现
    """
    our_results = batch_rank_check(keywords, city).get("results", [])
    comp_results = []

    for kw in keywords:
        r = check_ai_ranking(kw, city)
        comp_results.append(r)
        time.sleep(1)

    # 对比分析
    gap_analysis = []
    for kw, our, comp in zip(keywords, our_results, comp_results):
        our_found = any(
            p.get("ranking", {}).get("found")
            for p in our.get("results", {}).values()
        )
        comp_found = any(
            p.get("ranking", {}).get("found")
            for p in comp.get("results", {}).values()
        )

        gap_type = "both" if our_found and comp_found else \
                   "we_only" if our_found else \
                   "comp_only" if comp_found else \
                   "neither"

        if gap_type == "comp_only":
            gap_analysis.append({
                "keyword": kw,
                "gap": "竞品独占",
                "action": f"立即生产GEO优化内容覆盖: {kw}",
                "priority": "P0",
                "content_angle": _suggest_content_angle(kw, city),
            })
        elif gap_type == "neither":
            gap_analysis.append({
                "keyword": kw,
                "gap": "蓝海机会",
                "action": f"抢先布局: {kw}",
                "priority": "P1",
                "content_angle": _suggest_content_angle(kw, city),
            })

    return {
        "ok": True,
        "competitor": competitor_domain,
        "total_keywords": len(keywords),
        "gaps": gap_analysis,
        "urgent_gaps": len([g for g in gap_analysis if g["priority"] == "P0"]),
        "blue_ocean": len([g for g in gap_analysis if g["priority"] == "P1"]),
        "recommendation": _generate_geo_recommendation(gap_analysis),
    }


def _suggest_content_angle(keyword: str, city: str) -> str:
    """根据关键词建议内容角度"""
    angle_map = {
        "装修": f"{city}装修实拍案例+预算公开",
        "预算": f"{city}装修价格明细表+省钱攻略",
        "公司": f"{city}装修公司挑选指南+资质查询方法",
        "材料": f"{city}建材市场实地探访+价格对比",
        "流程": f"{city}装修全流程图解+时间节点",
        "公积金": f"{city}公积金装修提取实操教程",
        "风格": f"{city}热门装修风格实景案例",
        "改造": f"{city}旧房改造前后对比+花费清单",
        "避坑": f"{city}业主真实踩坑经历+解决方案",
        "设计": f"{city}户型设计改造方案",
        "小户型": f"{city}小户型空间利用技巧",
    }
    for k, v in angle_map.items():
        if k in keyword:
            return v
    return f"{city}{keyword}深度解析+本地数据"


def _generate_geo_recommendation(gaps: List[Dict]) -> str:
    """生成GEO优化建议"""
    p0 = [g for g in gaps if g["priority"] == "P0"]
    p1 = [g for g in gaps if g["priority"] == "P1"]

    rec = []
    if p0:
        rec.append(f"🚨 紧急: {len(p0)}个关键词被竞品独占，立即行动!")
        for g in p0[:3]:
            rec.append(f"  - {g['keyword']}: {g['action']}")
    if p1:
        rec.append(f"💡 机会: {len(p1)}个蓝海关键词待抢占")
        for g in p1[:3]:
            rec.append(f"  - {g['keyword']}: {g['action']}")
    if not p0 and not p1:
        rec.append("✅ 当前关键词覆盖良好，继续维护")

    return "\n".join(rec)


# ═══════════════════════════════════
# 四、内容缺口自动发现
# ═══════════════════════════════════

def discover_content_gaps(
    keyword_seeds: List[str],
    city: str = "漳州",
) -> dict:
    """
    自动发现内容缺口

    逻辑:
    1. 从种子关键词出发
    2. 搜索相关长尾词
    3. 检查是否已有GEO内容覆盖
    4. 输出缺口列表
    """
    # 长尾词扩展
    modifiers = [
        "多少钱", "价格", "费用", "报价", "预算",
        "流程", "步骤", "攻略", "指南", "注意",
        "推荐", "排名", "哪家好", "靠谱",
        "案例", "效果图", "实拍", "前后对比",
        f"{city}", "本地", "附近",
    ]

    expanded = []
    for seed in keyword_seeds:
        for mod in modifiers:
            expanded.append(f"{seed} {mod}")
        # 问题形式
        expanded.append(f"{seed}怎么选")
        expanded.append(f"{seed}要注意什么")

    # 去重
    expanded = list(set(expanded))[:50]

    # 检查已有内容（从 geo data 查）
    existing = _load_existing_geo_topics()
    gaps = []
    for kw in expanded:
        if kw not in existing:
            gaps.append({
                "keyword": kw,
                "status": "uncovered",
                "suggested_title": _generate_geo_title(kw, city),
                "content_type": _suggest_content_type(kw),
                "estimated_search_volume": _estimate_volume(kw),
            })

    gaps.sort(key=lambda x: x["estimated_search_volume"], reverse=True)

    return {
        "ok": True,
        "total_expanded": len(expanded),
        "existing_coverage": len(existing),
        "gaps": gaps[:20],
        "summary": f"发现 {len(gaps)} 个内容缺口，{len([g for g in gaps if g['estimated_search_volume'] >= 3])} 个高价值",
    }


def _load_existing_geo_topics() -> set:
    """加载已有GEO内容主题"""
    topics = set()
    for f in GEO_DATA.glob("*.jsonl"):
        try:
            for line in open(f, encoding="utf-8"):
                data = json.loads(line)
                topics.add(data.get("keyword", ""))
        except Exception:
            pass

    # 也从知识库加载
    try:
        from zhuangqi_knowledge_v1 import HIGH_FREQ_QUESTIONS
        for qs in HIGH_FREQ_QUESTIONS.values():
            for q in qs:
                topics.add(q)
    except Exception:
        pass

    return topics


def _generate_geo_title(keyword: str, city: str) -> str:
    """生成GEO标题"""
    if any(k in keyword for k in ["多少钱", "价格", "费用", "预算"]):
        return f"{city}{keyword}：2026最新报价清单（含明细表）"
    if any(k in keyword for k in ["推荐", "排名", "哪家"]):
        return f"{city}{keyword}？资深业主总结的5个挑选标准"
    if any(k in keyword for k in ["流程", "步骤", "攻略"]):
        return f"{city}装修{keyword}：从开工到入住全流程图解"
    return f"{city}{keyword}：装修必看的实战指南"


def _suggest_content_type(keyword: str) -> str:
    if any(k in keyword for k in ["案例", "效果", "实拍"]):
        return "图文+视频"
    if any(k in keyword for k in ["流程", "步骤"]):
        return "图解长文"
    if any(k in keyword for k in ["多少", "价格"]):
        return "清单/表格"
    return "深度文章"


def _estimate_volume(keyword: str) -> int:
    """估算搜索量 (1-5)"""
    high_volume = ["装修", "多少钱", "预算", "公司", "推荐"]
    if any(k in keyword for k in high_volume):
        return 5
    if "流程" in keyword or "攻略" in keyword:
        return 4
    if "案例" in keyword or "效果" in keyword:
        return 3
    return 2


# ═══════════════════════════════════
# 五、历史排名趋势
# ═══════════════════════════════════

def get_ranking_trend(keyword: str, days: int = 30) -> dict:
    """获取关键词排名历史趋势"""
    trend = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        daily_file = GEO_DATA / f"rankings_{date}.jsonl"
        if not daily_file.exists():
            continue

        for line in open(daily_file, encoding="utf-8"):
            data = json.loads(line)
            if data.get("keyword") == keyword:
                found = any(
                    p.get("ranking", {}).get("found")
                    for p in data.get("results", {}).values()
                )
                trend.append({"date": date, "found": found, "platforms": list(data.get("results", {}).keys())})
                break

    # 趋势判断
    recent = [t["found"] for t in trend[:7]]
    improving = sum(recent) > sum(not f for f in recent) if recent else None

    return {
        "ok": True,
        "keyword": keyword,
        "data_points": len(trend),
        "trend": trend[:days],
        "current_status": "found" if (trend and trend[0].get("found")) else "not_found",
        "trending": "improving" if improving else ("declining" if improving is False else "stable"),
    }


def get_geo_dashboard(city: str = "漳州") -> dict:
    """GEO总览仪表盘"""
    # 统计所有排名记录
    all_keywords = set()
    found_keywords = set()
    total_checks = 0

    for f in sorted(GEO_DATA.glob("rankings_*.jsonl"), reverse=True)[:7]:  # 最近7天
        for line in open(f, encoding="utf-8"):
            data = json.loads(line)
            kw = data.get("keyword", "")
            all_keywords.add(kw)
            total_checks += 1
            if any(p.get("ranking", {}).get("found") for p in data.get("results", {}).values()):
                found_keywords.add(kw)

    # 内容缺口
    gaps = discover_content_gaps(
        [f"{city}装修", f"{city}设计", f"{city}改造", f"{city}材料"],
        city,
    )

    return {
        "ok": True,
        "city": city,
        "total_keywords_monitored": len(all_keywords),
        "found_in_ai": len(found_keywords),
        "coverage_rate": f"{round(len(found_keywords)/max(len(all_keywords),1)*100)}%",
        "total_checks_7d": total_checks,
        "content_gaps": gaps.get("summary", ""),
        "top_gaps": gaps.get("gaps", [])[:5],
        "last_update": datetime.now().isoformat()[:19],
    }


# ═══════════════════════════════════
# CLI
# ═══════════════════════════════════

if __name__ == "__main__":
    print("GEO深度引擎 v2 就绪")
    print(f"数据目录: {GEO_DATA}")

    # 发现内容缺口
    gaps = discover_content_gaps(["漳州装修"], "漳州")
    print(f"内容缺口: {gaps['summary']}")
    for g in gaps.get("gaps", [])[:5]:
        print(f"  - {g['keyword']} [量:{g['estimated_search_volume']}] → {g['suggested_title'][:60]}")

    # 仪表盘
    dash = get_geo_dashboard("漳州")
    print(f"\nGEO仪表盘: 覆盖{dash['coverage_rate']} ({dash['found_in_ai']}/{dash['total_keywords_monitored']})")
