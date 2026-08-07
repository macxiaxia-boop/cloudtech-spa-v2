"""
学习力引擎 — Learning & Adaptation System
============================================
让系统学会你的偏好、风格和工作方式，越用越懂你

核心能力:
- 偏好学习: 从每次交互中学习你的风格偏好
- 纠错记忆: 记住你纠正过什么，不再犯同样错误  
- 内容风格适配: 学习你的写作风格、语气、格式偏好
- 决策模式识别: 从你的决策中学习判断逻辑
- 反馈闭环: 每次输出→收集反馈→优化下次输出
- 演化规则: 从反馈中自动生成行为规则
"""
import json, os, re, hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from collections import defaultdict

BASE = Path(__file__).parent
LEARN_DIR = BASE / "data" / "learning"
LEARN_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 一、偏好学习引擎
# ═══════════════════════════════════

class PreferenceLearner:
    """
    偏好学习: 从每次交互中提取偏好信号

    学习维度:
    - tone: 语气偏好 (正式/口语/幽默/专业)
    - length: 篇幅偏好 (简短/适中/详细)
    - format: 格式偏好 (表格/列表/段落)
    - depth: 深度偏好 (快速/标准/深度)
    - decision_style: 决策风格 (激进/稳健/保守)
    - platform_focus: 平台偏好 (小红书/抖音/公众号/视频号)
    """

    def __init__(self, tenant_id: str = "zq-5bb59623"):
        self.tid = tenant_id
        self.pref_file = LEARN_DIR / f"preferences_{tenant_id}.json"
        self.signal_file = LEARN_DIR / f"signals_{tenant_id}.jsonl"
        self._init()

    def _init(self):
        if not self.pref_file.exists():
            self.pref_file.write_text(json.dumps({
                "tone": {"formal": 0.2, "casual": 0.3, "professional": 0.5},
                "length": {"short": 0.3, "medium": 0.4, "long": 0.3},
                "format": {"table": 0.2, "list": 0.4, "paragraph": 0.4},
                "depth": {"quick": 0.3, "standard": 0.4, "deep": 0.3},
                "decision_style": {"aggressive": 0.3, "balanced": 0.4, "conservative": 0.3},
                "platform_focus": {"xiaohongshu": 0.3, "douyin": 0.25, "wechat_mp": 0.25, "shipinhao": 0.2},
                "learned_rules": [],
                "last_updated": "",
            }, ensure_ascii=False, indent=2), encoding="utf-8")

    def learn_from_interaction(self, message: str, response: str, rating: str = None):
        """从一次交互中学习"""
        signals = self._extract_signals(message, response, rating)
        with open(self.signal_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(signals, ensure_ascii=False) + "\n")

        self._update_preferences(signals)

    def _extract_signals(self, message: str, response: str, rating: str) -> dict:
        """提取偏好信号"""
        signals = {
            "timestamp": datetime.now().isoformat()[:19],
            "message_length": len(message),
            "response_length": len(response),
        }

        # 语气信号
        if any(kw in message for kw in ["简单", "简短", "一句话", "快速"]):
            signals["length_signal"] = "short"
        if any(kw in message for kw in ["详细", "深度", "全面", "完整"]):
            signals["length_signal"] = "long"
        if any(kw in message for kw in ["表格", "对比", "对照"]):
            signals["format_signal"] = "table"
        if any(kw in message for kw in ["口语", "随意", "轻松"]):
            signals["tone_signal"] = "casual"
        if any(kw in message for kw in ["专业", "正式", "严谨"]):
            signals["tone_signal"] = "professional"

        # 平台信号
        for plat in ["小红书", "抖音", "公众号", "视频号"]:
            if plat in message:
                signals["platform_signal"] = {
                    "小红书": "xiaohongshu", "抖音": "douyin",
                    "公众号": "wechat_mp", "视频号": "shipinhao",
                }.get(plat, "")
                break

        # 显式反馈
        if rating:
            signals["explicit_rating"] = rating  # good/bad/neutral

        # 隐式反馈
        if any(kw in message for kw in ["不对", "错了", "重来", "不是这样"]):
            signals["implicit_correction"] = True

        return signals

    def _update_preferences(self, signals: dict):
        """更新偏好权重"""
        prefs = json.loads(self.pref_file.read_text(encoding="utf-8"))

        # 学习率: 每次信号权重0.1
        lr = 0.1

        if "length_signal" in signals:
            target = signals["length_signal"]
            for k in prefs["length"]:
                prefs["length"][k] *= (1 - lr)
            prefs["length"][target] += lr

        if "tone_signal" in signals:
            target = signals["tone_signal"]
            for k in prefs["tone"]:
                prefs["tone"][k] *= (1 - lr)
            prefs["tone"][target] += lr

        if "format_signal" in signals:
            target = signals["format_signal"]
            for k in prefs["format"]:
                prefs["format"][k] *= (1 - lr)
            prefs["format"][target] += lr

        if "platform_signal" in signals:
            target = signals["platform_signal"]
            for k in prefs["platform_focus"]:
                prefs["platform_focus"][k] *= (1 - lr)
            prefs["platform_focus"][target] += lr

        # 重新归一化
        for dim in ["tone", "length", "format", "depth", "decision_style", "platform_focus"]:
            total = sum(prefs[dim].values())
            if total > 0:
                prefs[dim] = {k: round(v / total, 3) for k, v in prefs[dim].items()}

        prefs["last_updated"] = datetime.now().isoformat()[:19]
        self.pref_file.write_text(json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_profile(self) -> dict:
        """获取当前偏好画像"""
        prefs = json.loads(self.pref_file.read_text(encoding="utf-8"))

        # 找每个维度的最强偏好
        profile = {}
        for dim in ["tone", "length", "format", "depth"]:
            best = max(prefs[dim].items(), key=lambda x: x[1])
            profile[dim] = best[0]

        best_plat = max(prefs["platform_focus"].items(), key=lambda x: x[1])
        profile["primary_platform"] = best_plat[0]

        profile["confidence"] = {
            k: "high" if v[1] > 0.5 else ("medium" if v[1] > 0.35 else "low")
            for k, v in [
                ("tone", max(prefs["tone"].items(), key=lambda x: x[1])),
                ("length", max(prefs["length"].items(), key=lambda x: x[1])),
            ]
        }

        return {"ok": True, "profile": profile, "raw": prefs}

    def get_style_context(self) -> str:
        """生成风格上下文(注入到AI prompt)"""
        profile = self.get_profile()["profile"]
        rules = json.loads(self.pref_file.read_text(encoding="utf-8")).get("learned_rules", [])

        ctx = f"""【用户偏好】
语气: {profile.get('tone', 'professional')}
篇幅: {profile.get('length', 'medium')}  
格式: {profile.get('format', 'list')}
主要平台: {profile.get('primary_platform', 'xiaohongshu')}
"""

        if rules:
            ctx += "\n【已学习规则】\n" + "\n".join(f"- {r}" for r in rules[-5:])

        return ctx


# ═══════════════════════════════════
# 二、纠错记忆系统
# ═══════════════════════════════════

class CorrectionMemory:
    """
    纠错记忆: 记住每次被纠正的内容，不再重复犯错

    存储: 纠正内容→修正方向→上下文
    """

    def __init__(self, tenant_id: str = "zq-5bb59623"):
        self.tid = tenant_id
        self.correction_file = LEARN_DIR / f"corrections_{tenant_id}.jsonl"
        self.rules_file = LEARN_DIR / f"correction_rules_{tenant_id}.json"

    def record_correction(self, original: str, corrected: str, context: str = "", category: str = "content"):
        """记录一次纠正"""
        entry = {
            "timestamp": datetime.now().isoformat()[:19],
            "category": category,
            "original": original[:500],
            "corrected": corrected[:500],
            "context": context[:200],
        }
        with open(self.correction_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # 如果是模式纠正，提取规则
        if len(original) < 100:  # 简短纠正通常是模式
            self._extract_rule(entry)

    def _extract_rule(self, entry: dict):
        """从纠正中提取规则"""
        rules = {}
        if self.rules_file.exists():
            rules = json.loads(self.rules_file.read_text(encoding="utf-8"))

        rule_id = f"rule-{hashlib.md5(entry['original'].encode()).hexdigest()[:8]}"
        rules[rule_id] = {
            "pattern": entry["original"],
            "correction": entry["corrected"],
            "category": entry["category"],
            "times_corrected": rules.get(rule_id, {}).get("times_corrected", 0) + 1,
            "last_corrected": entry["timestamp"],
        }
        self.rules_file.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

    def check_and_correct(self, content: str, category: str = "content") -> dict:
        """检查内容是否需要纠正"""
        rules = {}
        if self.rules_file.exists():
            rules = json.loads(self.rules_file.read_text(encoding="utf-8"))

        corrections_applied = []
        corrected_content = content

        for rid, rule in rules.items():
            if rule["category"] != category:
                continue
            if rule.get("times_corrected", 0) >= 2 and rule["pattern"] in corrected_content:
                corrected_content = corrected_content.replace(rule["pattern"], rule["correction"])
                corrections_applied.append(rule["pattern"])

        return {
            "corrected": corrected_content != content,
            "content": corrected_content,
            "corrections": corrections_applied,
        }

    def get_correction_stats(self) -> dict:
        """纠正统计"""
        rules = {}
        if self.rules_file.exists():
            rules = json.loads(self.rules_file.read_text(encoding="utf-8"))

        return {
            "ok": True,
            "total_rules": len(rules),
            "frequent_corrections": [
                {"pattern": r["pattern"], "times": r["times_corrected"]}
                for r in sorted(rules.values(), key=lambda x: x["times_corrected"], reverse=True)[:10]
                if r["times_corrected"] >= 2
            ],
        }


# ═══════════════════════════════════
# 三、内容风格适配器
# ═══════════════════════════════════

class StyleAdapter:
    """
    风格适配: 学习你的写作风格并自动应用

    学习:
    - 标题风格: 数字型/悬念型/直白型
    - 开头方式: 痛点切入/数据冲击/故事引入
    - 结尾方式: CTA/总结/金句
    - emoji使用频率
    - 段落长度偏好
    """

    def __init__(self, tenant_id: str = "zq-5bb59623"):
        self.tid = tenant_id
        self.style_file = LEARN_DIR / f"style_{tenant_id}.json"

    def analyze_style(self, text: str) -> dict:
        """分析一段文本的写作风格"""
        style = {
            "has_emoji": bool(re.search(r'[\U0001F300-\U0001F9FF]', text)),
            "has_numbers": bool(re.search(r'\d+', text)),
            "avg_paragraph_length": round(len(text) / max(len(text.split('\n\n')), 1)),
            "starts_with_hook": any(kw in text[:100] for kw in ["?", "！", "震惊", "竟然", "注意"]),
            "ends_with_cta": any(kw in text[-100:] for kw in ["关注", "私信", "联系", "咨询", "领取"]),
        }

        # 标题风格
        first_line = text.split('\n')[0]
        if re.search(r'\d+', first_line):
            style["title_style"] = "data_driven"
        elif "?" in first_line or "？" in first_line:
            style["title_style"] = "question"
        else:
            style["title_style"] = "descriptive"

        return style

    def learn_style(self, text: str, approved: bool = True):
        """学习一段被认可的文本风格"""
        style = self.analyze_style(text)

        data = {"patterns": {}}
        if self.style_file.exists():
            data = json.loads(self.style_file.read_text(encoding="utf-8"))

        for key, value in style.items():
            if isinstance(value, bool) or isinstance(value, str):
                if key not in data["patterns"]:
                    data["patterns"][key] = {}
                key_str = str(value)
                data["patterns"][key][key_str] = data["patterns"][key].get(key_str, 0) + (1 if approved else -0.1)

        data["samples_learned"] = data.get("samples_learned", 0) + 1
        data["last_updated"] = datetime.now().isoformat()[:19]
        self.style_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_style_guide(self) -> dict:
        """获取学习到的风格指南"""
        data = {"patterns": {}}
        if self.style_file.exists():
            data = json.loads(self.style_file.read_text(encoding="utf-8"))

        guide = {"samples": data.get("samples_learned", 0)}

        for key in ["title_style", "has_emoji"]:
            if key in data.get("patterns", {}):
                best = max(data["patterns"][key].items(), key=lambda x: x[1])
                guide[key] = best[0]

        guide["style_brief"] = self._generate_style_brief(guide)
        return {"ok": True, "guide": guide}

    def _generate_style_brief(self, guide: dict) -> str:
        rules = []
        if guide.get("title_style") == "data_driven":
            rules.append("标题使用具体数字吸引点击")
        if guide.get("has_emoji") == "True":
            rules.append("适当使用emoji增加亲和力")
        if guide.get("samples", 0) < 3:
            rules.append("(样本不足，继续学习...)")
        return " | ".join(rules) if rules else "学习中..."


# ═══════════════════════════════════
# 四、演化规则生成器
# ═══════════════════════════════════

class EvolutionEngine:
    """
    演化引擎: 从反馈中自动生成行为规则

    类似于你之前建立的 extracted_rules 系统，
    但这里是自动化的——从交互中提取、验证、升级
    """

    def __init__(self, tenant_id: str = "zq-5bb59623"):
        self.tid = tenant_id
        self.rules_file = LEARN_DIR / f"evolved_rules_{tenant_id}.json"

    def propose_rule(self, trigger: str, action: str, evidence: str = "") -> dict:
        """提出一条演化规则"""
        rules = []
        if self.rules_file.exists():
            rules = json.loads(self.rules_file.read_text(encoding="utf-8"))

        rule = {
            "id": f"evo-{len(rules)+1:04d}",
            "trigger": trigger,
            "action": action,
            "evidence": evidence,
            "status": "proposed",     # proposed → verified → active → retired
            "confidence": 0.5,
            "applied_count": 0,
            "success_count": 0,
            "created_at": datetime.now().isoformat()[:19],
        }
        rules.append(rule)
        self.rules_file.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "rule": rule}

    def verify_rule(self, rule_id: str, success: bool) -> dict:
        """验证规则是否有效"""
        rules = json.loads(self.rules_file.read_text(encoding="utf-8"))
        for r in rules:
            if r["id"] == rule_id:
                r["applied_count"] += 1
                if success:
                    r["success_count"] += 1
                r["confidence"] = r["success_count"] / max(r["applied_count"], 1)

                if r["confidence"] >= 0.8 and r["applied_count"] >= 3:
                    r["status"] = "verified"
                elif r["confidence"] >= 0.9 and r["applied_count"] >= 5:
                    r["status"] = "active"
                elif r["confidence"] < 0.3 and r["applied_count"] >= 5:
                    r["status"] = "retired"

                self.rules_file.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"ok": True, "rule": r}
        return {"ok": False, "error": "规则不存在"}

    def get_active_rules(self) -> List[Dict]:
        """获取活跃规则"""
        if not self.rules_file.exists():
            return []
        rules = json.loads(self.rules_file.read_text(encoding="utf-8"))
        return [r for r in rules if r["status"] in ("verified", "active")]

    def get_rules_context(self) -> str:
        """生成规则上下文（注入 prompt）"""
        active = self.get_active_rules()
        if not active:
            return ""

        lines = ["\n【演化规则 - 这是从你的反馈中学到的】"]
        for r in sorted(active, key=lambda x: x["confidence"], reverse=True)[:10]:
            lines.append(f"- 当{r['trigger']}时 → {r['action']} (置信度: {r['confidence']:.0%})")
        return "\n".join(lines)


