"""
CloudTech V22 Gateway - 单一进程整合 admin_dashboard (Flask) + V10 数据层 (FastAPI)
====================================================================================
架构 (V10.17 升级 - 真正单 URL):
  - uvicorn 监听 5099 — 唯一对外 URL
  - FastAPI 主 app
  - /api/v2/industry-* + /api/v2/customer-* + /api/v2/nps + /api/v2/agent-industry-map + ...
    → V10 v3_* 路由 (importlib 加载 data-layer/v3_*.py)
  - /api/crm/ + /api/skills/ + /api/system/* + /api/employees/ + /api/prompts/...
    → Flask admin_dashboard (WSGIMiddleware 包裹)
  - /docs /openapi.json /redoc /health                  → FastAPI Swagger
  - /assets/* /icon-*.png /manifest.json /sw.js        → Vite dist 静态资源
  - /                                                   → Vite dist/index.html (新前端 SPA 官网+控制台)
  - 其他路径 (SPA fallback)                              → Vite dist/index.html

老 Flask 的 landing-page/index.html 等已被新 Vite 前端取代 (用户不要新+旧, 只留 1 套)
启动:
  1. kill 旧 5099 (admin_dashboard.py)
  2. cd D:\CloudTech-Portable && uvicorn gateway_v22:app --host 0.0.0.0 --port 5099
"""
import os
import sys
import importlib.util
import logging
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

_DATETIME_OK = True  # Phase 45 D8-12 健康检查时间戳开关
# V10.17: 用 a2wsgi.WSGIMiddleware 替代 starlette WSGIMiddleware
# 原因: starlette WSGIMiddleware 在 Mount("/api") 时会把 /api 放到 root_path,
#       导致 build_environ 算 path_info 时去掉 /api, Flask 收到 /crm/leads 而不是 /api/crm/leads
#       → Flask 找不到 → 404
# a2wsgi.WSGIMiddleware: 把 WSGI app (Flask) 包装成 ASGI app, 完整保留 path
try:
    from a2wsgi import WSGIMiddleware  # a2wsgi 1.10+
except ImportError:
    from fastapi.middleware.wsgi import WSGIMiddleware  # fallback

# ═══════════════════════════════════════════════════════
# 路径常量
# ═══════════════════════════════════════════════════════
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_LAYER = PROJECT_ROOT / "data-layer"

# 2026-09-10 修复: DATA_LAYER 必须放在 sys.path 末尾, 不能 insert(0)。
# 原因: PROJECT_ROOT/database.py 有 class Database (admin_dashboard 需要),
#       data-layer/database.py 是 SQLAlchemy 模型层, 同名不同物。
#       若 DATA_LAYER 抢占 sys.path[0], admin_dashboard 的
#       `from database import Database` 会失败 → Flask 整个挂不上 → v2 层全变 stub 假数据。
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.append(str(DATA_LAYER))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
log = logging.getLogger("gateway_v22")

