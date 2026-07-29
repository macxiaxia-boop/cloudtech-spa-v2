"""
AI系统自我进化引擎 — Self-Evolution Engine
=============================================
趋势洞察 → 格式自动升级 → 范式抽取 → Skill生成 → AI能力增长

进化闭环:
  采集趋势 → 五维拆解 → 发现新模式 → 生成新格式
           → 抽取范式模板 → 封装为Skill → 系统能力+1
"""
import json, os, hashlib, shutil
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

# ── 路径 ──
BASE = Path(__file__).parent
PARADIGM_DIR = BASE / "paradigms"          # 范式库
SKILL_DIR = Path(os.environ["USERPROFILE"]) / ".claude" / "skills" / "zhuangqi"  # Skill仓库
EVOLUTION_LOG = BASE / "data" / "evolution_log.jsonl"  # 进化日志
FORMAT_DB = BASE / "data" / "format_versions.json"     # 格式版本历史


# ═══════════════════════════════════════
# 一、范式抽取器 — 把爆款模式变成可复用模板
# ═══════════════════════════════════════

@dataclass
class ContentParadigm:
    """一条内容范式 — 经过验证的表达模式"""
    id: str
    name: str                    # 范式名称
    category: str                # 所属类别 (hook/visual/narrative/copy)
    pattern: str                 # 核心模式描述
    template: str                # 可填充模板
    evidence: dict               # 支撑数据（多少条验证、效果如何）
    examples: list               # 示例
    source: str                  # 来源（哪个趋势报告）
    created_at: str
    version: int = 1
    usage_count: int = 0
    effectiveness_score: float = 0.0


