"""
云数科技 v8.0 — API 开放平台
==============================
API Key 管理 + Rate Limit + 开放端点 + OpenAPI 3.0 文档 + 使用统计
"""
import json, os, sys, time, uuid, hashlib, secrets, threading
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import Optional

HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
TOOLS = Path(__file__).parent
API_DATA_DIR = HOME / ".openclaw" / "api_platform"


# ── API Key 管理 ──
class APIKeyManager:
    """API Key 生成/吊销/权限控制"""

    def __init__(self):
        self._keys_file = API_DATA_DIR / "api_keys.json"
        self._keys = {}
        self._load()

    def _load(self):
        """加载已存储的API Keys"""
        if self._keys_file.exists():
            try:
                data = json.loads(self._keys_file.read_text("utf-8"))
                self._keys = data.get("keys", {})
            except Exception:
                self._keys = {}

    def _save(self):
        """持久化API Keys"""
        API_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._keys_file.write_text(
            json.dumps({"keys": self._keys, "updated": datetime.now().isoformat()},
                       ensure_ascii=False),
            "utf-8",
        )

    def generate_key(self, name: str, permissions: list = None,
                     rate_limit_qps: int = 10, expires_in_days: int = 365) -> dict:
        """
        生成新的API Key

        Args:
            name: Key 名称/标识
            permissions: 权限列表 (默认所有)
            rate_limit_qps: QPS限制
            expires_in_days: 过期天数

        Returns:
            {"key": "...", "name": "...", ...}
        """
        key_id = f"ys_{secrets.token_hex(16)}"
        key_secret = secrets.token_hex(32)
        api_key = f"{key_id}.{key_secret}"

        now = datetime.now()
        entry = {
            "id": key_id,
            "name": name,
            "key": api_key,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=expires_in_days)).isoformat(),
            "permissions": permissions or ["content:write", "content:read", "compliance:check"],
            "rate_limit_qps": rate_limit_qps,
            "status": "active",
            "total_calls": 0,
            "last_used": None,
        }

        self._keys[key_id] = entry
        self._save()
        return {k: v for k, v in entry.items() if k != "key"}

    def revoke_key(self, key_id: str) -> bool:
        """吊销API Key"""
        if key_id in self._keys:
            self._keys[key_id]["status"] = "revoked"
            self._save()
            return True
        return False

    def validate_key(self, api_key: str) -> Optional[dict]:
        """验证API Key并返回权限信息"""
        try:
            key_id = api_key.split(".")[0]
            entry = self._keys.get(key_id)
            if not entry:
                return None
            if entry["status"] != "active":
                return None
            if entry["key"] != api_key:
                return None
            # 检查过期
            expires = datetime.fromisoformat(entry["expires_at"])
            if datetime.now() > expires:
                return None
            return entry
        except Exception:
            return None

    def record_call(self, api_key: str):
        """记录API调用"""
        try:
            key_id = api_key.split(".")[0]
            if key_id in self._keys:
                self._keys[key_id]["total_calls"] = self._keys[key_id].get("total_calls", 0) + 1
                self._keys[key_id]["last_used"] = datetime.now().isoformat()
                self._save()
        except Exception:
            pass

    def list_keys(self) -> list[dict]:
        """列出所有Keys（隐藏secret）"""
        result = []
        for kid, entry in self._keys.items():
            result.append({
                "id": kid,
                "name": entry["name"],
                "created_at": entry["created_at"],
                "expires_at": entry["expires_at"],
                "status": entry["status"],
                "permissions": entry["permissions"],
                "rate_limit_qps": entry["rate_limit_qps"],
                "total_calls": entry.get("total_calls", 0),
                "last_used": entry.get("last_used"),
            })
        return result

    def get_stats(self) -> dict:
        """获取API Key使用统计"""
        total = len(self._keys)
        active = sum(1 for e in self._keys.values() if e["status"] == "active")
        revoked = sum(1 for e in self._keys.values() if e["status"] == "revoked")
        total_calls = sum(e.get("total_calls", 0) for e in self._keys.values())
        return {
            "total_keys": total,
            "active_keys": active,
            "revoked_keys": revoked,
            "total_calls": total_calls,
        }


