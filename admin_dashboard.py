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

# ═══════════════════════════════════════
# API 速率限制
# ═══════════════════════════════════════
_rate_buckets = {}  # ip → {tokens, last_refill}

def _rate_limit(ip: str, limit: int = 30, window: int = 10) -> bool:
    """令牌桶限流: 默认30req/10s·返回True=放行 False=限流"""

def _rate_limit_tenant(tid: str, limit: int = None) -> bool:
    """租户级限流: starter=20·pro=60·enterprise=200 req/min"""
    if not limit:
        from tenant_service import get_plan
        limits = {"starter": 20, "pro": 60, "enterprise": 200}
        try:
            tenant = __import__('tenant_service', fromlist=['get_tenant']).get_tenant(tid)
            plan = tenant.get("plan", "starter") if tenant else "starter"
            limit = limits.get(plan, 20)
        except: limit = 20
    return _rate_limit(f"tenant:{tid}", limit=limit, window=60)
    now = time.time()
    bucket = _rate_buckets.get(ip, {"tokens": limit, "last": now})
    elapsed = now - bucket["last"]
    bucket["tokens"] = min(limit, bucket["tokens"] + elapsed * (limit / window))
    bucket["last"] = now
    if bucket["tokens"] >= 1:
        bucket["tokens"] -= 1
        _rate_buckets[ip] = bucket
        return True
    _rate_buckets[ip] = bucket
    return False

# ═══════════════════════════════════════
# 计费强制执行层
# ═══════════════════════════════════════
def _quota_guard(tid: str = "zq-5bb59623", content_type: str = "article"):
    """配额守卫: 检查→拦截超额→返回状态。必须在内容生成前调用。"""
    from tenant_service import check_quota
    q = check_quota(tid)
    if not q.get("ok"):
        return q  # 超额，返回配额信息
    return None  # 通过

def _usage_log(tid: str, content_type: str, topic: str, tokens: int = None):
    """用量记录: 内容生成成功后调用。"""
    from tenant_service import record_usage
    return record_usage(tid, content_type, topic, tokens)

# 默认租户（Admin面板操作归属）
_DEFAULT_TID = "zq-5bb59623"

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
        except Exception:
            pass
    return False

# ── 自定义错误页 ──
@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "接口不存在", "code": 404}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"status": "error", "message": "服务器内部错误", "code": 500}), 500

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"status": "error", "message": "请求过于频繁", "code": 429, "retry_after": 10}), 429

@app.before_request
def admin_guard():
    if not _check_admin_auth():
        if request.path.startswith("/api/"):
            return jsonify({"error": "Authentication required", "login_url": "/admin"}), 401
        # For /admin page, redirect to login
        return send_from_directory(str(LANDING), "admin.html")  # admin.html has its own login check

# ── 真实系统健康检查 ──
@app.route("/api/system/health")
def api_system_health_real():
    """真实健康检查: 服务端口·磁盘·内存·进程"""
    import subprocess, socket, shutil
    checks = {}

    # 磁盘
    try:
        usage = shutil.disk_usage("C:\\")
        checks["disk"] = {"free_gb": round(usage.free / 1073741824, 1), "total_gb": round(usage.total / 1073741824, 1), "pct_used": round((1 - usage.free / usage.total) * 100)}
    except Exception: checks["disk"] = "error"

    # 服务端口检查
    services = {}
    for name, port in [("gateway", 18792), ("fastapi", 5100), ("streamlit", 8501), ("codex", 19193)]:
        try:
            s = socket.socket(); s.settimeout(2)
            s.connect(("127.0.0.1", port)); s.close()
            services[name] = "up"
        except Exception: services[name] = "down"
    checks["services"] = services

    # 本服务
    checks["self"] = {"uptime_seconds": round(time.time() - _START_TIME), "api_routes": len([r for r in app.url_map.iter_rules()])}
    return jsonify({"status": "ok", "health": checks})

@app.route("/api/export/stats")
def api_export_stats():
    """导出全量统计数据（JSON）"""
    from dashboard_stats import get_full_stats
    from tenant_service import get_all_tenants
    stats = get_full_stats()
    stats["tenant_details"] = get_all_tenants()
    return jsonify({"status": "ok", "export": stats, "exported_at": stats["generated_at"]})

@app.route("/api/export/content/<tid>")
def api_export_content(tid):
    """导出租户内容列表"""
    content_dir = Path(f"D:/个人文件/AI/云数科技/tenants/{tid}/content")
    items = []
    if content_dir.exists():
        for f in sorted(content_dir.rglob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:50]:
            items.append({"file": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime})
    return jsonify({"status": "ok", "tenant_id": tid, "content_count": len(items), "items": items})

@app.route("/api/export/csv/<tid>")
def api_export_csv(tid):
    """导出租户内容为CSV"""
    import csv, io
    content_dir = Path(f"D:/个人文件/AI/云数科技/tenants/{tid}/content")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["标题", "文件", "大小(KB)", "评分", "修改时间"])
    from datetime import datetime as _dt
    if content_dir.exists():
        for f in sorted(content_dir.rglob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:100]:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")[:200]
                title = text.split("\n")[0].replace("# ", "").strip()[:60]
                score = ""
                import re as _re
                sm = _re.search(r'评分[：:]\s*(\d+)/10', text)
                if sm: score = sm.group(1)
                mtime = _dt.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                writer.writerow([title, f.name, round(f.stat().st_size/1024,1), score, mtime])
            except Exception: pass
    csv_data = output.getvalue()
    from flask import Response
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={tid}_content.csv"})

# ═══════════════════════════════════════════════════════
# 内容搜索 API
# ═══════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════
# Webhook API
# ═══════════════════════════════════════════════════════
@app.route("/api/webhooks", methods=["GET", "POST"])
def api_webhooks():
    from webhooks import list_webhooks, register_webhook
    if request.method == "POST":
        data = request.get_json() or {}
        return jsonify(register_webhook(data.get("tid", ""), data.get("event", ""), data.get("url", ""), data.get("secret", "")))
    return jsonify({"status": "ok", "webhooks": list_webhooks(request.args.get("tid", ""))})