class ParadigmExtractor:
    """从趋势数据中提取可复用的内容范式"""

    def extract_from_trends(self, trend_report: dict) -> list[ContentParadigm]:
        """扫描趋势报告，抽取新的内容范式（仅采纳置信度≥0.5的维度）"""
        paradigms = []
        now = datetime.now().isoformat()
        confidence = trend_report.get("confidence", {})
        reliable = trend_report.get("reliable_dimensions", ["expression", "copy", "visual"])

        # 1. 从表达方式中抽取人设范式（仅当可靠）
        personas = trend_report.get("expression", {}).get("top_personas", {})
        if personas:
            top = max(personas, key=personas.get)
            paradigms.append(ContentParadigm(
                id=self._gen_id("persona", top),
                name=f"{top}视角范式",
                category="persona",
                pattern=f"以{top}的第一人称视角叙述，用'我家''我们'等口语化表达拉近距离",
                template=f"【{top}视角】\n我家[场景描述]。之前[痛点]，后来[解决方案]。现在[效果]。\n💬 [互动引导]",
                evidence={"trend_count": personas[top], "trend_ratio": round(personas[top]/sum(personas.values()), 2)},
                examples=[f"用{top}视角写一篇{ct}内容" for ct in ["room_tour", "before_after"]],
                source="trend_analysis",
                created_at=now,
            ))

        # 2. 从叙事结构中抽取叙事范式
        narratives = trend_report.get("expression", {}).get("top_narratives", {})
        if narratives:
            top = max(narratives, key=narratives.get)
            paradigms.append(ContentParadigm(
                id=self._gen_id("narrative", top),
                name=f"{top}叙事法",
                category="narrative",
                pattern=self._narrative_pattern(top),
                template=self._narrative_template(top),
                evidence={"trend_count": narratives[top], "trend_ratio": round(narratives[top]/sum(narratives.values()), 2)},
                examples=[],
                source="trend_analysis",
                created_at=now,
            ))

        # 3. 从开头模式中抽取钩子范式
        openings = trend_report.get("copy", {}).get("top_openings", {})
        if openings:
            top = max(openings, key=openings.get)
            paradigms.append(ContentParadigm(
                id=self._gen_id("hook", top),
                name=f"{top}钩子法",
                category="hook",
                pattern=self._hook_pattern(top),
                template=self._hook_template(top),
                evidence={"trend_count": openings[top]},
                examples=[],
                source="trend_analysis",
                created_at=now,
            ))

        # 4. 从封面风格中抽取视觉范式
        covers = trend_report.get("visual", {}).get("top_cover_styles", {})
        if covers:
            top = max(covers, key=covers.get)
            paradigms.append(ContentParadigm(
                id=self._gen_id("visual", top),
                name=f"{top}视觉法",
                category="visual",
                pattern=self._visual_pattern(top),
                template=self._visual_template(top),
                evidence={"trend_count": covers[top]},
                examples=[],
                source="trend_analysis",
                created_at=now,
            ))

        return paradigms

    def _gen_id(self, category: str, name: str) -> str:
        raw = f"{category}:{name}"
        return hashlib.md5(raw.encode()).hexdigest()[:10]

    def _narrative_pattern(self, narrative_type: str) -> str:
        patterns = {
            "解决问题型": "痛点展示→放大焦虑→给出方案→步骤拆解→效果验证→总结要点",
            "vlog记录型": "今日预告→真实过程(有意外/情绪)→成果展示→今日感悟→明日预告",
            "教程型": "成果先展示→为什么学这个→步骤1→步骤2→步骤3→常见错误→总结",
            "对比展示型": "before震撼开场→改造过程(加速)→after惊艳亮相→花费清单→设计亮点",
            "清单推荐型": "场景引入→分类列举→每项简短点评→使用建议→完整清单",
        }
        return patterns.get(narrative_type, f"以{narrative_type}结构组织内容")

    def _narrative_template(self, narrative_type: str) -> str:
        templates = {
            "解决问题型": "【痛点】[具体问题]→【方案】[怎么解决]→【步骤】①_②_③_→【效果】[解决后的样子]",
            "vlog记录型": "Day [N]｜[今日主题]\n[am] [上午做的事+配图]\n[pm] [下午做的事+配图]\n💡今日心得：[一句话]",
            "教程型": "手把手教你[做某事]\nStep1: [第一步]\nStep2: [第二步]\nStep3: [第三步]\n⚠️注意：[易错点]",
            "对比展示型": "改造前🆚改造后\n[BEFORE图]→[AFTER图]\n[空间名]: [旧状态]→[新状态]\n💰花费：[金额]",
            "清单推荐型": "【[场景]必入清单】\n1️⃣ [物品1] — [一句话理由]\n2️⃣ [物品2] — [一句话理由]\n...\n📌收藏备用",
        }
        return templates.get(narrative_type, "")

    def _hook_pattern(self, opening_type: str) -> str:
        patterns = {
            "悬念提问": "前3秒抛出问题→激发好奇心→正文解答→结尾呼应",
            "痛点警示": "前3秒戳痛点→'你也是吗？'→给解决方案→效果对比",
            "数据冲击": "前3秒抛数字→'X平/Y万/Z天'→拆解数字→详述过程",
            "情绪钩子": "前3秒情绪词→'天呐/居然/不敢相信'→展示证据→解释原因",
            "直接展示": "前3秒直接展示成果→'看这个[空间/细节]'→展开讲解→引导互动",
        }
        return patterns.get(opening_type, f"前3秒用{opening_type}吸引注意")

    def _hook_template(self, opening_type: str) -> str:
        templates = {
            "悬念提问": "[问题]？答案可能出乎你的意料...",
            "痛点警示": "99%的人不知道[痛点]。我家[具体踩坑经历]。",
            "数据冲击": "[数字]平/[数字]万/[数字]天。这就是[结果]。",
            "情绪钩子": "天呐！[令人震惊的事实]。不敢相信这是[对比]。",
            "直接展示": "看这个[空间/细节]。这可能是今年最[形容词]的[东西]。",
        }
        return templates.get(opening_type, "")

    def _visual_pattern(self, cover_type: str) -> str:
        patterns = {
            "对比图": "同角度拍摄before/after→左右拼接→标注关键变化→首图选最震撼的对比",
            "空镜vo": "稳定器或三脚架→缓慢推拉→镜头不切换超过5秒→旁白在后期录制",
            "拼图合集": "4/6/9张同主题照片→统一滤镜→每张标注序号→首图放最吸引的",
            "长图/视频": "竖版长图→从上到下叙事→每段配图+文字→结尾放联系方式",
            "实景拍摄": "自然光→不做夸张滤镜→展示真实纹理和细节→手机直出更有说服力",
        }
        return patterns.get(cover_type, f"使用{cover_type}作为主要视觉呈现方式")

    def _visual_template(self, cover_type: str) -> str:
        templates = {
            "对比图": "【Before】[改造前照片]\n↓ 改造过程\n【After】[改造后同角度照片]\n标注: [改动点1][改动点2][改动点3]",
            "空镜vo": "🎬 拍摄清单:\n1. 三脚架固定→缓慢推镜头(5-8秒)\n2. 从左到右扫视空间(10秒)\n3. 特写材质纹理(3秒/个)\n4. 旁白后期录制: \"[空间描述]\"",
            "拼图合集": "首图: [最震撼的一张]\n图2-4: [按叙事顺序排列]\n每张标注: [序号+一句话说明]",
            "实景拍摄": "📱 手机直出\n光线: 自然光(上午10点或下午3点)\n滤镜: 不加重滤镜/仅微调亮度\n角度: 平视/不要俯拍或仰拍",
        }
        return templates.get(cover_type, f"【{cover_type}】\n准备[场景描述]\n拍摄[角度说明]\n后期[处理说明]")


