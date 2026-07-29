"""
装企内容生产控制台 v2.0 — 装修原生内容引擎
脱离财经口播模板。8格式×4平台×6视觉语言。
"""
import streamlit as st
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from zhuangqi_content_engine import ZhuangqiContentEngine, ContentScheduler, CONTENT_FORMATS, PLATFORM_ADAPTERS, VISUAL_LANGUAGE

st.set_page_config(page_title="装企内容控制台", page_icon="🏗️", layout="wide")

engine = ZhuangqiContentEngine()

# ── Sidebar ──
with st.sidebar:
    st.title("🏗️ 装企内容引擎")
    st.caption("8种装修原生格式 · 4平台适配")
    st.divider()

    mode = st.radio("模式", ["📝 单篇生成", "📅 周排期计划", "📖 格式库", "🎬 视觉语言库"])

    st.divider()
    st.caption(f"v2.0 · 脱离财经博主模板")

# ═══════════════════════════════════════
# 模式1: 单篇生成
# ═══════════════════════════════════════
if mode == "📝 单篇生成":
    st.title("📝 内容生成")

    col1, col2, col3 = st.columns(3)
    with col1:
        content_type = st.selectbox("内容格式", list(CONTENT_FORMATS.keys()),
                                     format_func=lambda x: f"{CONTENT_FORMATS[x]['icon']} {CONTENT_FORMATS[x]['name']}")
    with col2:
        platform = st.selectbox("发布平台", list(PLATFORM_ADAPTERS.keys()),
                                 format_func=lambda x: PLATFORM_ADAPTERS[x]['name'])
    with col3:
        city = st.text_input("城市", "漳州")

    st.divider()

    # Context inputs based on type
    fmt = CONTENT_FORMATS[content_type]
    st.subheader(f"{fmt['icon']} {fmt['name']}")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        size = st.number_input("面积(平)", 50, 500, 120)
    with col_b:
        budget = st.number_input("预算(万)", 5, 200, 30)
    with col_c:
        style = st.selectbox("风格", ["现代简约", "北欧风", "日式", "新中式", "轻奢", "工业风", "奶油风", "侘寂风", "美式", "法式"])

    if st.button("🚀 生成内容提纲", type="primary", use_container_width=True):
        context = {"city": city, "size": size, "w": budget, "style": style}
        brief = engine.generate_brief(content_type, platform, context)

        st.divider()
        st.subheader("📋 内容提纲")

        # Hook
        st.markdown(f"### 🎣 钩子")
        st.info(brief["hook"])

        # Structure
        st.markdown("### 📐 结构")
        for i, step in enumerate(brief["structure"]):
            st.markdown(f"**{i+1}. {step}**")

        # Visual
        st.markdown("### 🎬 视觉方式")
        st.markdown(f"**{brief['visual_style']}** — {brief['visual_instructions']}")

        # Platform rules
        st.markdown("### ⚠️ 平台规则")
        st.caption(f"语调: {brief['tone']}")
        st.caption(f"字数: {brief['target_length']}")
        if brief["forbidden_words"]:
            st.caption(f"🚫 禁用词: {', '.join(brief['forbidden_words'])}")

        # Full content
        with st.spinner("生成完整内容..."):
            content = engine.generate_content(brief)

        st.divider()
        st.subheader("📄 完整内容")

        with st.expander("📝 写作指导（展开查看）", expanded=True):
            for sec in content["sections"]:
                st.markdown(f"**{sec['step']}. {sec['title']}**")
                st.caption(sec["instruction"])
                st.divider()

        st.markdown(f"**🔖 标签:** {' '.join('#'+t for t in content['hashtags'])}")
        st.markdown(f"**✍️ 结尾:** {content['closing']}")

# ═══════════════════════════════════════
# 模式2: 周排期
# ═══════════════════════════════════════
elif mode == "📅 周排期计划":
    st.title("📅 周排期计划")

    st.markdown("### 账号配置")
    num_accounts = st.number_input("矩阵账号数", 1, 10, 3)

    accounts = []
    for i in range(int(num_accounts)):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input(f"账号{i+1}名称", f"装修号{i+1}", key=f"name_{i}")
        with col2:
            plat = st.selectbox(f"平台", list(PLATFORM_ADAPTERS.keys()),
                                format_func=lambda x: PLATFORM_ADAPTERS[x]['name'], key=f"plat_{i}")
        with col3:
            posts = st.number_input(f"日发帖", 1, 5, 1, key=f"posts_{i}")
        accounts.append({"name": name, "platform": plat, "posts_per_day": posts,
                         "context": {"city": "漳州", "size": 120, "w": 30, "style": "现代简约"}})

    if st.button("📅 生成周排期", type="primary", use_container_width=True):
        scheduler = ContentScheduler(engine)
        plan = scheduler.generate_week_plan(accounts)

        # Group by day
        days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for d in range(7):
            day_items = [p for p in plan if p["day"] == d + 1]
            if day_items:
                st.subheader(f"### {days[d]}")
                cols = st.columns(len(day_items))
                for i, item in enumerate(day_items):
                    with cols[i]:
                        brief = item["brief"]
                        st.markdown(f"**{item['account']}**")
                        st.caption(f"{brief['type_name']} · {brief['platform_name']}")
                        st.caption(brief['hook'][:50] + "...")

                        with st.expander("详情"):
                            st.write(brief)

# ═══════════════════════════════════════
# 模式3: 格式库
# ═══════════════════════════════════════
elif mode == "📖 格式库":
    st.title("📖 8种装修内容格式")
    st.caption("不是财经口播。装修行业原生表达方式。")

    cols = st.columns(2)
    for i, (fmt_id, fmt) in enumerate(CONTENT_FORMATS.items()):
        with cols[i % 2]:
            with st.container(border=True):
                st.subheader(f"{fmt['icon']} {fmt['name']}")
                st.caption(f"视觉: {fmt['visual']}")
                st.markdown("**结构:**")
                for s in fmt['structure']:
                    st.markdown(f"- {s}")
                st.markdown("**钩子示例:**")
                for h in fmt['hook_examples']:
                    st.caption(f"· {h}")
                st.caption(f"适用平台: {', '.join(fmt['platforms'])}")

# ═══════════════════════════════════════
# 模式4: 视觉语言库
# ═══════════════════════════════════════
elif mode == "🎬 视觉语言库":
    st.title("🎬 6种视觉表达方式")
    st.caption("装修内容的视觉语言——不是人物出镜口播")

    cols = st.columns(2)
    for i, (vid, vis) in enumerate(VISUAL_LANGUAGE.items()):
        with cols[i % 2]:
            with st.container(border=True):
                st.subheader(f"🎬 {vis['name']}")
                st.caption(f"代号: {vid}")
                st.markdown(f"**拍摄方式:** {vis['shot']}")
                st.markdown("**适用于:**")
                for s in vis['suitable']:
                    fmt_name = CONTENT_FORMATS.get(s, {}).get('name', s)
                    st.markdown(f"- {fmt_name}")
