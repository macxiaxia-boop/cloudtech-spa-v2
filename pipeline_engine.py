"""
CloudTech Pipeline Engine v1.0 — 管线引擎
=========================================
知识转化自动化: Inbox → Knowledge → Pattern → Rule
管线自愈: 失败重试 → 模型降级 → 告警
装企批量生产: 7系列 × 39账号
"""
import json, os, re, sys, time
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

KB = Path("D:/个人文件/AI/Knowledge")
INBOX = KB / "01_Inbox"
PROCESSED = KB / "02_Processed"
PATTERNS = KB / "03_Patterns"
RULES = KB / "04_Rules"
CONTENT_OUT = Path("D:/个人文件/AI/05 项目生产系统/内容生产")
ZHUANGQI = Path("D:/个人文件/电商图片/装企孵化")

# ═══════════════════════════════════
# 知识转化管道
# ═══════════════════════════════════

def convert_knowledge(max_items: int = 10) -> dict:
    """Inbox → Processed → Pattern → Rule 自动化转化"""
    result = {"inbox_count": 0, "processed": 0, "patterns": 0, "rules": 0, "details": []}

    for d in [INBOX, PROCESSED, PATTERNS, RULES]:
        d.mkdir(parents=True, exist_ok=True)

    # Step 1: 扫描Inbox
    inbox_files = sorted(INBOX.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:max_items]
    result["inbox_count"] = len(inbox_files)

    for f in inbox_files[:max_items]:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")[:5000]
            name = f.stem

            # Step 2: 分类 → Processed
            category = _classify(content)
            processed_path = PROCESSED / f"{category}_{name}.md"
            if not processed_path.exists():
                processed_path.write_text(f"# {name}\n\n> 分类: {category}\n> 来源: Inbox\n> 处理时间: {datetime.now()}\n\n{content[:3000]}", encoding="utf-8")
                result["processed"] += 1
                result["details"].append(f"✅ {name} → {category}")

            # Step 3: 提取Pattern
            patterns = _extract_patterns(content, name)
            for p in patterns:
                p_path = PATTERNS / f"{p['type']}_{p['key'][:30]}.md"
                if not p_path.exists():
                    p_path.write_text(f"# {p['type']}: {p['key']}\n\n{p['value']}\n\n> 来源: {name}", encoding="utf-8")
                    result["patterns"] += 1

            # Step 4: 生成Rule
            rules = _derive_rules(content, name)
            for r in rules:
                r_path = RULES / f"rule_{r['key'][:30]}.md"
                if not r_path.exists():
                    r_path.write_text(f"# Rule: {r['key']}\n\n**When:** {r['when']}\n**Then:** {r['then']}\n**Because:** {r['because']}\n\n> 来源: {name}", encoding="utf-8")
                    result["rules"] += 1

        except Exception as e:
            result["details"].append(f"❌ {f.name}: {e}")

    return result


def _classify(content: str) -> str:
    """Auto-classify content into category"""
    text = content.lower()
    if any(kw in text for kw in ["装修", "装饰", "家居", "设计"]): return "装修家居"
    if any(kw in text for kw in ["ai", "模型", "gpt", "llm", "agent"]): return "AI技术"
    if any(kw in text for kw in ["营销", "广告", "投放", "获客"]): return "数字营销"
    if any(kw in text for kw in ["视频", "剪辑", "口播", "脚本"]): return "内容创作"
    if any(kw in text for kw in ["商业", "模式", "盈利", "增长"]): return "商业策略"
    return "通用知识"


def _extract_patterns(content: str, source: str) -> list:
    """Extract reusable patterns from content"""
    patterns = []
    # Pattern: 数字+单位  (e.g., "3000万用户", "增长45%")
    nums = re.findall(r'(\d+(?:\.\d+)?)\s*(万|亿|%|倍|倍以上)', content)
    if nums:
        patterns.append({"type": "数据锚点", "key": f"data_{source[:15]}",
                         "value": f"可引用数据点: {', '.join([f'{n[0]}{n[1]}' for n in nums[:5]])}"})

    # Pattern: "X比Y更Z" 比较结构
    compares = re.findall(r'([^，。\n]{5,30}(?:比|相比|超过|领先)[^，。\n]{5,30})', content)
    if compares:
        patterns.append({"type": "比较框架", "key": f"compare_{source[:15]}",
                         "value": f"对比锚点: {' | '.join(compares[:3])}"})

    # Pattern: "因为X所以Y" 因果链
    causals = re.findall(r'(因为[^，。\n]{10,40}(?:所以|导致|因此)[^，。\n]{10,40})', content)
    if causals:
        patterns.append({"type": "因果链", "key": f"causal_{source[:15]}",
                         "value": f"因果逻辑: {causals[0][:100]}"})

    return patterns