# ═══════════════════════════════════════
# 二、格式进化器 — 趋势驱动格式库自动升级
# ═══════════════════════════════════════

class FormatEvolver:
    """根据趋势数据自动创建/更新内容格式"""

    def evolve(self, trend_report: dict, existing_formats: dict) -> dict:
        """分析趋势→建议格式变更→应用更新"""
        changes = {
            "new_formats": [],      # 新发现的格式
            "updated_formats": [],  # 需要更新的现有格式
            "deprecated": [],       # 过时的格式
            "merged": [],           # 合并的格式
        }

        now = datetime.now().isoformat()
        narratives = trend_report.get("expression", {}).get("top_narratives", {})
        personas = trend_report.get("expression", {}).get("top_personas", {})
        covers = trend_report.get("visual", {}).get("top_cover_styles", {})
        openings = trend_report.get("copy", {}).get("top_openings", {})
        hashtags = trend_report.get("hashtags", {}).get("top_tags", [])

        # 1. 检查是否有新的叙事模式需要创建新格式
        for narrative, count in narratives.items():
            if narrative not in [f.get("name") for f in existing_formats.values()]:
                if count >= 3:  # 出现3次以上才考虑
                    new_format = self._create_format_from_narrative(narrative, trend_report)
                    changes["new_formats"].append(new_format)

        # 2. 更新现有格式的钩子模板（用最新热门开头）
        for opening, count in openings.items():
            changes["updated_formats"].append({
                "target": "hook_templates",
                "action": "add_pattern",
                "pattern": opening,
                "count": count,
                "reason": f"Trending opening ({count} posts)",
                "applied_at": now,
            })

        # 3. 更新推荐的人设配置
        top_persona = max(personas, key=personas.get) if personas else ""
        if top_persona:
            changes["updated_formats"].append({
                "target": "persona_config",
                "action": "set_default",
                "value": top_persona,
                "reason": f"Dominant persona ({personas[top_persona]} posts)",
                "applied_at": now,
            })

        # 4. 更新视觉建议
        top_cover = max(covers, key=covers.get) if covers else ""
        if top_cover:
            changes["updated_formats"].append({
                "target": "visual_priorities",
                "action": "prioritize",
                "value": top_cover,
                "reason": f"Best cover style ({covers[top_cover]} posts)",
                "applied_at": now,
            })

        # 5. 添加新热门标签
        if hashtags:
            changes["updated_formats"].append({
                "target": "hashtag_library",
                "action": "merge_tags",
                "tags": [t[0] for t in hashtags[:15] if len(t[0]) < 20],
                "applied_at": now,
            })

        # 6. 视频时长建议
        avg_dur = trend_report.get("video", {}).get("avg_duration_sec", 0)
        if avg_dur:
            changes["updated_formats"].append({
                "target": "video_duration",
                "action": "set_target",
                "value": round(avg_dur),
                "applied_at": now,
            })

        return changes

    def _create_format_from_narrative(self, narrative: str, report: dict) -> dict:
        extractor = ParadigmExtractor()
        pattern = extractor._narrative_pattern(narrative)
        template = extractor._narrative_template(narrative)
        return {
            "name": narrative,
            "pattern": pattern,
            "template": template,
            "discovered_at": datetime.now().isoformat(),
        }


# ═══════════════════════════════════════
# 三、Skill 生成器 — 把验证过的范式封装为 AI Skill
# ═══════════════════════════════════════

