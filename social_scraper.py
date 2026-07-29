"""
社交媒体原生采集器 — Social Media Scraper
=============================================
小红书/抖音/公众号 原生内容采集
输出干净的结构化数据 → 直接喂给 TrendAnalyzer

采集维度（每个平台原生提取）:
  小红书: 标题/正文/#标签/封面描述/互动数据/笔记类型
  抖音:   视频标题/字幕/话题/时长/BGM/点赞评论/拍摄方式
  公众号:  标题/正文/排版/阅读量/互动
"""
import json, os, re, time, hashlib, random
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

# ═══════════════════════════════════════
# 数据模型 — 平台原生字段
# ═══════════════════════════════════════

@dataclass
class XHSNote:
    """小红书笔记 — 原生字段映射"""
    note_id: str
    title: str
    content: str
    hashtags: list = field(default_factory=list)
    topic_tags: list = field(default_factory=list)  # 小红书话题标签
    cover_description: str = ""     # 封面特征描述
    image_count: int = 0
    layout_type: str = ""           # 单图/拼图/长图/视频
    likes: int = 0
    comments: int = 0
    collects: int = 0
    author_type: str = ""           # 设计师/业主/品牌/博主
    publish_date: str = ""
    url: str = ""

    def to_analysis_dict(self) -> dict:
        """Convert to format TrendAnalyzer expects"""
        return {
            "url": self.url,
            "platform": "xiaohongshu",
            "title": self.title,
            "content": self.content,
            "hashtags": self.hashtags + self.topic_tags,
            "cover_style": self.layout_type,
            "engagement_estimate": {
                "likes": self.likes,
                "comments": self.comments,
                "collects": self.collects,
            },
        }


@dataclass
class DouyinVideo:
    """抖音视频 — 原生字段映射"""
    video_id: str
    title: str
    subtitle_text: str = ""         # 字幕/口播文案
    hashtags: list = field(default_factory=list)
    challenge_tags: list = field(default_factory=list)  # 挑战赛标签
    duration_sec: int = 0
    bgm_name: str = ""
    bgm_style: str = ""             # 卡点/舒缓/vlog/热门
    transition_count: int = 0       # 转场次数（近似）
    hook_text: str = ""             # 前3秒的字幕/文案
    likes: int = 0
    comments: int = 0
    shares: int = 0
    shooting_style: str = ""        # 口播/空镜/第一人称/vlog/卡点混剪
    publish_date: str = ""
    url: str = ""

    def to_analysis_dict(self) -> dict:
        """Convert to format TrendAnalyzer expects"""
        text = f"{self.hook_text} {self.title} {self.subtitle_text}"
        return {
            "url": self.url,
            "platform": "douyin",
            "title": self.title,
            "content": text,
            "hashtags": self.hashtags + self.challenge_tags,
            "duration": self.duration_sec,
            "cover_style": self.shooting_style,
            "bpm_style": self.bgm_style,
            "engagement_estimate": {
                "likes": self.likes,
                "comments": self.comments,
                "shares": self.shares,
            },
        }


# ═══════════════════════════════════════
# 搜索关键词库 — 装修行业 × 各平台
# ═══════════════════════════════════════

SEARCH_KEYWORDS = {
    "xiaohongshu": {
        "formats": [
            "装修前后对比 改造",
            "room tour 装修 全屋",
            "装修预算 费用明细",
            "装修施工日记 记录",
            "装修材料选购 测评",
            "装修风格设计 案例",
            "装修避坑 经验分享",
            "同城装修 本地案例",
        ],
        "styles": ["现代简约", "奶油风", "原木风", "新中式", "轻奢", "北欧", "日式", "法式"],
        "rooms": ["客厅", "厨房", "卧室", "卫生间", "阳台", "玄关", "书房"],
        "angles": ["省钱", "高级感", "小户型", "大平层", "老房改造", "精装房", "自装"],
    },
    "douyin": {
        "formats": [
            "装修全过程 记录",
            "装修验收 避坑",
            "装修设计 效果图vs实景",
            "装修材料 怎么选",
            "装修师傅 施工工艺",
            "roomtour 新家",
            "装修花费 多少钱",
            "同城装修 案例实拍",
        ],
        "styles": ["奶油风装修", "现代简约风", "原木风装修", "极简风", "轻奢风"],
        "angles": ["3秒钩子", "卡点", "before after", "一镜到底", "沉浸式"],
    },
}


# ═══════════════════════════════════════
# 核心采集器
# ═══════════════════════════════════════

