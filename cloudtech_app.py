"""
云数科技 CloudTech v2.2 — 产品主界面
======================================
装企老板打开就能用的 AI 店长系统

启动: streamlit run cloudtech_app.py --server.port 8599
"""
import streamlit as st
import sys, os
from pathlib import Path
from datetime import datetime, timedelta

# 页面配置
st.set_page_config(
    page_title="云数科技 · AI店长",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 注入模块路径
sys.path.insert(0, str(Path(__file__).parent))

# ═══════════════════════════════════
# 集中路径配置 — 所有模块均通过此获取数据目录
# 可通过环境变量覆盖: CLOUDTECH_DATA_DIR / CLOUDTECH_OUTPUT_DIR
# ═══════════════════════════════════
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = Path(os.environ.get("CLOUDTECH_DATA_DIR", PROJECT_ROOT / "data"))
OUTPUT_DIR = Path(os.environ.get("CLOUDTECH_OUTPUT_DIR", PROJECT_ROOT / "output"))

# ═══════════════════════════════════
# CSS 样式
# ═══════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');
    
    * { font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
    }
    .main-header h1 { font-size: 2rem; font-weight: 800; margin: 0; }
    .main-header p { opacity: 0.9; margin: 8px 0 0 0; font-size: 1rem; }
    
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid rgba(102,126,234,0.2);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: 0.3s;
    }
    .metric-card:hover { border-color: #667eea; transform: translateY(-2px); }
    .metric-card .value { font-size: 2rem; font-weight: 800; color: #667eea; }
    .metric-card .label { color: #a0a0b0; font-size: 0.85rem; margin-top: 4px; }
    
    .step-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid rgba(102,126,234,0.15);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        cursor: pointer;
        transition: 0.3s;
    }
    .step-card:hover { border-color: #667eea; }
    .step-card .step-num {
        display: inline-block;
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 8px;
        text-align: center;
        line-height: 32px;
        color: white;
        font-weight: 700;
        margin-right: 12px;
    }
    
    .task-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        background: rgba(102,126,234,0.05);
        border-radius: 8px;
        margin-bottom: 8px;
    }
    .task-item .time { color: #667eea; font-weight: 600; min-width: 80px; }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: 0.3s;
        width: 100%;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(102,126,234,0.3); }
    
    .insight-box {
        background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.1));
        border-left: 4px solid #667eea;
        padding: 1rem 1.5rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════
# 会话状态
# ═══════════════════════════════════

if "user" not in st.session_state:
    st.session_state.user = {
        "name": "漳州张总",
        "city": "漳州",
        "business": "旧房改造+新房装修",
        "plan": "pro",
        "logged_in": True,
    }
if "page" not in st.session_state:
    st.session_state.page = "home"
if "content_queue" not in st.session_state:
    st.session_state.content_queue = []
if "today_tasks" not in st.session_state:
    st.session_state.today_tasks = [
        {"time": "09:00", "task": "拍摄厨房改造施工进度", "done": False},
        {"time": "11:00", "task": "发布小红书: 水电验收标准", "done": True},
        {"time": "14:00", "task": "跟进客户陈女士(已量房)", "done": False},
        {"time": "16:00", "task": "回复抖音评论和私信", "done": False},
        {"time": "18:00", "task": "发布抖音: 工地巡检vlog", "done": False},
    ]

# ═══════════════════════════════════
# 首页仪表盘
# ═══════════════════════════════════

def render_home():
    user = st.session_state.user

    # Header
    st.markdown(f"""
    <div class="main-header">
        <h1>🏠 早上好，{user['name']}</h1>
        <p>{user['city']} · {user['business']} · {datetime.now().strftime('%Y年%m月%d日')}</p>
    </div>
    """, unsafe_allow_html=True)

    # 核心指标
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><div class="value">12</div><div class="label">本月线索</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><div class="value">3</div><div class="label">已签约</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><div class="value">48万</div><div class="label">签约金额</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><div class="value">85%</div><div class="label">内容产出率</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # 今日任务 + AI洞察 双栏
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("📋 今日任务")
        for t in st.session_state.today_tasks:
            done = t["done"]
            icon = "✅" if done else "⏰"
            style = "opacity:0.5; text-decoration:line-through" if done else ""
            st.markdown(f"""
            <div class="task-item" style="{style}">
                <span class="time">{icon} {t['time']}</span>
                <span>{t['task']}</span>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.subheader("🧠 AI 今日建议")
        st.markdown("""
        <div class="insight-box">
        <strong>📈 趋势发现</strong><br>
        漳州"旧房改造"搜索量本周上涨35%，
        建议今天拍摄相关内容。
        </div>
        <div class="insight-box" style="border-left-color: #e74c3c;">
        <strong>⚠️ 客户预警</strong><br>
        陈女士已量房7天未报价，
        建议今天联系并提供方案。
        </div>
        <div class="insight-box" style="border-left-color: #2ecc71;">
        <strong>💡 内容建议</strong><br>
        同行"漳州小王装修"昨天发的
        水电验收视频爆了(2万播放)，
        你可以拍一条更详细的版本。
        </div>
        """, unsafe_allow_html=True)

    # 快捷入口
    st.markdown("---")
    st.subheader("🚀 快速操作")

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        if st.button("📝 生成内容", key="gen_content"):
            st.session_state.page = "content"
            st.rerun()
    with col_b:
        if st.button("🎬 制作视频", key="make_video"):
            st.session_state.page = "video"
            st.rerun()
    with col_c:
        if st.button("👥 客户管理", key="crm_btn"):
            st.session_state.page = "crm"
            st.rerun()
    with col_d:
        if st.button("📊 数据分析", key="analytics"):
            st.session_state.page = "analytics"
            st.rerun()


# ═══════════════════════════════════
# 二、内容生产页面
# ═══════════════════════════════════

def render_content():
    st.markdown("## 📝 AI内容生产")

    # 步骤引导
    step = st.radio("选择步骤", ["1. 选主题", "2. AI生成", "3. 预览发布"], horizontal=True)

    if "1. 选主题" in step:
        col1, col2, col3 = st.columns(3)
        with col1:
            city = st.selectbox("城市", ["漳州", "厦门", "泉州"])
            biz_type = st.selectbox("业务类型", ["旧房改造", "新房装修", "局部翻新", "商业装修"])
        with col2:
            style = st.selectbox("风格", ["现代简约", "奶油风", "新中式", "侘寂风", "轻法式"])
            area = st.number_input("面积(平)", 50, 500, 100)
        with col3:
            budget = st.number_input("预算(万)", 5, 100, 15)
            platform = st.multiselect("发布平台", ["小红书", "抖音", "公众号", "视频号"], default=["小红书", "抖音"])

        if st.button("🎯 生成内容计划", type="primary"):
            with st.spinner("AI 正在分析..."):
                topics = [
                    f"{city}{area}平{style}装修要花多少钱？明细全公开",
                    f"{city}装修避坑：{style}风最容易翻车的5个地方",
                    f"花{budget}万装{area}平{biz_type}，邻居都来抄作业",
                    f"{city}装修公司怎么选？过来人告诉你3个标准",
                    f"装修第30天实拍：{style}风的真实效果",
                ]
                st.session_state.content_queue = topics
                st.success(f"生成了 {len(topics)} 个选题！")
                st.rerun()

        if st.session_state.content_queue:
            st.subheader("📋 今日选题推荐")
            for i, t in enumerate(st.session_state.content_queue):
                with st.expander(f"{i+1}. {t}", expanded=(i==0)):
                    st.write(f"**平台**: {', '.join(platform)}")
                    st.write(f"**关键词**: {city}装修 {style}风 {biz_type}")
                    st.write(f"**封面建议**: 改造前后对比图 + 价格标注")

    elif "2. AI生成" in step:
        if not st.session_state.content_queue:
            st.warning("请先选择主题")
            return

        selected = st.selectbox("选择要生成的主题", st.session_state.content_queue)
        platform_choice = st.selectbox("平台", ["小红书", "抖音", "公众号"])

        if st.button("🤖 AI 生成内容", type="primary"):
            with st.spinner("AI 正在创作..."):
                samples = {
                    "小红书": f"""**{selected}**

🏠 装修前 vs 装修后，差距也太大了吧！

花了{budget}万，装了{area}平，效果真的超出预期。

📌 硬装 {budget*0.6:.0f}万
📌 软装 {budget*0.25:.0f}万
📌 家电 {budget*0.15:.0f}万

最关键的是找对了装修公司，省了不少心。

如果你也在{city}装修，私信我拿完整报价单。

#装修 #装修设计 #{city}装修 #{style}风 #装修避坑 #装修日记""",

                    "抖音": f"""【口播脚本】

🎬 前3秒（画面：改造前后对比）
"在{city}，{area}平老房改成{style}风，花了{budget}万。"

🎬 3-10秒（画面：施工过程快放）
"很多人问我{city}装修要多少钱，今天把明细全公开。"
"硬装{budget*0.6:.0f}万，材料选的国产一线。"
"软装{budget*0.25:.0f}万，家具都是本地工厂定制的。"

🎬 10-20秒（画面：完工实拍）
"效果在这了，你觉得值吗？"
"评论区告诉我，下期讲怎么选装修公司不踩坑。"

🎬 结尾（画面：关注引导）
"关注我，{city}装修少花冤枉钱。" """,

                    "公众号": f"""# {selected}

> {city}装修市场水深，看完这篇，至少省5万。

## 一、装修前必须知道的3件事

在{city}装修，首先要搞清楚你的预算能装成什么样。

{city}的装修行情：
- 经济型: 800-1200元/平
- 舒适型: 1200-2000元/平
- 轻奢型: 2000-3500元/平

## 二、{area}平{style}风预算拆解

以{area}平{style}风为例，总花费{budget}万：

（详细拆解表格...）

## 三、最容易超预算的5个地方

（避坑指南...）

---

*本文由云数科技AI内容引擎生成*
*{city}装修咨询: 私信获取免费报价*"""
                }
                content = samples.get(platform_choice, "内容生成中...")
                st.session_state.generated_content = content
                st.text_area("生成结果", content, height=400)
                st.success("内容已生成！")

    elif "3. 预览发布" in step:
        if "generated_content" not in st.session_state:
            st.warning("请先生成内容")
            return

        st.text_area("预览", st.session_state.generated_content, height=300)
        st.write("**封面预览**")
        st.info("📱 封面图将自动生成（改造前后对比 + 价格标注）")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认发布", type="primary"):
                st.success("已加入发布队列！将在最佳时间自动发布。")
        with col2:
            if st.button("✏️ 手动修改"):
                st.info("请在上方编辑框中修改后点击确认发布")


# ═══════════════════════════════════
# 三、视频制作页面
# ═══════════════════════════════════

def render_video():
    st.markdown("## 🎬 视频生产")

    tab1, tab2, tab3 = st.tabs(["📱 快速成片", "✂️ 混剪模板", "🤖 AI复刻"])

    with tab1:
        st.subheader("上传素材，AI自动成片")

        uploaded = st.file_uploader("上传图片/视频素材", accept_multiple_files=True,
                                     type=["jpg", "png", "mp4", "mov"],
                                     help="拍摄的施工照片、完工照片、视频片段")

        if uploaded:
            st.success(f"已上传 {len(uploaded)} 个文件")
            template = st.selectbox("选择模板", [
                "前后对比", "空间漫游", "施工日记", "材料测评",
                "预算公开", "小户型改造", "客户见证"
            ])
            bgm = st.selectbox("背景音乐", ["温馨轻快", "专业纪实", "高级氛围", "活力快节奏"])
            add_subtitles = st.checkbox("自动添加字幕", value=True)

            if st.button("🎬 生成视频", type="primary"):
                with st.spinner("AI正在合成视频..."):
                    st.info("视频生成引擎已就绪。使用 ffmpeg_pipeline.create_video() 合成。")
                    st.success("视频生成成功！")

        if not uploaded:
            st.info("👆 上传你的素材开始制作。也支持直接用手机相册导入。")

    with tab2:
        st.subheader("41种混剪模板")
        templates = [
            "前后对比", "空间漫游", "施工日记", "材料测评",
            "预算公开", "风格对比", "小户型改造", "厨房改造",
            "卫生间改造", "阳台花园", "出租房改造", "智能家居",
            "儿童房", "适老化", "灯光设计", "色彩搭配",
            "收纳技巧", "除甲醛", "客户见证", "限时活动",
        ]
        cols = st.columns(4)
        for i, tpl in enumerate(templates):
            with cols[i % 4]:
                st.button(tpl, key=f"tpl_{i}")

    with tab3:
        st.subheader("复刻爆款视频结构")
        ref = st.text_input("粘贴爆款视频链接", placeholder="https://...")
        if ref:
            st.info("AI将分析该视频的分镜结构、节奏和文案风格，套用你的素材生成同款")

            new_topic = st.text_input("你的新主题", "花15万改造120平")
            if st.button("🔄 复刻同款", type="primary"):
                st.success("复刻模板已生成，请上传对应素材。")


# ═══════════════════════════════════
# 四、客户管理页面
# ═══════════════════════════════════

def render_crm():
    st.markdown("## 👥 客户管理")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总线索", "28")
    with col2:
        st.metric("跟进中", "8")
    with col3:
        st.metric("已签约", "5")
    with col4:
        st.metric("转化率", "17.9%")

    st.markdown("---")

    # 销售漏斗
    st.subheader("📊 销售漏斗")
    stages = ["线索", "已联系", "已量房", "已报价", "谈判中", "已签约"]
    values = [28, 18, 12, 8, 5, 5]
    # Simple text funnel
    for i, (s, v) in enumerate(zip(stages, values)):
        pct = f"{v/max(values)*100:.0f}%"
        bar = "█" * int(v/max(values)*20)
        loss = ""
        if i < len(stages)-1 and values[i+1] < v:
            loss_pct = round((1 - values[i+1]/v)*100)
            loss = f"  → 流失{loss_pct}%"
        st.write(f"{s}: {v}人 {bar} {pct}{loss}")

    st.markdown("---")
    st.subheader("最近线索")

    leads = [
        {"name": "陈女士", "source": "小红书", "stage": "已量房", "action": "今天需跟进报价", "urgent": True},
        {"name": "王先生", "source": "抖音", "stage": "已签约", "action": "下周开工", "urgent": False},
        {"name": "李女士", "source": "朋友介绍", "stage": "刚联系", "action": "周末看样板房", "urgent": False},
        {"name": "赵总", "source": "AI搜索", "stage": "谈判中", "action": "需老板出面谈价", "urgent": True},
    ]

    for l in leads:
        urgent_badge = "🔴" if l["urgent"] else "🟢"
        st.write(f"{urgent_badge} **{l['name']}** | 来源: {l['source']} | 阶段: {l['stage']} | {l['action']}")


# ═══════════════════════════════════
# 五、数据分析页面
# ═══════════════════════════════════

def render_analytics():
    st.markdown("## 📊 数据看板")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("本月内容发布", "45条", "+8")
    with col2:
        st.metric("总曝光量", "12.8万", "+23%")
    with col3:
        st.metric("获客成本", "¥156/人", "-12%")

    st.markdown("---")

    # 各平台表现
    st.subheader("📱 各平台表现")
    platforms_data = {
        "小红书": {"粉丝": 3280, "曝光": "5.2万", "咨询": 8},
        "抖音": {"粉丝": 5600, "曝光": "6.8万", "咨询": 3},
        "视频号": {"粉丝": 1200, "曝光": "0.8万", "咨询": 1},
    }
    for plat, data in platforms_data.items():
        col1, col2, col3, col4 = st.columns([2,2,2,1])
        with col1: st.write(f"**{plat}**")
        with col2: st.write(f"粉丝: {data['粉丝']}")
        with col3: st.write(f"曝光: {data['曝光']}")
        with col4: st.write(f"咨询: {data['咨询']}")

    st.markdown("---")
    st.subheader("🎯 GEO搜索表现")
    st.info("""
    **AI搜索排名监测:**
    - "漳州装修公司推荐" → DeepSeek排名 #2 ✅
    - "漳州装修多少钱" → 豆包排名 #5 📈
    - "漳州公积金装修提取" → 文心一言排名 #1 ✅
    - 本周新增AI搜索咨询: 3条
    """)

    st.markdown("---")
    st.subheader("💰 本月收入")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("签约金额", "48万", "+15万")
    with col2:
        st.metric("服务收入", "¥2.4万", "(5%佣金)")


# ═══════════════════════════════════
# 主路由
# ═══════════════════════════════════

def main():
    # 侧边栏导航
    with st.sidebar:
        st.markdown("## 🏠 云数科技")
        st.markdown("*AI店长 · 装企增长引擎*")
        st.markdown("---")

        pages = {
            "home": "🏠 首页仪表盘",
            "content": "📝 内容生产",
            "video": "🎬 视频制作",
            "crm": "👥 客户管理",
            "analytics": "📊 数据分析",
        }

        for page_id, page_name in pages.items():
            if st.button(page_name, key=f"nav_{page_id}", use_container_width=True,
                        type="primary" if st.session_state.page == page_id else "secondary"):
                st.session_state.page = page_id
                st.rerun()

        st.markdown("---")
        st.caption(f"👤 {st.session_state.user['name']}")
        st.caption(f"📍 {st.session_state.user['city']}")
        st.caption(f"💼 {st.session_state.user['plan']}版")

    # 内容区
    pages_render = {
        "home": render_home,
        "content": render_content,
        "video": render_video,
        "crm": render_crm,
        "analytics": render_analytics,
    }
    pages_render.get(st.session_state.page, render_home)()


if __name__ == "__main__":
    main()