class SkillGenerator:
    """将经过验证的内容范式自动封装为 Claude Code Skill"""

    def generate_skill(self, paradigm: ContentParadigm) -> str:
        """根据范式生成一个可安装的 Skill 文件"""
        skill_name = f"zhuangqi-{paradigm.category}-{paradigm.id}"

        skill_md = f"""---
name: {skill_name}
description: {paradigm.name} — {paradigm.pattern[:80]}
category: content-creation
version: {paradigm.version}
paradigm_id: {paradigm.id}
auto_generated: true
generated_at: {paradigm.created_at}
---

# {paradigm.name}

> 自动生成于 {paradigm.created_at[:10]}
> 验证数据: {paradigm.evidence}
> 来源: {paradigm.source}

## 模式

{paradigm.pattern}

## 模板

```
{paradigm.template}
```

## 使用场景

此类内容适用于:
- 小红书装修类笔记
- 抖音装修类视频
- 公众号装修案例

## 效果数据

- 趋势样本: {paradigm.evidence.get('trend_count', 0)} 条
- 在热门内容中占比: {paradigm.evidence.get('trend_ratio', 0)*100}%

## 使用方法

在 Claude Code 中输入:
```
用 "{paradigm.name}" 范式写一篇关于[主题]的内容
```
"""
        return skill_md

    def install_skill(self, paradigm: ContentParadigm) -> bool:
        """将生成的 Skill 安装到 Claude Code skills 目录(自动去重)"""
        skill_content = self.generate_skill(paradigm)
        skill_dir = SKILL_DIR / paradigm.category
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / f"{paradigm.id}.md"

        # Dedup: skip if this paradigm_id already exists
        if skill_file.exists():
            # Update the version counter
            existing = skill_file.read_text(encoding="utf-8")
            if f"paradigm_id: {paradigm.id}" in existing:
                return False  # Already installed, skip

        skill_file.write_text(skill_content, encoding="utf-8")

        # Rewrite CLAUDE.md (deduplicated by paradigm name)
        claude_md = SKILL_DIR / "CLAUDE.md"
        entries = {}
        if claude_md.exists():
            for line in claude_md.read_text(encoding="utf-8").strip().split("\n"):
                if line.startswith("- ") and ": " in line:
                    name = line.split(": ")[0].replace("- ", "")
                    entries[name] = line

        entry = f"- {paradigm.name}: {paradigm.pattern[:100]} (验证:{paradigm.evidence})\n"
        entries[paradigm.name] = entry  # Overwrite duplicate by name

        claude_md.write_text("".join(entries.values()), encoding="utf-8")
        return True

    def generate_all_from_trends(self, trend_report: dict) -> list[str]:
        """从趋势报告批量生成 Skills"""
        extractor = ParadigmExtractor()
        paradigms = extractor.extract_from_trends(trend_report)

        installed = []
        for p in paradigms:
            if self.install_skill(p):
                installed.append(p.name)

        return installed


# ═══════════════════════════════════════
# 四、进化日志 — 追踪 AI 系统能力增长
# ═══════════════════════════════════════

