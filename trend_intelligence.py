"""
装企趋势情报引擎 — Trend Intelligence Engine
================================================
实时采集→五维拆解→反哺内容引擎→趋势仪表盘

采集维度:
  1. #话题标签 — 什么标签在涨、怎么组合
  2. 表达方式 — 口吻/人设/叙事结构
  3. 图文呈现 — 构图/配色/排版/首图模式
  4. 视频节奏 — 时长/转场/钩子时机/BGM
  5. 文案结构 — 开头模式/信息密度/互动引导
"""
import json, os, time, hashlib, re
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from collections import Counter

# ═══════════════════════════════════════
# 数据存储
# ═══════════════════════════════════════
TREND_DB = Path(__file__).parent / "data" / "trends.jsonl"
INSIGHT_DB = Path(__file__).parent / "data" / "insights.json"

# ═══════════════════════════════════════
# 一、五维拆解模型
# ═══════════════════════════════════════

@dataclass
class ContentAnalysis:
    """一条内容的五维拆解结果"""
    url: str
    platform: str
    title: str

    # 维度1: 话题标签
    hashtags: list = field(default_factory=list)
    hashtag_strategy: str = ""  # 大词+小词 / 长尾堆叠 / 蹭热点

    # 维度2: 表达方式
    persona: str = ""           # 设计师/业主/工头/买手/测评
    tone: str = ""              # 专业/亲切/震惊/幽默/吐槽
    narrative: str = ""         # 解决问题型/vlog记录型/教程型/对比展示型

    # 维度3: 图文呈现
    cover_style: str = ""       # 对比图/效果图/实景/九宫格/细节特写
    color_scheme: str = ""      # 暖色/冷色/高饱和/低饱和/黑白
    layout_pattern: str = ""    # 拼图/单图/长图/卡片式/轮播

    # 维度4: 视频节奏
    duration_sec: int = 0
    hook_timing_sec: float = 0  # 钩子出现在第几秒
    bpm_style: str = ""         # 快节奏/舒缓/vlog/卡点
    transition_style: str = ""  # 硬切/叠化/推拉/旋转

    # 维度5: 文案结构
    opening_type: str = ""      # 悬念/痛点/数据/反问/直接展示
    copy_length: int = 0
    info_density: str = ""      # 高/中/低
    cta_style: str = ""         # 评论引导/关注引导/私信引导/无引导

    # 元数据
    engagement_estimate: dict = field(default_factory=dict)  # {likes, comments, shares}
    collected_at: str = ""


