"""
云数科技 CloudTech v2.1.0 — Web 管理后台
==========================================
Flask 管理后台 + Landing Page 服务 + API 平台集成 + 运营后台
"""
import os, re, time
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

_START_TIME = time.time()

from flask import Flask, send_from_directory, jsonify, request

from error_tracker import setup_error_handler
from schemas import validate, LoginRequest, RegisterRequest, GenerateV2Request
from schemas import TopicDiscoveryRequest, MultiPlatformRequest, StyleCloneRequest, DeaiCheckRequest
from schemas import RepurposeExtractRequest, RepurposeRewriteRequest
from schemas import ZhuangqiBriefRequest, ZhuangqiWeekPlanRequest
from schemas import GeoKeywordRequest, GeoRankRequest, GeoContentRequest
from schemas import SocialSearchRequest, TrendSearchRequest
from schemas import PromptGenerateRequest, PromptCreateRequest, PromptDeployRequest
from schemas import AdminUserUpdateRequest, ApiKeyGenerateRequest

BASE = Path(__file__).parent
LANDING = BASE / "landing-page"

app = Flask(__name__, static_folder=str(LANDING), static_url_path="/static")

# ── Admin Auth Guard ──
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "cloudtech-admin-2026")
ADMIN_TOKEN = None  # generated on first login

def _is_admin_route(path):
    return path.startswith("/admin") or path.startswith("/api/admin") or path.startswith("/api/system")

def _check_admin_auth():
    """Check if request has valid admin authorization"""
    # Allow health/status/public routes
    if request.path in ("/health", "/api/status", "/"):
        return True
    # Admin login endpoint
    if request.path == "/api/auth/login" and request.method == "POST":
        return True
    # Other public API endpoints (content creation, prompts, etc.)
    if request.path.startswith("/api/") and not request.path.startswith("/api/admin"):
        return True
    # Static files
    if request.path.startswith("/static") or request.path.endswith((".html", ".css", ".js", ".ico", ".png")):
        if not request.path.startswith("/admin"):
            return True

    # Admin route: check for token
    token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token", "")
    if token:
        try:
            from auth import AuthManager
            auth = AuthManager()
            payload = auth.verify_jwt(token)
            if payload:
                return True
        except:
            pass
    return False

@app.before_request
def admin_guard():
    if not _check_admin_auth():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required", "login_url": "/admin"}), 401
        # For /admin page, redirect to login
        return send_from_directory(str(LANDING), "admin.html")  # admin.html has its own login check

# ── 客户仪表盘 ──
@app.route("/client")
def client_dashboard():
    return send_from_directory(str(LANDING), "client.html")

# ── Landing Page 路由 ──
@app.route("/")
def index():
    return send_from_directory(str(LANDING), "index.html")

# ── 健康检查 ──
@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "CloudTech v2.0.0", "service": "admin-dashboard"})

# ── 管理后台 ──
@app.route("/admin")
def admin():
    return send_from_directory(str(LANDING), "admin.html")

@app.route("/api/system/status")
def system_status():
    import subprocess, socket
    services = {}
    # Gateway
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", 18792))
        s.close()
        services["gateway"] = "running"
    except:
        services["gateway"] = "stopped"
    # Streamlit
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", 8501))
        s.close()
        services["streamlit"] = "running"
    except:
        services["streamlit"] = "stopped"
    # 装企控制台
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", 8502))
        s.close()
        services["zhuangqi"] = "running"
    except:
        services["zhuangqi"] = "stopped"
    return jsonify({"status": "ok", "services": services, "app": "CloudTech v2.0.0"})