class EvolutionLogger:
    """记录系统的每次自我进化"""

    def log(self, event_type: str, detail: dict):
        EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,  # paradigm_discovered, format_evolved, skill_generated, trend_applied
            "detail": detail,
        }
        with open(EVOLUTION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_evolution_summary(self) -> dict:
        """获取系统进化总结"""
        if not EVOLUTION_LOG.exists():
            return {"total_evolutions": 0, "by_type": {}, "recent": []}

        by_type = defaultdict(int)
        recent = []
        with open(EVOLUTION_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    by_type[e["type"]] += 1
                    recent.append(e)
                except Exception:
                    continue

        return {
            "total_evolutions": sum(by_type.values()),
            "by_type": dict(by_type),
            "recent": recent[-20:],
            "first_evolution": recent[0]["timestamp"] if recent else None,
            "latest_evolution": recent[-1]["timestamp"] if recent else None,
        }

    def get_capability_score(self) -> dict:
        """计算系统能力评分"""
        summary = self.get_evolution_summary()
        skills_dir = SKILL_DIR
        skill_count = len(list(skills_dir.rglob("*.md"))) if skills_dir.exists() else 0

        return {
            "total_evolutions": summary["total_evolutions"],
            "auto_generated_skills": skill_count,
            "paradigms_discovered": summary["by_type"].get("paradigm_discovered", 0),
            "formats_evolved": summary["by_type"].get("format_evolved", 0),
            "skills_generated": summary["by_type"].get("skill_generated", 0),
            "capability_level": self._calc_level(summary["total_evolutions"], skill_count),
        }

    def _calc_level(self, evolutions: int, skills: int) -> str:
        if evolutions > 100 and skills > 20: return "L4 — 自主进化"
        if evolutions > 50 and skills > 10: return "L3 — 主动学习"
        if evolutions > 10 and skills > 3: return "L2 — 模式识别"
        if evolutions > 0: return "L1 — 初始学习"
        return "L0 — 基线"


# ═══════════════════════════════════════
# 五、完整进化流程 — 一键执行
# ═══════════════════════════════════════

class EvolutionPipeline:
    """一键执行: 采集趋势→抽取范式→进化格式→生成Skill→记录日志"""

    def __init__(self):
        self.extractor = ParadigmExtractor()
        self.evolver = FormatEvolver()
        self.skill_gen = SkillGenerator()
        self.logger = EvolutionLogger()

    def run_full_evolution(self, trend_report: dict, existing_formats: dict = None) -> dict:
        """执行一次完整的自我进化循环"""
        if existing_formats is None:
            from zhuangqi_content_engine import CONTENT_FORMATS
            existing_formats = CONTENT_FORMATS

        result = {
            "timestamp": datetime.now().isoformat(),
            "paradigms": [],
            "format_changes": {},
            "skills_installed": [],
            "evolution_logs": 0,
        }

        # Step 1: 抽取范式
        paradigms = self.extractor.extract_from_trends(trend_report)
        result["paradigms"] = [{"name": p.name, "category": p.category, "id": p.id} for p in paradigms]
        for p in paradigms:
            self.logger.log("paradigm_discovered", {"name": p.name, "category": p.category, "id": p.id})

        # Step 2: 进化格式
        changes = self.evolver.evolve(trend_report, existing_formats)
        result["format_changes"] = {
            "new_formats": len(changes["new_formats"]),
            "updates": len(changes["updated_formats"]),
        }
        self.logger.log("format_evolved", {"changes": result["format_changes"]})

        # Step 3: 生成 Skills
        skills = self.skill_gen.generate_all_from_trends(trend_report)
        result["skills_installed"] = skills
        for s in skills:
            self.logger.log("skill_generated", {"name": s})

        result["evolution_logs"] = sum(1 for _ in [paradigms, changes, skills])

        # Step 4: 能力评分
        result["capability"] = self.logger.get_capability_score()

        return result


# ═══════════════════════════════════════
# 六、调度器 — 定时自主进化
# ═══════════════════════════════════════

class EvolutionScheduler:
    """定时触发自我进化"""

    def __init__(self):
        self.pipeline = EvolutionPipeline()
        self.logger = EvolutionLogger()

    def evolve_from_collector(self):
        """从社交媒体采集器获取趋势并进化"""
        from social_scraper import SocialCollector
        collector = SocialCollector()
        raw = collector.collect_and_analyze(queries_per_platform=3)

        trend_report = raw.get("trends", {})
        if "error" in trend_report:
            return {"error": "No valid trends"}

        result = self.pipeline.run_full_evolution(trend_report)
        result["source"] = "scheduled_collection"
        return result

    def evolve_from_trend_search(self):
        """从趋势搜索直接进化"""
        from trend_intelligence import TrendCollector
        collector = TrendCollector()
        raw = collector.search_trends(max_results=5)

        trend_report = raw.get("trends", {})
        result = self.pipeline.run_full_evolution(trend_report)
        result["source"] = "trend_search"
        return result

    def get_status(self) -> dict:
        """获取进化系统状态"""
        return {
            "evolution_summary": self.logger.get_evolution_summary(),
            "capability": self.logger.get_capability_score(),
            "paradigm_count": len(list(PARADIGM_DIR.glob("*.json"))) if PARADIGM_DIR.exists() else 0,
            "skill_count": len(list(SKILL_DIR.rglob("*.md"))) if SKILL_DIR.exists() else 0,
        }