class TrendAnalyzer:
    """五维趋势分析引擎"""

    def analyze_content(self, raw_data: dict) -> ContentAnalysis:
        """Parse raw content data into structured five-dimension analysis"""
        a = ContentAnalysis(
            url=raw_data.get("url", ""),
            platform=self._detect_platform(raw_data),
            title=raw_data.get("title", ""),
        )

        # 1. Hashtag analysis
        a.hashtags = self._extract_hashtags(raw_data)
        a.hashtag_strategy = self._classify_hashtag_strategy(a.hashtags)

        # 2. Expression analysis
        text = raw_data.get("title", "") + " " + raw_data.get("content", "")
        a.persona = self._detect_persona(text)
        a.tone = self._detect_tone(text)
        a.narrative = self._detect_narrative(text)

        # 3. Visual analysis (from metadata/descriptions)
        a.cover_style = self._infer_cover_style(raw_data)
        a.color_scheme = self._infer_color_scheme(raw_data)
        a.layout_pattern = self._infer_layout(raw_data)

        # 4. Video rhythm (if video data available)
        if raw_data.get("duration"):
            a.duration_sec = int(raw_data.get("duration", 0))
            a.hook_timing_sec = self._estimate_hook_timing(text)
            a.bpm_style = self._infer_bpm(raw_data)
            a.transition_style = self._infer_transitions(raw_data)

        # 5. Copy structure
        a.opening_type = self._classify_opening(text)
        a.copy_length = len(text)
        a.info_density = self._calc_density(text)
        a.cta_style = self._detect_cta(text)

        a.collected_at = datetime.now().isoformat()
        return a

    # ── Detectors ──

    def _detect_platform(self, data: dict) -> str:
        url = data.get("url", "")
        if "xiaohongshu" in url or "xhslink" in url: return "xiaohongshu"
        if "douyin" in url or "iesdouyin" in url: return "douyin"
        if "mp.weixin" in url: return "wechat"
        if "bilibili" in url: return "bilibili"
        return data.get("platform", "unknown")

    def _extract_hashtags(self, data: dict) -> list:
        tags = data.get("hashtags", [])
        if not tags:
            text = data.get("title", "") + " " + data.get("content", "")
            # Only match valid hashtags: short, no newlines, no URLs
            raw = re.findall(r'#([^\s#\n]{1,15})', text)
            raw += re.findall(r'#([^#\n]{1,15})#', text)
            # Clean: remove whitespace, numbers-only, URLs
            cleaned = []
            for t in raw:
                t = t.strip()
                if not t: continue
                if t.isdigit(): continue
                if 'http' in t: continue
                if '\n' in t: continue
                if len(t) < 2: continue
                if len(t) > 15: continue
                cleaned.append(t)
            tags = cleaned
        return list(set(tags))[:20]

    def _classify_hashtag_strategy(self, tags: list) -> str:
        """Classify hashtag strategy used"""
        if len(tags) <= 3: return "精选大词"
        if len(tags) <= 8: return "大词+长尾组合"
        if len(tags) > 8 and any(len(t) > 6 for t in tags): return "长尾堆叠"
        return "蹭热点+品类词"

    _PERSONA_KEYWORDS = {
        "设计师": ["设计", "方案", "落地", "改造", "户型", "动线", "布局"],
        "业主": ["我家", "老公", "装修ing", "终于", "入住", "踩坑"],
        "工头": ["施工", "师傅", "工地", "材料", "工艺", "标准"],
        "测评博主": ["测评", "对比", "推荐", "品牌", "性价比", "排行榜"],
        "生活方式博主": ["vlog", "日常", "治愈", "氛围感", "仪式感"],
    }

    def _detect_persona(self, text: str) -> str:
        scores = {k: sum(1 for kw in v if kw in text) for k, v in self._PERSONA_KEYWORDS.items()}
        return max(scores, key=scores.get) if any(scores.values()) else "业主"

    _TONE_KEYWORDS = {
        "专业": ["数据", "标准", "规范", "工艺", "尺寸", "比例"],
        "亲切": ["～", "呀", "哦", "啦", "吧", "分享", "安利"],
        "震惊": ["天呐", "居然", "震惊", "没想到", "不敢相信", "!"],
        "吐槽": ["避坑", "后悔", "千万别", "太坑了", "无语", "踩雷"],
        "治愈": ["温暖", "阳光", "治愈", "安静", "舒服", "氛围感"],
    }

    def _detect_tone(self, text: str) -> str:
        scores = {k: sum(1 for kw in v if kw in text) for k, v in self._TONE_KEYWORDS.items()}
        return max(scores, key=scores.get) if any(scores.values()) else "亲切"

    _NARRATIVE_KEYWORDS = {
        "解决问题型": ["问题", "方案", "解决", "原来", "方法", "技巧"],
        "vlog记录型": ["今天", "装修第", "Day", "记录", "日常", "vlog"],
        "教程型": ["步骤", "教程", "教学", "怎么", "如何", "攻略"],
        "对比展示型": ["before", "after", "改造前", "改造后", "对比", "差距"],
        "清单推荐型": ["清单", "推荐", "TOP", "必买", "合集", "盘点"],
    }

    def _detect_narrative(self, text: str) -> str:
        scores = {k: sum(1 for kw in v if kw in text) for k, v in self._NARRATIVE_KEYWORDS.items()}
        return max(scores, key=scores.get) if any(scores.values()) else "vlog记录型"

    def _infer_cover_style(self, data: dict) -> str:
        styles = data.get("cover_style", "")
        if not styles:
            text = data.get("title", "") + data.get("content", "")
            if any(w in text for w in ["before", "after", "改造前", "改造后", "对比"]): return "对比图"
            if any(w in text for w in ["效果图", "渲染", "3D"]): return "效果图"
            if any(w in text for w in ["实景", "实拍", "落地"]): return "实景拍摄"
            if any(w in text for w in ["细节", "材质", "纹理", "特写"]): return "细节特写"
            if any(w in text for w in ["roomtour", "漫游", "走进"]): return "空间漫游"
        return styles or "实景拍摄"

    def _infer_color_scheme(self, data: dict) -> str:
        text = data.get("title", "") + data.get("content", "")
        if any(w in text for w in ["奶油", "温暖", "原木", "暖"]): return "暖色调"
        if any(w in text for w in ["黑白", "极简", "灰", "暗黑"]): return "冷色调/黑白"
        if any(w in text for w in ["复古", "浓郁", "高饱和", "彩色"]): return "高饱和"
        if any(w in text for w in ["莫兰迪", "低饱和", "侘寂", "素雅"]): return "低饱和"
        return "自然色调"

    def _infer_layout(self, data: dict) -> str:
        platform = self._detect_platform(data)
        if platform == "xiaohongshu": return "3:4竖版卡片"
        if platform == "douyin": return "9:16竖屏"
        return "自适应"

    def _estimate_hook_timing(self, text: str) -> float:
        """Estimate where the hook appears (first 3 seconds = first sentence)"""
        first_sentence = text.split("。")[0] if "。" in text else text[:50]
        if any(w in first_sentence for w in ["?", "？", "!", "！", "震惊", "天呐"]):
            return 0.5  # Instant hook
        return 2.0  # Delayed reveal

    def _infer_bpm(self, data: dict) -> str:
        duration = data.get("duration", 60)
        if duration < 15: return "快节奏卡点"
        if duration < 60: return "中速叙述"
        return "慢节奏沉浸"

    def _infer_transitions(self, data: dict) -> str:
        text = data.get("title", "") + data.get("content", "")
        if any(w in text for w in ["对比", "before", "after", "变化"]): return "硬切对比"
        if any(w in text for w in ["漫游", "走进", "推开"]): return "推拉运镜"
        return "硬切"

    def _classify_opening(self, text: str) -> str:
        first_50 = text[:50]
        if "?" in first_50 or "？" in first_50: return "悬念提问"
        if any(w in first_50 for w in ["后悔", "千万别", "踩坑", "避坑"]): return "痛点警示"
        if any(w in first_50 for w in ["㎡", "平", "万", "元", "¥"]): return "数据冲击"
        if any(w in first_50 for w in ["天呐", "居然", "震惊"]): return "情绪钩子"
        return "直接展示"

    def _calc_density(self, text: str) -> str:
        """Information density: numbers per 100 chars"""
        if len(text) < 10: return "低"
        numbers = len(re.findall(r'\d+', text))
        rate = numbers / len(text) * 100
        if rate > 5: return "高"
        if rate > 2: return "中"
        return "低"

    def _detect_cta(self, text: str) -> str:
        last_100 = text[-100:] if len(text) > 100 else text
        if any(w in last_100 for w in ["评论", "留言", "讨论"]): return "评论引导"
        if any(w in last_100 for w in ["关注", "点赞", "收藏"]): return "互动引导"
        if any(w in last_100 for w in ["私信", "咨询", "联系"]): return "私信引导"
        return "无引导"