# ═══════════════════════════════════
# 五、学习仪表盘
# ═══════════════════════════════════

def learning_dashboard(tenant_id: str = "zq-5bb59623") -> dict:
    """学习系统总览"""
    learner = PreferenceLearner(tenant_id)
    corrector = CorrectionMemory(tenant_id)
    styler = StyleAdapter(tenant_id)
    evolver = EvolutionEngine(tenant_id)

    profile = learner.get_profile()
    corrections = corrector.get_correction_stats()
    style = styler.get_style_guide()
    rules = evolver.get_active_rules()

    return {
        "ok": True,
        "timestamp": datetime.now().isoformat()[:19],
        "preferences": {
            "tone": profile["profile"].get("tone"),
            "length": profile["profile"].get("length"),
            "format": profile["profile"].get("format"),
            "confidence": profile["profile"].get("confidence", {}),
        },
        "style_learned": {
            "samples": style["guide"].get("samples", 0),
            "guide": style["guide"].get("style_brief", ""),
        },
        "corrections": {
            "total_rules": corrections["total_rules"],
            "top_corrections": corrections.get("frequent_corrections", [])[:3],
        },
        "evolved_rules": {
            "active": len(rules),
            "rules": [{"trigger": r["trigger"], "action": r["action"], "confidence": r["confidence"]} for r in rules[:5]],
        },
    }


