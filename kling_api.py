"""
可灵 (Kling) AI API 客户端 — 视频生成
============================================
支持两种鉴权模式:
  模式A (官方): AK/SK → JWT Bearer → api.klingai.com
  模式B (网关): 静态 API Key → Bearer → 网关域名

文档: https://kling.ai/document-api/
端点: https://api-beijing.klingai.com (国内) / https://api-singapore.klingai.com (海外)

用法:
  from kling_api import text_to_video, check_status
  result = text_to_video(prompt="...", duration=5)
"""
import os, sys, json, time, hashlib, hmac
from pathlib import Path
from datetime import datetime
from typing import Optional
from urllib import request, error, parse


# ═══════════════════════════════════
# 配置加载
# ═══════════════════════════════════

def _load_env():
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() not in os.environ:
                os.environ[k.strip()] = v.strip()

_load_env()

KLING_AK = os.getenv("KLING_ACCESS_KEY", "")
KLING_SK = os.getenv("KLING_SECRET_KEY", "")
KLING_API_KEY = os.getenv("KLING_API_KEY", "")
KLING_GATEWAY = os.getenv("KLING_GATEWAY_URL", "")

# 官方端点
KLING_BASE = os.getenv("KLING_BASE_URL", "https://api-beijing.klingai.com")

# 识别 key 类型
IS_OFFICIAL_API_KEY = KLING_API_KEY.startswith("api-key-kling-")  # 官方静态 API Key (新格式)
IS_GATEWAY_KEY = bool(KLING_API_KEY) and KLING_GATEWAY and not IS_OFFICIAL_API_KEY  # 第三方网关
IS_OFFICIAL_JWT = bool(KLING_AK and KLING_SK)  # 官方 AK/SK JWT (旧格式)


# ═══════════════════════════════════
# JWT Token 生成 (官方模式)
# ═══════════════════════════════════

def _generate_jwt(ak: str, sk: str) -> str:
    """用 AK/SK 生成 Kling JWT Token (HS256, 30分钟有效)"""
    import base64

    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"iss": ak, "exp": now + 1800, "nbf": now - 5}

    # 手动编码 JWT (不依赖 PyJWT 库)
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}"

    signature = hmac.new(sk.encode(), signing_input.encode(), hashlib.sha256).digest()
    sig_b64 = _b64url(signature)

    return f"{signing_input}.{sig_b64}"


# ═══════════════════════════════════
# HTTP 调用
# ═══════════════════════════════════

def _api_call(method: str, path: str, body: dict = None, timeout: int = 120,
              gateway_mode: bool = False) -> dict:
    """调用 Kling API"""

    # 鉴权: 官方静态key(新) → 官方JWT(旧) → 网关静态key
    if IS_OFFICIAL_API_KEY:
        # 官方静态 API Key (api-key-kling-...) → Bearer on KLING_BASE
        auth_token = KLING_API_KEY
        base_url = KLING_BASE
    elif IS_OFFICIAL_JWT:
        # 官方 AK/SK → JWT → Bearer on KLING_BASE
        auth_token = _generate_jwt(KLING_AK, KLING_SK)
        base_url = KLING_BASE
    elif IS_GATEWAY_KEY or (KLING_API_KEY and gateway_mode):
        # 第三方网关: 静态 Key → Bearer on gateway URL
        auth_token = KLING_API_KEY
        base_url = KLING_GATEWAY
    else:
        return {"ok": False, "error": "无可用的 Kling 鉴权凭据 (需 KLING_API_KEY 或 KLING_ACCESS_KEY+KLING_SECRET_KEY)"}

    url = f"{base_url}{path}"

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    body_bytes = json.dumps(body).encode() if body else None

    try:
        req = request.Request(url, data=body_bytes, headers=headers, method=method)
        resp = request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode())
        return {"ok": True, "http_code": resp.status, "data": data}
    except error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = {"raw": err_body[:500]}
        return {"ok": False, "http_code": e.code, "error": err_json}
    except Exception as e:
        return {"ok": False, "http_code": 0, "error": str(e)[:300]}


# ═══════════════════════════════════
# 文生视频 API
# ═══════════════════════════════════

def text_to_video(
    prompt: str,
    negative_prompt: str = "",
    duration: str = "5",
    mode: str = "std",
    aspect_ratio: str = "9:16",
    cfg_scale: float = 0.5,
) -> dict:
    """
    文生视频

    Args:
        prompt:         视频描述 (中英文均可)
        negative_prompt: 负面提示词
        duration:       时长 "5" | "10"
        mode:           模式 "std"(标准) | "pro"(高画质)
        aspect_ratio:   比例 "16:9"|"9:16"|"1:1"
        cfg_scale:      创意度 0-1

    Returns:
        {"ok": True, "task_id": "...", "status": "submitted"}
    """
    model = "kling-v1-6" if mode == "pro" else "kling-v1"

    body = {
        "model_name": model,
        "prompt": prompt,
        "duration": duration,
        "mode": mode,
        "aspect_ratio": aspect_ratio,
        "cfg_scale": cfg_scale,
    }
    if negative_prompt:
        body["negative_prompt"] = negative_prompt

    # POST /v1/videos/text2video
    result = _api_call("POST", "/v1/videos/text2video", body)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error", "未知错误")}

    data = result["data"]
    err_code = data.get("code", 0)
    if err_code != 0:
        return {"ok": False, "error": f"Kling API error {err_code}: {data.get('message', '?')}"}

    task_id = data.get("data", {}).get("task_id", "")
    return {
        "ok": True,
        "task_id": task_id,
        "status": "submitted",
        "provider": "kling",
        "mode": mode,
    }