# ═══════════════════════════════════════
# 二、趋势聚合器
# ═══════════════════════════════════════

class TrendAggregator:
    """Aggregate individual analyses into trend patterns"""

    def aggregate(self, analyses: list[ContentAnalysis]) -> dict:
        """Generate trend report from collected analyses"""
        if not analyses:
            return {"error": "No data"}

        # Confidence: text-based dimensions are reliable, video/hashtag are not from web search
        source_type = self._detect_source_type(analyses)
        confidence = {
            "expression": 0.8,   # Text analysis works well on web articles
            "copy": 0.8,         # Opening/CTA/density from text analysis
            "visual": 0.5,       # Cover/color inference is approximate
            "hashtags": 0.2 if source_type == "web_search" else 0.7,   # Web search has no real hashtags
            "video": 0.1 if source_type == "web_search" else 0.8,      # Web search has no video metadata
        }

        return {
            "period": f"{analyses[-1].collected_at[:10]} / {analyses[0].collected_at[:10]}" if len(analyses) > 1 else analyses[0].collected_at[:10],
            "sample_size": len(analyses),
            "confidence": confidence,
            "reliable_dimensions": [k for k, v in confidence.items() if v >= 0.5],
            "unreliable_dimensions": [k for k, v in confidence.items() if v < 0.5],
            # Dimension 1: Hashtag trends
            "hashtags": {
                "top_tags": self._top_hashtags(analyses, 20),
                "best_strategy": self._best_strategy(analyses, "hashtag_strategy"),
                "avg_tags_per_post": round(sum(len(a.hashtags) for a in analyses) / len(analyses), 1),
            },
            # Dimension 2: Expression trends
            "expression": {
                "top_personas": self._count_field(analyses, "persona"),
                "top_tones": self._count_field(analyses, "tone"),
                "top_narratives": self._count_field(analyses, "narrative"),
            },
            # Dimension 3: Visual trends
            "visual": {
                "top_cover_styles": self._count_field(analyses, "cover_style"),
                "top_colors": self._count_field(analyses, "color_scheme"),
                "top_layouts": self._count_field(analyses, "layout_pattern"),
            },
            # Dimension 4: Video trends
            "video": {
                "avg_duration_sec": round(sum(a.duration_sec for a in analyses if a.duration_sec) / max(1, sum(1 for a in analyses if a.duration_sec)), 1),
                "top_bpm": self._count_field(analyses, "bpm_style"),
                "top_transitions": self._count_field(analyses, "transition_style"),
                "avg_hook_sec": round(sum(a.hook_timing_sec for a in analyses if a.hook_timing_sec) / max(1, sum(1 for a in analyses if a.hook_timing_sec)), 1),
            },
            # Dimension 5: Copy trends
            "copy": {
                "top_openings": self._count_field(analyses, "opening_type"),
                "avg_length": round(sum(a.copy_length for a in analyses) / len(analyses), 0),
                "density_distribution": self._count_field(analyses, "info_density"),
                "top_cta": self._count_field(analyses, "cta_style"),
            },
        }

    # Tags that are clearly NOT decoration content (noise filter)
    _NOISE_TAGS = {
        "美食", "旅游", "游戏", "动漫", "电影", "音乐", "小说", "读书",
        "健身", "跑步", "瑜伽", "美妆", "穿搭", "护肤", "发型", "美甲",
        "宠物", "猫", "狗", "留学", "考研", "英语", "日语", "编程",
        "股票", "基金", "比特币", "创业", "职场", "面试", "简历",
        "汽车", "数码", "手机", "电脑", "相机", "无人机",
        "精灵宝可梦", "原神", "王者荣耀", "吃鸡", "LOL",
        "移民", "出国", "打工", "签证", "护照",
        "钩织", "毛线", "手工", "烘焙", "做饭", "菜谱",
    }

    _DECORATION_TAGS = {
        "装修", "设计", "家居", "改造", "翻新", "全屋", "定制",
        "客厅", "卧室", "厨房", "卫生间", "阳台", "玄关", "书房",
        "奶油风", "原木风", "现代简约", "北欧", "日式", "新中式", "轻奢", "极简", "法式",
        "瓷砖", "地板", "涂料", "墙纸", "窗帘", "灯具", "沙发", "餐桌",
        "水电", "瓦工", "木工", "油漆", "施工", "监理", "验收",
        "软装", "硬装", "家电", "家具", "收纳", "空间", "布局",
        "roomtour", "before", "after", "装修日记", "装修记录",
        "老房", "新房", "婚房", "二手房", "loft", "别墅", "小户型",
        "装修预算", "装修费用", "装修省钱", "避坑", "后悔",
    }

    def _top_hashtags(self, analyses: list, n: int) -> list:
        all_tags = []
        for a in analyses:
            for tag in a.hashtags:
                # Filter: only keep decoration-related tags
                tag_clean = tag.strip().lower()
                # Skip noise
                if tag_clean in self._NOISE_TAGS:
                    continue
                # Skip tags that are too long (likely article fragments)
                if len(tag) > 15:
                    continue
                # Keep if decoration-related or unknown (could be new trend)
                all_tags.append(tag)
        return Counter(all_tags).most_common(n)

    def _detect_source_type(self, analyses: list) -> str:
        """Detect if data comes from web search (low hashtag/video quality) or social media"""
        if not analyses:
            return "unknown"
        # Check if any analysis has video duration data
        has_video = any(a.duration_sec > 0 for a in analyses)
        # Check if hashtags look like real social tags (short, no punctuation)
        all_tags = []
        for a in analyses:
            all_tags.extend(a.hashtags)
        clean_count = sum(1 for t in all_tags if 2 <= len(t) <= 10 and not any(c in t for c in '（()）[]【】'))
        tag_quality = clean_count / max(len(all_tags), 1)

        if has_video and tag_quality > 0.5:
            return "social_media"
        return "web_search"

    def _best_strategy(self, analyses: list, field: str) -> str:
        strategies = [getattr(a, field, "") for a in analyses if getattr(a, field, "")]
        return Counter(strategies).most_common(1)[0][0] if strategies else ""

    def _count_field(self, analyses: list, field: str) -> dict:
        values = [getattr(a, field, "") for a in analyses if getattr(a, field, "")]
        return dict(Counter(values).most_common(10))