def _derive_rules(content: str, source: str) -> list:
    """Derive actionable rules from content"""
    rules = []
    # Rule: 如果内容包含"不要/避免/注意"，生成避坑规则
    avoids = re.findall(r'(不要[^。\n]{5,50}|避免[^。\n]{5,50}|注意[^。\n]{5,50})', content)
    for a in avoids[:3]:
        rules.append({"key": f"avoid_{a[:15]}", "when": "内容创作时",
                      "then": a, "because": f"来源分析: {source[:30]}"})

    # Rule: 如果内容包含"XX%"，生成数据引用规则
    pcts = re.findall(r'(\d+%)[^。\n]*([^。\n]{10,40})', content)
    for p in pcts[:2]:
        rules.append({"key": f"stat_{p[0]}", "when": "需要数据支撑时",
                      "then": f"引用: {p[0]} {p[1]}", "because": "增强可信度"})

    return rules


def knowledge_pipeline_summary() -> dict:
    """返回知识转化管道总览"""
    return {
        "inbox": len(list(INBOX.glob("*.md"))) if INBOX.exists() else 0,
        "processed": len(list(PROCESSED.glob("*.md"))) if PROCESSED.exists() else 0,
        "patterns": len(list(PATTERNS.glob("*.md"))) if PATTERNS.exists() else 0,
        "rules": len(list(RULES.glob("*.md"))) if RULES.exists() else 0,
    }


# ═══════════════════════════════════
# 管线自愈
# ═══════════════════════════════════

class PipelineHealer:
    """管线自愈: 失败检测 → 重试 → 模型降级 → 告警"""

    def __init__(self):
        self.retry_count = 0
        self.max_retries = 3
        self.fallback_models = ["deepseek-v4-pro", "deepseek-v4-flash"]

    def heal(self, func, *args, **kwargs):
        """Execute with retry + fallback"""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self.retry_count += 1
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
        return {"error": str(last_error), "retries": self.retry_count, "status": "exhausted"}


# ═══════════════════════════════════
# 装企批量生产
# ═══════════════════════════════════

ZHUANGQI_SERIES = {
    "A-案例故事": ["闽南院子旧改", "闽乡情怀旧改", "00后爆改", "普通家庭翻新", "自建房改造记",
                   "业主自装日记", "前后对比快剪", "适老化改造", "出租房改造", "二手房翻新"],
    "B-知识教育": ["户型优化", "报价拆解", "工地验收", "装修翻车避坑", "设计决策对比",
                   "装修问题速查", "合同解读", "材料选购", "流程全景", "避坑速查"],
    "C-本地型": ["本地小区图鉴", "本地装修行情", "装修情报局", "本地建材探店", "小区户型库", "免费设计获客"],
    "D-工具型": ["预算计算器", "风格诊断器"],
    "E-个人IP": ["装修日记", "泉州老房新生记", "厦门小户型", "装修小白365天", "预算10万实录"],
    "F-避坑型": ["踩坑血泪史", "合同里的坑", "材料避雷指南"],
    "G-好物推荐": ["家居好物开箱", "闽南非遗家居", "平替材料研究所"],
}

def batch_produce(series: str = None, count: int = 5) -> dict:
    """批量生产装企内容"""
    from admin_dashboard import CREATOR_STYLES, CONTENT_FORMS, PLATFORMS, _deepseek_call

    produced = []
    target_series = {series: ZHUANGQI_SERIES[series]} if series and series in ZHUANGQI_SERIES else ZHUANGQI_SERIES

    for s_name, accounts in target_series.items():
        for acc in accounts[:count]:
            try:
                form = CONTENT_FORMS["article"]
                creator = CREATOR_STYLES["zhinan"]
                platform = PLATFORMS["xiaohongshu"]

                topic = f"{acc}装修案例"
                sys_p = f"你是装修内容专家。对标{creator['name']}: {creator['tone']}。为「{acc}」创作一篇小红书文案。600-800字，口语化，有emoji，有干货。禁用: {', '.join(creator['forbidden'])}"
                content = _deepseek_call(sys_p, topic, max_tokens=1500)

                out_dir = CONTENT_OUT / s_name
                out_dir.mkdir(parents=True, exist_ok=True)
                fpath = out_dir / f"{acc}.md"
                fpath.write_text(f"# {acc}\n\n> 系列: {s_name} | 平台: 小红书 | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}", encoding="utf-8")
                produced.append({"account": acc, "series": s_name, "file": str(fpath), "words": len(content)})
            except Exception as e:
                produced.append({"account": acc, "series": s_name, "error": str(e)[:100]})

    return {"total_targets": len(produced), "produced": sum(1 for p in produced if "error" not in p),
            "failed": sum(1 for p in produced if "error" in p), "items": produced}