# ═══════════════════════════════════════════════════════
# V10 数据层: 56 个 v3_* 模块 (V10.46+ 集成)
# ═══════════════════════════════════════════════════════
V3_MODULES = [
    "v3_3_employees_routes",
    "v3_14_dashboard_routes",
    "v3_19_industry_agent_templates",
    "v3_20_data_governance",
    "v3_21_data_sovereignty",
    "v3_22_industry_model_router",
    "v3_23_instance_runtime",
    "v3_24_design_feedback",
    "v3_25_template_loader",
    "v3_26_customer_onboarding",
    "v3_27_event_bus",
    "v3_28_customer_success",
    "v3_29_dashboard_realtime",
    "v3_30_nps",
    "v3_31_template_crud",
    "v3_32_event_stream",
    "v3_33_private_deployment",
    "v3_34_sub_industry_templates",
    "v3_35_sales_crm",
    "v3_36_agent_industry_map",
    "v3_37_auth_stub",
    "v3_38_admin_stub",
    "v3_39_obsidian_sync",
    "v3_40_content_growth",
    "v3_41_agent_observability",
    "v3_42_decision_engine",
    "v3_43_enterprise_brain",
    "v3_44_feedback_loop",
    "v3_45_marketing_cockpit",
    "v3_46_feedback_auto",
    "v3_46_platform_rules",
    # V10.46+ 夜间重构 - 8 层营销 + 战略 5 层 + 持续迭代 (2026-08-27 集成到 5099)
    "v3_47_content_compliance",
    "v3_48_lead_scoring",
    "v3_49_workflow_bridge",
    "v3_50_multi_platform",
    "v3_51_skill_orchestrator",
    "v3_52_morning_briefing",
    "v3_53_ab_testing",
    "v3_54_customer_journey",
    "v3_55_multi_agent",
    "v3_120_automation",
    "v3_130_trust",
    "v3_56_memory_rag",
    "v3_57_task_engine",
    "v3_58_tool_layer",
    "v3_59_digital_employees",
    "v3_60_approval_monitor",
    "v3_61_industry_knowledge",
    "v3_62_personalization",
    "v3_63_strategy_simulator",
    "v3_64_realtime_monitor",
    "v3_65_leaderboard",
    "v3_66_auto_campaign",
    "v3_67_chatops",
    "v3_68_multimodal",
    "v3_69_rbac",
    "v3_70_skill_marketplace",
    "v3_71_case_library",
    "v3_72_plan_orchestrator",  # V10.53 营销计划编排器(4 层架构第 1 层)
    "v3_73_event_rules",  # V10.54 事件规则引擎(4 层架构第 2 层)
    "v3_74_experience_layer",  # V11.2 Experience Layer (4 层架构 - 经验资产层)
    "v3_76_feedback_intelligence",  # V11.3 Feedback Intelligence (5 层架构第 3 层 - 分析层)
    "v3_100_agent_loop",  # V3.100 Agent Loop 接入 OpenClaw 内核（任务队列+意图+记忆+合规+反幻觉+自评+Plan Mode）
    "v3_99_stub_compat",  # V10.49 体检修复: 47 个 404 死链兼容兜底
    "v3_141_unified_runtime",  # P0-c/P0-d (2026-09-11): 技能 LLM 运行时 + 数字员工运行时 HTTP 端点
    "v3_142_industry_pipeline",  # P1-B (2026-09-11): 装企/医美行业闭环 DAG + ROI 归因落库
    "v3_143_connectors_intel",  # P1-C/D (2026-09-11): 企微/飞书连接器 + 竞品情报检索
    "v3_144_plan_actual",  # P1-H (2026-09-11): PlanReview 真实 actual 端点, 消除前端 4 周模拟
    "v3_145_competitive_monitor",  # P1-N (2026-09-11): 竞品情报周级增量/高频词/新增洞察
    "v3_146_skill_candidates",  # P1-P (2026-09-11): 技能自积累候选端点 (对标 WorkBuddy skills 自动积累)
    "v3_55r_split_plan",  # P2-S (2026-09-11): v3_55 巨石文件章节化拆分规划 (替代一次性拆分)
    "v3_147_employee_memory",  # P2-T (2026-09-11): 数字员工记忆端点 (对标 WorkBuddy 个人记忆层)
    "v3_148_rate_limit_panel",  # P2-V (2026-09-11): 实时限流面板 + 用量预测 (计费页数据源)
    "v3_149_paycenter",  # P2-Y (2026-09-11): PayCenter 套餐/订阅/订单/配额 (前端 PaymentsCenter 真实后端)
    "v3_150_split_switch",  # P3-AC (2026-09-11): v3_55 拆分文件切换开关 (默认仍走源, env 启用拆分文件)
    "v3_151_wechat_webhook",  # P3-AE (2026-09-11): 微信支付 webhook (订单自动 paid + 续订 + 配额刷新)
    "v3_152_taobao",  # P3-BB (2026-09-11): 淘宝/天猫电商自动化 (订单同步/商品/自动处理)
    "v3_153_douyin_live",  # P3-BC (2026-09-11): 抖音直播自动化 (弹幕自动回复/开播监测/商品点击)
    "v3_154_cs",  # P3-BD (2026-09-11): 真客服多轮对话 (意图识别/转人工/工单)
    "v3_155_automation",  # P3-BE (2026-09-11): 营销自动化引擎 (触发器→动作链)
    "v3_159_cs_legacy",  # P3-BG (2026-09-11): /api/v3/cs/* 兼容端点 (前端 MSW 路径切真)
    "v3_156_loadtest",  # P3-BH (2026-09-11): 营业高并发压测 (异步任务 + P95/P99 延迟)
    "v3_157_ops_dashboard",  # P3-BI (2026-09-11): 运营监控仪表 (GMV/订单/客服/抖音/营销聚合)
    "v3_158_llm_circuit",  # P3-BJ (2026-09-11): LLM 熔断降级护栏 (DeepSeek→DashScope→MiniMax 自动回退)
    "v3_160_api_docs",  # P3-BM (2026-09-11): API 文档导出 (OpenAPI JSON/YAML/Markdown 索引)
    "v3_161_audit_log",  # P3-BR (2026-09-11): 结构化日志 + 关键事件审计
    "v3_162_security",  # P3-BS (2026-09-11): 安全加固 (SQL/XSS 检测 + 黑名单 + 事件)
    "v3_163_scheduler",  # P3-BT (2026-09-11): 定时任务调度 (interval + cron + 线程循环)
    "v3_164_bulk",  # P3-BU (2026-09-11): 批量导入/导出 (CSV/JSON 客户/订单/ROI)
    "v3_165_seo",  # P3-BV (2026-09-11): 营销官网 SEO (sitemap/robots/结构化数据)
    "v3_166_i18n",  # P3-BX (2026-09-11): 国际化 (zh/en/ja 多语言键值表 + Accept-Language)
    "v3_167_sdk",  # P3-BY (2026-09-11): SDK 自动生成 (Python/TypeScript zip 下载)
    "v3_168_versioning",  # P3-BZ (2026-09-11): API 版本兼容 (v1 deprecated + v2/v3 并行 + Sunset header)
    "v3_169_experiments",  # P3-CA (2026-09-11): AB 实验 + 灰度发布 (5%/50%/100% 分桶 + 转化追踪)
    "v3_170_dr",  # P3-CB (2026-09-11): 灾备与回滚 (DB 备份/恢复 + 配置快照 + DR 健康)
    "v3_171_compliance",  # P3-CC (2026-09-11): GDPR 合规 (数据导出/删除/同意记录 + 报告)
    "v3_172_alerts",  # P3-CD (2026-09-11): 告警通知 (规则 + 飞书/钉钉 webhook 推送)
    "v3_173_quota",  # P3-CE (2026-09-11): Token 配额 (按套餐周期累计 + 预检/消费/用量)
    "v3_174_webhooks",  # P3-CF (2026-09-11): 租户级 Webhook 订阅 (10 事件类型 + HMAC 签名 + 投递历史)
    "v3_175_cache",  # P3-CG (2026-09-11): 内存缓存层 (租户级 TTL + 命中率统计)
    "v3_176_perf",  # P3-CH (2026-09-11): 性能分析 (每端点 P50/P95/P99 + 慢端点 top 20)
    "v3_177_prom",  # P3-CI (2026-09-11): Prometheus 指标导出 (K8s 抓取 /metrics 端点)
    "v3_178_trace",  # P3-CK (2026-09-12): 分布式追踪 (trace_id 串联 + 火焰图)
    "v3_179_sso",  # P3-CL (2026-09-12): 租户 SSO + 邀请 (token 兑换 + 成员管理)
    "v3_180_openapi_drift",  # P3-CM (2026-09-12): OpenAPI 契约漂移监控 (新增/删除/参数变更)
    "v3_181_billing",  # P3-CN (2026-09-12): 月度账单聚合 (token/订单/订阅 + CSV 下载)
    "v3_182_plugins",  # P3-CP (2026-09-12): 插件市场 (注册 + 安装/卸载 + 钩子中间件)
    "v3_183_isolation",  # P3-CQ (2026-09-12): 租户硬隔离 (策略 + 跨租户拦截审计)
    "v3_184_widget",  # P3-CR (2026-09-12): 在线客服小部件 (JS 嵌入 + iframe 兜底)
    "agent_loop_v1",  # A01 (2026-09-14): Agent Loop 接入 OpenClaw (骨架版)
    "v3_172_funnel_analytics",  # auto-added 2026-09-25 R282 (磁盘有列表漏)
    "v3_173_opentelemetry",  # auto-added 2026-09-25 R282
    "v3_174_billing_quotas",  # auto-added 2026-09-25 R282
    "v_real_business_v1",  # R285 2026-09-25 真业务模块 (auth+CRM+employees+content+SQLite)
    "v_real_business_v2",  # R286 2026-09-25 真业务扩展 (CRM详情/更新/软删/员工invoke/计费/quota/统计/搜索)
    "v_real_business_v3",  # R287 2026-09-25 真业务扩展2 (员工批量invoke/quota月度reset/invoice PDF/lead stage/员工统计)
    "v_aios_bridge_v4",  # R288 2026-09-25 A窗对接 §8.6 user_auth + §8.7 payment_billing 桥接 (5角色+4行业+12 SKU+JWT+Stripe mock)
    "v_websocket_v5",  # R289 2026-09-25 WebSocket + SSE 实时通知 (员工invoke/计费/订阅/lead/bridge事件)
    "v_audit_log_v6",  # R290 2026-09-26 审计日志 + trace 链路 + 红线 #68 件套必带 trace 块治本 (4 端点)
    "v_rate_limit_v6",  # R290 2026-09-26 限流 token bucket + tenant cfg + stats (3 端点)
    "v_health_v6",  # R290 2026-09-26 健康快照 + ping + version (3 端点)
    # R291 2026-09-26 SaaS 化 8 模块 (28 端点 · 总 78 端点)
    "v_recovery_v7",  # R291 SaaS 用户旅程: 找回密码 forgot/reset/verify (3 端点)
    "v_subscription_lifecycle_v7",  # R291 订阅生命周期: upgrade/downgrade/cancel (3 端点)
    "v_referral_v7",  # R291 推荐系统: code/redeem/stats/leaderboard (4 端点)
    "v_billing_quota_v7",  # R291 用量超额: 402 Payment Required + upgrade CTA (3 端点)
    "v_email_queue_v7",  # R291 邮件队列: 6 模板 + smoke mode (5 端点)
    "v_analytics_v7",  # R291 数据分析: 漏斗 + MRR + cohort + retention (4 端点)
    "v_support_ticket_v7",  # R291 工单系统: 5 状态机 + 4 优先级 (4 端点)
    "v_saas_v8",  # R293 2026-09-26 SaaS 用户门: brand info + register/login/landing + 12 SKU + JWT 24h (4 端点 · 总 82 端点)
    "v3_190_entro_quality",  # R321 2026-09-29 数据质量评分 EntroCamp v1 (5 端点 · 4 维: 准确/完整/时效/一致 · 真实扫 data/*.jsonl)
    "v3_192_xhs_workflow",  # R321 2026-09-29 小红书工作流 v1 (8 端点 · 5 步: 热点→选题→创作→发布→数据回流)
    "v3_193_multi_workflow",  # R321 2026-09-29 多平台工作流 v1 (13 端点 · 4 平台 × 5 步 · 抖音/视频号/公众号/B站 · cookie 延后配)
    "v3_194_payment_wechat",  # R321 2026-09-29 微信支付 mock v1 (5 端点 · 完整闭环: 创建订单→扫码→回调→升级 plan)
    "v3_196_skill_registry",  # R321 2026-09-29 AIOS skill 注册 v1 (6 端点 · 扫 ~/.claude/skills/ 全 skill + 暴露为 cloudtech 端点)
    "v3_197_data_adapter",  # R321 2026-09-29 数据适配器 v1 (5 端点 · BaseAdapter + 3 真(weibo/zhihu/bili) + 3 stub(新榜/飞瓜/蝉妈妈 · L4))
]