# ── Rate Limit (滑动窗口) ──
class RateLimiter:
    """基于滑动窗口的速率限制"""

    def __init__(self):
        self._windows: dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key_id: str, qps_limit: int) -> dict:
        """
        检查是否超过速率限制

        Returns:
            {"allowed": bool, "remaining": int, "reset_after": float}
        """
        now = time.time()
        window_start = now - 1.0  # 1秒滑动窗口

        with self._lock:
            # 清理过期记录
            self._windows[key_id] = [
                t for t in self._windows[key_id] if t > window_start
            ]
            current_count = len(self._windows[key_id])

            if current_count >= qps_limit:
                reset_after = self._windows[key_id][0] + 1.0 - now if self._windows[key_id] else 0
                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_after": round(max(reset_after, 0), 3),
                }

            # 允许请求
            self._windows[key_id].append(now)
            return {
                "allowed": True,
                "remaining": qps_limit - current_count - 1,
                "reset_after": 0,
            }


# ── 使用统计 ──
class UsageTracker:
    """API 调用统计追踪"""

    def __init__(self):
        self._file = API_DATA_DIR / "usage_log.jsonl"
        API_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def record(self, entry: dict):
        """记录一条调用"""
        entry["_ts"] = datetime.now().isoformat()
        try:
            with open(str(self._file), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def get_stats(self, days: int = 7) -> dict:
        """获取使用统计"""
        cutoff = datetime.now() - timedelta(days=days)
        records = []

        if self._file.exists():
            try:
                with open(str(self._file), "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            r = json.loads(line.strip())
                            ts = datetime.fromisoformat(r["_ts"])
                            if ts > cutoff:
                                records.append(r)
                        except Exception:
                            continue
            except Exception:
                pass

        stats = {
            "period_days": days,
            "total_requests": len(records),
            "success_rate": 0,
            "avg_latency_ms": 0,
            "by_endpoint": {},
            "by_key": {},
        }

        successes = 0
        total_latency = 0

        for r in records:
            ep = r.get("endpoint", "unknown")
            k = r.get("key_name", "anonymous")
            ok = r.get("success", False)
            lat = r.get("latency_ms", 0)

            # By endpoint
            if ep not in stats["by_endpoint"]:
                stats["by_endpoint"][ep] = {"calls": 0, "success": 0, "failures": 0, "total_latency": 0}
            stats["by_endpoint"][ep]["calls"] += 1
            if ok:
                stats["by_endpoint"][ep]["success"] += 1
            else:
                stats["by_endpoint"][ep]["failures"] += 1
            stats["by_endpoint"][ep]["total_latency"] += lat

            # By key
            if k not in stats["by_key"]:
                stats["by_key"][k] = {"calls": 0, "success": 0, "failures": 0}
            stats["by_key"][k]["calls"] += 1
            if ok:
                stats["by_key"][k]["success"] += 1
            else:
                stats["by_key"][k]["failures"] += 1

            if ok:
                successes += 1
            total_latency += lat

        stats["success_rate"] = round(successes / max(1, len(records)) * 100, 1)
        stats["avg_latency_ms"] = round(total_latency / max(1, len(records)), 1)

        # 按端点计算平均延迟
        for ep in stats["by_endpoint"]:
            c = stats["by_endpoint"][ep]["calls"]
            stats["by_endpoint"][ep]["avg_latency_ms"] = round(
                stats["by_endpoint"][ep]["total_latency"] / max(1, c), 1
            )

        return stats


# ── 全局单例 ──
_key_manager = None
_rate_limiter = None
_usage_tracker = None


def get_key_manager() -> APIKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager


def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def get_usage_tracker() -> UsageTracker:
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker


# ── OpenAPI 3.0 文档生成 ──
def generate_openapi_spec(base_url: str = "http://127.0.0.1:8888") -> dict:
    """生成 OpenAPI 3.0 规范文档"""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "云数科技 API 开放平台",
            "description": "AI内容生成、二创、合规检测、竞品分析等能力的开放API接口",
            "version": "1.0.0",
            "contact": {"name": "云数科技", "url": base_url},
        },
        "servers": [{"url": base_url, "description": "本地服务器"}],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "云数科技 API Key，格式: ys_xxx.yyy",
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "code": {"type": "integer"},
                    },
                },
                "ContentGenerateRequest": {
                    "type": "object",
                    "required": ["topic", "platform"],
                    "properties": {
                        "topic": {"type": "string", "description": "内容主题"},
                        "platform": {"type": "string", "enum": ["小红书", "公众号", "抖音", "知乎", "B站"]},
                        "style": {"type": "string", "description": "写作风格"},
                        "tone": {"type": "string", "description": "情绪基调"},
                    },
                },
                "ContentGenerateResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "data": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "word_count": {"type": "integer"},
                                "model": {"type": "string"},
                            },
                        },
                    },
                },
                "RepurposeRequest": {
                    "type": "object",
                    "required": ["source", "target_platform"],
                    "properties": {
                        "source": {"type": "string", "description": "原文链接或文本"},
                        "target_platform": {"type": "string", "description": "目标平台"},
                        "style": {"type": "string", "description": "目标风格"},
                    },
                },
                "ComplianceRequest": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string", "description": "待检测文案"},
                        "platform": {"type": "string", "description": "目标平台"},
                        "industry": {"type": "string", "description": "行业"},
                    },
                },
                "CompetitorRequest": {
                    "type": "object",
                    "required": ["competitor"],
                    "properties": {
                        "competitor": {"type": "string", "description": "竞品名称"},
                        "depth": {"type": "string", "description": "分析深度"},
                    },
                },
            },
        },
        "paths": {
            "/api/v1/content/generate": {
                "post": {
                    "summary": "AI内容生成",
                    "description": "根据主题和平台生成AI文案，支持多风格",
                    "operationId": "generateContent",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ContentGenerateRequest"},
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "生成成功",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ContentGenerateResponse"},
                                }
                            },
                        },
                        "401": {"description": "未授权"},
                        "429": {"description": "请求频率超限"},
                    },
                }
            },
            "/api/v1/content/repurpose": {
                "post": {
                    "summary": "内容二创",
                    "description": "跨平台内容改写和二次创作",
                    "operationId": "repurposeContent",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RepurposeRequest"},
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "二创成功"},
                        "401": {"description": "未授权"},
                    },
                }
            },
            "/api/v1/compliance/check": {
                "post": {
                    "summary": "违禁词检测",
                    "description": "广告法+平台规则+行业词库实时检测",
                    "operationId": "complianceCheck",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ComplianceRequest"},
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "检测完成"},
                        "401": {"description": "未授权"},
                    },
                }
            },
            "/api/v1/competitor/analyze": {
                "post": {
                    "summary": "竞品分析",
                    "description": "一键分析竞品内容策略和差异化机会",
                    "operationId": "competitorAnalyze",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CompetitorRequest"},
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "分析完成"},
                        "401": {"description": "未授权"},
                    },
                }
            },
            "/api/v1/keys": {
                "get": {
                    "summary": "列出所有API Keys",
                    "operationId": "listKeys",
                    "security": [{"ApiKeyAuth": []}],
                    "responses": {
                        "200": {"description": "Keys列表"},
                    },
                },
                "post": {
                    "summary": "生成新API Key",
                    "operationId": "createKey",
                    "security": [{"ApiKeyAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "rate_limit_qps": {"type": "integer"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Key创建成功"},
                    },
                },
            },
            "/api/v1/stats": {
                "get": {
                    "summary": "使用统计",
                    "operationId": "getStats",
                    "security": [{"ApiKeyAuth": []}],
                    "parameters": [
                        {"name": "days", "in": "query", "schema": {"type": "integer", "default": 7}},
                    ],
                    "responses": {
                        "200": {"description": "统计结果"},
                    },
                }
            },
        },
    }