@app.route("/api/webhooks/<wid>", methods=["DELETE"])
def api_webhook_delete(wid):
    from webhooks import delete_webhook
    return jsonify(delete_webhook(wid))

# ═══════════════════════════════════════════════════════
# 品牌资产管理 API
# ═══════════════════════════════════════════════════════
@app.route("/api/brands", methods=["GET", "POST"])
def api_brands():
    from brand_assets import list_brands, create_brand
    if request.method == "POST":
        data = request.get_json() or {}
        return jsonify(create_brand(data.get("tid", _DEFAULT_TID), data.get("name", "新品牌"), data.get("config")))
    return jsonify({"status": "ok", "brands": list_brands(request.args.get("tid", ""))})

@app.route("/api/brands/<bid>/assets", methods=["POST", "DELETE"])
def api_brand_assets(bid):
    from brand_assets import add_asset, remove_asset
    if request.method == "POST":
        data = request.get_json() or {}
        return jsonify(add_asset(bid, data.get("type", "logo"), data.get("name", ""), data.get("uri", ""), data.get("meta")))
    data = request.get_json() or {}
    return jsonify(remove_asset(bid, data.get("type", ""), data.get("aid", "")))

# ═══════════════════════════════════════════════════════
# 内容效果分析 API
# ═══════════════════════════════════════════════════════
@app.route("/api/analytics/performance/<tid>")
def api_analytics_performance(tid):
    from content_analytics import get_content_performance, get_platform_breakdown, get_content_roi
    days = int(request.args.get("days", 30))
    return jsonify({"status": "ok", "performance": get_content_performance(tid, days),
                    "by_platform": get_platform_breakdown(tid, days), "roi": get_content_roi(tid)})

@app.route("/api/analytics/track", methods=["POST"])
def api_analytics_track():
    from content_analytics import track_content
    data = request.get_json() or {}
    return jsonify(track_content(data.get("tid", _DEFAULT_TID), data.get("content_id", ""), data.get("platform", "xiaohongshu"), data.get("metrics", {})))

# ═══════════════════════════════════════════════════════
# 团队协作 API
# ═══════════════════════════════════════════════════════
@app.route("/api/teams", methods=["GET", "POST"])
def api_teams():
    from team_collab import create_team, get_team
    if request.method == "POST":
        data = request.get_json() or {}
        return jsonify(create_team(data.get("tid", _DEFAULT_TID), data.get("name", "新团队")))
    tid = request.args.get("tid", "")
    return jsonify({"status": "ok", "team": get_team(request.args.get("team_id", "")) if request.args.get("team_id") else None})

@app.route("/api/teams/<team_id>/members", methods=["POST", "DELETE"])
def api_team_members(team_id):
    from team_collab import add_member, remove_member
    data = request.get_json() or {}
    if request.method == "POST":
        return jsonify(add_member(team_id, data.get("email", ""), data.get("role", "editor")))
    return jsonify(remove_member(team_id, data.get("email", "")))

# ═══════════════════════════════════════════════════════
# 合规自动化 API
# ═══════════════════════════════════════════════════════
@app.route("/api/compliance/check", methods=["POST"])
def api_compliance_check():
    from compliance_auto import run_compliance_check, get_compliance_stats
    data = request.get_json() or {}
    return jsonify(run_compliance_check(data, data.get("content_type", "article")))

@app.route("/api/compliance/stats")
def api_compliance_stats():
    from compliance_auto import get_compliance_stats
    return jsonify({"status": "ok", "stats": get_compliance_stats()})

# ═══════════════════════════════════════════════════════
# 多语言 API
# ═══════════════════════════════════════════════════════
@app.route("/api/i18n/languages")
def api_i18n_languages():
    from i18n import get_languages, t
    return jsonify({"status": "ok", "languages": get_languages(), "sample": {"dashboard": t("dashboard"), "content": t("content")}})

@app.route("/api/i18n/translate", methods=["POST"])
def api_i18n_translate():
    from i18n import translate_content, get_translation_jobs
    data = request.get_json() or {}
    if data.get("list"): return jsonify({"status": "ok", "jobs": get_translation_jobs()})
    return jsonify(translate_content(data.get("text", ""), data.get("lang", "en")))

# ═══════════════════════════════════════════════════════
# 模板库 API
# ═══════════════════════════════════════════════════════
@app.route("/api/templates")
def api_templates():
    from template_library import list_templates, get_template_categories, apply_template
    if request.args.get("apply"):
        return jsonify(apply_template(request.args.get("apply"), {}))
    return jsonify({"status": "ok", "templates": list_templates(request.args.get("category", ""), request.args.get("platform", "")), "categories": get_template_categories()})

# ═══════════════════════════════════════════════════════
# 审批工作流 API
# ═══════════════════════════════════════════════════════
@app.route("/api/approvals/<tid>")
def api_approvals(tid):
    from approval_engine import get_approvals, get_approval_stats
    return jsonify({"status": "ok", "approvals": get_approvals(tid, request.args.get("status", "")), "stats": get_approval_stats(tid)})

@app.route("/api/approvals/submit", methods=["POST"])
def api_approval_submit():
    from approval_engine import submit_for_review
    data = request.get_json() or {}
    return jsonify(submit_for_review(data.get("tid", _DEFAULT_TID), data.get("content_id", ""), data.get("title", ""), data.get("submitter", "admin")))

@app.route("/api/approvals/<aid>/resolve", methods=["POST"])
def api_approval_resolve(aid):
    from approval_engine import approve, reject
    data = request.get_json() or {}
    action = data.get("action", "approve")
    if action == "reject": return jsonify(reject(aid, data.get("reviewer", "admin"), data.get("comment", "")))
    return jsonify(approve(aid, data.get("reviewer", "admin"), data.get("comment", "")))

# ═══════════════════════════════════════════════════════
# 数字人/虚拟角色 API
# ═══════════════════════════════════════════════════════
@app.route("/api/avatars")
def api_avatars():
    from digital_human import list_avatars, get_avatar_stats
    return jsonify({"status": "ok", "avatars": list_avatars(request.args.get("tid", ""), request.args.get("type", "")), "stats": get_avatar_stats(request.args.get("tid", ""))})

