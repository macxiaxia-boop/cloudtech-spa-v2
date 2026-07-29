"""
AI Operating System — 统一仪表盘 v2.0
一个界面整合: 系统监控 · 选题发现 · 内容生产 · 数据分析 · 研究助手
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
plt.rcParams.update({
    "font.family": "Microsoft YaHei", "axes.unicode_minus": False,
    "figure.facecolor": "#0e1117", "axes.facecolor": "#1a1d23",
    "axes.labelcolor": "#ccc", "text.color": "#e0e0e0",
    "xtick.color": "#999", "ytick.color": "#999", "grid.color": "#2a2d33",
})
import json, os, sys, time, tempfile, io
from datetime import datetime
from pathlib import Path

# Enable importing from tools/core
CORE = Path(r"C:\Users\xinzh\.openclaw\tools\core")
sys.path.insert(0, str(CORE))

st.set_page_config(page_title="AI操作系统", page_icon="🤖", layout="wide")

# ── CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .kpi-card { background: #1a1d23; border: 1px solid #2a2d33; border-radius: 8px;
        padding: 16px; text-align: center; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #8bd3ff; }
    .kpi-label { font-size: 0.8rem; color: #888; margin-top: 4px; }
    .status-ok { color: #00c853; } .status-warn { color: #ffd600; } .status-err { color: #ff1744; }
    .tool-card { background: #1a1d23; border: 1px solid #2a2d33; border-radius: 8px;
        padding: 20px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

# ── Paths ──────────────────────────────────────────
STATE = Path(r"C:\Users\xinzh\.openclaw\workspace\state")
CRON = Path(r"C:\Users\xinzh\.openclaw\cron-jobs.json")
TOPIC_DIR = Path(r"D:\个人文件\AI\01 世界模型系统\话题追踪")
INTEL_DIR = Path(r"D:\个人文件\AI\01 世界模型系统\情报日报")
SEARCH_CFG = TOPIC_DIR / "search-config.json"
OUT_DIRS = {
    "charts": Path(r"D:\个人文件\AI\04 素材资产系统\数据图表"),
    "reports": Path(r"D:\个人文件\AI\05 项目生产系统\数据分析报告"),
    "content": Path(r"D:\个人文件\AI\05 项目生产系统\内容生产"),
    "briefs": TOPIC_DIR / "选题建议",
}
for d in OUT_DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

# ── Helpers ────────────────────────────────────────
def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except:
        return default or {}

@st.cache_data(ttl=30)
def get_system_stats():
    stats = {"tasks_total": 0, "tasks_done": 0, "tasks_failed": 0,
             "cron_count": 0, "cron_enabled": 0, "log_entries": 0}
    tq = load_json(STATE / "task-queue.json", {})
    stats["tasks_total"] = len(tq.get("tasks", [])) + len(tq.get("history", []))
    stats["tasks_done"] = tq.get("stats", {}).get("completed", 0)
    stats["tasks_failed"] = tq.get("stats", {}).get("failed", 0)
    cron = load_json(CRON, [])
    stats["cron_count"] = len(cron)
    stats["cron_enabled"] = sum(1 for c in cron if c.get("schedule"))
    ll = load_json(STATE / "learning_log.json", [])
    stats["log_entries"] = len(ll) if isinstance(ll, list) else len(ll.get("entries", []))
    return stats

def topic_briefs():
    """List existing topic briefs."""
    d = OUT_DIRS["briefs"]
    if not d.exists(): return []
    return sorted(d.glob("*.md"), key=os.path.getmtime, reverse=True)[:10]

def recent_content():
    """List recent content productions."""
    d = OUT_DIRS["content"]
    if not d.exists(): return []
    files = []
    for p in d.rglob("*.md"):
        files.append((p, p.stat().st_mtime))
    return [f[0] for f in sorted(files, key=lambda x: x[1], reverse=True)[:10]]

# ── Sidebar ────────────────────────────────────────
with st.sidebar:
    st.title("🤖 AI 操作系统")
    st.caption(f"v2.0 · {datetime.now().strftime('%H:%M')}")
    page = st.radio("导航", ["🏠 系统总览", "🌐 情报中心", "🎯 选题发现", "✍️ 内容生产",
                              "📊 数据分析", "📝 研究助手"])
    st.divider()
    stats = get_system_stats()
    st.metric("任务完成", f"{stats['tasks_done']}/{stats['tasks_total']}")
    st.metric("Cron任务", f"{stats['cron_enabled']}/{stats['cron_count']}")
    st.metric("学习记录", stats["log_entries"])
    st.divider()
    st.caption("仪表盘 · http://localhost:8501")

# ════════════════════════════════════════════════════
# PAGE 1: 系统总览
# ════════════════════════════════════════════════════
if "🏠" in page:
    st.title("🏠 系统总览")
    s = stats

    cols = st.columns(4)
    cols[0].markdown(f'<div class="kpi-card"><div class="kpi-value">{s["tasks_done"]}</div><div class="kpi-label">已完成任务</div></div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="kpi-card"><div class="kpi-value">{s["tasks_failed"]}</div><div class="kpi-label">失败任务</div></div>', unsafe_allow_html=True)
    cols[2].markdown(f'<div class="kpi-card"><div class="kpi-value">{s["cron_count"]}</div><div class="kpi-label">Cron任务</div></div>', unsafe_allow_html=True)
    cols[3].markdown(f'<div class="kpi-card"><div class="kpi-value">{s["log_entries"]}</div><div class="kpi-label">学习记录</div></div>', unsafe_allow_html=True)

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📋 Cron任务状态")
        cron = load_json(CRON, [])
        if cron:
            data = [{"名称": c["name"], "时间": c.get("schedule", {}).get("expr", "?"),
                     "模型": c.get("agent", {}).get("model", "")} for c in cron[:8]]
            st.dataframe(pd.DataFrame(data), use_container_width=True)

    with c2:
        st.subheader("📝 最近内容产出")
        recent = recent_content()
        if recent:
            for r in recent[:6]:
                st.caption(f"📄 {r.parent.name}/{r.name}")
        else:
            st.info("暂无内容产出")

    st.divider()
    st.subheader("📂 输出目录")
    for name, path in OUT_DIRS.items():
        file_count = len(list(path.rglob("*"))) if path.exists() else 0
        st.caption(f"**{name}**: {path} ({file_count} 文件)")

# ════════════════════════════════════════════════════
# PAGE 2: 情报中心 (REAL DATA from intel-agent + live search)
# ════════════════════════════════════════════════════
elif "情报" in page:
    st.title("🌐 情报中心")
    st.caption("数据来源: GitHub · Hacker News · Product Hunt · Reddit · 知乎 · 微博 · B站 · YouTube")

    # Load real intel reports
    intel_files = sorted(INTEL_DIR.glob("*.md"), reverse=True) if INTEL_DIR.exists() else []
    latest_intel = None
    if intel_files:
        latest_intel = intel_files[0].read_text(encoding="utf-8")

    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📡 最新情报")
        if latest_intel:
            # Extract key items
            lines = latest_intel.split("\n")
            p0_section = False
            p0_items = []
            for l in lines:
                if "## 🔴 P0" in l: p0_section = True
                elif "## 🟡 P1" in l: p0_section = False
                elif p0_section and l.startswith("### "):
                    p0_items.append(l.strip("# "))
            if p0_items:
                for item in p0_items[:8]:
                    st.markdown(f"🔴 {item}")
            else:
                st.info("暂无P0级别情报")

            # Show latest report preview
            with st.expander("📄 完整最新报告"):
                st.markdown(latest_intel[:3000])
        else:
            st.warning("暂无情报报告。运行 `python live_search_engine.py` 来生成第一个。")

    with c2:
        st.subheader("📊 来源覆盖")
        sources = {
            "GitHub Trending": "✅ P0",
            "Hacker News": "✅ P0",
            "Product Hunt": "✅ P1",
            "Reddit ML": "✅ P1",
            "HuggingFace": "✅ P2",
            "Twitter/X AI": "✅ P2",
            "微博热搜": "✅ P0",
            "B站热门": "✅ P0",
            "知乎热榜": "✅ P1",
            "小红书": "✅ P1",
            "YouTube": "✅ P1",
        }
        for src, priority in sources.items():
            color = "#00c853" if "P0" in priority else "#ffd600" if "P1" in priority else "#999"
            st.markdown(f'<span style="color:{color}">{priority}</span> {src}', unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 历史情报")
    for f in intel_files[:5]:
        st.caption(f"📄 {f.stem} — {datetime.fromtimestamp(f.stat().st_mtime).strftime('%m-%d %H:%M')}")

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("情报报告数", len(intel_files))
    c2.metric("覆盖来源", "11 个")
    c3.metric("最新更新", datetime.fromtimestamp(intel_files[0].stat().st_mtime).strftime("%H:%M") if intel_files else "N/A")

# ════════════════════════════════════════════════════
# PAGE 3: 选题发现
# ════════════════════════════════════════════════════
elif "选题" in page:
    st.title("🎯 选题发现")

    col1, col2 = st.columns([2, 1])
    with col1:
        domain = st.text_input("话题领域", "AI工具", help="输入你想探索的话题领域")
    with col2:
        creators = st.multiselect("对标创作者", ["直男财经", "小A学财经", "小Lin说", "高盖伦"],
                                   default=["直男财经", "小A学财经"])

    if st.button("🔍 开始选题发现", type="primary", use_container_width=True):
        with st.spinner(f"正在搜索 '{domain}' 相关话题..."):
            try:
                from topic_discovery_engine import TopicDiscoveryEngine
                engine = TopicDiscoveryEngine(domain=domain, creators=creators, max_briefs=5)
                engine.collect_topics()
                engine.score_topics()
                engine.generate_briefs()

                st.success(f"发现 {len(engine.raw_topics)} 个话题，生成 {len(engine.briefs)} 个选题简报")

                for i, brief in enumerate(engine.briefs):
                    with st.expander(f"#{i+1} [{brief.get('score', 0):.2f}] {brief.get('title', '')}", expanded=i==0):
                        c1, c2, c3 = st.columns(3)
                        c1.metric("对标创作者", brief.get("creator", ""))
                        c2.metric("推荐平台", brief.get("platform", "公众号"))
                        c3.metric("建议字数", brief.get("word_count_range", "1500-2500"))
                        st.caption(f"**角度**: {brief.get('angle', '')}")
                        st.caption(f"**为什么值得做**: {brief.get('why_worth_it', '')}")
                        if brief.get("outline"):
                            st.markdown("**大纲**:\n" + "\n".join(f"- {o}" for o in brief["outline"]))
            except Exception as e:
                st.error(f"选题引擎出错: {e}")
                st.info("请确保已安装依赖: pip install requests")

    st.divider()
    st.subheader("📚 已有选题简报")
    briefs = topic_briefs()
    if briefs:
        for b in briefs[:5]:
            st.caption(f"📄 {b.name}")
            with st.expander("预览"):
                try:
                    st.markdown(b.read_text(encoding="utf-8")[:500])
                except:
                    pass
    else:
        st.info("暂无选题简报，运行选题发现来生成第一个")

# ════════════════════════════════════════════════════
# PAGE 3: 内容生产
# ════════════════════════════════════════════════════
elif "内容" in page:
    st.title("✍️ 内容生产")

    col1, col2, col3 = st.columns(3)
    with col1:
        topic = st.text_input("创作主题", "AI如何改变装修行业")
    with col2:
        creator = st.selectbox("对标创作者", ["直男财经", "小A学财经", "小Lin说", "高盖伦"])
    with col3:
        platform = st.selectbox("目标平台", ["公众号", "知乎", "小红书", "抖音", "朋友圈"])

    word_map = {"小红书": 800, "公众号": 2000, "知乎": 3000, "抖音": 1500, "朋友圈": 300}
    words = st.slider("目标字数", 300, 4000, word_map.get(platform, 2000), 100)

    if st.button("🚀 开始生产内容", type="primary", use_container_width=True):
        with st.spinner(f"4-Agent协作中: 研究员→文案→编辑+SEO..."):
            try:
                from crewai_content_team import ContentCrew
                crew = ContentCrew(topic=topic, creator=creator, platform=platform, word_count=words)
                result = crew.run()

                st.success("内容生产完成!")
                tabs = st.tabs(["📝 终稿", "🔬 研究简报", "✅ 编辑报告", "🔍 SEO报告"])
                with tabs[0]:
                    st.markdown(result.get("final_content", "（等待生成）"))
                with tabs[1]:
                    st.markdown(result.get("research_brief", "（等待生成）")[:2000])
                with tabs[2]:
                    st.json(result.get("editor_report", {}))
                with tabs[3]:
                    st.json(result.get("seo_report", {}))
            except Exception as e:
                st.error(f"内容生产出错: {e}")

    st.divider()
    st.subheader("📂 最近生产")
    recent = recent_content()
    if recent:
        for r in recent[:5]:
            st.caption(f"📄 {r.parent.name}/{r.name}")
    else:
        st.info("暂无内容产出")

# ════════════════════════════════════════════════════
# PAGE 4: 数据分析
# ════════════════════════════════════════════════════
elif "数据" in page:
    st.title("📊 数据分析")

    uploaded = st.file_uploader("上传数据文件", type=["csv", "xlsx", "json"],
                                 help="支持 CSV / Excel / JSON 格式")
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            elif uploaded.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded)
            else:
                df = pd.read_json(uploaded)

            st.success(f"已加载: {len(df)} 行 × {len(df.columns)} 列")
            st.dataframe(df.head(10), use_container_width=True)

            # Auto-analysis
            num_cols = df.select_dtypes(include=["number"]).columns.tolist()
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

            if num_cols:
                st.subheader("📈 数值列统计")
                st.dataframe(df[num_cols].describe(), use_container_width=True)

                # Charts
                chart_type = st.selectbox("选择图表类型", ["柱状图", "折线图", "散点图", "饼图"])
                chart_cols = st.columns(2)
                x_col = chart_cols[0].selectbox("X轴", num_cols)
                y_col = chart_cols[1].selectbox("Y轴", num_cols, index=min(1, len(num_cols)-1))

                if st.button("生成图表"):
                    fig, ax = plt.subplots(figsize=(8, 4))
                    if chart_type == "柱状图":
                        df.groupby(x_col)[y_col].mean().plot.bar(ax=ax, color="#2979ff")
                    elif chart_type == "折线图":
                        ax.plot(df[x_col], df[y_col], color="#00c853")
                    elif chart_type == "散点图":
                        ax.scatter(df[x_col], df[y_col], c="#ffd600", alpha=0.6)
                    elif chart_type == "饼图" and cat_cols:
                        df[cat_cols[0]].value_counts().head(6).plot.pie(ax=ax, autopct="%1.1f%%")
                    ax.set_facecolor("#1a1d23")
                    st.pyplot(fig)

                    # Save
                    chart_path = OUT_DIRS["charts"] / f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="#0e1117")
                    st.success(f"图表已保存: {chart_path}")

        except Exception as e:
            st.error(f"数据加载失败: {e}")

# ════════════════════════════════════════════════════
# PAGE 5: 研究助手
# ════════════════════════════════════════════════════
elif "研究" in page:
    st.title("📝 研究助手 (NotebookLM风格)")

    source_text = st.text_area("粘贴文本内容", height=200,
                                placeholder="粘贴文章、访谈记录、视频字幕...")
    source_type = st.selectbox("内容类型", ["article", "interview", "video", "podcast", "paper"])

    if st.button("🔬 分析内容", type="primary", use_container_width=True) and source_text.strip():
        with st.spinner("分析中..."):
            try:
                from notebooklm_research import NotebookLM
                nb = NotebookLM(source_text, source_type)
                outputs = nb.generate_all()

                tabs = st.tabs(["📋 摘要", "❓ FAQ", "🧠 导图", "⏱ 时间线"])
                with tabs[0]:
                    st.markdown(outputs["summary"])
                with tabs[1]:
                    st.markdown(outputs["faq"])
                with tabs[2]:
                    st.markdown(outputs["mindmap"])
                with tabs[3]:
                    timeline = outputs["timeline"]
                    if timeline:
                        for e in timeline[:15]:
                            st.caption(f"**{e['date']}** — {e['context']}")
                    else:
                        st.info("未检测到时间线事件")

                st.divider()
                st.subheader("🔑 关键词")
                st.write(", ".join(outputs["keywords"]))

            except Exception as e:
                st.error(f"分析出错: {e}")