def register_api_routes(app):
    """向 Flask 应用注册 API 开放平台路由"""
    from flask import request, jsonify, Response

    km = get_key_manager()
    rl = get_rate_limiter()
    ut = get_usage_tracker()

    # ── API Key 中间件 ──
    def require_api_key(f):
        """API Key 验证装饰器"""
        from functools import wraps

        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = (
                request.headers.get("X-API-Key", "") or
                request.args.get("api_key", "")
            )
            if not api_key:
                return jsonify({"error": "缺少 API Key", "code": 401}), 401

            entry = km.validate_key(api_key)
            if not entry:
                return jsonify({"error": "API Key 无效或已过期", "code": 401}), 401

            # Rate Limit
            check = rl.check(entry["id"], entry["rate_limit_qps"])
            if not check["allowed"]:
                return jsonify({
                    "error": f"请求频率超限 (上限: {entry['rate_limit_qps']} QPS)",
                    "code": 429,
                    "retry_after": check["reset_after"],
                }), 429

            # 注入已验证的 key 信息
            kwargs["_api_key_entry"] = entry
            kwargs["_api_key"] = api_key
            return f(*args, **kwargs)

        return decorated

    # ── OpenAPI 文档 ──
    @app.route("/api/docs")
    def api_platform_docs():
        """Swagger UI"""
        from flask import send_file
        template_dir = TOOLS / "templates"
        swagger_file = template_dir / "swagger.html"
        if swagger_file.exists():
            return send_file(str(swagger_file))
        # 内联 Swagger UI
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>云数科技 API 文档</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
  SwaggerUIBundle({{
    url: '{request.base_url}/openapi.json',
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis],
  }});