# ═══════════════════════════════════════
# 三、反馈引擎 — 反哺内容格式库
# ═══════════════════════════════════════

class FeedbackEngine:
    """Push trend insights back into the content format library"""

    def generate_format_updates(self, trend_report: dict) -> list:
        """Generate suggested updates to content formats based on trends"""
        updates = []
        report = trend_report

        # Hashtag recommendations
        top_tags = report.get("hashtags", {}).get("top_tags", [])
        if top_tags:
            updates.append({
                "target": "hashtag_library",
                "action": "add",
                "data": [t[0] for t in top_tags[:10]],
                "reason": f"Top {len(top_tags[:10])} trending hashtags",
            })

        # Opening pattern recommendations
        top_openings = report.get("copy", {}).get("top_openings", {})
        best_opening = max(top_openings, key=top_openings.get) if top_openings else ""
        if best_opening:
            updates.append({
                "target": "hook_templates",
                "action": "prioritize",
                "data": best_opening,
                "reason": f"Best performing opening: {best_opening} ({top_openings[best_opening]} posts)",
            })

        # Visual recommendations
        top_covers = report.get("visual", {}).get("top_cover_styles", {})
        best_cover = max(top_covers, key=top_covers.get) if top_covers else ""
        if best_cover:
            updates.append({
                "target": "visual_styles",
                "action": "prioritize",
                "data": best_cover,
                "reason": f"Best performing cover: {best_cover} ({top_covers[best_cover]} posts)",
            })

        # Persona shift
        top_personas = report.get("expression", {}).get("top_personas", {})
        best_persona = max(top_personas, key=top_personas.get) if top_personas else ""
        if best_persona:
            updates.append({
                "target": "persona_config",
                "action": "suggest",
                "data": best_persona,
                "reason": f"Trending persona: {best_persona}",
            })

        # Video rhythm
        avg_duration = report.get("video", {}).get("avg_duration_sec", 60)
        updates.append({
            "target": "video_duration",
            "action": "suggest",
            "data": f"{avg_duration:.0f}s",
            "reason": f"Average trending video duration",
        })

        return updates