class SocialCollector:
    """社交媒体内容采集器 — 支持浏览器自动化和API两种模式"""

    def __init__(self, use_browser: bool = False):
        self.use_browser = use_browser
        self.data_dir = Path(__file__).parent / "data" / "social_raw"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Check for saved browser login states
        self.profile_dir = Path(__file__).parent / "data" / "browser_profiles"
        self._has_xhs_login = (self.profile_dir / "xiaohongshu_state.json").exists()
        self._has_dy_login = (self.profile_dir / "douyin_state.json").exists()

    # ── 小红书采集 ──

    def search_xiaohongshu(self, keyword: str, count: int = 10, sort: str = "general") -> list[XHSNote]:
        """
        Search Xiaohongshu for decoration content.
        sort: "general" (综合) | "hot" (最热) | "newest" (最新)
        """
        notes = []

        if self.use_browser:
            notes = self._xhs_browser_search(keyword, count, sort)
        else:
            notes = self._xhs_api_search(keyword, count, sort)

        # Save raw data
        for note in notes:
            self._save_raw("xiaohongshu", note.__dict__)

        return notes

    def _search_raw(self, query: str, count: int) -> list[dict]:
        """Raw search using Tavily — returns unstructured results"""
        import urllib.request
        api_key = os.environ.get("TAVILY_API_KEY_1",
                  os.environ.get("TAVILY_API_KEY_2",
                  os.environ.get("TAVILY_API_KEY_3", "")))
        if not api_key:
            return [{"title": f"[模拟] {query}", "content": f"搜索: {query}", "url": ""}]

        try:
            body = json.dumps({"query": query, "max_results": count, "search_depth": "advanced"}).encode()
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=body,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            )
            resp = urllib.request.urlopen(req, timeout=30)
            return json.loads(resp.read().decode()).get("results", [])
        except Exception as e:
            return [{"title": f"[Error] {query}", "content": str(e), "url": ""}]

    def _xhs_api_search(self, keyword: str, count: int, sort: str) -> list[XHSNote]:
        """API-based search for Xiaohongshu content"""
        results = self._search_raw(f"site:xiaohongshu.com 装修 {keyword} 爆款内容", count)

        notes = []
        for r in results:
            content = r.get("content", "")
            note = XHSNote(
                note_id=hashlib.md5(f"{keyword}{content[:50]}{time.time()}".encode()).hexdigest()[:12],
                title=r.get("title", f"[XHS] {keyword}"),
                content=content,
                hashtags=self._extract_clean_tags(content),
                topic_tags=self._extract_clean_tags(r.get("title", "")),
                cover_description=self._infer_xhs_layout(content),
                layout_type=self._infer_xhs_layout(content),
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                url=r.get("url", ""),
            )
            notes.append(note)

        return notes

    def _xhs_browser_search(self, keyword: str, count: int, sort: str) -> list[XHSNote]:
        """Browser-based search using Playwright (uses saved login state if available)"""
        try:
            from playwright.sync_api import sync_playwright
            notes = []

            state_file = self.profile_dir / "xiaohongshu_state.json"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx_opts = {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                if state_file.exists():
                    ctx_opts["storage_state"] = str(state_file)
                context = browser.new_context(**ctx_opts)
                page = context.new_page()

                # Navigate to search
                search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&sort={sort}"
                page.goto(search_url, timeout=30000)
                page.wait_for_timeout(3000)

                # Parse note cards
                cards = page.query_selector_all(".note-item, .search-result-item")
                for card in cards[:count]:
                    try:
                        title_el = card.query_selector(".title, .note-title")
                        content_el = card.query_selector(".desc, .note-desc")
                        tags_els = card.query_selector_all(".tag, .hashtag")
                        like_el = card.query_selector(".like-count, .count")

                        title = title_el.inner_text() if title_el else ""
                        content = content_el.inner_text() if content_el else ""
                        tags = [t.inner_text().replace("#", "").strip() for t in tags_els if t.inner_text()]
                        likes = self._parse_count(like_el.inner_text()) if like_el else 0

                        notes.append(XHSNote(
                            note_id=hashlib.md5(f"{keyword}{title}{time.time()}".encode()).hexdigest()[:12],
                            title=title,
                            content=content,
                            hashtags=tags,
                            likes=likes,
                            publish_date=datetime.now().strftime("%Y-%m-%d"),
                            url=page.url,
                        ))
                    except Exception:
                        continue

                browser.close()
            return notes
        except ImportError:
            return self._xhs_api_search(keyword, count, sort)

    # ── 抖音采集 ──

    def search_douyin(self, keyword: str, count: int = 10) -> list[DouyinVideo]:
        """Search Douyin for decoration videos"""
        videos = []

        if self.use_browser:
            videos = self._dy_browser_search(keyword, count)
        else:
            videos = self._dy_api_search(keyword, count)

        for video in videos:
            self._save_raw("douyin", video.__dict__)

        return videos

    def _dy_api_search(self, keyword: str, count: int) -> list[DouyinVideo]:
        """API-based Douyin search"""
        results = self._search_raw(f"抖音 装修 {keyword} 视频 拍摄 节奏 剪辑", count)

        videos = []
        for r in results:
            content = r.get("content", "")
            videos.append(DouyinVideo(
                video_id=hashlib.md5(f"{keyword}{content[:50]}{time.time()}".encode()).hexdigest()[:12],
                title=r.get("title", f"[DY] {keyword}"),
                subtitle_text=content[:500],
                hashtags=self._extract_clean_tags(content),
                challenge_tags=self._extract_clean_tags(r.get("title", "")),
                duration_sec=self._estimate_duration(content),
                bgm_style=self._detect_bgm_style(content),
                shooting_style=self._detect_shooting_style(content),
                hook_text=(content[:100] if content else ""),
                publish_date=datetime.now().strftime("%Y-%m-%d"),
                url=r.get("url", ""),
            ))

        return videos

    def _dy_browser_search(self, keyword: str, count: int) -> list[DouyinVideo]:
        """Browser-based Douyin search (uses saved login state if available)"""
        try:
            from playwright.sync_api import sync_playwright
            videos = []

            state_file = self.profile_dir / "douyin_state.json"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx_opts = {"user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                if state_file.exists():
                    ctx_opts["storage_state"] = str(state_file)
                context = browser.new_context(**ctx_opts)
                page = context.new_page()
                page.goto(f"https://www.douyin.com/search/{keyword}", timeout=30000)
                page.wait_for_timeout(5000)

                cards = page.query_selector_all(".search-result-card, .video-card")
                for card in cards[:count]:
                    try:
                        title_el = card.query_selector(".title, .video-title")
                        duration_el = card.query_selector(".duration")
                        like_el = card.query_selector(".like-count")

                        title = title_el.inner_text() if title_el else ""
                        duration = self._parse_duration(duration_el.inner_text()) if duration_el else 0
                        likes = self._parse_count(like_el.inner_text()) if like_el else 0

                        videos.append(DouyinVideo(
                            video_id=hashlib.md5(f"{keyword}{title}{time.time()}".encode()).hexdigest()[:12],
                            title=title,
                            duration_sec=duration,
                            likes=likes,
                            publish_date=datetime.now().strftime("%Y-%m-%d"),
                            url=page.url,
                        ))
                    except Exception:
                        continue

                browser.close()
            return videos
        except ImportError:
            return self._dy_api_search(keyword, count)

    # ── 批量采集 ──

    def collect_trending_all(self, queries_per_platform: int = 3) -> dict:
        """Batch collect from all platforms and formats"""
        results = {"xiaohongshu": [], "douyin": []}

        # Xiaohongshu: pick random queries across formats
        xhs_queries = self._pick_diverse_queries("xiaohongshu", queries_per_platform)
        for q in xhs_queries:
            try:
                notes = self.search_xiaohongshu(q, count=5)
                results["xiaohongshu"].extend(notes)
            except Exception as e:
                results["xiaohongshu"].append({"error": str(e), "query": q})

        # Douyin: pick random queries
        dy_queries = self._pick_diverse_queries("douyin", queries_per_platform)
        for q in dy_queries:
            try:
                videos = self.search_douyin(q, count=5)
                results["douyin"].extend(videos)
            except Exception as e:
                results["douyin"].append({"error": str(e), "query": q})

        return {
            "timestamp": datetime.now().isoformat(),
            "xhs_count": len(results["xiaohongshu"]),
            "dy_count": len(results["douyin"]),
            "results": results,
        }

    # ── 批量采集并分析 ──

    def collect_and_analyze(self, queries_per_platform: int = 3) -> dict:
        """Collect + analyze — full pipeline output"""
        from trend_intelligence import TrendAnalyzer, TrendAggregator, FeedbackEngine

        # Collect
        raw = self.collect_trending_all(queries_per_platform)

        # Analyze
        analyzer = TrendAnalyzer()
        analyses = []

        for note in raw["results"]["xiaohongshu"]:
            if isinstance(note, XHSNote):
                analyses.append(analyzer.analyze_content(note.to_analysis_dict()))

        for video in raw["results"]["douyin"]:
            if isinstance(video, DouyinVideo):
                analyses.append(analyzer.analyze_content(video.to_analysis_dict()))

        # Aggregate
        aggregator = TrendAggregator()
        trend_report = aggregator.aggregate(analyses)

        # Feedback
        feedback = FeedbackEngine()
        updates = feedback.generate_format_updates(trend_report)

        return {
            "collection": {
                "xhs_collected": raw["xhs_count"],
                "dy_collected": raw["dy_count"],
            },
            "analysis": {
                "analyzed": len(analyses),
            },
            "trends": trend_report,
            "updates": updates,
        }

    # ── Helpers ──

    def _pick_diverse_queries(self, platform: str, count: int) -> list:
        """Pick diverse queries across formats, styles, and angles"""
        kw = SEARCH_KEYWORDS.get(platform, {})
        queries = []
        formats = kw.get("formats", [])
        styles = kw.get("styles", [])
        angles = kw.get("angles", [])

        for i in range(count):
            fmt = formats[i % len(formats)] if formats else ""
            style = styles[i % len(styles)] if styles else ""
            angle = angles[i % len(angles)] if angles else ""
            # Combine: format + style + angle
            parts = [p for p in [fmt, style, angle] if p]
            random.shuffle(parts)
            queries.append(" ".join(parts[:2]))

        return queries

    def _extract_clean_tags(self, text: str) -> list:
        """Extract clean hashtags from text"""
        tags = re.findall(r'#([^\s#,，。！？]+)', text)
        # Also match Chinese hashtag format #装修日记#
        tags += re.findall(r'#([^#]+)#', text)
        # Filter out obviously non-tag content
        return [t.strip() for t in tags if len(t) < 20 and len(t) > 1 and not t.startswith("http")]

    def _infer_xhs_layout(self, text: str) -> str:
        if any(w in text for w in ["对比", "before", "改造前"]): return "对比图"
        if any(w in text for w in ["合集", "推荐", "TOP"]): return "拼图合集"
        if any(w in text for w in ["roomtour", "漫游", "全屋"]): return "长图/视频"
        return "单图/实拍"

    def _estimate_duration(self, text: str) -> int:
        """Estimate video duration from content signals"""
        if any(w in text for w in ["vlog", "记录", "全过程"]): return 180
        if any(w in text for w in ["教程", "攻略", "怎么"]): return 90
        if any(w in text for w in ["对比", "改造"]): return 45
        return 30  # Default short form

    def _detect_bgm_style(self, text: str) -> str:
        if any(w in text for w in ["卡点", "节奏", "踩点"]): return "卡点"
        if any(w in text for w in ["治愈", "氛围", "轻音乐"]): return "舒缓vlog"
        if any(w in text for w in ["热门", "流行", "BGM"]): return "热门BGM"
        return "原声/旁白"

    def _detect_shooting_style(self, text: str) -> str:
        if any(w in text for w in ["口播", "讲解", "告诉"]): return "口播讲解"
        if any(w in text for w in ["第一人称", "walk through", "走进"]): return "第一人称漫游"
        if any(w in text for w in ["对比", "before", "改造"]): return "对比混剪"
        if any(w in text for w in ["沉浸式", "ASMR", "无声"]): return "沉浸式"
        return "空镜vo"

    def _parse_count(self, text: str) -> int:
        """Parse '1.2万' → 12000, '3,456' → 3456"""
        text = text.strip().replace(",", "")
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        try:
            return int(text)
        except ValueError:
            return 0

    def _parse_duration(self, text: str) -> int:
        """Parse '03:25' → 205, '01:02:15' → 3735"""
        parts = text.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    def _save_raw(self, platform: str, data: dict):
        fname = self.data_dir / f"{platform}_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(fname, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════
# 定时采集调度
# ═══════════════════════════════════════

class CollectionScheduler:
    """Schedule regular collection runs"""

    def __init__(self):
        self.collector = SocialCollector()

    def run_daily_collection(self) -> dict:
        """Daily collection: trending content + analysis"""
        return self.collector.collect_and_analyze(queries_per_platform=5)

    def run_hourly_hotspot(self) -> dict:
        """Hourly: check for sudden trending topics (1 query per platform)"""
        return self.collector.collect_and_analyze(queries_per_platform=1)