# ═══════════════════════════════════
# 六、学习闭环函数
# ═══════════════════════════════════

def feedback_loop(
    message: str,
    response: str,
    rating: str = None,
    correction: str = None,
) -> dict:
    """
    完整学习闭环

    每次AI输出后调用此函数完成:
    1. 学习偏好信号
    2. 记录风格
    3. 处理纠正
    4. 更新演化规则
    """
    learner = PreferenceLearner()
    corrector = CorrectionMemory()
    styler = StyleAdapter()
    evolver = EvolutionEngine()

    actions = []

    # 1. 偏好学习
    learner.learn_from_interaction(message, response, rating)
    actions.append("preferences_updated")

    # 2. 风格学习
    if rating == "good":
        styler.learn_style(response, approved=True)
        actions.append("style_learned_positive")

    # 3. 纠正处理
    if correction:
        corrector.record_correction(response, correction, message)
        actions.append("correction_recorded")

        # 提取演化规则
        if len(correction) < 200:
            evolver.propose_rule(
                f"用户纠正内容",
                f"按照: {correction[:100]}",
                f"原始内容: {response[:100]}",
            )
            actions.append("evolution_rule_proposed")

    # 4. 更新已知规则
    for rule in evolver.get_active_rules():
        if rule["trigger"] in message:
            evolver.verify_rule(rule["id"], True)

    return {
        "ok": True,
        "actions": actions,
        "profile_snapshot": learner.get_profile()["profile"],
    }


# ═══════════════════════════════════
# CLI
# ═══════════════════════════════════

if __name__ == "__main__":
    # 学习测试
    learner = PreferenceLearner()

    # 模拟用户交互
    learner.learn_from_interaction(
        "帮我写一篇深度分析，用表格对比",
        "这是深度分析...",
        "good",
    )

    profile = learner.get_profile()
    print(f"偏好: tone={profile['profile']['tone']} length={profile['profile']['length']}")

    # 纠正测试
    corrector = CorrectionMemory()
    corrector.record_correction("不要用'赋能'这种词", "用'帮助'代替", "内容写作", "style")
    stats = corrector.get_correction_stats()
    print(f"纠正规则: {stats['total_rules']}条")

    # 演化规则
    evolver = EvolutionEngine()
    evolver.propose_rule("要对比筷子科技", "先做功能矩阵，再做差异化分析", "竞品分析模式")
    print(f"活跃规则: {len(evolver.get_active_rules())}条")

    # 学习仪表盘
    dash = learning_dashboard()
    print(f"\n学习仪表盘:")
    print(f"  偏好置信度: {dash['preferences']['confidence']}")
    print(f"  风格样本: {dash['style_learned']['samples']}")