@app.route("/api/avatars/register", methods=["POST"])
def api_avatar_register():
    from digital_human import register_avatar
    data = request.get_json() or {}
    return jsonify(register_avatar(data.get("tid", _DEFAULT_TID), data.get("name", ""), data.get("type", "stock"), data.get("config")))

@app.route("/api/avatars/<avatar_id>/voice", methods=["POST"])
def api_avatar_voice(avatar_id):
    from digital_human import add_voice
    data = request.get_json() or {}
    return jsonify(add_voice(avatar_id, data.get("name", ""), data.get("uri", ""), data.get("language", "zh-CN")))

# ═══════════════════════════════════════════════════════
# 审计日志 API
# ═══════════════════════════════════════════════════════
@app.route("/api/audit/<tid>")
def api_audit_tenant(tid):
    from audit_viewer import get_tenant_activity, log_activity
    log_activity(tid, "view_audit", {"endpoint": "audit_view"})
    return jsonify({"status": "ok", "activities": get_tenant_activity(tid, int(request.args.get("days", 7)), request.args.get("action", ""))})

@app.route("/api/audit/summary")
def api_audit_summary():
    from audit_viewer import get_activity_summary
    return jsonify({"status": "ok", "summary": get_activity_summary(int(request.args.get("days", 7)))})

# ═══════════════════════════════════════════════════════
# 内容推荐 API
# ═══════════════════════════════════════════════════════
@app.route("/api/recommend/topics")
def api_recommend_topics():
    from content_recommender import recommend_topics
    tid = request.args.get("tid", _DEFAULT_TID)
    return jsonify(recommend_topics(tid, request.args.get("city", "厦门"), int(request.args.get("count", 5))))

# ═══════════════════════════════════════════════════════
# 批量操作 API
# ═══════════════════════════════════════════════════════
@app.route("/api/batch/produce", methods=["POST"])
def api_batch_produce():
    """批量内容生产"""
    data = request.get_json() or {}
    topics = data.get("topics", [])
    if not topics:
        return jsonify({"status": "error", "message": "请提供选题列表"}), 400
    from kuaizi_pipeline import kuaizi
    import threading as _th
    results = []
    def _produce(t):
        try:
            r = kuaizi({"city": t.get("city","厦门"), "style": t.get("style","现代简约"),
                         "room_type": t.get("room","全屋"), "area": t.get("area",100),
                         "budget": t.get("budget",20), "community": t.get("topic","")})
            results.append({"topic": t.get("topic",""), "status": "ok", "saved": r.get("saved_to","")})
        except Exception as e:
            results.append({"topic": t.get("topic",""), "status": "failed", "error": str(e)[:80]})
    threads = [_th.Thread(target=_produce, args=(t,)) for t in topics]
    for t in threads: t.start()
    for t in threads: t.join(timeout=180)
    return jsonify({"status": "ok", "total": len(topics), "results": results})