# ═══════════════════════════════════════
# 四、搜索采集器（使用 Tavily）
# ═══════════════════════════════════════

class TrendCollector:
    """Search and collect trending decoration content"""

    SEARCH_QUERIES = [
        # Hashtag-focused
        "2026装修热门话题 小红书 hashtag 趋势",
        "装修内容爆款 表达方式 呈现形式 分析",
        # Visual-focused
        "装修设计 小红书爆款封面 构图方式",
        "装修案例 短视频拍摄手法 运镜技巧",
        # Video rhythm
        "装修抖音爆款视频 节奏 转场 BGM",
        "装修vlog 视频节奏 钩子前3秒",
        # Copy patterns
        "装修文案 小红书爆文 开头写法 分析",
        "装修避坑文案 爆款结构 信息密度",
        # Specific formats
        "装修前后对比 爆款内容 怎么做",
        "room tour 装修 爆款视频 拍摄教程",
    ]

    def __init__(self):
        self.analyzer = TrendAnalyzer()
        self.aggregator = TrendAggregator()
        self.feedback = FeedbackEngine()

    def search_trends(self, query_override: str = None, max_results: int = 10) -> dict:
        """Search for trending content patterns using Tavily API"""
        queries = [query_override] if query_override else self.SEARCH_QUERIES

        all_results = []
        for q in queries[:5]:  # 5 queries x 10 results = 50 samples
            try:
                results = self._tavily_search(q, max_results)
                all_results.extend(results)
            except Exception as e:
                all_results.append({"error": str(e), "query": q})

        # Analyze each result
        analyses = []
        for r in all_results:
            if "error" in r:
                continue
            try:
                analysis = self.analyzer.analyze_content(r)
                analyses.append(analysis)
                self._save_analysis(analysis)
            except Exception:
                continue

        # Aggregate trends
        trend_report = self.aggregator.aggregate(analyses)

        # Generate feedback
        updates = self.feedback.generate_format_updates(trend_report)

        # Save trend report
        self._save_trend_report(trend_report)

        return {
            "collected": len(all_results),
            "analyzed": len(analyses),
            "trends": trend_report,
            "updates": updates,
            "timestamp": datetime.now().isoformat(),
        }

    def _tavily_search(self, query: str, max_results: int) -> list:
        """Search using Tavily API (uses existing API keys in env)"""
        import urllib.request
        api_key = os.environ.get("TAVILY_API_KEY_1",
                  os.environ.get("TAVILY_API_KEY_2",
                  os.environ.get("TAVILY_API_KEY_3", "")))
        if not api_key:
            return [{"source": "mock", "query": query,
                     "title": f"[模拟] {query}",
                     "content": f"搜索关键词: {query}。请配置TAVILY_API_KEY以启用真实搜索。",
                     "url": "", "platform": "mock"}]

        try:
            body = json.dumps({
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced",
                "include_domains": [],
            }).encode()
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {api_key}"}
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read().decode())
            return data.get("results", [])
        except Exception as e:
            return [{"source": "error", "query": query, "error": str(e)}]

    def _save_analysis(self, analysis: ContentAnalysis):
        TREND_DB.parent.mkdir(parents=True, exist_ok=True)
        with open(TREND_DB, "a", encoding="utf-8") as f:
            f.write(json.dumps(analysis.__dict__, ensure_ascii=False) + "\n")

    def _save_trend_report(self, report: dict):
        INSIGHT_DB.parent.mkdir(parents=True, exist_ok=True)
        report["_updated"] = datetime.now().isoformat()
        # Keep last 30 reports
        history = []
        if INSIGHT_DB.exists():
            try:
                history = json.loads(INSIGHT_DB.read_text(encoding="utf-8"))
            except Exception:
                history = []
        history.append(report)
        history = history[-30:]  # Keep last 30
        INSIGHT_DB.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════
# 五、趋势仪表盘数据
# ═══════════════════════════════════════

def get_trend_dashboard() -> dict:
    """Get current trend dashboard data"""
    collector = TrendCollector()
    latest = {}

    if INSIGHT_DB.exists():
        try:
            history = json.loads(INSIGHT_DB.read_text(encoding="utf-8"))
            if history:
                latest = history[-1]
        except Exception:
            pass

    # Also get recent analyses
    recent_analyses = []
    if TREND_DB.exists():
        with open(TREND_DB, "r", encoding="utf-8") as f:
            for line in f.readlines()[-100:]:
                try:
                    recent_analyses.append(json.loads(line.strip()))
                except Exception:
                    continue

    return {
        "latest_report": latest,
        "recent_count": len(recent_analyses),
        "available_queries": TrendCollector.SEARCH_QUERIES,
        "next_refresh": (datetime.now() + timedelta(hours=6)).isoformat(),
    }