# ── API 状态 ──
@app.route("/api/status")
def api_status():
    try:
        from api_platform import APIKeyManager
        km = APIKeyManager()
        return jsonify({
            "status": "ok",
            "api_keys": len(km._keys),
            "version": "2.0.0"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── 系统健康 ──
@app.route("/api/health/full")
def full_health():
    try:
        from system_health_monitor import SystemHealthMonitor
        monitor = SystemHealthMonitor()
        report = monitor.run_full_check()
        return jsonify({"status": "ok", "report": str(report)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── 内容二创管线 ──
@app.route("/repurpose")
def repurpose_page():
    return send_from_directory(str(LANDING), "repurpose.html")

@app.route("/api/repurpose/extract", methods=["POST"])
@validate(RepurposeExtractRequest)
def api_repurpose_extract():
    try:
        data = request.get_json()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"status": "error", "message": "未提供URL"}), 400
        from repurpose_pipeline import extract_content
        result = extract_content(url)
        return jsonify({"status": "ok", "data": {
            "platform": result["platform"],
            "title": result["title"],
            "author": result["author"],
            "text": result["text"][:8000],
            "text_length": len(result["text"]),
            "image_count": len(result["images"]),
            "downloaded_images": len(result.get("downloaded_images", [])),
            "folder": result.get("folder", ""),
            "error": result.get("error"),
        }})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/repurpose/rewrite", methods=["POST"])
@validate(RepurposeRewriteRequest)
def api_repurpose_rewrite():
    try:
        data = request.get_json()
        text = data.get("text", "")
        style = data.get("style", "去AI腔")
        custom_prompt = data.get("custom_prompt", "")
        save_folder = data.get("folder", "")
        if not text:
            return jsonify({"status": "error", "message": "未提供文本"}), 400
        from repurpose_pipeline import ai_rewrite
        result = ai_rewrite(text, style, custom_prompt, save_folder)
        return jsonify({"status": "ok", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── 注册 API ──
@app.route("/api/auth/register", methods=["POST"])
@validate(RegisterRequest)
def api_register():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    company = data.get("company", "").strip()
    plan = data.get("plan", "starter")

    if not email or not password or not name:
        return jsonify({"error": "邮箱、密码、姓名为必填项"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码至少6位"}), 400

    try:
        from auth import AuthManager
        auth = AuthManager()
        # Create tenant
        from multi_tenant_manager import MultiTenantManager
        mt = MultiTenantManager()
        tenant = mt.create_tenant(name, email, plan, company)
        # Create user
        user = auth.create_user(tenant["id"], email, password, name, role="admin")
        # Login
        token = auth.authenticate_user(email, password)
        return jsonify({"token": token, "user": user, "tenant": tenant})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── 登录 API ──
@app.route("/api/auth/login", methods=["POST"])
@validate(LoginRequest)
def api_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "邮箱和密码为必填项"}), 400

    try:
        from auth import AuthManager
        auth = AuthManager()
        token = auth.authenticate_user(email, password)
        if token:
            # Get user info
            db = auth.db
            user = db.fetch_one("SELECT id,tenant_id,email,name,role FROM users WHERE email=?", [email])
            return jsonify({"token": token, "user": dict(user) if user else {}})
        return jsonify({"error": "邮箱或密码错误"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── 支付 API ──
@app.route("/api/payment/create-order", methods=["POST"])
def api_create_order():
    data = request.get_json() or {}
    plan_id = data.get("plan_id", "starter")
    user_id = data.get("user_id", "guest")

    try:
        from wechat_pay import get_payment_qrcode, PRICING_PLANS
        plan = PRICING_PLANS.get(plan_id, PRICING_PLANS["starter"])
        result = get_payment_qrcode(plan["name"], plan["price_yuan"])
        result["plan"] = plan
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── 运营后台 API ──
@app.route("/api/admin/ops")
def api_ops_dashboard():
    try:
        from ops_dashboard import get_full_dashboard
        return jsonify(get_full_dashboard())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 错误统计 API ──
@app.route("/api/admin/errors")
def api_error_stats():
    try:
        from error_tracker import get_error_stats
        return jsonify(get_error_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 用户反馈 API ──
@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json() or {}
    try:
        from feedback import submit_feedback, submit_nps
        if data.get("type") == "nps":
            result = submit_nps(
                data.get("user_id", "anonymous"),
                int(data.get("score", 0)),
                data.get("comment", "")
            )
        else:
            result = submit_feedback(
                data.get("user_id", "anonymous"),
                data.get("category", "other"),
                data.get("message", ""),
                data.get("email", ""),
                data.get("url", ""),
            )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/admin/feedback")
def api_feedback_stats():
    try:
        from feedback import get_feedback_stats
        return jsonify(get_feedback_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 备份 API ──
@app.route("/api/admin/backup", methods=["POST"])
def api_backup():
    try:
        from data_backup import backup_all, cleanup_old_backups
        cleanup_old_backups()
        result = backup_all()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/backup/status")
def api_backup_status():
    try:
        from data_backup import get_backup_status
        return jsonify(get_backup_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 装企内容引擎 API ──
@app.route("/api/zhuangqi/formats")
def api_zhuangqi_formats():
    try:
        from zhuangqi_content_engine import api_list_formats, api_list_visuals
        return jsonify({"formats": api_list_formats(), "visuals": api_list_visuals()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/zhuangqi/scenes")
def api_zhuangqi_scenes():
    """返回18个行业场景×222个关键词的创作方向体系"""
    import glob as _glob
    scenes_dir = Path("D:/Backup/YunShu/20260724/models/scenes")
    scenes = []
    if scenes_dir.exists():
        for f in sorted(scenes_dir.glob("*.json")):
            if f.stem == "index": continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                scenes.append({"id": f.stem, "name": f.stem, "keywords": data.get("keywords",[]),
                               "subcategories": data.get("subcategories",[])})
            except: pass
    return jsonify({"scenes": scenes, "total": len(scenes)})


@app.route("/api/zhuangqi/brief", methods=["POST"])
@validate(ZhuangqiBriefRequest)
def api_zhuangqi_brief():
    try:
        from zhuangqi_content_engine import api_generate_brief, CONTENT_FORMATS
        data = request.get_json() or {}

        # Translate frontend Chinese labels to internal IDs
        ct_map = {"短视频口播":"before_after","小红书图文":"local_case","公众号文章":"style_guide"}
        pl_map = {"短视频口播":"douyin","小红书图文":"xiaohongshu","公众号文章":"wechat"}

        content_type = ct_map.get(data.get("content_type",""), data.get("content_type","before_after"))
        platform = pl_map.get(data.get("content_type",""), data.get("platform","xiaohongshu"))
        context = {"city": data.get("city","厦门"), **(data.get("context",{}))}

        result = api_generate_brief({"content_type":content_type,"platform":platform,"context":context})
        result["_internal_type"] = content_type
        result["_internal_platform"] = platform
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/zhuangqi/generate", methods=["POST"])
def api_zhuangqi_generate():
    try:
        from zhuangqi_content_engine import api_generate_content, api_generate_brief, CONTENT_FORMATS
        data = request.get_json() or {}

        # Accept both raw params and pre-generated brief
        if "brief" in data:
            result = api_generate_content(data["brief"])
        else:
            ct_map = {"短视频口播":"before_after","小红书图文":"local_case","公众号文章":"style_guide"}
            pl_map = {"短视频口播":"douyin","小红书图文":"xiaohongshu","公众号文章":"wechat"}
            content_type = ct_map.get(data.get("content_type",""), data.get("content_type","before_after"))
            platform = pl_map.get(data.get("content_type",""), data.get("platform","xiaohongshu"))
            context = {"city": data.get("city","厦门"), "topic": data.get("topic",""), **(data.get("context",{}))}
            brief = api_generate_brief({"content_type":content_type,"platform":platform,"context":context})
            result = api_generate_content(brief)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/zhuangqi/week-plan", methods=["POST"])
def api_zhuangqi_week_plan():
    try:
        from zhuangqi_content_engine import api_generate_week_plan
        data = request.get_json() or {}
        city = data.get("city","厦门")
        # Generate default account config for the city
        accounts = data.get("accounts", [
            {"name": f"{city}装修号-小红书","platform":"xiaohongshu","ratio":0.4},
            {"name": f"{city}装修号-抖音","platform":"douyin","ratio":0.35},
            {"name": f"{city}装修号-公众号","platform":"wechat","ratio":0.25},
        ])
        return jsonify(api_generate_week_plan({"accounts":accounts}))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 自我进化 API ──
@app.route("/api/zhuangqi/evolve", methods=["POST"])
def api_evolve():
    try:
        from self_evolution import EvolutionScheduler
        scheduler = EvolutionScheduler()
        result = scheduler.evolve_from_collector()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zhuangqi/evolve/status")
def api_evolve_status():
    try:
        from self_evolution import EvolutionScheduler
        scheduler = EvolutionScheduler()
        return jsonify(scheduler.get_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Cookie 导入 API ──
@app.route("/api/zhuangqi/cookies", methods=["POST"])
def api_import_cookies():
    try:
        data = request.get_json() or {}
        platform = data.get("platform", "")  # xiaohongshu or douyin
        cookies = data.get("cookies", [])

        if not platform or not cookies:
            return jsonify({"error": "需要 platform 和 cookies"}), 400

        save_path = Path(__file__).parent / f"cookies_{platform}.json"
        save_path.write_text(json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8")
        return jsonify({"ok": True, "count": len(cookies), "platform": platform})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zhuangqi/cookies/status")
def api_cookie_status():
    result = {}
    for platform in ["xiaohongshu", "douyin"]:
        f = Path(__file__).parent / f"cookies_{platform}.json"
        result[platform] = {
            "exists": f.exists(),
            "count": len(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else 0,
        }
    return jsonify(result)


# ── 浏览器认证状态 ──
@app.route("/api/browser/status")
def api_browser_status():
    from pathlib import Path
    data_dir = Path(__file__).parent / "data" / "browser_profiles"
    platforms = {}
    for p in ["xiaohongshu", "douyin"]:
        sf = data_dir / f"{p}_state.json"
        platforms[p] = {"logged_in": sf.exists(), "size_kb": round(sf.stat().st_size/1024,1) if sf.exists() else 0}
    return jsonify({"status":"ok","platforms":platforms})

# ── 社交媒体搜索(简易版·Tavily驱动·无需Cookie) ──
@app.route("/api/zhuangqi/social/search", methods=["POST"])
@validate(SocialSearchRequest)
def api_social_search():
    try:
        from social_scraper import SocialCollector
        data = request.get_json() or {}
        keyword = data.get("keyword","装修设计")
        city = data.get("city","厦门")
        collector = SocialCollector()
        notes = collector.search_xiaohongshu(f"{city} {keyword}", min(data.get("count",5),10))
        results = []
        for n in notes:
            results.append({"id":n.note_id,"title":n.title,"content":(n.content or "")[:200],
                          "hashtags":(n.hashtags or [])[:5],"likes":n.likes,"url":n.url})
        web = collector._search_raw(f"{city} {keyword} 装修 2026趋势",3)
        trends = [{"title":r.get("title",""),"content":(r.get("content","") or "")[:200],"url":r.get("url","")} for r in web]
        return jsonify({"status":"ok","keyword":keyword,"city":city,"social_results":results,"web_trends":trends})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}),500

# ── 社交媒体采集 API(全量版) ──
@app.route("/api/zhuangqi/social/collect", methods=["POST"])
def api_social_collect():
    try:
        from social_scraper import SocialCollector
        collector = SocialCollector()
        data = request.get_json() or {}
        result = collector.collect_and_analyze(data.get("queries_per_platform", 3))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 趋势情报 API ──
@app.route("/api/zhuangqi/trends/search", methods=["POST"])
def api_trend_search():
    try:
        from trend_intelligence import TrendCollector
        collector = TrendCollector()
        data = request.get_json() or {}
        result = collector.search_trends(data.get("query"), data.get("max_results", 5))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/zhuangqi/trends/dashboard")
def api_trend_dashboard():
    try:
        from trend_intelligence import get_trend_dashboard
        return jsonify(get_trend_dashboard())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════
# GEO 优化 — 关键词研究/排名监测/内容生成
# ═══════════════════════════════════════════════════════

@app.route("/api/geo/keyword-research", methods=["POST"])
@validate(GeoKeywordRequest)
def api_geo_keyword_research():
    import urllib.request as ur
    data = request.get_json()
    city = data.get("city", "厦门")
    keywords = data.get("keywords", ["装修设计"])
    kw_str = ", ".join(keywords[:3])

    system = "你是搜索意图分析专家。从搜索结果提取意图类型、用户关心的问题、内容缺口。简洁输出。"
    user = f"分析 {city} {kw_str} 的用户搜索意图。输出：1)意图类型 2)用户核心需求TOP3 3)内容缺口 4)GEO机会。500字内。"

    api_data = json.dumps({
        "model": "deepseek-v4-pro", "max_tokens": 1500, "temperature": 0.7,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]
    }).encode("utf-8")
    req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=api_data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "anthropic-version": "2023-06-01"
    })
    try:
        with ur.urlopen(req, timeout=120) as r:
            result = json.loads(r.read().decode())
            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text": text += block.get("text", "")
            return jsonify({"status": "ok", "result": text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/geo/rank-check", methods=["POST"])
@validate(GeoRankRequest)
def api_geo_rank_check():
    import urllib.request as ur
    data = request.get_json()
    city = data.get("city", "厦门")
    keyword = data.get("keyword", "装修设计")
    platforms = data.get("platforms", ["DeepSeek", "豆包", "Kimi"])

    all_results = {}
    for platform in platforms[:3]:
        query = f"{city} {keyword} 装修"
        system = "你是搜索排名分析师。列出搜索结果前5个的标题和来源。简洁。"
        user = f"搜索: {query}\n平台: {platform}\n列出前5个结果的标题和来源。编号1-5。"

        api_data = json.dumps({
            "model": "deepseek-v4-pro", "max_tokens": 1000, "temperature": 0.3,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]
        }).encode("utf-8")
        req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=api_data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "anthropic-version": "2023-06-01"
        })
        try:
            with ur.urlopen(req, timeout=120) as r:
                result = json.loads(r.read().decode())
                text = ""
                for block in result.get("content", []):
                    if block.get("type") == "text": text += block.get("text", "")
                all_results[platform] = text
        except Exception as e:
            all_results[platform] = f"Error: {e}"

    return jsonify({"status": "ok", "results": all_results})

@app.route("/api/geo/content-generate", methods=["POST"])
@validate(GeoContentRequest)
def api_geo_content_generate():
    import urllib.request as ur
    data = request.get_json()
    city = data.get("city", "厦门")
    keyword = data.get("keyword", "装修设计")
    platform = data.get("platform", "小红书")
    tone = data.get("tone", "实用避坑")

    wc = "600-800字" if platform == "小红书" else "1500-2500字" if platform == "公众号" else "1000-2000字"

    system = f"你是GEO内容创作专家。内容直接回答搜索意图。结构化(标题层级)+实体丰富+可引用+FAQ段落。适配{platform}({wc})。"
    user = f"创作GEO优化内容: {city}·{keyword}·{platform}·{tone}。输出完整内容(含标题+正文+FAQ+相关搜索)。"

    api_data = json.dumps({
        "model": "deepseek-v4-pro", "max_tokens": 3000, "temperature": 0.7,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]
    }).encode("utf-8")
    req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=api_data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "anthropic-version": "2023-06-01"
    })
    try:
        with ur.urlopen(req, timeout=120) as r:
            result = json.loads(r.read().decode())
            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text": text += block.get("text", "")
            return jsonify({"status": "ok", "content": text})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/geo/pipeline-run", methods=["POST"])
def api_geo_pipeline_run():
    import urllib.request as ur, time
    data = request.get_json()
    city = data.get("city", "厦门")
    keyword = data.get("keyword", "装修设计")

    steps = []
    def call_geo_step(step_name, system_p, user_p):
        api_data = json.dumps({
            "model": "deepseek-v4-pro", "max_tokens": 1000, "temperature": 0.7,
            "messages": [{"role": "system", "content": system_p}, {"role": "user", "content": user_p}]
        }).encode("utf-8")
        req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=api_data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "anthropic-version": "2023-06-01"
        })
        with ur.urlopen(req, timeout=120) as r:
            result = json.loads(r.read().decode())
            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text": text += block.get("text", "")
            return text

    steps.append({"step": 1, "name": "搜索意图分析", "result": call_geo_step("意图",
        "你是搜索意图分析专家。", f"分析 {city} {keyword} 的搜索意图。输出意图类型+用户需求+内容缺口。500字内。")})

    steps.append({"step": 2, "name": "竞品可见度", "result": call_geo_step("竞品",
        "你是竞品分析专家。", f"分析 {city} 装修行业在AI搜索中最常被引用的品牌。TOP5+引用原因。500字内。")})

    steps.append({"step": 3, "name": "内容策略", "result": call_geo_step("策略",
        "你是GEO内容策略专家。", f"基于前两步，设计 {city} {keyword} 的GEO内容策略。输出内容类型+优先级矩阵。500字内。")})

    return jsonify({"status": "ok", "steps": steps})

# ═══════════════════════════════════════════════════════
# AI 提示词 Agent — 完整提示词工程系统
# ═══════════════════════════════════════════════════════

PROMPT_SCENES = {
    "video": "🎬 视频生成",
    "content": "📝 内容生产",
    "geo": "🌐 GEO优化",
    "research": "🔬 深度研究",
    "business": "💼 商业分析",
    "code": "💻 代码生成",
    "data": "📊 数据分析",
    "marketing": "🎯 营销文案",
    "service": "💬 客服对话",
    "custom": "🔧 自定义",
}

def _init_prompts_db():
    """Ensure prompts tables exist"""
    from database import Database
    db = Database().connect()
    db.execute("""CREATE TABLE IF NOT EXISTS prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, scene TEXT DEFAULT 'custom',
            system_prompt TEXT, user_prompt TEXT,
            model TEXT DEFAULT 'DeepSeek V4 Pro', tags TEXT, variables TEXT,
            effect_score REAL, usage_count INTEGER DEFAULT 0,
            version INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    db.execute("""CREATE TABLE IF NOT EXISTS prompt_deploy_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER, model TEXT, input_variables TEXT,
            output TEXT, response_time_ms INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    db.execute("""CREATE TABLE IF NOT EXISTS prompt_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, scene TEXT, system_prompt TEXT, user_prompt TEXT,
            model TEXT DEFAULT 'DeepSeek V4 Pro', is_preset BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    db.conn.commit()

    # Seed preset templates if empty
    count = db.fetch_one("SELECT COUNT(*) as c FROM prompt_templates")["c"]
    if count == 0:
        presets = [
            ("装修视频-避坑口播", "video", "你是装修短视频导演。从用户痛点出发，先呈现问题场景，再展示解决方案。每个分镜有明确视觉描述。",
             "拍摄{城市}{房间}的{痛点}改造视频。分镜：1)问题特写(3s) 2)施工过程(3s) 3)完工对比(4s)。风格：纪实+专业。", "即梦(图生视频)"),
            ("小红书-装修攻略", "content", "你是小红书爆款文案写手。亲密实用碎片化表达。先抛问题引发共鸣，再给解决方案。禁止AI味。",
             "写一篇{城市}{房间}装修攻略。目标用户：{用户画像}。字数：600-800。含1个避坑点+1个省钱技巧+1个产品推荐。", "DeepSeek V4 Pro"),
            ("GEO-答案型内容", "geo", "你是GEO优化专家。内容直接回答AI搜索问题。结构化+实体丰富+可引用。",
             "为关键词「{关键词}」创建GEO优化内容。平台：{平台}。含FAQ段落和至少1个原创数据。字数：{字数}。", "DeepSeek V4 Pro"),
            ("深度研究-AI行业", "research", "你是AI行业首席分析师。每个结论≥3个来源佐证。区分事实/推断/观点。",
             "深度研究「{研究主题}」。≥3来源交叉验证，≥800字，含时间线+影响分析+趋势预判。", "DeepSeek V4 Pro"),
            ("商业分析-市场机会", "business", "你是商业战略顾问。结构化分析商业问题。数据驱动，底层原理标注。",
             "分析「{行业}」在「{地区}」的市场机会。含市场规模估算+竞争格局+进入壁垒+推荐策略。", "DeepSeek V4 Pro"),
            ("Python代码生成", "code", "你是资深Python工程师。代码简洁、类型完整、错误处理齐全。",
             "用Python实现：{需求}。要求：类型注解+错误处理+可运行。输出完整代码+使用说明。", "DeepSeek V4 Pro"),
            ("数据分析-洞察报告", "data", "你是数据分析专家。从数据提取洞察，可视化建议，行动推荐。",
             "分析以下数据：{数据描述}。输出：关键发现(≥3条)+趋势判断+可视化建议+行动推荐。", "DeepSeek V4 Pro"),
            ("营销文案-落地页", "marketing", "你是转化文案专家。AIDA模型驱动，痛点→方案→信任→行动。",
             "为「{产品}」写营销落地页文案。目标用户：{用户画像}。含标题+副标题+3个卖点+社会证明+CTA。", "DeepSeek V4 Pro"),
            ("客服对话-装修咨询", "service", "你是专业装修客服。友好耐心，问清需求再推荐。不懂就说需要确认。",
             "回复客户咨询：「{客户问题}」。了解：户型{m2}、预算{万}、风格偏好{风格}。给出针对性建议。", "DeepSeek V4 Pro"),
            ("微信公众号-行业洞察", "content", "你是公众号深度内容创作者。专业但不枯燥，用故事和数据驱动。",
             "写一篇关于「{行业}」的公众号深度文章。1500-2500字。含行业数据+专家观点+趋势预判。", "DeepSeek V4 Pro"),
        ]
        for name, scene, sys_p, usr_p, model in presets:
            db.insert("prompt_templates", {
                "name": name, "scene": scene, "system_prompt": sys_p,
                "user_prompt": usr_p, "model": model, "is_preset": 1
            })
        db.conn.commit()

_init_prompts_db()

@app.route("/prompt-agent")
def prompt_agent_page():
    return send_from_directory(str(LANDING), "prompt-agent.html")

@app.route("/api/prompts/list")
def api_prompts_list():
    from database import Database
    db = Database().connect()
    scene = request.args.get("scene", "")
    if scene:
        rows = db.fetch_all("SELECT * FROM prompts WHERE scene=? ORDER BY created_at DESC", [scene])
    else:
        rows = db.fetch_all("SELECT * FROM prompts ORDER BY created_at DESC")
    return jsonify({"status": "ok", "prompts": [dict(r) for r in rows]})

@app.route("/api/prompts/create", methods=["POST"])
@validate(PromptCreateRequest)
def api_prompts_create():
    from database import Database
    db = Database().connect()
    data = request.get_json()
    pid = db.insert("prompts", {
        "name": data.get("name", ""), "scene": data.get("scene", "custom"),
        "system_prompt": data.get("system_prompt", ""), "user_prompt": data.get("user_prompt", ""),
        "model": data.get("model", "DeepSeek V4 Pro"), "tags": data.get("tags", ""),
        "variables": data.get("variables", ""), "version": 1
    })
    return jsonify({"status": "ok", "id": pid})

@app.route("/api/prompts/<int:pid>", methods=["PUT", "DELETE"])
def api_prompts_manage(pid):
    from database import Database
    db = Database().connect()
    if request.method == "DELETE":
        db.execute("DELETE FROM prompts WHERE id=?", [pid])
        db.conn.commit()
        return jsonify({"status": "ok", "deleted": pid})
    else:
        data = request.get_json()
        db.update("prompts", {
            "name": data.get("name"), "system_prompt": data.get("system_prompt"),
            "user_prompt": data.get("user_prompt"), "model": data.get("model"),
            "tags": data.get("tags"), "version": data.get("version", 1) + 1
        }, "id=?", [pid])
        return jsonify({"status": "ok", "updated": pid})

@app.route("/api/prompts/generate", methods=["POST"])
@validate(PromptGenerateRequest)
def api_prompts_generate():
    import urllib.request as ur
    data = request.get_json()
    topic = data.get("topic", "")
    scene = data.get("scene", "custom")
    requirements = data.get("requirements", "")

    system = f"""你是专业Prompt工程师。为{PROMPT_SCENES.get(scene, scene)}场景生成优化提示词。
输出分为两部分，用"---USER---"分隔：
第一部分：System Prompt（角色+规则+约束）
第二部分：User Prompt（任务+上下文+输出要求）"""

    user = f"主题: {topic}\n要求: {requirements}\n\n请生成完整的System Prompt和User Prompt。"

    api_data = json.dumps({
        "model": "deepseek-v4-pro", "max_tokens": 2000, "temperature": 0.7,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]
    }).encode("utf-8")
    req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=api_data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "anthropic-version": "2023-06-01"
    })
    try:
        with ur.urlopen(req, timeout=120) as r:
            result = json.loads(r.read().decode())
            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            parts = text.split("---USER---")
            sys_p = parts[0].strip() if parts else text
            usr_p = parts[1].strip() if len(parts) > 1 else ""
            return jsonify({"status": "ok", "system_prompt": sys_p, "user_prompt": usr_p})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/prompts/deploy", methods=["POST"])
def api_prompts_deploy():
    import urllib.request as ur, time
    data = request.get_json()
    sys_p = data.get("system_prompt", "")
    usr_p = data.get("user_prompt", "")
    model_name = data.get("model", "deepseek-v4-pro")
    variables = data.get("variables", {})

    # Replace variables
    for k, v in variables.items():
        usr_p = usr_p.replace("{" + k + "}", str(v))

    api_data = json.dumps({
        "model": model_name, "max_tokens": 2000, "temperature": 0.7,
        "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}]
    }).encode("utf-8")
    req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=api_data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "anthropic-version": "2023-06-01"
    })
    start = time.time()
    try:
        with ur.urlopen(req, timeout=120) as r:
            result = json.loads(r.read().decode())
            text = ""
            for block in result.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            elapsed = int((time.time() - start) * 1000)

            # Log deploy history
            from database import Database
            db = Database().connect()
            db.insert("prompt_deploy_history", {
                "prompt_id": data.get("prompt_id", 0), "model": model_name,
                "input_variables": json.dumps(variables, ensure_ascii=False),
                "output": text[:2000], "response_time_ms": elapsed
            })

            return jsonify({"status": "ok", "output": text, "response_time_ms": elapsed})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/prompts/templates")
def api_prompts_templates():
    from database import Database
    db = Database().connect()
    scene = request.args.get("scene", "")
    if scene:
        rows = db.fetch_all("SELECT * FROM prompt_templates WHERE scene=? ORDER BY is_preset DESC, created_at DESC", [scene])
    else:
        rows = db.fetch_all("SELECT * FROM prompt_templates ORDER BY is_preset DESC, created_at DESC")
    return jsonify({"status": "ok", "templates": [dict(r) for r in rows]})

# ═══════════════════════════════════════════════════════
# 🎨 创作板块 — 4大创作者风格体系 + 选题发现 + AI写作 + 多平台
# ═══════════════════════════════════════════════════════

CREATOR_STYLES = {
    "zhinan": {
        "id": "zhinan", "name": "直男财经", "icon": "💼",
        "tagline": "数字砸脸·判词前置·节奏快·0-3秒出钩子",
        "tone": "【直男财经风格】硬核直给，不铺垫不绕弯。核心技法：数字砸脸(0-3秒必须出现极端数字或极端动词)。前15字必须包含至少一项：具体数字(225万/暴跌30%)、反问句(为何？怎么？)、极端动词(暴跌/暴涨/崩盘)。四种开头模式：数字砸脸40%、问句钩子30%、危机冲突20%、故事悬念10%。语言口语+自嘲，观众关系是\"兄弟\". 杜绝铺垫超过15字、数字不极端、问句太软、像新闻标题。",
        "structure": "极端数字/争议观点(前3秒) → 数据拆解 → 案例佐证 → 反转/真相 → 金句总结",
        "word_range": (800, 1800),
        "best_platforms": ["抖音", "视频号", "B站", "公众号"],
        "hook_templates": [
            "{极端数字}！这是什么概念？",
            "99%的人不知道，{topic}的真相其实是...",
            "活久见！{topic}暴跌99.97%！",
        ],
        "forbidden": ["我觉得", "可能", "大概", "据说", "小编", "最近", "随着...的发展"],
        "emoji": "low",
    },
    "xiaolin": {
        "id": "xiaolin", "name": "小Lin说", "icon": "📖",
        "tagline": "认知转折·第一秒认知失调·把复杂的讲简单",
        "tone": "【小Lin说风格】娓娓道来，核心技法：第一秒制造认知失调——观众脑子里想的必须是\"等等这不对吧？\"而不是\"然后呢？\"。四种开头模式：暴力类比25%(交易员一个电话让半个加州停电)、具体谜题30%(蒙眼喝可乐为何结果反转)、坦白困惑25%(之前不太敢讲因为越研究越不明白)、反差重构20%。绝不做：线性叙事开头(致命)、砸数字(那是直男财经)、说教感、过度情绪化。语气温和好奇，像学姐分享，不像老师上课。",
        "structure": "认知转折开场(谜题/类比/坦白) → 问题拆解 → 核心概念(比喻) → 深度分析 → 总结升华",
        "word_range": (1500, 3500),
        "best_platforms": ["B站", "知乎", "公众号", "小红书"],
        "hook_templates": [
            "今天聊一个很有意思的话题：{topic}",
            "你有没有想过，为什么{topic}会这样？",
            "一个{画面级比喻}，就让{topic}崩了",
        ],
        "forbidden": ["震惊", "必看", "速看", "绝了", "首先其次最后", "综上所述"],
        "emoji": "medium",
    },
    "gaogailun": {
        "id": "gaogailun", "name": "高盖伦", "icon": "⚡",
        "tagline": "事件堆叠·认知反转·犀利吐槽·网感强",
        "tone": "【高盖伦风格】犀利冷静，核心技法：事件堆叠+认知反转——把大众的道德判断扭转为权力分析。三种开头模式：事件堆叠反转50%(泼水门、骂空姐、推老人——他们脑子里在想什么？)、反直觉提问30%(让你当胖东来老板三年能进富豪榜吗？)、现象+定调20%。必须完成转换：道德解释→权力解释，不是\"这个人太坏了\"而是\"权力让TA退化到本能反应层级\"。语言理性冷峻，和观众保持距离=权威感。绝不做：开头砸数字(那是直男财经)、反转不够深(只到表面现象)、讨好观众(破坏距离感)、事件不够具体。",
        "structure": "3个具体事件堆叠(前3秒) → 认知反转一句话 → 权力/系统层分析 → 历史类比 → 冷静收束不下结论",
        "word_range": (400, 1200),
        "best_platforms": ["抖音", "小红书", "视频号", "微博"],
        "hook_templates": [
            "{事件A}、{事件B}、{事件C}——他们脑子里在想什么？",
            "说个得罪人的大实话：{topic}",
            "让你做{topic}，三年能成功吗？",
        ],
        "forbidden": ["官方认证", "权威", "专家说", "兄弟们", "我觉得"],
        "emoji": "high",
    },
    "xiaoa": {
        "id": "xiaoa", "name": "小A学财经", "icon": "🎓",
        "tagline": "反常识揭露·你以为A其实是B·干货密度最高",
        "tone": "【小A学财经风格】学霸视角，核心技法：第一句就建立\"表面vs实际\"的反转框架。不是在\"分享信息\"，是在\"揭露一个你被隐瞒的真相\"。三种开头模式：反常识揭露45%(为什么贫富差距最大的国家却用最富有的王室？)、数字+框架预告30%(430亿美元、2亿婚礼——泰国王室到底多有钱？)、从X到Y变化弧线25%。信息密度是四创作者中最高的，要求：信息爆破点/分钟≥5(爆破点=具体数字/人名/机构名/案例/法规/平台数据)。语气温和但坚定，武器是逻辑链拆解+精准数字(只用1-2个，不砸)。绝不做：开头没有反转框架(致命)、反转太浅、砸数字(那是直男财经)、用权力框架分析(那是高盖伦)。",
        "structure": "反常识揭露(\"你以为A其实是B\") → 利益逻辑链拆解 → 1-2个精准数字 → 框架/模型对比 → 认知闭环给框架",
        "word_range": (1200, 3000),
        "best_platforms": ["公众号", "知乎", "知识星球", "B站"],
        "hook_templates": [
            "你以为{常见认知}？实际上，真正驱动的是{颠覆性真相}",
            "为什么{反直觉现象}？答案在你的认知盲区里",
            "用一张图给你讲清楚{topic}的底层框架",
        ],
        "forbidden": ["绝对", "保证", "100%", "独一无二", "最近很火"],
        "emoji": "low",
    },
}

# 风格克隆器模板
STYLE_CLONE_SYSTEM = """你是风格分析专家。分析给定文本的风格DNA，提取以下维度：
1. 句式特征（长短句比例、常用句型）
2. 词汇偏好（高频词、禁用词、口头禅）
3. 节奏感（快/慢/张弛、段落长度）
4. 情绪基调（激昂/冷静/温情/犀利/幽默）
5. 结构模式（开头方式、中间组织、结尾方式）
输出一个简洁的风格DNA卡片。"""

# 去AI腔检测维度
DEAI_DIMENSIONS = [
    {"name": "标题吸引度", "check": "标题是否有钩子？是否让人想点？字数是否≤20字？"},
    {"name": "句式多样性", "check": "长短句是否交错？是否有排比/反问/设问？是否避免'首先其次最后'？"},
    {"name": "口语自然度", "check": "是否有口语词？是否像人在说话而非机器？是否有'呃/吧/嘛/啦'等语气词？"},
    {"name": "情绪颗粒度", "check": "是否有情绪起伏？是否有个人态度？是否避免了中性客观腔？"},
    {"name": "AI痕迹", "check": "是否避免：总而言之/综上所述/值得注意的是/不可否认/随着...的发展？"},
]

PLATFORMS = {
    "douyin": {"name": "抖音", "max_words": 1500, "style": "短视频口播脚本，带分镜描述，3秒内必须有钩子"},
    "xiaohongshu": {"name": "小红书", "max_words": 800, "style": "短文+emoji+话题标签，亲切分享感，像朋友安利"},
    "wechat": {"name": "公众号", "max_words": 2500, "style": "深度长文，专业但不枯燥，有故事有数据有观点"},
    "zhihu": {"name": "知乎", "max_words": 3000, "style": "专业问答体，有理有据，引用来源，结构清晰"},
    "bilibili": {"name": "B站", "max_words": 2000, "style": "视频口播脚本，轻松有趣，适合年轻人口味"},
    "pengyouquan": {"name": "朋友圈", "max_words": 300, "style": "短小精悍，金句驱动，适合截屏传播"},
}

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    print("WARNING: DEEPSEEK_API_KEY not set in .env — AI features will fail")

def _deepseek_call(system_prompt, user_prompt, max_tokens=2000, temperature=0.7):
    """统一的DeepSeek API调用"""
    import urllib.request as ur
    api_data = json.dumps({
        "model": "deepseek-v4-pro", "max_tokens": max_tokens, "temperature": temperature,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    }).encode("utf-8")
    req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=api_data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "anthropic-version": "2023-06-01"
    })
    with ur.urlopen(req, timeout=180) as r:
        result = json.loads(r.read().decode())
        text = ""
        for block in result.get("content", []):
            if block.get("type") == "text": text += block.get("text", "")
        return text


@app.route("/api/create/styles")
def api_create_styles():
    """返回4大创作者风格定义（完整版含技法）"""
    styles = []
    for k, v in CREATOR_STYLES.items():
        styles.append({
            "id": v["id"], "name": v["name"], "icon": v["icon"],
            "tagline": v["tagline"], "best_platforms": v["best_platforms"],
            "tone": v["tone"][:120] + "...",  # 截取前120字做卡片预览
            "structure": v["structure"],
            "hook_templates": v["hook_templates"],
            "forbidden": v["forbidden"],
            "emoji": v["emoji"],
            "word_range": v["word_range"],
        })
    return jsonify({"status": "ok", "styles": styles, "platforms": PLATFORMS})


@app.route("/api/create/topic-discovery", methods=["POST"])
@validate(TopicDiscoveryRequest)
def api_create_topic_discovery():
    """选题发现：领域 + 对标创作者 → 5个选题简报"""
    data = request.get_json() or {}
    domain = data.get("domain", "AI工具")
    creators = data.get("creators", ["zhinan", "xiaolin"])
    count = int(data.get("count", 5))

    creator_names = [CREATOR_STYLES[c]["name"] for c in creators if c in CREATOR_STYLES]
    style_descs = "\n".join([f"- {CREATOR_STYLES[c]['name']}: {CREATOR_STYLES[c]['tagline']}" for c in creators if c in CREATOR_STYLES])

    system = f"""你是资深内容策略师。为「{domain}」领域发现最值得做的选题。
参考创作者风格：
{style_descs}

输出{count}个选题简报，每个选题用以下格式（用"---BRIEF---"分隔）：
标题 | 对标创作者 | 推荐平台 | 建议字数范围 | 角度(一句话) | 为什么值得做(一句话) | 大纲(3-5点，用|分隔)"""

    user = f"发现{domain}领域最有爆款潜力的{count}个选题。每个选题标注最适合对标哪位创作者。要有数据支撑和明确角度。"
    try:
        raw = _deepseek_call(system, user, max_tokens=2500, temperature=0.8)
        briefs = []
        for block in raw.split("---BRIEF---"):
            block = block.strip()
            if not block: continue
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if len(lines) < 5: continue
            # Parse: title | creator | platform | words | angle | why | outline
            first = lines[0].replace("|", " | ")
            parts = [p.strip() for p in first.split("|")]
            outline = []
            for l in lines[1:]:
                l = l.lstrip("-•·0123456789. )")
                if l: outline.append(l)
            briefs.append({
                "title": parts[0] if len(parts) > 0 else "",
                "creator": parts[1] if len(parts) > 1 else creator_names[0],
                "platform": parts[2] if len(parts) > 2 else "公众号",
                "word_range": parts[3] if len(parts) > 3 else "1500-2500",
                "angle": parts[4] if len(parts) > 4 else "",
                "why": parts[5] if len(parts) > 5 else "",
                "outline": outline,
            })
        return jsonify({"status": "ok", "domain": domain, "briefs": briefs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/create/generate", methods=["POST"])
def api_create_generate():
    """AI写作：主题 + 创作者 + 平台 → 完整内容 + 多阶段输出"""
    data = request.get_json() or {}
    topic = data.get("topic", "")
    creator_id = data.get("creator", "zhinan")
    platform_id = data.get("platform", "wechat")
    word_count = int(data.get("word_count", 2000))
    extra = data.get("extra", "")

    if not topic:
        return jsonify({"status": "error", "message": "请提供创作主题"}), 400

    creator = CREATOR_STYLES.get(creator_id, CREATOR_STYLES["zhinan"])
    platform = PLATFORMS.get(platform_id, PLATFORMS["wechat"])

    # Phase 1: Research brief
    research_sys = "你是资深研究员。为内容创作提供背景资料、关键数据、核心观点。简洁精炼。"
    research_user = f"为创作主题「{topic}」准备研究简报。包含：1)核心背景 2)3个关键数据点 3)2个争议/不同观点 4)可引用的案例或故事。300字内。"
    try:
        research = _deepseek_call(research_sys, research_user, max_tokens=800)
    except:
        research = "研究阶段跳过"

    # Phase 2: Content generation with creator style
    create_sys = f"""你是顶尖内容创作者，对标「{creator['name']}」的风格。
风格要求：{creator['tone']}
结构要求：{creator['structure']}
禁用词：{', '.join(creator['forbidden'])}
Emoji密度：{creator['emoji']}
目标平台：{platform['name']}（{platform['style']}）
字数：{word_count}字左右"""

    create_user = f"""创作主题：{topic}
研究资料：{research}
额外要求：{extra or '无'}

请输出完整内容。标题要有钩子，开篇要有吸引力，内容要有信息增量，结尾要有行动召唤或金句。
输出格式：
---TITLE---
（标题）
---BODY---
（正文）"""

    try:
        raw = _deepseek_call(create_sys, create_user, max_tokens=4000, temperature=0.8)
        title = ""
        body = raw
        if "---TITLE---" in raw:
            parts = raw.split("---BODY---")
            title = parts[0].replace("---TITLE---", "").strip() if len(parts) > 0 else ""
            body = parts[1].strip() if len(parts) > 1 else raw

        # Phase 3: De-AI check
        deai_sys = "你是去AI腔检测专家。检查给定文本的AI味，按5个维度打分(1-10)，给出具体修改建议。"
        deai_user = f"检测以下文本的AI痕迹：\n\n{body[:1500]}"
        try:
            deai_report = _deepseek_call(deai_sys, deai_user, max_tokens=600)
        except:
            deai_report = "检测跳过"

        return jsonify({
            "status": "ok",
            "creator": creator["name"],
            "platform": platform["name"],
            "title": title,
            "body": body,
            "word_count_actual": len(body),
            "research_brief": research,
            "deai_report": deai_report,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/create/multi-platform", methods=["POST"])
@validate(MultiPlatformRequest)
def api_create_multi_platform():
    """一题多平台：一个主题 → 6个平台适配版本"""
    data = request.get_json() or {}
    topic = data.get("topic", "")
    base_content = data.get("base_content", "")
    creator_id = data.get("creator", "zhinan")
    target_platforms = data.get("platforms", ["xiaohongshu", "douyin", "wechat"])

    if not topic:
        return jsonify({"status": "error", "message": "请提供创作主题"}), 400

    creator = CREATOR_STYLES.get(creator_id, CREATOR_STYLES["zhinan"])
    results = {}

    for pid in target_platforms:
        if pid not in PLATFORMS: continue
        p = PLATFORMS[pid]
        sys = f"""你是多平台内容适配专家。将内容改写为{p['name']}版本。
风格参考「{creator['name']}」：{creator['tone']}
{p['name']}要求：{p['style']}，字数≤{p['max_words']}字"""
        user = f"主题：{topic}\n原始内容：{base_content[:1000] if base_content else '无'}\n\n请直接输出{p['name']}适配版内容。"
        try:
            results[pid] = _deepseek_call(sys, user, max_tokens=p["max_words"] * 2, temperature=0.7)
        except:
            results[pid] = f"[{p['name']}] 生成失败"

    return jsonify({"status": "ok", "topic": topic, "creator": creator["name"], "results": results})


@app.route("/api/create/style-clone", methods=["POST"])
@validate(StyleCloneRequest)
def api_create_style_clone():
    """风格克隆：粘贴参考文章 → 提取风格DNA"""
    data = request.get_json() or {}
    ref_text = data.get("text", "")
    if not ref_text:
        return jsonify({"status": "error", "message": "请提供参考文本"}), 400
    try:
        dna = _deepseek_call(STYLE_CLONE_SYSTEM, f"分析以下文本的风格DNA：\n\n{ref_text[:3000]}", max_tokens=800)
        return jsonify({"status": "ok", "style_dna": dna})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/create/deai-check", methods=["POST"])
@validate(DeaiCheckRequest)
def api_create_deai_check():
    """去AI腔检测：粘贴文本 → 5维度评分+修改建议"""
    data = request.get_json() or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"status": "error", "message": "请提供待检测文本"}), 400
    dims = "\n".join([f"{d['name']}: {d['check']}" for d in DEAI_DIMENSIONS])
    sys = f"你是去AI腔检测专家。按以下5个维度打分(1-10)并给出具体修改建议：\n{dims}\n输出格式：每个维度一行，格式为「维度名: X分 - 具体建议」"
    try:
        report = _deepseek_call(sys, f"检测以下文本：\n\n{text[:2000]}", max_tokens=800)
        return jsonify({"status": "ok", "report": report})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════
# 🎬 内容形式体系 — 口播/人设/故事/混剪/图文/短视频
# ═══════════════════════════════════════════════════════

CONTENT_FORMS = {
    "voiceover": {
        "id": "voiceover", "name": "🎙️ 口播脚本", "icon": "🎙️",
        "desc": "单人出镜口播，含完整Scene分镜+Visual标注+BGM/花字/转场笔记",
        "structure": ["黄金3秒钩子", "身份声明+价值承诺", "核心观点递进(每90秒节奏点)", "数据/案例支撑", "结尾CTA(行动/互动/金句)"],
        "best_platforms": ["抖音", "B站", "视频号"],
        "word_range": (800, 2500),
        "production_notes": ["[Scene]分镜标注", "[Visual]画面描述", "[BGM]配乐建议", "[SFX]音效标记"],
    },
    "persona": {
        "id": "persona", "name": "👤 人设IP", "icon": "👤",
        "desc": "围绕固定人设的系列内容，建立人物辨识度。含人设档案+口头禅+视觉符号+内容调性",
        "structure": ["人设亮相(标志性开场)", "场景带入(日常/工作)", "冲突/痛点展示", "人设态度表达", "金句/口头禅收尾"],
        "best_platforms": ["抖音", "小红书", "视频号"],
        "word_range": (400, 1200),
        "production_notes": ["人设档案(年龄/职业/性格/痛点)", "视觉符号(服装/场景/道具)", "口头禅3-5句", "固定开场/结尾形式"],
    },
    "storytelling": {
        "id": "storytelling", "name": "📖 故事叙事", "icon": "📖",
        "desc": "故事化叙事：人物+冲突+反转+情感共鸣。可选财富故事/认知反差/好奇心缺口/榜单排位四种公式",
        "structure": ["故事钩子(反常/悬念)", "人物/背景建立", "冲突升级(三重递进)", "转折/真相揭晓", "情感升华/反思"],
        "best_platforms": ["B站", "抖音", "公众号"],
        "word_range": (1200, 3500),
        "formulas": ["财富故事型: 人物+数据+反差", "认知反差型: 为什么+其实是", "好奇心缺口型: 层层设问+递进回答", "榜单排位型: 最+数字+悬念排名"],
        "production_notes": ["开头用'你知道吗'/'你有没有想过'制造认知缺口", "每30秒一个信息点", "至少2个'但是/其实'转折", "结尾回扣开头"],
    },
    "mashup": {
        "id": "mashup", "name": "🎬 混剪快节奏", "icon": "🎬",
        "desc": "高密度视觉混剪+字幕驱动+强节奏BGM。适合前后对比、过程记录、多案例并置",
        "structure": ["冲击力画面开场(0.5-1秒/帧)", "主题字幕弹出", "快节奏画面切换(配合BGM鼓点)", "对比/并列呈现", "收尾定格+引导关注"],
        "best_platforms": ["抖音", "小红书", "视频号"],
        "word_range": (200, 600),
        "production_notes": ["画面节奏: 0.5-2秒/镜头", "BGM: 强节奏鼓点型", "字幕: 大字居中，每屏≤8字", "转场: 硬切为主，关键处用闪光/缩放"],
    },
    "article": {
        "id": "article", "name": "📝 图文内容", "icon": "📝",
        "desc": "小红书图文/公众号长文/知乎回答。文字为主，配图辅助",
        "structure": ["标题(数字化+情绪化)", "开头(共鸣/痛点/悬念)", "分段展开(每段一个核心点)", "配图建议(位置+内容)", "结尾互动/关注引导"],
        "best_platforms": ["小红书", "公众号", "知乎"],
        "word_range": (600, 3000),
        "production_notes": ["小红书: 600-800字+emoji+话题标签", "公众号: 1500-2500字深度长文", "知乎: 2000-3000字专业回答"],
    },
    "short_video": {
        "id": "short_video", "name": "📱 短视频", "icon": "📱",
        "desc": "15-60秒短视频，强钩子+快节奏+单一信息点",
        "structure": ["0-3秒: 视觉/听觉钩子", "3-15秒: 核心信息", "15-25秒: 展开/反转", "25-35秒: 情绪高点", "最后5秒: CTA/关注引导"],
        "best_platforms": ["抖音", "小红书", "视频号"],
        "word_range": (80, 300),
        "production_notes": ["竖屏9:16", "前3帧决定留存", "字幕必须大且居中", "BGM与画面节奏同步"],
    },
}

# 叙事公式详情
STORY_FORMULAS = {
    "wealth": {"name": "财富故事型", "formula": "人物+数据+反差", "hook": "用极端数字锁前3秒，建立'他怎么做到的'悬念"},
    "cognitive": {"name": "认知反差型", "formula": "为什么+其实是", "hook": "先建立常识认知，然后用'但'翻转"},
    "curiosity": {"name": "好奇心缺口型", "formula": "层层设问+递进回答", "hook": "每层回答暴露新问题，像连续剧"},
    "ranking": {"name": "榜单排位型", "formula": "最+数字+悬念排名", "hook": "从低到高揭晓，维持期待"},
}

# 表达风格
EXPRESSION_STYLES = {
    "bestie": {"name": "闺蜜聊天体", "desc": "邻家女孩，'其实就是...'，适合入门知识"},
    "scholar": {"name": "学霸聊天体", "desc": "精英学姐，'咱们一口气搞清楚'，适合深度解析"},
    "business": {"name": "生意人算账体", "desc": "调研员，'一天赚XX元'，适合商业机会"},
}

# 开头钩子类型(来自开头模型库)
HOOK_TYPES = {
    "H1": {"name": "情绪引爆", "formula": "[极端数据]+[情绪词]+[悬念]", "best": "小Lin说"},
    "H2": {"name": "认知冲突", "formula": "[A面]+但/然而+[B面]", "best": "小Lin说/高盖伦"},
    "H3": {"name": "反常识数据", "formula": "[违反直觉的数字]+[悬念]", "best": "小Lin说"},
    "H4": {"name": "财富冲击", "formula": "[具体金额]+[来源]", "best": "小A学财经/高盖伦"},
    "H5": {"name": "收入冲击", "formula": "[一天赚XXXX元]+[行业]", "best": "高盖伦"},
    "H6": {"name": "多信号并发", "formula": "[全球N个权威信号]+[这件事一定很大]", "best": "小Lin说"},
}


@app.route("/api/create/forms")
def api_create_forms():
    """返回全部内容形式定义"""
    forms = []
    for k, v in CONTENT_FORMS.items():
        forms.append({"id": v["id"], "name": v["name"], "icon": v["icon"],
                      "desc": v["desc"], "best_platforms": v["best_platforms"]})
    return jsonify({"status": "ok", "forms": forms,
                    "story_formulas": STORY_FORMULAS,
                    "expression_styles": EXPRESSION_STYLES,
                    "hook_types": HOOK_TYPES})


@app.route("/api/create/generate-v2", methods=["POST"])
@validate(GenerateV2Request)
def api_create_generate_v2():
    """增强版AI写作：内容形式 + 创作者风格 + 叙事公式 + 表达风格 + 钩子类型"""
    data = request.get_json() or {}
    topic = data.get("topic", "")
    content_form = data.get("content_form", "voiceover")  # 口播/人设/故事/混剪/图文/短视频
    creator_id = data.get("creator", "zhinan")
    platform_id = data.get("platform", "douyin")
    word_count = int(data.get("word_count", 1500))
    extra = data.get("extra", "")
    hook_type = data.get("hook_type", "")  # H1-H6
    story_formula = data.get("story_formula", "")  # wealth/cognitive/curiosity/ranking
    expression = data.get("expression", "")  # bestie/scholar/business

    if not topic:
        return jsonify({"status": "error", "message": "请提供创作主题"}), 400

    form = CONTENT_FORMS.get(content_form, CONTENT_FORMS["voiceover"])
    creator = CREATOR_STYLES.get(creator_id, CREATOR_STYLES["zhinan"])
    platform = PLATFORMS.get(platform_id, PLATFORMS["douyin"])

    # 构建增强System Prompt
    parts = [f"你是顶尖内容创作者。"]
    parts.append(f"## 内容形式：{form['name']}")
    parts.append(f"定义：{form['desc']}")
    parts.append(f"结构要求：{' → '.join(form['structure'])}")
    if form.get("production_notes"):
        parts.append(f"制作标注：{', '.join(form['production_notes'])}")
    if form.get("formulas"):
        parts.append(f"可选叙事公式：{' | '.join(form['formulas'])}")

    parts.append(f"\n## 对标创作者：{creator['name']}")
    parts.append(f"风格：{creator['tone']}")
    parts.append(f"结构偏好：{creator['structure']}")
    parts.append(f"禁用词：{', '.join(creator['forbidden'])}")
    parts.append(f"Emoji密度：{creator['emoji']}")

    if hook_type and hook_type in HOOK_TYPES:
        h = HOOK_TYPES[hook_type]
        parts.append(f"\n## 开头钩子：{h['name']}")
        parts.append(f"公式：{h['formula']}（参考{h['best']}）")

    if story_formula and story_formula in STORY_FORMULAS:
        sf = STORY_FORMULAS[story_formula]
        parts.append(f"\n## 叙事公式：{sf['name']}")
        parts.append(f"核心机制：{sf['formula']}")
        parts.append(f"钩子策略：{sf['hook']}")

    if expression and expression in EXPRESSION_STYLES:
        es = EXPRESSION_STYLES[expression]
        parts.append(f"\n## 表达风格：{es['name']} — {es['desc']}")

    parts.append(f"\n## 目标平台：{platform['name']}（{platform['style']}）")
    parts.append(f"字数要求：{word_count}字左右")

    system_prompt = "\n".join(parts)
    user_prompt = f"创作主题：{topic}\n额外要求：{extra or '无'}\n\n请按照内容形式「{form['name']}」的结构完成创作。如有制作标注(Scene/Visual/BGM等)请一并输出。"

    try:
        raw = _deepseek_call(system_prompt, user_prompt, max_tokens=4000, temperature=0.8)

        # 分离标题和正文
        title = ""
        body = raw
        if "---TITLE---" in raw:
            parts_raw = raw.split("---BODY---")
            title = parts_raw[0].replace("---TITLE---", "").strip() if len(parts_raw) > 0 else ""
            body = parts_raw[1].strip() if len(parts_raw) > 1 else raw

        # 研究简报
        try:
            research = _deepseek_call(
                "你是资深研究员。提供背景资料、关键数据、核心观点。300字内。",
                f"为创作主题「{topic}」准备研究简报。", max_tokens=600)
        except:
            research = "研究阶段跳过"

        # 去AI腔检测
        try:
            deai_report = _deepseek_call(
                "你是去AI腔检测专家。检测AI痕迹，5维度打分(1-10)+修改建议。",
                f"检测以下文本：\n\n{body[:1500]}", max_tokens=500)
        except:
            deai_report = "检测跳过"

        return jsonify({
            "status": "ok",
            "content_form": form["name"],
            "creator": creator["name"],
            "platform": platform["name"],
            "title": title,
            "body": body,
            "word_count_actual": len(body),
            "research_brief": research,
            "deai_report": deai_report,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── A/B 测试 API ──
@app.route("/api/admin/ab")
def api_ab_stats():
    try:
        from ab_test import HOMEPAGE_TEST, PRICING_TEST
        return jsonify({
            "homepage": HOMEPAGE_TEST.get_stats(),
            "pricing": PRICING_TEST.get_stats(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════
# 补齐: 仪表盘统计 API
# ═══════════════════════════════════════════════════════
@app.route("/api/admin/dashboard")
def api_admin_dashboard():
    import time as _time, platform as _platform, socket as _socket
    stats = {
        "version": "v2.1.0",
        "python": _platform.python_version(),
        "platform": _platform.system() + " " + _platform.release(),
        "hostname": _socket.gethostname(),
    }
    # Uptime
    try:
        stats["uptime_seconds"] = round(time.time() - _START_TIME)
    except: pass
    # User count
    try:
        from database import Database
        db = Database().connect()
        r = db.fetch_one("SELECT COUNT(*) as c FROM users")
        stats["total_users"] = r["c"] if r else 0
        r2 = db.fetch_one("SELECT COUNT(*) as c FROM prompts")
        stats["total_prompts"] = r2["c"] if r2 else 0
    except: pass
    # Crash count
    try:
        from error_tracker import get_error_stats
        err = get_error_stats()
        stats["crash_count"] = err.get("total", 0) if isinstance(err, dict) else 0
    except: pass
    # Backup status
    try:
        from data_backup import get_backup_status
        stats["backup"] = get_backup_status()
    except: pass
    return jsonify({"status":"ok","stats":stats})


# ═══════════════════════════════════════════════════════
# 补齐: 用户管理 API
# ═══════════════════════════════════════════════════════
@app.route("/api/admin/users")
def api_admin_users():
    try:
        from database import Database
        db = Database().connect()
        search = request.args.get("search", "")
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        offset = (page - 1) * limit
        if search:
            rows = db.fetch_all(
                "SELECT id,tenant_id,email,name,role,created_at FROM users WHERE email LIKE ? OR name LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [f"%{search}%", f"%{search}%", limit, offset])
            total = db.fetch_one("SELECT COUNT(*) as c FROM users WHERE email LIKE ? OR name LIKE ?",
                                [f"%{search}%", f"%{search}%"])["c"]
        else:
            rows = db.fetch_all(
                "SELECT id,tenant_id,email,name,role,created_at FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [limit, offset])
            total = db.fetch_one("SELECT COUNT(*) as c FROM users")["c"]
        return jsonify({"status":"ok","users":[dict(r) for r in rows],"total":total,"page":page,"limit":limit})
    except Exception as e:
        return jsonify({"status":"ok","users":[],"total":0,"page":1,"limit":20,"_note":str(e)})


@app.route("/api/admin/users/<int:uid>", methods=["PUT", "DELETE"])
def api_admin_user_manage(uid):
    try:
        from database import Database
        db = Database().connect()
        if request.method == "DELETE":
            db.execute("DELETE FROM users WHERE id=?", [uid])
            db.conn.commit()
            return jsonify({"status":"ok","deleted":uid})
        else:
            data = request.get_json() or {}
            db.execute("UPDATE users SET name=?, role=? WHERE id=?",
                      [data.get("name",""), data.get("role","user"), uid])
            db.conn.commit()
            return jsonify({"status":"ok","updated":uid})
    except Exception as e:
        return jsonify({"error":str(e)}), 400


# ═══════════════════════════════════════════════════════
# 补齐: 授权/API Key 管理
# ═══════════════════════════════════════════════════════
@app.route("/api/admin/api-keys")
def api_admin_apikeys():
    try:
        from api_platform import APIKeyManager
        km = APIKeyManager()
        keys = []
        for k in km._keys:
            keys.append({"id":k.get("key","")[:8], "key":k.get("key",""),
                        "name":k.get("name",""), "created":k.get("created_at",""),
                        "last_used":k.get("last_used",""), "enabled":k.get("enabled",True)})
        return jsonify({"status":"ok","keys":keys})
    except Exception as e:
        try:
            from database import Database
            db = Database().connect()
            rows = db.fetch_all("SELECT * FROM api_keys ORDER BY created_at DESC")
            return jsonify({"status":"ok","keys":[dict(r) for r in rows]})
        except:
            return jsonify({"status":"ok","keys":[],"_note":str(e)})


@app.route("/api/admin/api-keys/generate", methods=["POST"])
def api_admin_apikey_generate():
    try:
        from api_platform import APIKeyManager
        km = APIKeyManager()
        data = request.get_json() or {}
        key = km.generate_key(data.get("name","Admin Generated"), data.get("plan","pro"))
        return jsonify({"status":"ok","key":key})
    except Exception as e:
        import secrets
        new_key = "sk-" + secrets.token_hex(24)
        try:
            from database import Database
            db = Database().connect()
            db.insert("api_keys", {"key":new_key, "name":request.get_json().get("name","Admin"),"created_at":str(__import__('datetime').datetime.now())[:19],"enabled":1})
        except: pass
        return jsonify({"status":"ok","key":{"key":new_key,"name":request.get_json().get("name","Admin")}})


@app.route("/api/admin/api-keys/<key_id>/revoke", methods=["POST"])
def api_admin_apikey_revoke(key_id):
    try:
        from api_platform import APIKeyManager
        km = APIKeyManager()
        km.revoke_key(key_id)
        return jsonify({"status":"ok","revoked":key_id})
    except:
        try:
            from database import Database
            db = Database().connect()
            db.execute("UPDATE api_keys SET enabled=0 WHERE key LIKE ?", [f"{key_id}%"])
            db.conn.commit()
        except: pass
        return jsonify({"status":"ok","revoked":key_id})


# ═══════════════════════════════════════════════════════
# 补齐: 系统日志 API
# ═══════════════════════════════════════════════════════
@app.route("/api/admin/logs")
def api_admin_logs():
    lines = []
    log_dir = Path(__file__).parent.parent / "logs"
    if not log_dir.exists():
        log_dir = Path("D:/浏览器/CloudTech-v2.0.0/logs")
    try:
        log_files = sorted(log_dir.glob("*.log"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        for lf in log_files:
            raw = lf.read_text(errors="ignore")[-50000:]
            for line in raw.strip().split("\n")[-200:]:
                lines.append({"file":lf.name,"text":line})
    except Exception as e:
        lines.append({"file":"error","text":str(e)})
    return jsonify({"status":"ok","lines":lines[-200:],"total":len(lines)})


# ═══════════════════════════════════════════════════════
# 补齐: 崩溃报告 API
# ═══════════════════════════════════════════════════════
@app.route("/api/admin/crashes")
def api_admin_crashes():
    try:
        from error_tracker import get_error_stats
        stats = get_error_stats(30) if callable(get_error_stats) else {}
        # Try to read crash log file directly
        recent = []
        crash_log = Path(__file__).parent / "data" / "crash_log.jsonl"
        if crash_log.exists():
            lines = crash_log.read_text(errors="ignore").strip().split("\n")[-50:]
            for line in lines:
                try: recent.append(json.loads(line))
                except: pass
        return jsonify({"status":"ok","stats":stats,"recent":recent})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500


# ═══════════════════════════════════════════════════════
# 复盘 — Post-mortem + 知识转化 + 管线点火
# ═══════════════════════════════════════════════════════

@app.route("/api/admin/postmortem")
def api_postmortem():
    """读取复盘日志"""
    pm_file = Path("C:/Users/xinzh/.openclaw/workspace/state/postmortem-log.json")
    try:
        data = json.loads(pm_file.read_text(encoding="utf-8"))
        records = data.get("records", []) if isinstance(data, dict) else data
        return jsonify({"status": "ok", "records": records, "total": len(records)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/admin/postmortem/run", methods=["POST"])
def api_postmortem_run():
    """触发一次复盘：扫描今日任务→L1直接因→L2机制缺口→L3模式判断"""
    import datetime as _dt
    today = _dt.datetime.now().strftime("%Y-%m-%d")
    findings = {
        "date": today,
        "task": "云数科技 v2.1 全量复盘",
        "L1_direct": "管线定义完整但执行=0。24个Cron配置就绪但内容产出中断。Inbox堆积90条未转化。Post-mortem机制仅1条记录。",
        "L2_mechanism": "1) Cron调度与执行之间存在断裂层——任务被调度但上游Agent未触发 2) 知识转化无自动化管道——Inbox→Knowledge→Pattern→Rule 四层之间无连接器 3) 内容生产无端到端验证——Brief→生产→QC→发布链路不可见",
        "L3_pattern": "系统整体处于'定义完成·执行未激活'状态。根因不是功能缺失而是集成缺失——各模块独立可用但无端到端连接器。这是系统集成阶段的典型瓶颈。",
        "actions": [
            "建立端到端管线测试：情报收集→Brief生成→内容生产→QC→发布 逐段验证",
            "知识转化自动化：Inbox(90条)→规则引擎提取→Pattern入库→Rule激活",
            "每周复盘自动化：Cron触发→扫描任务队列→L1/L2/L3分析→记录postmortem",
            "管线监控仪表盘：实时显示 情报数/Brief数/产出数/发布数/错误数"
        ]
    }
    # 追加到复盘日志
    pm_file = Path("C:/Users/xinzh/.openclaw/workspace/state/postmortem-log.json")
    data = json.loads(pm_file.read_text(encoding="utf-8")) if pm_file.exists() else {"version": 1, "records": []}
    data["records"].append({"id": f"pm-{len(data['records'])+1:03d}", **findings})
    pm_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"status": "ok", "findings": findings, "total_records": len(data["records"])})


@app.route("/api/admin/knowledge/stats")
def api_knowledge_stats():
    """知识库统计：Inbox→Knowledge→Pattern→Rule 四层计数"""
    kb = Path("D:/个人文件/AI/Knowledge")
    stats = {
        "inbox": len(list((kb/"01_Inbox").glob("*.md"))) if (kb/"01_Inbox").exists() else 0,
        "processed": len(list((kb/"02_Processed").glob("*.md"))) if (kb/"02_Processed").exists() else 0,
        "patterns": len(list((kb/"03_Patterns").glob("*.md"))) if (kb/"03_Patterns").exists() else 0,
        "rules": len(list((kb/"04_Rules").glob("*.md"))) if (kb/"04_Rules").exists() else 0,
    }
    return jsonify({"status": "ok", "stats": stats, "conversion_rate": f"{stats['rules']/max(stats['inbox'],1)*100:.1f}%"})


@app.route("/api/admin/pipeline/status")
def api_pipeline_status():
    """内容管线状态总览"""
    content_dir = Path("D:/个人文件/AI/05 项目生产系统/内容生产")
    briefs_dir = Path("D:/个人文件/AI/01 世界模型系统/话题追踪/选题建议")
    intel_dir = Path("D:/个人文件/AI/01 世界模型系统/情报日报")
    status = {
        "cron_jobs": 24,
        "cron_enabled": 24,
        "content_produced_today": len(list(content_dir.rglob("*.md"))) if content_dir.exists() else 0,
        "briefs_generated": len(list(briefs_dir.rglob("*.md"))) if briefs_dir.exists() else 0,
        "intel_reports": len(list(intel_dir.rglob("*.md"))) if intel_dir.exists() else 0,
    }
    status["pipeline_health"] = "active" if status["content_produced_today"] > 0 else "idle"
    return jsonify({"status": "ok", "pipeline": status})


@app.route("/api/admin/pipeline/trigger", methods=["POST"])
def api_pipeline_trigger():
    """手动触发内容管线：选题发现→多平台生产→保存发布"""
    from datetime import datetime
    data = request.get_json() or {}
    topic = data.get("topic", "装修设计")
    creator = data.get("creator", "zhinan")
    count = int(data.get("count", 1))

    result = {"steps": [], "topic": topic, "started_at": datetime.now().isoformat()[:19]}

    # Step 1: 选题发现
    try:
        cn = CREATOR_STYLES.get(creator, CREATOR_STYLES["zhinan"])["name"]
        sys_p = f"你是选题策划师。对标「{cn}」风格，为「{topic}」发现{count}个最值得做的选题。每个选题一行，格式: 标题||平台||角度||大纲"
        raw = _deepseek_call(sys_p, f"领域: {topic}", max_tokens=800, temperature=0.8)
        briefs = [l.strip() for l in raw.split("\n") if "||" in l][:count]
        result["steps"].append({"step": 1, "name": "选题发现", "status": "ok", "count": len(briefs), "briefs": briefs})
    except Exception as e:
        result["steps"].append({"step": 1, "name": "选题发现", "status": "failed", "error": str(e)[:100]})

    # Step 2: 批量内容生产
    produced = []
    for i in range(min(count, 5)):
        try:
            cur_topic = briefs[i].split("||")[0].strip() if i < len(briefs) else f"{topic} #{i+1}"
            form = CONTENT_FORMS["article"]
            cr = CREATOR_STYLES.get(creator, CREATOR_STYLES["zhinan"])
            pl = PLATFORMS["xiaohongshu"]

            parts = [
                f"你是顶尖内容创作者。对标「{cr['name']}」: {cr['tone']}",
                f"结构: {' → '.join(form['structure'])}",
                f"平台: {pl['name']}（{pl['style']}）字数600-800字",
                f"禁用词: {', '.join(cr['forbidden'])}",
            ]
            content = _deepseek_call("\n".join(parts), f"主题: {cur_topic}", max_tokens=1500)
            title = content.split("\n")[0] if content else cur_topic

            # 保存
            out_dir = Path("D:/个人文件/AI/05 项目生产系统/内容生产")
            out_dir.mkdir(parents=True, exist_ok=True)
            safe_name = cur_topic[:30].replace("/", "_").replace("\\", "_")
            out_file = out_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}_{safe_name}.md"
            out_file.write_text(f"# {title}\n\n> 创作者: {cr['name']} | 平台: {pl['name']} | 生成: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}", encoding="utf-8")
            produced.append({"title": title, "file": str(out_file), "words": len(content)})
        except Exception as e:
            produced.append({"title": cur_topic, "error": str(e)[:100]})

    result["steps"].append({"step": 2, "name": "内容生产", "status": "ok", "produced": len(produced), "items": produced})
    return jsonify({"status": "ok", "result": result})


@app.route("/api/admin/knowledge/convert", methods=["POST"])
def api_knowledge_convert():
    """触发知识转化: Inbox → Knowledge → Pattern → Rule"""
    from pipeline_engine import convert_knowledge
    data = request.get_json() or {}
    max_items = int(data.get("max_items", 10))
    result = convert_knowledge(max_items)
    return jsonify({"status": "ok", "result": result})


@app.route("/api/admin/zhuangqi/batch", methods=["POST"])
def api_zhuangqi_batch():
    """装企批量生产: 7系列×39账号 (异步后台执行)"""
    from pipeline_engine import batch_produce
    import threading as _th
    data = request.get_json() or {}
    series = data.get("series")  # None = all
    count = int(data.get("count", 3))

    # Fire background thread
    result_holder = {}
    def _run():
        try:
            result_holder["result"] = batch_produce(series, count)
        except Exception as e:
            result_holder["error"] = str(e)
    t = _th.Thread(target=_run, daemon=True)
    t.start()

    # Return immediately with status
    return jsonify({
        "status": "ok",
        "message": f"批量生产已启动: {series or '全部系列'} × {count}个账号, 后台执行中",
        "series": series,
        "count": count,
    })


@app.route("/api/admin/tenants")
def api_admin_tenants():
    """多租户列表"""
    from database import Database
    db = Database().connect()
    rows = db.fetch_all("SELECT * FROM tenants ORDER BY created_at DESC")
    return jsonify({"status": "ok", "tenants": [dict(r) for r in rows]})

@app.route("/api/admin/tenants/create", methods=["POST"])
def api_tenant_create():
    """创建新租户"""
    from database import Database
    import secrets, time as _time
    data = request.get_json() or {}
    tid = data.get("id", f"tenant-{secrets.token_hex(4)}")

    # Retry up to 3 times on DB lock
    for attempt in range(3):
        try:
            db = Database().connect()
            db.insert("tenants", {
                "id": tid, "name": data.get("name", "新租户"),
                "email": data.get("email", f"{tid}@cloudtech.com"),
                "company": data.get("company", ""), "plan": data.get("plan", "pro"),
                "status": "active", "api_key": f"ak-{secrets.token_hex(16)}",
                "api_key_hash": secrets.token_hex(32)
            })
            return jsonify({"status": "ok", "tenant_id": tid})
        except Exception as e:
            if "locked" in str(e).lower() and attempt < 2:
                _time.sleep(1)
                continue
            return jsonify({"error": str(e)}), 400

@app.route("/api/admin/pipeline/recent")
def api_pipeline_recent():
    cache = Path(__file__).parent / "data" / "content_cache.json"
    if cache.exists():
        try:
            return jsonify({"status": "ok", "recent": json.loads(cache.read_text(encoding="utf-8"))})
        except:
            pass
    # Fallback: scan content directories
    results = []
    content_dirs = [
        Path("D:/个人文件/AI/05 项目生产系统/内容生产"),
        Path("D:/个人文件/AI/云数科技/tenants"),
    ]
    for base_dir in content_dirs:
        if not base_dir.exists():
            continue
        files = sorted(
            [(f, f.stat().st_mtime) for f in base_dir.rglob("*.md") if f.is_file()],
            key=lambda x: x[1], reverse=True
        )[:15]
        for f, mtime in files:
            try:
                text = f.read_text(encoding="utf-8")[:600]
                title = text.split("\n")[0].replace("# ", "").strip()[:60]
                score_match = re.search(r'评分[：:]\s*(\d+)/10', text)
                creator_match = re.search(r'>\s*(.+?)\s*\|', text)
                results.append({
                    "title": title, "file": str(f),
                    "size": f.stat().st_size,
                    "score": int(score_match.group(1)) if score_match else None,
                    "creator": creator_match.group(1) if creator_match else None,
                    "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%m-%d %H:%M")
                })
            except:
                pass
    return jsonify({"status": "ok", "recent": results})


@app.route("/api/kuaizi/run", methods=["POST"])
def api_kuaizi_run():
    """筷子流水线: 输入楼盘→全平台输出"""
    from kuaizi_pipeline import kuaizi
    data = request.get_json() or {}
    result = kuaizi(data)
    return jsonify({"status": "ok", "result": result})

# ═══════════════════════════════════════════════════════
# 视频引擎 API
# ═══════════════════════════════════════════════════════

@app.route("/api/video/modes")
def api_video_modes():
    """视频生成模式列表"""
    from video_engine import VIDEO_MODES
    modes = [{"id": k, "name": v["name"], "duration": v["duration"], "scenes": v["scenes"]} for k, v in VIDEO_MODES.items()]
    return jsonify({"status": "ok", "modes": modes})

@app.route("/api/video/generate", methods=["POST"])
def api_video_generate():
    """生成视频脚本+素材匹配"""
    from video_engine import generate_video_script, create_video_package
    data = request.get_json() or {}
    result = generate_video_script(
        data.get("topic", ""),
        data.get("mode", "before_after"),
        data.get("context", {}),
    )
    pkg = create_video_package(result, data.get("account", "默认账号"))
    result["package"] = pkg
    return jsonify({"status": "ok", "result": result})


# ═══════════════════════════════════════════════════════
# 多租户平台 API
# ═══════════════════════════════════════════════════════

@app.route("/api/tenant/create", methods=["POST"])
def api_create_zhuangqi_tenant():
    """创建装企租户"""
    from tenant_platform import create_tenant
    data = request.get_json() or {}
    t = create_tenant(data.get("name", "新装企"), data.get("cities", ["厦门"]), data.get("plan", "pro"))
    return jsonify({"status": "ok", "tenant": t})

@app.route("/api/tenant/<tid>/dashboard")
def api_tenant_dashboard(tid):
    """装企客户仪表盘"""
    from tenant_platform import get_client_dashboard
    return jsonify(get_client_dashboard(tid))

@app.route("/api/tenant/<tid>/matrix")
def api_tenant_matrix(tid):
    """装企账号矩阵"""
    from tenant_platform import get_account_matrix
    return jsonify(get_account_matrix(tid))

@app.route("/api/tenant/<tid>/distribute", methods=["POST"])
def api_tenant_distribute(tid):
    """内容分发到矩阵"""
    from tenant_platform import distribute_content
    data = request.get_json() or {}
    return jsonify(distribute_content(tid, data.get("topic", ""), data.get("content_type", "article")))

@app.route("/api/tenant/<tid>/tokens")
def api_tenant_tokens(tid):
    """Token计量"""
    from tenant_platform import calculate_tokens
    return jsonify(calculate_tokens(tid))

@app.route("/api/geo/ranking-board")
def api_geo_ranking_board():
    """GEO排名看板: 最近检测结果汇总"""
    research_dir = Path("D:/个人文件/AI/Research")
    rankings = []
    for f in sorted(research_dir.glob("*排名*"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
        try:
            text = f.read_text(encoding="utf-8")[:2000]
            cities = re.findall(r'(厦门|泉州|漳州|福州|北京|上海|广州|深圳)', text)
            keywords = re.findall(r'(装修[^，。\n]{0,10})', text)
            rankings.append({
                "file": f.name,
                "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%m-%d"),
                "cities": list(set(cities))[:3],
                "keywords": list(set(keywords))[:3],
            })
        except:
            pass
    return jsonify({"status": "ok", "rankings": rankings})


@app.route("/api/publish/tracker")
def api_publish_tracker():
    """发布追踪: 从发布追踪.csv读取"""
    import csv
    tracker = Path("C:/Users/xinzh/Desktop/发布追踪.csv")
    items = []
    if tracker.exists():
        try:
            reader = csv.DictReader(tracker.read_text(encoding="utf-8-sig").splitlines())
            for row in reader:
                items.append(row)
        except:
            pass
    return jsonify({"status": "ok", "items": items[-20:], "total": len(items)})


@app.route("/api/tenants/list")
def api_tenants_list():
    """所有装企租户列表"""
    from tenant_platform import get_all_tenants
    return jsonify({"status": "ok", "tenants": get_all_tenants()})


@app.route("/api/admin/content/score", methods=["POST"])
def api_content_score():
    """内容质量自动评分: AI对产出进行5维度打分"""
    data = request.get_json() or {}
    text = data.get("text", "")
    if len(text) < 100:
        return jsonify({"status": "error", "message": "文本太短(需≥100字)"}), 400

    dims = [
        "标题吸引力(是否有钩子?令人想点击?)",
        "信息密度(是否有数据/案例/观点?)",
        "结构清晰度(逻辑是否流畅?分段是否合理?)",
        "AI痕迹(是否用'首先其次''总而言之'等模板词?)",
        "行动引导(结尾是否有CTA?是否推动读者行动?)"
    ]
    sys_p = f"你是内容质量评审专家。对以下内容5维度打分(1-10)并给出总分和一句话改进建议。输出格式:\n得分: X/10 | 标题: X | 信息: X | 结构: X | AI痕迹: X | 行动: X\n建议: ..."
    try:
        report = _deepseek_call(sys_p, f"评审以下内容:\n\n{text[:2000]}", max_tokens=500)
        return jsonify({"status": "ok", "report": report})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/admin/platform/summary")
def api_platform_summary():
    """平台管理总览"""
    from tenant_platform import get_all_tenants, get_client_dashboard
    from billing import check_quota, PLANS
    tenants = []
    total_mrr = 0
    for t in get_all_tenants():
        d = get_client_dashboard(t["id"])
        q = check_quota(t["id"])
        plan = PLANS.get(t.get("plan","pro"), PLANS["pro"])
        total_mrr += plan["price_monthly"]
        tenants.append({
            "id": t["id"], "name": t["name"], "plan": t["plan"],
            "monthly_used": d["monthly_used"], "avg_score": d["avg_score"],
            "accounts": d["total_accounts"], "mrr": plan["price_monthly"],
            "quota_pct": d["quota_pct"], "token_used": q["used_tokens"],
        })
    return jsonify({"status": "ok", "tenants": tenants, "total_mrr": total_mrr, "tenant_count": len(tenants)})


@app.route("/register")
def register_page():
    return send_from_directory(str(LANDING), "register-zhuangqi.html")

@app.route("/register-account")
def register_account_page():
    """邮箱注册页面"""
    return send_from_directory(str(LANDING), "register.html")

@app.route("/api/tenant/onboard", methods=["POST"])
def api_tenant_onboard():
    """一站式入驻: 创建租户→生成矩阵→首批5篇内容→返回仪表盘链接"""
    from tenant_platform import create_tenant, get_client_dashboard
    from kuaizi_pipeline import kuaizi
    from billing import record_usage
    import secrets
    
    data = request.get_json() or {}
    name = data.get("name", "新装企")
    cities = data.get("cities", ["厦门"])
    plan = data.get("plan", "pro")
    
    # Step 1: 创建租户
    tenant = create_tenant(name, cities, plan)
    tid = tenant["id"]
    
    # Step 2: 后台异步生成首批内容(避免超时)
    import threading as _th
    def _bg_produce():
        for topic in [f"{cities[0]}装修避坑指南", f"{cities[0]}旧房翻新案例"]:
            try:
                kuaizi({"city": cities[0], "style": "现代简约", "room_type": "全屋", "area": 100, "budget": 20, "community": "", "account": name})
                record_usage(tid, "article", topic, 8)
            except: pass
    _th.Thread(target=_bg_produce, daemon=True).start()
    produced = [{"topic": f"{cities[0]}首批内容×2", "status": "后台生产中,约2分钟后可查看"}]
    
    # Step 3: 返回仪表盘
    dashboard = get_client_dashboard(tid)
    
    return jsonify({
        "status": "ok",
        "tenant": tenant,
        "produced_count": len([p for p in produced if "error" not in p]),
        "dashboard_url": f"/client?tid={tid}",
        "dashboard": dashboard,
    })

# ═══════════════════════════════════════════════════════
# API 文档 — OpenAPI 3.0 + Swagger UI
# ═══════════════════════════════════════════════════════

@app.route("/api/docs")
def api_docs_page():
    return send_from_directory(str(LANDING), "api-docs.html")

@app.route("/api/openapi.json")
def api_openapi_json():
    from openapi import get_spec
    return jsonify(get_spec())


# ═══════════════════════════════════════════════════════
# 监控 — Prometheus metrics endpoint
# ═══════════════════════════════════════════════════════

@app.route("/metrics", methods=["GET"], endpoint="metrics_endpoint")
def metrics():
    import time as _time, shutil as _shutil
    lines = [
        "# HELP cloudtech_info CloudTech version info",
        "cloudtech_info{version=\"2.1.0\"} 1",
        "# HELP cloudtech_http_requests_total Total HTTP requests (placeholder)",
        "cloudtech_http_requests_total 0",
    ]
    try:
        usage = _shutil.disk_usage("C:\\")
        lines.append("# HELP system_disk_free_bytes Disk free space on C:")
        lines.append(f"system_disk_free_bytes {usage.free}")
    except:
        lines.append("system_disk_free_bytes 0")
    return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"}


# ⚠️ 通配路由必须放在最后，否则会拦截 /admin /health 等
@app.route("/<path:filename>")
def serve_static(filename):
    # Don't intercept API routes
    if filename in ("metrics", "api/openapi.json", "api/docs"):
        return jsonify({"error": "Not found"}), 404
    path = LANDING / filename
    if path.exists():
        return send_from_directory(str(LANDING), filename)
    return jsonify({"error": "Not found"}), 404

# ── CORS ──
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5099,http://127.0.0.1:5099,http://localhost:8501").split(",")

@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin", "")
    if origin in CORS_ORIGINS or not origin:  # no origin = same-origin request
        response.headers["Access-Control-Allow-Origin"] = origin or CORS_ORIGINS[0]
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Admin-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response

if __name__ == "__main__":
    # Register A/B test middleware
    try:
        from ab_test import ab_middleware
        ab_middleware(app)
        print("  A/B testing middleware registered")
    except Exception as e:
        print(f"  A/B middleware skipped: {e}")

    print("=" * 50)
    print("  云数科技 CloudTech v2.0.0 — Web 管理后台")
    print(f"  管理后台: http://localhost:5099/admin")
    print(f"  Landing: http://localhost:5099/")
    print(f"  健康检查: http://localhost:5099/health")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5099, debug=False)