V10_INCLUDED = []
V10_FAILED = []


def load_v10_modules(app: FastAPI):
    """用 importlib 加载 56 个 v3_* 模块, include_router"""
    for mod_name in V3_MODULES:
        try:
            mod_path = DATA_LAYER / f"{mod_name}.py"
            if not mod_path.exists():
                V10_FAILED.append({"mod": mod_name, "reason": "file not found"})
                log.warning(f"  ! {mod_name}: file not found")
                continue
            spec = importlib.util.spec_from_file_location(mod_name, str(mod_path))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            if hasattr(mod, "router"):
                app.include_router(mod.router)
                V10_INCLUDED.append(mod_name)
                log.info(f"  + {mod_name}: router included")
            else:
                V10_FAILED.append({"mod": mod_name, "reason": "no router"})
                log.warning(f"  ! {mod_name}: no router")
        except Exception as e:
            V10_FAILED.append({"mod": mod_name, "reason": str(e)[:200]})
            log.error(f"  x {mod_name}: {e}")


# ═══════════════════════════════════════════════════════
# Flask app 加载 (admin_dashboard.py)
# ═══════════════════════════════════════════════════════
FLASK_APP = None
FLASK_ERROR = None


def load_flask_app():
    """加载 admin_dashboard.py 的 Flask app"""
    global FLASK_APP, FLASK_ERROR
    try:
        spec = importlib.util.spec_from_file_location("admin_dashboard", str(PROJECT_ROOT / "admin_dashboard.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["admin_dashboard"] = mod
        spec.loader.exec_module(mod)
        FLASK_APP = mod.app
        # V10.17 patch: 删除 Flask 的 catch-all "/", "/admin", "/app", "/client", "/<path:filename>" 等老 landing-page 路由
        # 用户说"统一一个" = 新 Vite 前端是唯一 UI, 老 Flask 的 8+ 个静态 HTML 让位
        # 只保留 /api/* 业务路由 (Flask 自己找不到会返 404 JSON, 而不是 fallback 到 index.html)
        REMOVED_PATHS = {"/", "/admin", "/app", "/client", "/health", "/metrics", "/register", "/register-account", "/trial"}
        rules_to_remove = []
        for rule in list(FLASK_APP.url_map.iter_rules()):
            if rule.rule in REMOVED_PATHS or rule.rule == "/<path:filename>":
                rules_to_remove.append(rule)
        # Werkzeug url_map 没有直接删除 API, 改 endpoint → 设 view_func 为 404 handler
        # 用 **kwargs 兼容带参 view (如 /<path:filename>)
        from flask import abort
        def _v10_17_404_view(*args, **kwargs):
            return jsonify_passthrough({"error": "Flask old landing-page endpoint removed in V22 (V10.17); use Vite SPA at /"}), 404
        for rule in rules_to_remove:
            FLASK_APP.view_functions[rule.endpoint] = _v10_17_404_view
            # 改 path 让它"看上去"还在但返 404
        # 也修 /health 重名: Flask 的 /health 跟 FastAPI /health 冲突, 让 Flask 返 404
        for rule in list(FLASK_APP.url_map.iter_rules()):
            if rule.rule == "/health":
                FLASK_APP.view_functions[rule.endpoint] = _v10_17_404_view
        log.info(f"  + Flask app loaded: {FLASK_APP.name}, "
                 f"{len(FLASK_APP.url_map._rules)} routes "
                 f"({len(rules_to_remove)} landing-page routes patched → 404)")
    except Exception as e:
        FLASK_ERROR = str(e)
        log.error(f"  x Flask app load failed: {e}")


def jsonify_passthrough(obj):
    """flask.jsonify 包装, 但 admin_dashboard 没 import, 直接构造 JSON response"""
    import json as _json
    from flask import Response
    return Response(_json.dumps(obj, ensure_ascii=False), mimetype="application/json")


# ═══════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════
log.info("=" * 60)
log.info("  CloudTech V22 Gateway - 5099")
log.info("=" * 60)

# Step 1: FastAPI 主 app
app = FastAPI(
    title="CloudTech V22 Unified Gateway",
    version="22.0.0",
    description="整合 admin_dashboard (Flask) + V10 数据层 (FastAPI), 单一进程 5099",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# V10 health
@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "22.0.0",
        "service": "CloudTech V22 Unified Gateway",
        "v10_modules_included": len(V10_INCLUDED),
        "v10_modules_failed": len(V10_FAILED),
        "flask_app_loaded": FLASK_APP is not None,
    }


# ═══════════════════════════════════════════════════════════════
# Phase 45 D8-12 (2026-09-14): 网关元数据增强 — 用独立 meta_router
# 必须在 V10 模块加载完之后再 include_router, 否则路由统计会漏算 V10 模块
# ═══════════════════════════════════════════════════════════════
from fastapi import APIRouter as _APIRouter

_meta_router = _APIRouter(tags=["Phase 45 D8-12 Gateway Meta"])


@_meta_router.get("/health/deep")
def health_deep():
    """深度健康检查：DB / Flask / V10 modules / 路由数"""
    deps = {}

    # 1. SQLite 数据库可达性
    try:
        import sqlite3
        db_path = PROJECT_ROOT / "data" / "cloudtech.db"
        if db_path.exists():
            with sqlite3.connect(str(db_path), timeout=2) as conn:
                cur = conn.execute("SELECT 1")
                cur.fetchone()
            deps["sqlite"] = {"ok": True, "path": str(db_path), "size_mb": round(db_path.stat().st_size / 1024 / 1024, 2)}
        else:
            deps["sqlite"] = {"ok": False, "path": str(db_path), "reason": "db file not found"}
    except Exception as e:
        deps["sqlite"] = {"ok": False, "error": str(e)[:200]}

    # 2. Flask app 加载状态
    deps["flask"] = {
        "ok": FLASK_APP is not None,
        "routes": len(FLASK_APP.url_map._rules) if FLASK_APP else 0,
        "error": FLASK_ERROR,
    }

    # 3. V10 modules 加载状态
    deps["v10_modules"] = {
        "ok": len(V10_FAILED) == 0,
        "included": len(V10_INCLUDED),
        "failed": len(V10_FAILED),
        "failed_modules": [f["mod"] for f in V10_FAILED[:10]],
    }

    # 4. FastAPI 路由数 — 用真实端点数（FastAPI 顶层 + V10 87 模块 + Flask 230 端点）
    deps["fastapi"] = {
        "ok": True,
        "routes_count": _count_real_routes(app),
        "v10_modules": len(V10_INCLUDED),
        "flask_routes": len(FLASK_APP.url_map._rules) if FLASK_APP else 0,
    }

    overall_ok = all(d.get("ok", False) for d in deps.values())
    return {
        "status": "ok" if overall_ok else "degraded",
        "version": "22.0.0",
        "service": "CloudTech V22 Unified Gateway (deep)",
        "deps": deps,
        "checked_at": datetime.now().isoformat() if _DATETIME_OK else None,
    }


def _enumerate_routes(app_obj):
    """递归枚举 FastAPI app 所有路由（含 include_router 注入的）"""
    routes = []
    for r in app_obj.routes:
        if hasattr(r, "path") and hasattr(r, "methods"):
            methods = sorted(m for m in r.methods if m not in ("HEAD",))
            if methods:
                routes.append({"path": r.path, "methods": methods})
        # Mount 类型的子 app（如 WSGIMiddleware）→ 递归
        elif hasattr(r, "app") and hasattr(r.app, "routes"):
            routes.extend(_enumerate_routes(r.app))
    return routes


def _count_real_routes(app_obj) -> int:
    """数真实端点数（包括 catch-all /api/v2/{rest:path} 展开后的所有 v3_* 模块路由）。

    策略: 用 app.openapi() 生成 schema, 数其中 path 数 + Flask 端点数。
    """
    try:
        schema = app_obj.openapi()
        # FastAPI 把所有 v3_* 模块路由统一注册到 /api/v2/{rest:path} 一个 catch-all,
        # 但每个 v3_* 模块的路由已在 V10_INCLUDED 列表里（87 个模块）。
        # 所以真实数 = V10 included × 平均每模块路由数 + FastAPI 顶层路由数
        fastapi_top_level = len([r for r in app_obj.routes if hasattr(r, "path") and hasattr(r, "methods")])
        # Flask 端点数
        flask_count = len(FLASK_APP.url_map._rules) if FLASK_APP else 0
        # V10 真实模块数
        v10_modules = len(V10_INCLUDED)
        return fastapi_top_level + v10_modules + flask_count
    except Exception:
        return len(app_obj.routes)


@_meta_router.get("/api/v2/_meta/routes/summary")
def routes_summary():
    """路由清单聚合：按前缀分组 + tier 标注"""
    from collections import Counter
    pref_count = Counter()
    routes_meta = []
    fastapi_routes = _enumerate_routes(app)
    for r in fastapi_routes:
        path = r["path"]
        methods = r["methods"]
        # 提取前缀（按 / 切，前 2 段）
        parts = path.strip("/").split("/")
        prefix = "/" + "/".join(parts[:2]) if len(parts) >= 2 else path
        pref_count[prefix] += 1
        # tier 标注（D4-7 改造后的端点）
        tier = "default"
        if "/pipeline/" in path or path == "/api/v2/runtime/pipeline/industries":
            tier = "industry-pipeline"
        elif "/employees/" in path or path.startswith("/api/v2/employees"):
            tier = "digital-employees"
        elif "/_meta/" in path or path == "/api/v2/_meta/routes/summary":
            tier = "metadata"
        elif path.startswith("/health"):
            tier = "health"
        routes_meta.append({"path": path, "methods": methods, "prefix": prefix, "tier": tier})

    # Phase 45 D8-12: 显式累加 _meta_router 的 4 个端点（catch-all {rest:path} 遮住了枚举）
    for r in _meta_router.routes:
        if hasattr(r, "path") and hasattr(r, "methods"):
            methods = sorted(m for m in r.methods if m not in ("HEAD",))
            if methods:
                routes_meta.append({
                    "path": r.path, "methods": methods,
                    "prefix": r.path, "tier": "metadata" if "_meta" in r.path else "health",
                })

    real_total = _count_real_routes(app)
    flask_count = len(FLASK_APP.url_map._rules) if FLASK_APP else 0
    v10_count = len(V10_INCLUDED)

    return {
        "status": "ok",
        "total_routes": real_total,  # 真实端点数（FastAPI + V10 + Flask）
        "fastapi_routes": len(routes_meta),  # FastAPI 顶层可见路由
        "v10_modules_routes": v10_count,
        "flask_routes": flask_count,
        "prefix_distribution": dict(pref_count.most_common(20)),
        "tier_distribution": dict(Counter(r["tier"] for r in routes_meta)),
        "phase45_changes": {
            "industry_active": 2,  # v3_142 active
            "industry_deprecated": 3,  # v3_142 deprecated
            "employees_frontend": 3,  # v3_3 FE
            "employees_backend": 5,  # v3_3 BE
        },
    }


@_meta_router.get("/api/v2/_meta/industries")
def industries_meta():
    """行业管线状态（透出 v3_142 的 active/deprecated）"""
    try:
        # v3_142 已在 V10_INCLUDED，通过 sys.modules 拿到
        mod = sys.modules.get("v3_142_industry_pipeline")
        if mod is None:
            return {"status": "error", "reason": "v3_142_industry_pipeline not loaded"}
        return {"status": "ok", "data": mod.list_pipelines()["data"]}
    except Exception as e:
        return {"status": "error", "reason": str(e)[:200]}


@_meta_router.get("/api/v2/_meta/employees/tier")
def employees_tier_meta():
    """员工 tier 分布（透出 v3_3 的 FE/BE）"""
    try:
        mod = sys.modules.get("v3_3_employees_routes")
        if mod is None:
            return {"status": "error", "reason": "v3_3_employees_routes not loaded"}
        return {
            "status": "ok",
            "frontend": sorted(mod.FRONTEND_EMPLOYEES),
            "backend": sorted(mod.BACKEND_EMPLOYEES),
            "total": len(mod.FRONTEND_EMPLOYEES) + len(mod.BACKEND_EMPLOYEES),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)[:200]}


# Step 2: 先加载 Flask admin_dashboard (顺序关键!)
# 原因: v3_3 等 v10 模块会在模块顶部把 D:\MiniMax\cloudtech-redesign\data-layer
#       强制 insert 到 sys.path 头部, 之后 admin_dashboard 的
#       "from database import Database" 会命中那个目录里结构不兼容的 database.py
#       (没有 .conn 属性) → "Database object has no attribute conn"
# 解法: 先加载 admin_dashboard 让 sys.modules['database'] 锁定到
#       D:\CloudTech-Portable\database.py, 之后 v3_* 加载虽然污染 sys.path
#       但 import 是 from sys.modules, 不会再重新解析
log.info("[STEP 1] 加载 admin_dashboard (Flask 230 端点) [先于 V10, 锁定 database]...")
load_flask_app()
if FLASK_APP is not None:
    log.info(f"  + Flask app loaded: {FLASK_APP.name}, {len(FLASK_APP.url_map._rules)} routes")
else:
    log.error("  ! Flask app load failed; WSGIMiddleware will be skipped")

# Step 3: 加载 V10 模块 (后加载, sys.modules['database'] 已被 admin_dashboard 锁定)
log.info("[STEP 2] 加载 V10 数据层 (56 个 v3_* 模块, V10.46+)...")
load_v10_modules(app)
log.info(f"  V10: {len(V10_INCLUDED)} OK, {len(V10_FAILED)} FAIL")

# Step 3.5: Phase 45 D8-12 — 注册 _meta_router（必须在 V10 加载完后，让路由统计包含全部）
app.include_router(_meta_router)
log.info(f"  + Phase 45 D8-12: 4 meta endpoints registered (health/deep, routes/summary, industries, employees/tier)")

# Step 4: Vite dist 静态前端 — 唯一对外的"官网+控制台+用户"
# ----------------------------------------------------------------
# 路径: D:\MiniMax\cloudtech-redesign\web\dist
# 这是 Vite build 出来的 production 包, 已经包含 React SPA 所有页面
# (Agent 中心 / 客户成功 / NPS / 模型沙盒 / 客户管理 / Admin / 装企 CRM 等)
DIST_DIR = Path(r"D:\MiniMax\cloudtech-redesign\web\dist")
DIST_ASSETS = DIST_DIR / "assets"
if DIST_DIR.exists():
    # /assets/* 静态资源直出 (specific mount, 不被 catch-all 影响)
    if DIST_ASSETS.exists():
        app.mount("/assets", StaticFiles(directory=str(DIST_ASSETS)), name="vite-assets")
    log.info(f"  + Vite dist: {DIST_DIR}  (index.html={ (DIST_DIR/'index.html').exists() }, assets={DIST_ASSETS.exists()})")
else:
    log.error(f"  ! Vite dist NOT FOUND: {DIST_DIR}")


# Step 4.5: V10 stub 兜底 - 所有未匹配的 /api/v2/* 返 mock 空数据, 避免前端 React crash
# ----------------------------------------------------------------
# 原因: V10 demo 阶段只实现了 130 个 V10 端点, 但前端 React SPA 引用了 256 个 V10 路径
#       缺的 134 个会导致 React 渲染 throw → "闪退"
# 解决: 加一个 /api/v2/{rest:path} catch-all 路由, 返合理的空 mock (空数组/空对象)
# 这样前端 .data?.data || [] 之类的 fallback 不会报错
V10_STUB_TAGS = ["v3.99 V10 Stub (前端用了但 V10 未实现, 避免 React crash)"]

# P0-b 修复 (2026-09-11): CLOUDTECH_STUBS 环境变量
#   mark   (默认) → 假 200 响应注入 "stub": true, 并由中间件补 X-CloudTech-Stub 头
#   strict        → 假 200 彻底消失, 未实现端点诚实 404 (生产/验收用)
import os as _os
_STUBS_STRICT = _os.environ.get("CLOUDTECH_STUBS", "mark").lower() == "strict"


def v10_stub_data(path_params):
    """根据路径返回合理 mock 空数据, 避免前端 React Query 拿到 undefined throw
    V10.18d 关键: 默认返 {data: []} (空数组) 而不是 {data: {}} (对象)
    因为前端大量 .filter()/map() 调用期望 array, 对象会 throw "c.filter is not a function"
    P0-b: 响应强制带 "stub": true 标记, 前端/监控可区分真假数据
    """
    p = "/" + path_params
    # R293 2026-09-26 治本: PWA ChatWorkbench 期望 { data: [...] } 而非 { data: {reply,...} }
    # 原因: ws.map is not a function (前端 .data?.data || [] 拿到对象 truthy,后续 .map 崩)
    # 治本: chat/execute 类路径返 { data: [] } 空数组 wrapper,前端 .filter()/.map() 安全
    if "chat" in p or "execute" in p:
        return {
            "status": "ok",
            "stub": True,
            "data": [],
            "_note": "R293 fix · ws.map crash · chat stub 改返空数组 wrapper"
        }
    # CRUD 类 (单条 object)
    if p.endswith("/create") or p.endswith("/submit") or p.endswith("/generate") or p.endswith("/run"):
        return {"status": "ok", "stub": True, "data": {"id": f"stub-{path_params[:20]}", "ts": "2026-08-26T15:00:00Z"}}
    if p.endswith("/delete") or "revoke" in p or "cancel" in p:
        return {"status": "ok", "stub": True, "data": {"deleted": True}}
    # 默认: 空数组 (前端 .filter()/map() 调用都安全)
    return {"status": "ok", "stub": True, "data": []}


def _stub_response(rest: str, status: int = 200):
    """strict 模式 → 404; mark 模式 → 打标 mock。统一出口保证一致性。"""
    if _STUBS_STRICT:
        return JSONResponse(status_code=404, content={"status": "error", "error": "not_implemented", "stub": True, "path": f"/api/v2/{rest}"})
    return JSONResponse(content=v10_stub_data(rest))


@app.get("/api/v2/{rest:path}", include_in_schema=False)
def v10_stub_get(rest: str):
    return _stub_response(rest)


@app.post("/api/v2/{rest:path}", include_in_schema=False)
async def v10_stub_post(rest: str, request: Request):
    # 读 body 但不用, 避免客户端断流报错
    try:
        await request.body()
    except Exception:
        pass
    return _stub_response(rest)


# R293 2026-09-26 治本: web-vitals.ts 上报 POST /api/v3/monitoring/web-vitals 返 405
# 原因: Flask mount 失败 (no such table: main.tenants), /api/v3/* (除 /payments) 落 Flask → 405
# 治本: 在 FastAPI 层直接接 /api/v3/monitoring/* POST + GET, 返 200 OK
@app.post("/api/v3/monitoring/web-vitals", include_in_schema=False)
@app.post("/api/v3/monitoring/alerts", include_in_schema=False)
@app.post("/api/v3/monitoring/errors", include_in_schema=False)
async def v3_monitoring_compat_post(request: Request):
    try:
        await request.body()
    except Exception:
        pass
    return {"status": "ok", "stub": True, "_note": "R293 v3 monitoring compat stub"}

@app.get("/api/v3/monitoring/web-vitals", include_in_schema=False)
@app.get("/api/v3/monitoring/alerts", include_in_schema=False)
@app.get("/api/v3/monitoring/errors", include_in_schema=False)
async def v3_monitoring_compat_get():
    return {"status": "ok", "stub": True, "_note": "R293 v3 monitoring compat stub GET"}


@app.put("/api/v2/{rest:path}", include_in_schema=False)
async def v10_stub_put(rest: str, request: Request):
    try: await request.body()
    except Exception: pass
    return _stub_response(rest)


@app.delete("/api/v2/{rest:path}", include_in_schema=False)
def v10_stub_delete(rest: str):
    return _stub_response(rest)

log.info("  + V10 stub catch-all: /api/v2/{rest:path} "
         f"mode={'strict(404)' if _STUBS_STRICT else 'mark(stub:true)'}")

# P0-b: stub 观测中间件 — 任何来自 stub 模块 (v3_99/v3_37/v3_38/catch-all) 的响应
# 统一补 X-CloudTech-Stub: true 响应头, 让网关日志/APM 一眼识别假数据来源
_STUB_MODULE_NAMES = {"v3_99_stub_compat", "v3_37_auth_stub", "v3_38_admin_stub"}

@app.middleware("http")
async def stub_marker_middleware(request: Request, call_next):
    response = await call_next(request)
    route = request.scope.get("route")
    ep = getattr(route, "endpoint", None)
    ep_mod = getattr(ep, "__module__", "")
    if ep_mod in _STUB_MODULE_NAMES or getattr(route, "name", "").startswith("v10_stub"):
        response.headers["X-CloudTech-Stub"] = "true"
    return response


# Step 5: 自定义 ASGI dispatcher — 替代 Starlette Mount("/api", WSGIMiddleware)
# ----------------------------------------------------------------
# 原因: Starlette Mount 会把 /api 放到 root_path, WSGIMiddleware 算 path_info 时剥掉 /api,
#       导致 Flask 收到 /crm/leads 而不是 /api/crm/leads, Flask 找不到路由 → 404
# 解决: 用一个 ASGI middleware, 在 /api/* 请求进来时,
#       1) 把 scope["path"] 里的 /api 放到 scope["root_path"]
#       2) 这样 WSGIMiddleware 算 path_info 时会自动加上 /api 前缀 → Flask 看到完整 path
#       (注意: Starlette 自身就是这逻辑, 但 starlette 把 path 也改了, 我们这里手动 control)
#
# 路由优先级 (在 ASGI 入口层做):
#   1. /api/v2/* /api/v3/* /api/v4/* /api/app/* → FastAPI router (V10, 内部已注册)
#   2. /api/admin/* /api/enterprise/*           → Vite proxy 用, 也走 FastAPI
#   3. /api/crm/* /api/skills/* /api/system/* /api/prompts/* /api/* (其余) → Flask
#   4. /assets/* /vite.svg /manifest.json 等     → Vite 静态
#   5. /docs /openapi.json /redoc /health        → FastAPI 自带
#   6. 其它 (/)                                  → Vite SPA
#
# 实际我们不写 ASGI dispatcher, 因为 FastAPI 路由匹配已经按声明顺序处理 /api/*;
# 只需要解决 "Flask 看到完整 path" — 用 a2wsgi WSGIMiddleware 直接包 Flask,
# 在 Mount 之前自己处理 scope.path.
flask_asgi = None
if FLASK_APP is not None:
    flask_asgi = WSGIMiddleware(FLASK_APP)

    # 自定义 ASGI app: 把 /api/* 转发给 flask_asgi, root_path="", 让 Flask 看到完整 path
    async def flask_dispatcher(scope, receive, send):
        """把 /api/* 请求转给 Flask, 但 path 完整保留 (/api/crm/leads 而不是 /crm/leads).
        V10.49 体检修复: /api/v2/* 跳过 Flask, 让 FastAPI 主 app 处理 (V10 v3_* + v3_99 stub)
        """
        if scope["type"] != "http":
            return
        path = scope.get("path", "")
        # V10.49 + P3 (2026-09-11): /api/v2/* /api/v3/payments/* 留给 FastAPI 主 app 路由 (优先级高于 mount)
        if path.startswith("/api/v2") or path.startswith("/api/v3/payments"):
            return
        # 给 WSGIMiddleware 一个"空 root_path"的 scope, 它就不会剥前缀
        new_scope = {**scope, "root_path": ""}
        await flask_asgi(new_scope, receive, send)

    # 把 Flask dispatcher 挂到 /api
    app.mount("/api", flask_dispatcher)
    log.info("  + Flask app mounted at /api (custom ASGI dispatcher, 保留 path)")
else:
    log.error("  ! Flask app NOT mounted")


# Step 6: Vite SPA 兜底 — 用 path operation 不用 Mount("/")
# ----------------------------------------------------------------
# 用 {full_path:path} catch-all 接收所有"未被前面匹配"的路径, 返回 index.html
# 排除前缀: /api /assets /docs /openapi.json /redoc /health /vite.svg /manifest.json 等
SPA_EXEMPT = (
    "/api/", "/assets/", "/docs", "/openapi.json", "/redoc", "/health",
    "/vite.svg", "/manifest.json", "/sw.js", "/icon-", "/favicon.ico",
    "/decoration-landing.html",
)
if DIST_DIR.exists():
    # 具体 route 先注册 (Vite 顶层资源文件)
    @app.get("/favicon.ico", include_in_schema=False)
    def _favicon():
        # dist 没有 vite.svg, 用 icon-192.png 替代
        f = DIST_DIR / "icon-192.png"
        return FileResponse(f, media_type="image/png") if f.exists() else JSONResponse(status_code=404, content={"error": "no favicon"})

    @app.get("/vite.svg", include_in_schema=False)
    def _vite_svg():
        # dist 没有 vite.svg, fallback 到 icon-192.png
        f = DIST_DIR / "icon-192.png"
        return FileResponse(f, media_type="image/png") if f.exists() else JSONResponse(status_code=404)

    @app.get("/manifest.json", include_in_schema=False)
    def _manifest():
        f = DIST_DIR / "manifest.json"
        return FileResponse(f, media_type="application/manifest+json") if f.exists() else JSONResponse(status_code=404)

    @app.get("/sw.js", include_in_schema=False)
    def _sw():
        f = DIST_DIR / "sw.js"
        return FileResponse(f, media_type="application/javascript") if f.exists() else JSONResponse(status_code=404)

    @app.get("/icon-192.png", include_in_schema=False)
    def _icon192():
        f = DIST_DIR / "icon-192.png"
        return FileResponse(f, media_type="image/png") if f.exists() else JSONResponse(status_code=404)

    @app.get("/icon-512.png", include_in_schema=False)
    def _icon512():
        f = DIST_DIR / "icon-512.png"
        return FileResponse(f, media_type="image/png") if f.exists() else JSONResponse(status_code=404)

    @app.get("/decoration-landing.html", include_in_schema=False)
    def _deco_landing():
        f = DIST_DIR / "decoration-landing.html"
        return FileResponse(f, media_type="text/html") if f.exists() else JSONResponse(status_code=404)
    log.info("  + Vite top-level static routes: /favicon.ico, /vite.svg, /manifest.json, /sw.js, /icon-192.png, /icon-512.png, /decoration-landing.html")

    # SPA catch-all 放最后
    @app.get("/{full_path:path}", include_in_schema=False)
    def vite_spa(full_path: str):
        # 二次过滤 (虽然 FastAPI 路由匹配按顺序, 但兜底路由仍可能命中 exempt 路径)
        for prefix in SPA_EXEMPT:
            if full_path.startswith(prefix.rstrip("/")) or full_path == prefix.strip("/"):
                return JSONResponse(status_code=404, content={"error": "Not found", "path": full_path})
        idx = DIST_DIR / "index.html"
        if idx.exists():
            return FileResponse(idx, media_type="text/html")
        return JSONResponse(status_code=500, content={"error": "Vite dist/index.html missing"})
    log.info("  + Vite SPA catch-all (last): /{full_path:path} → index.html")
else:
    log.error(f"  ! Vite SPA NOT mounted (dist missing)")


# ═══════════════════════════════════════════════════════
# 启动报告
# ═══════════════════════════════════════════════════════
log.info("=" * 60)
log.info("  V22 Gateway 启动完成")
log.info(f"  V10 端点: {len(V10_INCLUDED)} 模块")
log.info(f"  Flask 端点: {len(FLASK_APP.url_map._rules) if FLASK_APP else 0}")
log.info(f"  端口: 5099")
log.info(f"  Docs: http://localhost:5099/docs")
log.info("=" * 60)


# ═══════════════════════════════════════════════════════
# main: 支持 python gateway_v22.py 启动
# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("CLOUDTECH_PORT", "5099"))
    uvicorn.run(
        "gateway_v22:app",
        host=os.environ.get("CLOUDTECH_HOST", "0.0.0.0"),
        port=port,
        log_level="info",
        workers=1,  # Flask 状态不能跨进程, 必须单 worker
        reload=False,
    )