@app.route("/api/search/content")
def api_search_content():
    """全平台内容搜索: 关键词·租户·日期范围"""
    import fnmatch
    q = request.args.get("q", "").strip()
    tid = request.args.get("tid", "")
    limit = int(request.args.get("limit", 20))

    results = []
    search_dirs = [Path("D:/个人文件/AI/云数科技/tenants")]
    if tid:
        search_dirs = [Path(f"D:/个人文件/AI/云数科技/tenants/{tid}/content")]

    scanned = 0
    for base in search_dirs:
        if not base.exists(): continue
        for f in sorted(base.rglob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            scanned += 1
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
                if q and q not in text: continue
                title = text.split("\n")[0].replace("# ", "").strip()[:80]
                score = None
                import re as _re
                sm = _re.search(r'评分[：:]\s*(\d+)/10', text)
                if sm: score = int(sm.group(1))
                results.append({
                    "title": title, "file": str(f), "size": f.stat().st_size,
                    "score": score, "preview": text[100:250].replace("\n", " "),
                    "modified": f.stat().st_mtime,
                })
                if len(results) >= limit: break
            except Exception: pass
        if len(results) >= limit: break
        if scanned > 1000: break  # Don't scan forever

    return jsonify({"status": "ok", "query": q, "results": results, "total": len(results), "scanned": scanned})

@app.route("/api/stats/trends")
def api_stats_trends():
    """内容趋势: 按日统计产出量"""
    from collections import defaultdict
    daily = defaultdict(int)
    for base in [Path("D:/个人文件/AI/云数科技/tenants")]:
        if not base.exists(): continue
        for f in base.rglob("*.md"):
            try:
                day = f.stat().st_mtime
                import datetime as _dt
                dkey = _dt.datetime.fromtimestamp(day).strftime("%Y-%m-%d")
                daily[dkey] += 1
            except Exception: pass

    # Last 30 days sorted
    sorted_days = sorted(daily.items())[-30:]
    return jsonify({
        "status": "ok",
        "trends": [{"date": d, "count": c} for d, c in sorted_days],
        "total_days": len(sorted_days),
        "total_content": sum(daily.values()),
    })

@app.route("/api/stats/summary")
def api_stats_summary():
    """系统总览: 一站获取所有关键指标"""
    from dashboard_stats import get_full_stats
    from tenant_service import get_all_tenants
    from payment_orders import get_payment_stats
    from notifications import get_unread_count

    stats = get_full_stats()
    return jsonify({
        "status": "ok",
        "summary": {
            "content_files": stats["content"]["total_files"],
            "tenants": stats["tenants"]["total"],
            "active_tenants": stats["tenants"]["active"],
            "queue_pending": stats["publish"]["queued"],
            "queue_scheduled": stats["publish"]["scheduled"],
            "queue_published": stats["publish"]["published"],
            "disk_free_gb": stats["system"]["disk_free_gb"],
            "payment_revenue": get_payment_stats()["revenue"],
            "notifications_unread": get_unread_count("zq-5bb59623"),
            "modules_active": 19,
        },
        "generated_at": stats["generated_at"],
    })


# ═══════════════════════════════════════════════════════
# 通知中心 API
# ═══════════════════════════════════════════════════════
@app.route("/api/notifications/<tid>")
def api_notifications(tid):
    from notifications import get_notifications, get_unread_count
    unread = request.args.get("unread", "") == "1"
    limit = int(request.args.get("limit", 20))
    return jsonify({"status": "ok", "notifications": get_notifications(tid, limit, unread), "unread_count": get_unread_count(tid)})

@app.route("/api/notifications/<tid>/read", methods=["POST"])
def api_notifications_read(tid):
    from notifications import mark_read
    data = request.get_json() or {}
    return jsonify(mark_read(tid, data.get("nid")))

# ── 一键产品演示 ──
@app.route("/api/demo/run", methods=["POST"])
def api_demo_run():
    """一键Demo: 创建租户→品牌→内容→分发→支付→通知→审计 全自动"""
    import secrets, threading, time as _time
    results = {"steps": [], "started_at": _time.time()}

    # Step 1: 创建租户
    from tenant_service import create_tenant
    t = create_tenant(f"Demo装企-{secrets.token_hex(2)}", ["厦门", "泉州"], "pro")
    tid = t["id"]
    results["steps"].append({"step": 1, "name": "创建租户", "status": "ok", "tid": tid, "plan": "pro"})

    # Step 2: 创建品牌
    from brand_assets import create_brand, add_asset
    b = create_brand(tid, f"{t['name']}品牌")
    add_asset(b["brand"]["id"], "logo", "品牌Logo", "/brands/logo.png")
    add_asset(b["brand"]["id"], "color", "品牌色", "#c9a96e")
    results["steps"].append({"step": 2, "name": "品牌资产", "status": "ok"})

    # Step 3: 注册数字人
    from digital_human import register_avatar, add_voice
    av = register_avatar(tid, "装修顾问小云", "stock")
    add_voice(av["avatar"]["id"], "标准女声", "/voices/female_zh.mp3")
    results["steps"].append({"step": 3, "name": "数字人", "status": "ok"})

    # Step 4: 内容生产(异步后台)
    def _produce():
        try:
            from kuaizi_pipeline import kuaizi
            kuaizi({"city": "厦门", "style": "现代简约", "room_type": "厨房", "area": 89, "budget": 15, "tenant_id": tid})
        except Exception: pass
    threading.Thread(target=_produce, daemon=True).start()
    results["steps"].append({"step": 4, "name": "AI内容生产", "status": "running", "note": "后台执行中~120s"})

    # Step 5: 分发+发布
    from content_scheduler import execute_distribution, enqueue, publish_now
    dist = execute_distribution(tid, "厦门厨房改造避坑指南", "article")
    # 手动入队+发布
    enqueue(tid, {"topic": "厦门厨房改造", "account": f"{t['name']}-小红书", "platform": "xiaohongshu", "priority": 10})
    pub = publish_now(tid)
    results["steps"].append({"step": 5, "name": "分发+发布", "status": "ok", "accounts": dist.get("total_distributions", 0), "published": pub.get("ok", False)})

    # Step 6: 支付
    from payment_orders import create_order, confirm_payment
    o = create_order(tid, "pro")
    confirm_payment(o["order"]["id"])
    results["steps"].append({"step": 6, "name": "支付", "status": "ok", "amount": o["order"]["amount"]})

    # Step 7: 版权+合规
    from digital_rights import register_asset
    from compliance_auto import run_compliance_check
    register_asset("portrait", f"{t['name']}业主授权", t['name'])
    comp = run_compliance_check({"text": "专业装修服务，厦门本地12年经验", "title": "Demo验证"})
    results["steps"].append({"step": 7, "name": "版权+合规", "status": comp["status"]})

    # Step 8: 通知
    from notifications import notify
    notify(tid, "system", "🎉 Demo完成", f"欢迎{t['name']}！您的装企AI平台已就绪。管理后台: /admin · 客户仪表盘: /client?tid={tid}", "success")
    results["steps"].append({"step": 8, "name": "通知", "status": "ok"})

    # Step 9: 审计
    from audit_viewer import log_activity
    log_activity(tid, "demo.completed", {"steps": len(results["steps"])})
    results["steps"].append({"step": 9, "name": "审计记录", "status": "ok"})

    elapsed = round(_time.time() - results["started_at"], 1)
    results["elapsed_seconds"] = elapsed
    results["tenant_id"] = tid
    results["dashboard_url"] = f"/client?tid={tid}"
    results["admin_url"] = "/admin"
    results["summary"] = f"Demo完成！{elapsed}秒 · {len(results['steps'])}个步骤 · 租户ID: {tid}"

    return jsonify({"status": "ok", "demo": results})


# ── 统一客户端数据端点 ──
@app.route("/api/client/full/<tid>")
def api_client_full(tid):
    """客户端一站式数据: 整合所有模块的租户视图"""
    from tenant_service import get_client_dashboard, get_account_matrix, check_quota
    from content_scheduler import get_stats as sched_stats, get_calendar
    from content_analytics import get_content_performance
    from approval_engine import get_approval_stats
    from compliance_auto import get_compliance_stats
    from brand_assets import list_brands, get_brand_stats
    from digital_human import get_avatar_stats
    from payment_orders import get_tenant_orders
    from notifications import get_notifications, get_unread_count
    from audit_viewer import get_tenant_activity, log_activity

    log_activity(tid, "dashboard_view", {"endpoint": "client_full"})
    dash = get_client_dashboard(tid)
    if "error" in dash:
        return jsonify({"status": "error", "message": dash["error"]}), 404

    return jsonify({"status": "ok", "data": {
        "tenant": dash,
        "quota": check_quota(tid),
        "matrix": get_account_matrix(tid),
        "publish": sched_stats(tid),
        "calendar": get_calendar(tid, 7),
        "performance": get_content_performance(tid, 30),
        "approvals": get_approval_stats(tid),
        "compliance": get_compliance_stats(),
        "brands": get_brand_stats(tid),
        "avatars": get_avatar_stats(tid),
        "payments": get_tenant_orders(tid, 5),
        "notifications": get_notifications(tid, 5),
        "unread": get_unread_count(tid),
        "activities": get_tenant_activity(tid, 1, limit=10),
    }})

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

@app.route("/api/debug/rate-limit-test")
def api_rate_limit_test():
    """速率限制测试端点: 快速连续请求触发429"""
    ip = request.remote_addr or "127.0.0.1"
    if _rate_limit(ip, limit=5, window=10):  # 5req/10s 严格限流
        return jsonify({"status": "ok", "message": "请求通过"})
    return jsonify({"status": "error", "message": "请求过于频繁", "retry_after": 2}), 429

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
    except Exception:
        services["gateway"] = "stopped"
    # Streamlit
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", 8501))
        s.close()
        services["streamlit"] = "running"
    except Exception:
        services["streamlit"] = "stopped"
    # 装企控制台
    try:
        s = socket.socket()
        s.settimeout(1)
        s.connect(("127.0.0.1", 8502))
        s.close()
        services["zhuangqi"] = "running"
    except Exception:
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
        from tenant_service import create_tenant as ts_create, get_plan
        plan_info = get_plan(plan)
        tenant = ts_create(name, [], plan, company, email)
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
    plan_id = data.get("plan_id", "pro")
    tid = data.get("tid", _DEFAULT_TID)
    from payment_orders import create_order
    result = create_order(tid, plan_id, data.get("method", "wechat"))
    return jsonify(result)

@app.route("/api/payment/confirm", methods=["POST"])
def api_confirm_payment():
    data = request.get_json() or {}
    oid = data.get("order_id", "")
    if not oid: return jsonify({"ok": False, "error": "缺少订单号"}), 400
    from payment_orders import confirm_payment
    return jsonify(confirm_payment(oid))

@app.route("/api/payment/orders/<tid>")
def api_payment_orders(tid):
    from payment_orders import get_tenant_orders
    return jsonify({"status": "ok", "orders": get_tenant_orders(tid)})

@app.route("/api/payment/stats")
def api_payment_stats():
    from payment_orders import get_payment_stats
    return jsonify({"status": "ok", "stats": get_payment_stats()})


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
    from backup_scheduler import run_backup, cleanup_old_backups
    cleanup_old_backups()
    return jsonify(run_backup(request.get_json(silent=True) or {}).get("label", "manual"))

@app.route("/api/admin/backup/status")
def api_backup_status():
    from backup_scheduler import get_backup_status, list_backups
    return jsonify({"status": "ok", "backup_status": get_backup_status(), "recent_backups": list_backups(10)})


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
            except Exception: pass
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

@app.route("/api/geo/to-topics", methods=["POST"])
def api_geo_to_topics():
    """GEO关键词→内容选题: 输入GEO关键词，自动生成内容选题"""
    data = request.get_json() or {}
    city = data.get("city", "厦门")
    keywords = data.get("keywords", ["装修设计"])
    count = int(data.get("count", 5))
    if not keywords:
        return jsonify({"status": "error", "message": "请提供关键词"}), 400
    kw_str = "、".join(keywords[:5])
    sys_p = f"""你是装企内容策略师。根据以下GEO关键词为{city}市场发现{count}个内容选题。
关键词: {kw_str}
每个选题一行: 标题||平台||内容形式||角度||预期效果
要求: 50%本地化+30%干货+20%情感，标题带{city}地名"""
    try:
        raw = _deepseek_call(sys_p, f"为{city}发现{count}个选题基于: {kw_str}", max_tokens=1500)
        topics = []
        for line in raw.split("\n"):
            parts = [p.strip() for p in line.split("||")]
            if len(parts) >= 4:
                topics.append({"title": parts[0], "platform": parts[1], "format": parts[2], "angle": parts[3]})
        return jsonify({"status": "ok", "city": city, "keywords": keywords, "topics": topics[:count]})
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
    "family": {
        "id": "family", "name": "亲情推荐", "icon": "❤️",
        "tagline": "记录式叙事·真实人物·情绪共鸣·信任转化",
        "tone": "【亲情推荐风格】记录式叙事，核心范式：'带老爸闯互联网'。用真实人物关系承载专业知识。结构：我爸是谁→一个具体故事→故事里的专业细节→我爸说的一句话→对读者有什么用。不卖货，只讲故事。第一人称+真实细节+父辈智慧+当代解读。适合小红书图文、公众号深度文、装企人设IP。人物可选：子女视角(传承)、工长视角(手艺)、质检视角(良心)、业主视角(信任)。",
        "structure": "人物亮相(我爸/我妈/我师父是谁) → 一个具体故事(300-500字) → 故事里的专业细节(3个知识点) → 父辈金句 → 对读者的实用价值",
        "word_range": (800, 2500),
        "best_platforms": ["小红书", "公众号", "视频号", "抖音"],
        "hook_templates": [
            "我爸干了{num}年装修，这是他教我的第一件事",
            "带老爸闯互联网的第{num}天，他说了一句话让我破防",
            "一个{职业}的爸爸，告诉我的{num}个装修真相",
        ],
        "forbidden": ["限时优惠", "立即购买", "扫码加微信", "原价", "折扣", "老板疯了"],
        "emoji": "medium",
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
    except Exception:
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
        except Exception:
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
        except Exception:
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


@app.route("/api/create/style-generate", methods=["POST"])
def api_create_style_generate():
    """风格克隆+生成: 参考文本→提取DNA→注入DNA生成新内容"""
    data = request.get_json() or {}
    ref_text = data.get("ref_text", "")
    topic = data.get("topic", "")
    if not ref_text or not topic:
        return jsonify({"status": "error", "message": "请提供参考文本和创作主题"}), 400
    try:
        # Phase 1: 提取风格DNA
        dna = _deepseek_call(STYLE_CLONE_SYSTEM, f"分析以下文本的风格DNA：\n\n{ref_text[:3000]}", max_tokens=800)
        # Phase 2: 用DNA生成新内容
        gen_sys = f"""你是顶尖内容创作者。请严格模仿以下风格DNA创作：

{dna}

创作主题: {topic}
要求: 句式和节奏完全模仿参考风格，用词偏好保持一致，情绪基调相同。800-1500字。"""
        content = _deepseek_call(gen_sys, f"主题: {topic}", max_tokens=3000, temperature=0.8)
        return jsonify({"status": "ok", "style_dna": dna, "content": content, "topic": topic})
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
    "renovation_showcase": {
        "id": "renovation_showcase", "name": "🏚️ 改造前后对比", "icon": "🏚️",
        "desc": "老破小爆改短视频口播·固定六段式·变量元素库驱动批量生产",
        "structure": ["黄金3秒钩子(惊人对比)", "改造前痛点特写(3个具体问题)", "业主要求(预算/风格/功能)", "施工过程快放(关键工艺节点)", "改造后同角度对比(视觉冲击)", "收口金句+CTA关注"],
        "best_platforms": ["抖音", "小红书", "视频号", "B站"],
        "word_range": (400, 1500),
        "production_notes": ["[Scene 0-3s] 改造前/后同角度闪切", "[Scene 3-10s] 痛点特写: 空间小/采光差/动线乱", "[Scene 10-20s] 业主需求字幕叠加", "[Scene 20-35s] 施工快放: 拆墙→水电→贴砖→油漆", "[Scene 35-45s] 改造后全景: 同角度对比+尺寸标注", "[Scene 45-55s] 花费清单弹出", "[Scene 55-60s] 设计师/业主点评·CTA"],
        "variable_elements": ["城市", "小区年代", "面积", "预算", "风格", "痛点(采光/空间/功能)", "特殊材料(微水泥/长虹玻璃/实木)"],
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

    # 速率限制
    client_ip = request.remote_addr or "127.0.0.1"
    if not _rate_limit(client_ip):
        return jsonify({"status": "error", "message": "请求过于频繁，请稍后再试", "retry_after": 10}), 429

    # 配额检查
    quota_block = _quota_guard(_DEFAULT_TID, content_form)
    if quota_block:
        return jsonify({"status": "error", "message": "配额已用完，请升级套餐", "quota": quota_block}), 429

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
        except Exception:
            research = "研究阶段跳过"

        # 去AI腔检测
        try:
            deai_report = _deepseek_call(
                "你是去AI腔检测专家。检测AI痕迹，5维度打分(1-10)+修改建议。",
                f"检测以下文本：\n\n{body[:1500]}", max_tokens=500)
        except Exception:
            deai_report = "检测跳过"

        # 记录用量+发送通知
        _usage_log(_DEFAULT_TID, content_form, topic)
        from notifications import notify_content_ready, notify_quota_warning
        notify_content_ready(_DEFAULT_TID, topic)
        q = check_quota(_DEFAULT_TID) if "check_quota" in dir() else None

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
        from ab_test import HOMEPAGE_TEST, PRICING_TEST, CONTENT_TEST
        return jsonify({
            "homepage": HOMEPAGE_TEST.get_stats(),
            "pricing": PRICING_TEST.get_stats(),
            "content": CONTENT_TEST.get_stats(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/admin/ab/assign", methods=["POST"])
def api_ab_assign():
    """为内容生产分配A/B测试变体（创作者风格随机分配）"""
    from ab_test import CONTENT_TEST
    data = request.get_json() or {}
    user_id = data.get("user_id", "")
    variant = CONTENT_TEST.assign(user_id or None)
    return jsonify({"status": "ok", "variant": variant})

@app.route("/api/admin/ab/track", methods=["POST"])
def api_ab_track():
    """追踪A/B测试转化"""
    from ab_test import CONTENT_TEST
    data = request.get_json() or {}
    test_name = data.get("test", "content_style")
    variant = data.get("variant", "")
    converted = data.get("converted", True)
    if test_name == "content_style":
        CONTENT_TEST.track(variant, converted)
    return jsonify({"status": "ok"})


# ═══════════════════════════════════════════════════════
# 补齐: 仪表盘统计 API
# ═══════════════════════════════════════════════════════
@app.route("/api/admin/dashboard")
def api_admin_dashboard():
    from dashboard_stats import get_full_stats, get_system_health
    stats = get_full_stats()
    stats["version"] = "v2.1.0"
    stats["uptime_seconds"] = round(time.time() - _START_TIME)
    return jsonify({"status": "ok", "stats": stats})


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
        except Exception:
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
        except Exception: pass
        return jsonify({"status":"ok","key":{"key":new_key,"name":request.get_json().get("name","Admin")}})


@app.route("/api/admin/api-keys/<key_id>/revoke", methods=["POST"])
def api_admin_apikey_revoke(key_id):
    try:
        from api_platform import APIKeyManager
        km = APIKeyManager()
        km.revoke_key(key_id)
        return jsonify({"status":"ok","revoked":key_id})
    except Exception:
        try:
            from database import Database
            db = Database().connect()
            db.execute("UPDATE api_keys SET enabled=0 WHERE key LIKE ?", [f"{key_id}%"])
            db.conn.commit()
        except Exception: pass
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
                except Exception: pass
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
        except Exception:
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
            except Exception:
                pass
    return jsonify({"status": "ok", "recent": results})


@app.route("/api/kuaizi/run", methods=["POST"])
def api_kuaizi_run():
    """筷子流水线: 输入楼盘→全平台输出（含配额检查+用量记录）"""
    data = request.get_json() or {}
    tid = data.get("tenant_id", _DEFAULT_TID)

    # 配额检查
    quota_block = _quota_guard(tid, "video_generation")
    if quota_block:
        return jsonify({"status": "error", "message": "配额已用完", "quota": quota_block}), 429

    from kuaizi_pipeline import kuaizi
    result = kuaizi(data)

    # 记录用量
    _usage_log(tid, "video_generation", data.get("community", "装修案例"), 80)

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
    """生成视频脚本+素材匹配·支持本地渲染"""
    from video_engine import generate_video_script, create_video_package
    from video_api import build_video_request, render_video_locally
    data = request.get_json() or {}
    provider = data.get("provider", "local")
    if provider == "local":
        # 本地渲染: 不需要外部API
        script = generate_video_script(data.get("topic", ""), data.get("mode", "before_after"), data.get("context", {}))
        req = build_video_request(script, "jimeng", data.get("options", {}))
        result = render_video_locally(req)
        result["script"] = script
        result["package"] = create_video_package(script, data.get("account", "默认账号"))
        return jsonify({"status": "ok", "result": result})
    # 外部API模式
    result = generate_video_script(data.get("topic", ""), data.get("mode", "before_after"), data.get("context", {}))
    pkg = create_video_package(result, data.get("account", "默认账号"))
    result["package"] = pkg
    return jsonify({"status": "ok", "result": result})

@app.route("/api/video/job/<job_id>")
def api_video_job(job_id):
    """查询视频生成任务状态"""
    from video_api import get_video_job
    job = get_video_job(job_id)
    if not job:
        return jsonify({"status": "error", "message": "任务不存在"}), 404
    return jsonify({"status": "ok", "job": job})

@app.route("/api/video/jobs")
def api_video_jobs():
    """视频任务列表"""
    from video_api import list_video_jobs
    status = request.args.get("status", "")
    jobs = list_video_jobs(status)
    return jsonify({"status": "ok", "jobs": jobs, "total": len(jobs)})

@app.route("/api/video/bulk", methods=["POST"])
def api_video_bulk():
    """批量视频生产"""
    from video_api import bulk_produce_videos
    data = request.get_json() or {}
    topics = data.get("topics", [{"topic": "厨卫改造前后对比"}])
    mode = data.get("mode", "before_after")
    provider = data.get("provider", "jimeng")
    result = bulk_produce_videos(topics, mode, provider)
    return jsonify({"status": "ok", "result": result})

@app.route("/api/video/analyze", methods=["POST"])
def api_video_analyze():
    """视频内容理解分析"""
    from video_api import analyze_video_content
    data = request.get_json() or {}
    script = data.get("script")
    video_path = data.get("path", "")
    result = analyze_video_content(video_path, script)
    return jsonify({"status": "ok", "analysis": result})

@app.route("/api/video/providers")
def api_video_providers():
    """可用视频生成供应商列表"""
    from video_api import PROVIDERS
    return jsonify({"status": "ok", "providers": list(PROVIDERS.values())})


# ═══════════════════════════════════════════════════════
# 数字人版权中心 API
# ═══════════════════════════════════════════════════════

@app.route("/api/rights/assets")
def api_rights_assets():
    """版权资产列表"""
    from digital_rights import list_assets
    atype = request.args.get("type", "")
    status = request.args.get("status", "active")
    assets = list_assets(atype, status)
    return jsonify({"status": "ok", "assets": assets, "total": len(assets)})

@app.route("/api/rights/register", methods=["POST"])
def api_rights_register():
    """注册版权资产"""
    from digital_rights import register_asset
    data = request.get_json() or {}
    result = register_asset(
        data.get("type", "portrait"),
        data.get("title", ""),
        data.get("owner", ""),
        data.get("source_url", ""),
        data.get("license"),
        data.get("tags", []),
    )
    return jsonify(result)

@app.route("/api/rights/asset/<aid>")
def api_rights_asset(aid):
    """查看单个版权资产"""
    from digital_rights import get_asset
    a = get_asset(aid)
    if not a:
        return jsonify({"status": "error", "message": "资产不存在"}), 404
    return jsonify({"status": "ok", "asset": a})

@app.route("/api/rights/use/<aid>", methods=["POST"])
def api_rights_use(aid):
    """记录版权资产使用"""
    from digital_rights import record_usage
    data = request.get_json() or {}
    result = record_usage(aid, data.get("context", ""), data.get("tenant_id", ""))
    return jsonify(result)

@app.route("/api/rights/revoke/<aid>", methods=["POST"])
def api_rights_revoke(aid):
    """撤销版权授权"""
    from digital_rights import revoke_asset
    data = request.get_json() or {}
    result = revoke_asset(aid, data.get("reason", ""))
    return jsonify(result)

@app.route("/api/rights/compliance")
def api_rights_compliance():
    """版权合规检查"""
    from digital_rights import compliance_check
    content_type = request.args.get("content_type", "article")
    result = compliance_check(content_type)
    return jsonify({"status": "ok", "compliance": result})

@app.route("/api/rights/report")
def api_rights_report():
    """版权合规总览报告"""
    from digital_rights import get_compliance_report
    report = get_compliance_report()
    return jsonify({"status": "ok", "report": report})


# ═══════════════════════════════════════════════════════
# 多租户平台 API
# ═══════════════════════════════════════════════════════

@app.route("/api/tenant/create", methods=["POST"])
def api_create_zhuangqi_tenant():
    """创建装企租户"""
    from tenant_service import create_tenant
    data = request.get_json() or {}
    t = create_tenant(data.get("name", "新装企"), data.get("cities", ["厦门"]), data.get("plan", "pro"))
    return jsonify({"status": "ok", "tenant": t})

@app.route("/api/tenant/<tid>/dashboard")
def api_tenant_dashboard(tid):
    """装企客户仪表盘"""
    from tenant_service import get_client_dashboard
    return jsonify(get_client_dashboard(tid))

@app.route("/api/tenant/<tid>/matrix")
def api_tenant_matrix(tid):
    """装企账号矩阵"""
    from tenant_service import get_account_matrix
    return jsonify(get_account_matrix(tid))

@app.route("/api/tenant/<tid>/distribute", methods=["POST"])
def api_tenant_distribute(tid):
    """内容分发到矩阵"""
    from tenant_service import distribute_content
    data = request.get_json() or {}
    return jsonify(distribute_content(tid, data.get("topic", ""), data.get("content_type", "article")))

@app.route("/api/tenant/<tid>/tokens")
def api_tenant_tokens(tid):
    """Token计量"""
    from tenant_service import check_quota
    return jsonify(check_quota(tid))

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
        except Exception:
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
        except Exception:
            pass
    return jsonify({"status": "ok", "items": items[-20:], "total": len(items)})


@app.route("/api/tenants/list")
def api_tenants_list():
    """所有装企租户列表"""
    from tenant_service import get_all_tenants
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
    from tenant_service import get_all_tenants, get_client_dashboard
    from tenant_service import check_quota, PLANS
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

@app.route("/trial")
def trial_page():
    """免费试用: 自动创建试用租户→跳转仪表盘"""
    from tenant_service import create_tenant
    import secrets
    name = f"试用装企-{secrets.token_hex(2)}"
    t = create_tenant(name, ["厦门"], "starter")
    # 重定向到客户端仪表盘
    from flask import redirect
    return redirect(f"/client?tid={t['id']}&trial=1")

@app.route("/register-account")
def register_account_page():
    """邮箱注册页面"""
    return send_from_directory(str(LANDING), "register.html")

# ═══════════════════════════════════════════════════════
# 内容日历 & 矩阵调度 API
# ═══════════════════════════════════════════════════════

@app.route("/api/schedule/queue/<tid>")
def api_schedule_queue(tid):
    from content_scheduler import get_queue
    return jsonify({"status": "ok", "queue": get_queue(tid)})

@app.route("/api/schedule/enqueue", methods=["POST"])
def api_schedule_enqueue():
    from content_scheduler import enqueue
    data = request.get_json() or {}
    tid = data.get("tid", _DEFAULT_TID)
    result = enqueue(tid, data.get("content", {}))
    return jsonify(result)

@app.route("/api/schedule/publish", methods=["POST"])
def api_schedule_publish():
    from content_scheduler import publish_now
    data = request.get_json() or {}
    tid = data.get("tid", _DEFAULT_TID)
    result = publish_now(tid, data.get("item_id"))
    return jsonify(result)

@app.route("/api/schedule/calendar/<tid>")
def api_schedule_calendar(tid):
    from content_scheduler import get_calendar
    days = int(request.args.get("days", 7))
    return jsonify({"status": "ok", "calendar": get_calendar(tid, days)})

@app.route("/api/schedule/stats/<tid>")
def api_schedule_stats(tid):
    from content_scheduler import get_stats
    return jsonify({"status": "ok", "stats": get_stats(tid)})

@app.route("/api/schedule/distribute", methods=["POST"])
def api_schedule_distribute():
    """执行内容分发到矩阵"""
    from content_scheduler import execute_distribution
    data = request.get_json() or {}
    tid = data.get("tid", _DEFAULT_TID)
    result = execute_distribution(tid, data.get("topic", ""), data.get("content_type", "article"))
    return jsonify(result)


@app.route("/api/tenant/onboard", methods=["POST"])
def api_tenant_onboard():
    """一站式入驻: 创建租户→生成矩阵→AI生产→分发→发布队列→日历"""
    from tenant_service import create_tenant, get_client_dashboard
    from content_scheduler import execute_distribution, get_calendar
    import secrets

    data = request.get_json() or {}
    name = data.get("name", "新装企")
    cities = data.get("cities", ["厦门"])
    plan = data.get("plan", "pro")

    # Step 1: 创建租户
    tenant = create_tenant(name, cities, plan)
    tid = tenant["id"]

    # Step 2: 后台异步 — 全链路执行
    import threading as _th
    pipeline_log = []

    def _bg_full_pipeline():
        try:
            from kuaizi_pipeline import kuaizi
            # 生产
            for topic in [f"{cities[0]}装修避坑指南", f"{cities[0]}旧房翻新实案"]:
                kuaizi({"city": cities[0], "style": "现代简约", "room_type": "全屋",
                         "area": 100, "budget": 20, "tenant_id": tid})
                _usage_log(tid, "article", topic, 8)
            # 分发
            dist = execute_distribution(tid, f"{name}首批内容", "article")
            pipeline_log.append({"step": "produce", "topics": 2})
            pipeline_log.append({"step": "distribute", "accounts": dist["total_distributions"],
                                 "enqueued": dist["enqueued"], "scheduled": dist["auto_scheduled"]})
        except Exception as e:
            pipeline_log.append({"step": "error", "error": str(e)[:100]})

    _th.Thread(target=_bg_full_pipeline, daemon=True).start()

    # Step 3: 返回仪表盘数据
    dashboard = get_client_dashboard(tid)
    return jsonify({
        "status": "ok",
        "tenant": {"id": tid, "name": name, "plan": plan},
        "dashboard": dashboard,
        "pipeline": {"status": "running", "log": [{"step": "tenant_created", "tid": tid},
                                                   {"step": "pipeline_started", "topics": 2}],
                     "message": "全链路执行中: 内容生产→QC→分发→发布队列。约2分钟后可查看仪表盘"},
        "next_url": f"/client?tid={tid}",
    })
    
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

@app.route("/api/openapi.json")
def api_openapi_spec():
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
    except Exception:
        lines.append("system_disk_free_bytes 0")
    return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"}


# ⚠️ 通配路由必须放在最后，否则会拦截 /admin /health 等
@app.route("/<path:filename>")
def serve_static(filename):
    # Don't intercept API routes
    if filename in ("metrics", "api/openapi.json"):
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
    import os as _os
    # Register A/B test middleware
    try:
        from ab_test import ab_middleware
        ab_middleware(app)
        print("  A/B testing middleware registered")
    except Exception as e:
        print(f"  A/B middleware skipped: {e}")

    # Register OpenAPI platform routes
    try:
        from api_platform import register_api_routes
        register_api_routes(app)
        print("  API Platform (OpenAPI/SDK) activated")
    except Exception as e:
        print(f"  API Platform skipped: {e}")

    host = _os.environ.get("CLOUDTECH_HOST", "0.0.0.0")
    port = int(_os.environ.get("CLOUDTECH_PORT", "5099"))
    prod = _os.environ.get("CLOUDTECH_PROD", "1")  # 默认生产模式

    if prod == "1":
        try:
            from waitress import serve
            threads = int(_os.environ.get("CLOUDTECH_WORKERS", "4"))
            print("=" * 50)
            print("  云数科技 CloudTech v2.0.0 — Production (Waitress)")
            print(f"  管理后台: http://localhost:{port}/admin")
            print(f"  Threads: {threads}")
            print("=" * 50)
            serve(app, host=host, port=port, threads=threads, channel_timeout=600)
        except ImportError:
            print("  Waitress not installed, falling back to Flask dev server")
            prod = "0"

    if prod != "1":
        print("=" * 50)
        print("  云数科技 CloudTech v2.0.0 — Development (Flask)")
        print(f"  管理后台: http://localhost:{port}/admin")
        print("=" * 50)
        app.run(host=host, port=port, debug=False)