def image_to_video(
    image_url: str = "",
    image_base64: str = "",
    prompt: str = "",
    duration: str = "5",
    mode: str = "std",
) -> dict:
    """图生视频"""
    body = {
        "model_name": "kling-v1-6" if mode == "pro" else "kling-v1",
        "duration": duration,
        "mode": mode,
    }
    if image_url:
        body["image"] = image_url
    elif image_base64:
        body["image"] = image_base64
    else:
        return {"ok": False, "error": "需要 image_url 或 image_base64"}
    if prompt:
        body["prompt"] = prompt

    result = _api_call("POST", "/v1/videos/image2video", body)
    if not result["ok"]:
        return {"ok": False, "error": result.get("error", "未知错误")}

    data = result["data"]
    if data.get("code", 0) != 0:
        return {"ok": False, "error": f"Kling API error: {data.get('message', '?')}"}

    return {"ok": True, "task_id": data["data"]["task_id"], "status": "submitted", "provider": "kling"}


def query_task(task_id: str) -> dict:
    """查询任务结果"""
    result = _api_call("GET", f"/v1/videos/text2video/{task_id}")
    if not result["ok"]:
        return {"ok": False, "error": result.get("error", "查询失败")}

    data = result["data"]
    if data.get("code", 0) != 0:
        return {"ok": False, "error": f"查询错误: {data.get('message', '?')}"}

    task_data = data.get("data", {})
    status = task_data.get("task_status", "")
    if status == "succeed":
        videos = task_data.get("task_result", {}).get("videos", [])
        return {"ok": True, "task_id": task_id, "status": "done", "videos": videos}
    elif status == "failed":
        return {"ok": False, "task_id": task_id, "status": "failed", "error": task_data.get("task_status_msg", "")}

    return {"ok": True, "task_id": task_id, "status": status}


# ═══════════════════════════════════
# 健康检查
# ═══════════════════════════════════

def check_status() -> dict:
    """检查 Kling API 配置与连通性"""
    issues = []
    auth_mode = "none"

    if not KLING_API_KEY and not (KLING_AK and KLING_SK):
        issues.append("无可用的 Kling 鉴权凭据")
        return {"configured": False, "issues": issues, "provider": "kling", "auth_mode": "none"}

    # 测试连通性
    if IS_OFFICIAL_API_KEY:
        auth_mode = "official_api_key"
        try:
            result = _api_call("GET", "/v1/videos/text2video?page_num=1&page_size=1")
            if result["ok"]:
                issues.append("官方API Key鉴权通过 ✓ (api-key-kling-... → api-beijing.klingai.com)")
            else:
                err = result.get("error", {})
                if isinstance(err, dict):
                    issues.append(f"API错误 {err.get('code')}: {str(err.get('message',''))[:80]}")
                else:
                    issues.append(f"连通失败: {str(err)[:80]}")
        except Exception as e:
            issues.append(f"测试失败: {str(e)[:80]}")

    elif IS_OFFICIAL_JWT:
        auth_mode = "official_jwt"
        try:
            result = _api_call("GET", "/v1/videos/text2video?page_num=1&page_size=1")
            if result["ok"]:
                issues.append("官方JWT鉴权通过 ✓")
            else:
                err = result.get("error", {})
                if isinstance(err, dict):
                    code = err.get("code", 0)
                    msg = err.get("message", "")
                    if code == 1000:
                        issues.append("官方JWT鉴权失败: Auth failed (AK/SK可能无效)")
                    elif code == 1002:
                        issues.append("官方JWT格式错误: JWT生成可能有bug")
                    else:
                        issues.append(f"官方API错误 {code}: {msg[:80]}")
                else:
                    issues.append(f"连通失败: {str(err)[:80]}")
        except Exception as e:
            issues.append(f"JWT生成失败: {str(e)[:80]}")

    elif IS_GATEWAY_KEY:
        auth_mode = "gateway"
        key_prefix = KLING_API_KEY[:8]
        try:
            result = _api_call("GET", "/v1/videos/text2video?page_num=1&page_size=1")
            if result["ok"]:
                issues.append(f"网关鉴权通过 ✓ ({KLING_GATEWAY})")
            else:
                issues.append(f"网关鉴权失败 ({key_prefix}... @ {KLING_GATEWAY})")
        except Exception as e:
            issues.append(f"网关测试失败: {str(e)[:80]}")

    else:
        # API key exists but format unknown and no gateway URL
        auth_mode = "unknown"
        key_prefix = KLING_API_KEY[:8]
        issues.append(f"API Key已配置({key_prefix}...)但格式未知且缺少网关URL — 需 KLING_GATEWAY_URL 或官方 api-key-kling- 格式")

    return {
        "configured": any("通过" in i for i in issues),
        "issues": issues,
        "provider": "kling",
        "auth_mode": auth_mode,
        "base_url": KLING_BASE,
    }


if __name__ == "__main__":
    status = check_status()
    print(f"Kling API 状态: {json.dumps(status, ensure_ascii=False, indent=2)}")

    if status["configured"] and len(sys.argv) > 1:
        prompt = sys.argv[1]
        print(f"\n测试文生视频: {prompt[:80]}...")
        result = text_to_video(prompt=prompt, duration="5")
        print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