</script>
</body></html>"""

    @app.route("/api/docs/openapi.json")
    def api_openapi_json():
        base_url = request.host_url.rstrip("/")
        return jsonify(generate_openapi_spec(base_url))

    # ── API Key 管理端点 ──
    @app.route("/api/v1/keys", methods=["GET"])
    @require_api_key
    def api_list_keys(*args, **kwargs):
        return jsonify({"success": True, "keys": km.list_keys()})

    @app.route("/api/v1/keys", methods=["POST"])
    @require_api_key
    def api_create_key(*args, **kwargs):
        data = request.json or {}
        name = data.get("name", f"Key-{uuid.uuid4().hex[:6]}")
        qps = data.get("rate_limit_qps", 10)
        permissions = data.get("permissions")
        key_data = km.generate_key(name, permissions, qps)
        return jsonify({"success": True, "key": key_data}), 201

    @app.route("/api/v1/keys/<key_id>", methods=["DELETE"])
    @require_api_key
    def api_revoke_key(key_id, *args, **kwargs):
        if km.revoke_key(key_id):
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Key not found"}), 404

    # ── 开放端点 ──
    @app.route("/api/v1/content/generate", methods=["POST"])
    @require_api_key
    def api_content_generate(*args, **kwargs):
        entry = kwargs["_api_key"]
        data = request.json or {}
        topic = data.get("topic", "")
        platform = data.get("platform", "小红书")
        style = data.get("style", "直男财经·数据幽默流")
        tone = data.get("tone", "轻松幽默")

        if not topic:
            return jsonify({"success": False, "error": "请提供 topic 字段"}), 400

        start = time.time()
        try:
            # 通过 model_router 分发
            try:
                from model_router import get_router
            except ImportError:
                from admin_dashboard import _deepseek_call
                get_router = lambda: type('r',(),{'route': lambda m,p: _deepseek_call(p, '')})()
            router = get_router()
            messages = [
                {"role": "system", "content": f"你是{style}风格的内容创作者。目标平台：{platform}。语气：{tone}"},
                {"role": "user", "content": f"请写一篇关于「{topic}」的{platform}内容。"},
            ]
            model_result = router.chat(messages, task_type="writing")
            elapsed_ms = int((time.time() - start) * 1000)

            ut.record({
                "endpoint": "/api/v1/content/generate",
                "key_name": entry.get("name", "unknown"),
                "success": model_result["success"],
                "latency_ms": elapsed_ms,
                "model": model_result.get("model_id", ""),
            })

            if model_result["success"]:
                return jsonify({
                    "success": True,
                    "data": {
                        "content": model_result["content"],
                        "word_count": len(model_result["content"]),
                        "model": model_result.get("model_name", ""),
                        "cost": model_result.get("cost", 0),
                    },
                })
            else:
                return jsonify({
                    "success": False,
                    "error": model_result.get("error", "生成失败"),
                }), 500

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/v1/content/repurpose", methods=["POST"])
    @require_api_key
    def api_content_repurpose(*args, **kwargs):
        entry = kwargs["_api_key"]
        data = request.json or {}
        source = data.get("source", "")
        target_platform = data.get("target_platform", "小红书")
        style = data.get("style", "去AI腔·自然口语")

        if not source:
            return jsonify({"success": False, "error": "请提供 source 字段"}), 400

        start = time.time()
        try:
            try:
                from model_router import get_router
            except ImportError:
                from admin_dashboard import _deepseek_call
                get_router = lambda: type('r',(),{'route': lambda m,p: _deepseek_call(p, '')})()
            router = get_router()
            messages = [
                {"role": "system", "content": f"你是内容二创专家。目标平台：{target_platform}。风格：{style}。请改写以下内容，保留核心信息但改变表达。"},
                {"role": "user", "content": source},
            ]
            model_result = router.chat(messages, task_type="writing")
            elapsed_ms = int((time.time() - start) * 1000)

            ut.record({
                "endpoint": "/api/v1/content/repurpose",
                "key_name": entry.get("name", "unknown"),
                "success": model_result["success"],
                "latency_ms": elapsed_ms,
            })

            if model_result["success"]:
                return jsonify({
                    "success": True,
                    "data": {
                        "content": model_result["content"],
                        "word_count": len(model_result["content"]),
                        "original_platform": "auto",
                        "target_platform": target_platform,
                    },
                })
            else:
                return jsonify({"success": False, "error": model_result.get("error")}), 500

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/v1/compliance/check", methods=["POST"])
    @require_api_key
    def api_compliance_check(*args, **kwargs):
        entry = kwargs["_api_key"]
        data = request.json or {}
        text = data.get("text", "")
        platform = data.get("platform", "通用")
        industry = data.get("industry", "通用")

        if not text:
            return jsonify({"success": False, "error": "请提供 text 字段"}), 400

        start = time.time()
        try:
            import subprocess as sp, shlex
            cmd = f'python "{TOOLS}\\compliance-checker.py" "{(text[:2000])}" "{platform}" "{industry}"'
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
            result = sp.run(shlex.split(cmd), shell=False, capture_output=True, text=True,
                           timeout=60, encoding="utf-8", errors="replace", env=env)
            elapsed_ms = int((time.time() - start) * 1000)

            ut.record({
                "endpoint": "/api/v1/compliance/check",
                "key_name": entry.get("name", "unknown"),
                "success": result.returncode == 0,
                "latency_ms": elapsed_ms,
            })

            try:
                output = json.loads(result.stdout) if result.stdout else {"raw": result.stdout[:2000]}
            except json.JSONDecodeError:
                output = {"raw": result.stdout[:2000]}

            return jsonify({
                "success": result.returncode == 0,
                "data": output,
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/v1/competitor/analyze", methods=["POST"])
    @require_api_key
    def api_competitor_analyze(*args, **kwargs):
        entry = kwargs["_api_key"]
        data = request.json or {}
        competitor = data.get("competitor", "")
        depth = data.get("depth", "快速(1分钟)")

        if not competitor:
            return jsonify({"success": False, "error": "请提供 competitor 字段"}), 400

        start = time.time()
        try:
            import subprocess as sp, shlex
            cmd = f'python "{TOOLS}\\competitor-analyzer.py" "{competitor}" "{depth}"'
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
            result = sp.run(shlex.split(cmd), shell=False, capture_output=True, text=True,
                           timeout=120, encoding="utf-8", errors="replace", env=env)
            elapsed_ms = int((time.time() - start) * 1000)

            ut.record({
                "endpoint": "/api/v1/competitor/analyze",
                "key_name": entry.get("name", "unknown"),
                "success": result.returncode == 0,
                "latency_ms": elapsed_ms,
            })

            return jsonify({
                "success": result.returncode == 0,
                "data": {
                    "report": result.stdout[:10000] if result.returncode == 0 else "",
                    "error": result.stderr[:500] if result.returncode != 0 else "",
                },
            })

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # ── 使用统计 ──
    @app.route("/api/v1/stats")
    def api_stats():
        days = request.args.get("days", 7, type=int)
        return jsonify({
            "success": True,
            "usage": ut.get_stats(days),
            "keys": km.get_stats(),
        })

    # ── 模型状态 ──
    @app.route("/api/v1/models")
    def api_models():
        from model_router import get_router
        router = get_router()
        return jsonify({"success": True, "models": router.get_status()})

    @app.route("/api/v1/models/test", methods=["POST"])
    def api_model_test():
        from model_router import get_router
        router = get_router()
        data = request.json or {}
        model_id = data.get("model_id", "deepseek-v3")
        result = router.test_model(model_id)
        return jsonify(result)

    # ── API Key 验证测试端点 ──
    @app.route("/api/v1/verify")
    def api_verify():
        api_key = request.headers.get("X-API-Key", "") or request.args.get("api_key", "")
        entry = km.validate_key(api_key)
        if entry:
            return jsonify({
                "success": True,
                "key_name": entry["name"],
                "permissions": entry["permissions"],
                "rate_limit_qps": entry["rate_limit_qps"],
            })
        return jsonify({"success": False}), 401


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "key":
        km = get_key_manager()
        if len(sys.argv) > 2 and sys.argv[2] == "list":
            keys = km.list_keys()
            print(json.dumps(keys, ensure_ascii=False, indent=2))
        elif len(sys.argv) > 2 and sys.argv[2] == "generate":
            name = sys.argv[3] if len(sys.argv) > 3 else "default"
            key_info = km.generate_key(name)
            print(f"API Key: {key_info}")
        elif len(sys.argv) > 2 and sys.argv[2] == "revoke":
            key_id = sys.argv[3]
            if km.revoke_key(key_id):
                print(f"已吊销: {key_id}")
            else:
                print(f"未找到: {key_id}")
        else:
            print("用法:")
            print("  python api_platform.py key list              - 列出Keys")
            print("  python api_platform.py key generate <name>   - 生成Key")
            print("  python api_platform.py key revoke <id>       - 吊销Key")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        ut = get_usage_tracker()
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        print(json.dumps(ut.get_stats(days), ensure_ascii=False, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "openapi":
        spec = generate_openapi_spec()
        print(json.dumps(spec, ensure_ascii=False, indent=2))
    else:
        print("用法:")
        print("  python api_platform.py key ...       - API Key 管理")
        print("  python api_platform.py stats [days]  - 使用统计")
        print("  python api_platform.py openapi        - OpenAPI 规范")
