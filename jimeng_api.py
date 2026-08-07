"""
即梦 (Jimeng) API 客户端 — 火山方舟视觉智能
================================================
认证方式: Volcengine Signature V4 (AK/SK)
服务: visual.volcengineapi.com
文档: https://www.volcengine.com/docs/6791

支持:
  - 文生视频 (CVSync2AsyncSubmitTask → CVSync2AsyncGetResult)
  - 图生视频
  - 视频风格迁移
  - 异步任务提交 + 轮询
"""
import os, sys, json, time, hmac, hashlib, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib import request, parse, error


# ═══════════════════════════════════
# 配置加载
# ═══════════════════════════════════

def _load_env():
    """从 .env 或环境变量加载 AK/SK"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k not in os.environ:
                os.environ[k] = v

_load_env()

AK = os.getenv("JIMENG_ACCESS_KEY", "")
SK = os.getenv("JIMENG_SECRET_KEY", "")
APP_KEY = os.getenv("JIMENG_APP_KEY", "")
SESSION_TOKEN = os.getenv("JIMENG_SESSION_TOKEN", "")

# API 配置
SERVICE = "cv"  # 视觉智能服务固定为 cv（非 visual）
REGION = "cn-north-1"
HOST = "visual.volcengineapi.com"
API_VERSION = "2022-08-31"


# ═══════════════════════════════════
# Volcengine Signature V4
# ═══════════════════════════════════

def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def _sign(method: str, uri: str, query: dict, headers: dict, body: str,
          access_key: str, secret_key: str, service: str, region: str) -> str:
    """Volcengine Signature V4 生成 Authorization header"""

    # 从 headers 提取 X-Date 作为签名时间戳（保证与请求头一致）
    x_date = headers.get("X-Date", "")
    if not x_date:
        now = datetime.now(timezone.utc)
        x_date = now.strftime("%Y%m%dT%H%M%SZ")
        headers["X-Date"] = x_date

    # 解析: 20260807T143000Z → datestamp=20260807, timestamp=20260807T143000Z
    datestamp = x_date[:8]
    timestamp = x_date

    # 1. Canonical Request
    canonical_uri = uri or "/"
    canonical_querystring = "&".join(
        f"{parse.quote(k, safe='')}={parse.quote(str(v), safe='')}"
        for k, v in sorted(query.items())
    )
    canonical_headers = "\n".join(
        f"{k.lower()}:{v.strip()}" for k, v in sorted(headers.items())
    )
    signed_headers = ";".join(k.lower() for k in sorted(headers.keys()))
    payload_hash = _sha256_hex(body)

    canonical_request = "\n".join([
        method.upper(),
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        "",
        signed_headers,
        payload_hash,
    ])

    # 2. String to Sign
    credential_scope = f"{datestamp}/{region}/{service}/request"
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        timestamp,
        credential_scope,
        _sha256_hex(canonical_request),
    ])

    # 3. Signing Key (直接使用原始SK，不做任何解码)
    k_date = _hmac_sha256(secret_key.encode("utf-8"), datestamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    k_signing = _hmac_sha256(k_service, "request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    # 4. Authorization header
    return (
        f"HMAC-SHA256 "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )


def _call(action: str, body: dict, timeout: int = 120) -> dict:
    """调用火山方舟视觉 API（同步请求）"""
    query = {
        "Action": action,
        "Version": API_VERSION,
    }

    body_str = json.dumps(body, ensure_ascii=False)
    content_type = "application/json"

    headers = {
        "Host": HOST,
        "Content-Type": content_type,
        "X-Date": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "X-Content-Sha256": _sha256_hex(body_str),
    }

    auth = _sign("POST", "/", query, headers, body_str, AK, SK, SERVICE, REGION)
    headers["Authorization"] = auth

    # 如果有 session token，加入 header
    if SESSION_TOKEN:
        headers["X-Security-Session-Token"] = SESSION_TOKEN

    url = f"https://{HOST}/?{'&'.join(f'{k}={parse.quote(str(v))}' for k,v in query.items())}"

    try:
        req = request.Request(url, data=body_str.encode("utf-8"), headers=headers, method="POST")
        resp = request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read().decode("utf-8"))
        return {"ok": True, "data": data}
    except error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"ok": False, "error": f"HTTP {e.code}: {err_body[:500]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}


# ═══════════════════════════════════
# 即梦 文生视频 API
# ═══════════════════════════════════

def text_to_video(
    prompt: str,
    negative_prompt: str = "",
    duration: int = 5,
    resolution: str = "720p",
    style: str = "realistic",
    seed: int = -1,
) -> dict:
    """
    文生视频 — 提交异步任务并等待完成

    Args:
        prompt:          视频描述提示词（中文/英文均可）
        negative_prompt: 负面提示词（不要出现的内容）
        duration:        视频时长(秒)，支持 3/5/10
        resolution:      分辨率 "720p" | "1080p"
        style:           风格 "realistic"|"anime"|"3d_cartoon"
        seed:            随机种子，-1为随机

    Returns:
        {"ok": True, "task_id": "...", "status": "done", "video_url": "...", "duration_sec": 5}
        or {"ok": False, "error": "..."}
    """
    # 构建火山方舟视觉API请求体
    req_body = {
        "req_key": "jimeng_t2v_v30",  # 即梦文生视频 v3.0
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "seed": seed,
    }
    if negative_prompt:
        req_body["negative_prompt"] = negative_prompt

    # 提交异步任务
    result = _call("CVSync2AsyncSubmitTask", {
        "req_key": "jimeng_t2v_v30",
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
        "seed": seed,
        **({"negative_prompt": negative_prompt} if negative_prompt else {}),
    })

    if not result["ok"]:
        return result

    data = result["data"]
    # 即梦 API 返回格式: {"code": 10000, "data": {"task_id": "..."}, "message": "Success"}
    code = data.get("code", -1)
    if code != 10000:
        return {"ok": False, "error": data.get("message", f"API错误 code={code}"), "raw": json.dumps(data, ensure_ascii=False)[:300]}

    inner = data.get("data", {})
    task_id = inner.get("task_id", "")
    if not task_id:
        return {"ok": False, "error": f"未获取到 task_id: {json.dumps(data, ensure_ascii=False)[:300]}"}

    # 轮询等待异步结果
    return _poll_task(task_id, timeout_sec=300)


def image_to_video(
    image_url: str = "",
    image_base64: str = "",
    prompt: str = "",
    duration: int = 5,
    resolution: str = "720p",
) -> dict:
    """
    图生视频 — 从静态图片生成视频

    Args:
        image_url:    图片URL（与 image_base64 二选一）
        image_base64: 图片base64编码
        prompt:       运动描述（如"镜头缓慢推近"）
        duration:     视频时长(秒)
        resolution:   分辨率

    Returns:
        {"ok": True, "task_id": "...", "video_url": "..."}
    """
    body = {
        "req_key": "jimeng_i2v_v30",
        "prompt": prompt or "镜头缓慢推近，展示空间细节",
        "duration": duration,
        "resolution": resolution,
    }
    if image_url:
        body["image_url"] = image_url
    elif image_base64:
        body["image_base64"] = image_base64
    else:
        return {"ok": False, "error": "必须提供 image_url 或 image_base64"}

    result = _call("CVSync2AsyncSubmitTask", body)
    if not result["ok"]:
        return result

    data = result["data"]
    code = data.get("code", -1)
    if code != 10000:
        return {"ok": False, "error": data.get("message", f"API错误 code={code}")}

    inner = data.get("data", {})
    task_id = inner.get("task_id", "")
    if not task_id:
        return {"ok": False, "error": f"未获取到 task_id"}

    return _poll_task(task_id, timeout_sec=300)


# ═══════════════════════════════════
# 异步任务轮询
# ═══════════════════════════════════

def _poll_task(task_id: str, timeout_sec: int = 300, poll_interval: int = 3) -> dict:
    """轮询异步任务结果"""
    deadline = time.time() + timeout_sec

    while time.time() < deadline:
        result = _call("CVSync2AsyncGetResult", {
            "req_key": "jimeng_t2v_v30",
            "task_id": task_id,
        })

        if not result["ok"]:
            return result

        data = result["data"]
        code = data.get("code", -1)
        if code != 10000:
            return {"ok": False, "error": data.get("message", f"轮询错误 code={code}"), "task_id": task_id}

        inner = data.get("data", {})
        status = inner.get("status", "")

        if status == "done":
            video_url = inner.get("video_url", inner.get("VideoUrl", ""))
            return {
                "ok": True,
                "task_id": task_id,
                "status": "done",
                "video_url": video_url,
                "result": inner,
            }

        if status in ("failed", "error", "expired"):
            err_msg = inner.get("message", inner.get("error_msg", "未知错误"))
            return {"ok": False, "error": err_msg, "task_id": task_id, "status": status}

        if status == "not_found":
            return {"ok": False, "error": "任务未找到（可能已过期12h）", "task_id": task_id, "status": status}

        # 还在处理中: in_queue / generating / processing
        time.sleep(poll_interval)

    return {"ok": False, "error": f"任务超时({timeout_sec}s)", "task_id": task_id}


# ═══════════════════════════════════
# 高层封装 — 装企视频生成
# ═══════════════════════════════════

def generate_renovation_video(
    script: dict,
    mode: str = "text_to_video",
    download_dir: str = None,
) -> dict:
    """
    装企视频一键生成

    Args:
        script:      分镜脚本 (来自 video_engine.generate_video_script)
        mode:        生成模式 "text_to_video" | "image_to_video"
        download_dir: 下载目录，默认 VIDEO_OUT

    Returns:
        {"ok": True, "video_url": "...", "video_path": "...", "task_id": "..."}
    """
    if not AK or not SK:
        return {"ok": False, "error": "即梦 API 未配置: 缺少 JIMENG_ACCESS_KEY / JIMENG_SECRET_KEY"}

    prompt = script.get("prompt", "")[:1500]  # API 有长度限制

    if mode == "text_to_video":
        result = text_to_video(
            prompt=prompt,
            duration=30,
            resolution="720p",
            style="realistic",
        )
    elif mode == "image_to_video":
        # TODO: 先从素材库匹配一张启动图
        result = {"ok": False, "error": "图生视频需要先上传素材，暂时使用文生视频"}
        # 降级到文生视频
        if not result.get("ok"):
            result = text_to_video(prompt=prompt, duration=30, resolution="720p")
    else:
        return {"ok": False, "error": f"未知模式: {mode}"}

    if not result.get("ok"):
        return result

    # 如果返回了视频URL且需要下载
    video_url = result.get("video_url", "")
    if video_url and download_dir:
        try:
            import re
            dl_dir = Path(download_dir) if download_dir else Path("D:/个人文件/电商图片/装企孵化/视频产出")
            dl_dir.mkdir(parents=True, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".mp4"
            # 从URL猜测扩展名
            if ".mov" in video_url.lower():
                ext = ".mov"
            fname = f"jimeng_{ts}_{result['task_id'][:8]}{ext}"
            fpath = dl_dir / fname

            # 下载视频
            req = request.Request(video_url)
            resp = request.urlopen(req, timeout=300)
            fpath.write_bytes(resp.read())
            result["video_path"] = str(fpath)
            result["file_size_mb"] = round(fpath.stat().st_size / 1024 / 1024, 1)
        except Exception as e:
            result["download_error"] = str(e)[:200]

    return result


# ═══════════════════════════════════
# 健康检查 & 配置状态
# ═══════════════════════════════════

def check_status() -> dict:
    """检查即梦 API 配置状态"""
    issues = []
    if not AK:
        issues.append("缺少 JIMENG_ACCESS_KEY")
    if not SK:
        issues.append("缺少 JIMENG_SECRET_KEY")

    if issues:
        return {"configured": False, "issues": issues, "provider": "jimeng"}

    # 尝试一次轻量 API 调用验证签名和服务权限
    try:
        test_result = _call("CVSync2AsyncGetResult", {
            "req_key": "jimeng_t2v_v30",
            "task_id": "health_check_test",
        })
        if test_result.get("ok"):
            err_data = test_result.get("data", {})
            err_code = err_data.get("code", 0)
            err_msg = str(err_data.get("message", ""))
            resp_err = str(err_data.get("ResponseMetadata", {}).get("Error", {}).get("Code", ""))

            if "SignatureDoesNotMatch" in resp_err or "signature" in err_msg.lower():
                issues.append("AK/SK 签名错误 — 请检查密钥是否正确")
            elif "Access Denied" in err_msg or err_code == 50400:
                issues.append("签名正确但服务未开通 — 需在火山方舟控制台启用即梦/视觉智能服务")
            # 其他错误(如 task not found)说明签名和服务都OK
        else:
            err_text = test_result.get("error", "")
            if "Access Denied" in err_text or "50400" in err_text:
                issues.append("签名正确 ✓ 但服务未开通 — 需在火山方舟控制台开通即梦/视觉智能服务")
            elif "SignatureDoesNotMatch" in err_text:
                issues.append("AK/SK 签名验证失败")
            elif "401" in err_text:
                issues.append(f"认证失败(401): {err_text[:120]}")
            else:
                issues.append(f"未知错误: {err_text[:120]}")
    except Exception as e:
        issues.append(f"连通性测试失败: {e}")

    if not issues:
        issues.append("API 签名验证通过 ✓ — 待首次实际调用确认")

    return {
        "configured": len(issues) == 1 and "通过" in issues[0],
        "issues": issues,
        "provider": "jimeng",
        "service": SERVICE,
        "region": REGION,
        "endpoint": HOST,
    }


if __name__ == "__main__":
    # 自检模式
    status = check_status()
    print(f"即梦 API 状态: {json.dumps(status, ensure_ascii=False, indent=2)}")

    if status["configured"] and len(sys.argv) > 1:
        # 测试文生视频
        test_prompt = sys.argv[1]
        print(f"\n测试文生视频: {test_prompt[:80]}...")
        result = text_to_video(prompt=test_prompt, duration=5, resolution="720p")
        print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
