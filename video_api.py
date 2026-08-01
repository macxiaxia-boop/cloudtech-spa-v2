"""
视频生成API集成层 — Video Generation API
对接: 即梦(Jimeng) / 剪映(Jianying) / Seedance
"""
import os, json, time, hashlib, hmac, base64, threading
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE = Path(__file__).parent
VIDEO_OUT = Path("D:/个人文件/电商图片/装企孵化/视频产出")
VIDEO_OUT.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# API Providers
# ═══════════════════════════════════

PROVIDERS = {
    "jimeng": {
        "name": "即梦 AI",
        "endpoint": "https://api.jimeng.ai/v1/video/generate",
        "models": ["jimeng-video-1.0", "jimeng-video-1.5-pro"],
        "max_duration": 60,
        "supported_formats": ["9:16", "16:9", "1:1"],
        "cost_per_second": 0.5,  # ¥/秒
    },
    "jianying": {
        "name": "剪映 API",
        "endpoint": "https://api.jianying.com/v1/export",
        "models": ["jianying-auto-edit"],
        "max_duration": 180,
        "supported_formats": ["9:16", "16:9"],
        "cost_per_second": 0.1,
    },
    "seedance": {
        "name": "Seedance 2.0",
        "endpoint": "https://api.seedance.cn/v2/generate",
        "models": ["seedance-2.0", "seedance-2.0-fast"],
        "max_duration": 120,
        "supported_formats": ["9:16", "16:9", "1:1", "4:5"],
        "cost_per_second": 0.8,
    },
}

# ═══════════════════════════════════
# Video Generation Request Builder
# ═══════════════════════════════════

def build_video_request(script: dict, provider: str = "jimeng", options: dict = None) -> dict:
    """构建视频生成API请求"""
    provider_cfg = PROVIDERS.get(provider, PROVIDERS["jimeng"])
    opts = options or {}

    request = {
        "provider": provider,
        "provider_name": provider_cfg["name"],
        "model": opts.get("model", provider_cfg["models"][0]),
        "prompt": script.get("prompt", ""),
        "duration": _parse_duration(script.get("duration", "30s")),
        "aspect_ratio": opts.get("aspect_ratio", "9:16"),
        "style": script.get("visual_style", "cinematic"),
        "scenes": script.get("scenes", []),
        "bgm": script.get("bgm", "轻快温馨"),
        "resolution": opts.get("resolution", "1080p"),
        "callback_url": opts.get("callback_url", ""),
        "metadata": {
            "mode": script.get("mode", ""),
            "topic": script.get("topic", ""),
            "account": script.get("account", ""),
        },
    }

    # 成本估算
    duration_sec = request["duration"]
    request["estimated_cost"] = {
        "amount": round(duration_sec * provider_cfg["cost_per_second"], 2),
        "currency": "¥",
        "provider": provider_cfg["name"],
    }

    return request


def _parse_duration(dur_str: str) -> int:
    """解析时长字符串 '30-60s' → 45 (取中值)"""
    try:
        parts = dur_str.replace("s", "").split("-")
        nums = [int(p.strip()) for p in parts if p.strip().isdigit()]
        return sum(nums) // len(nums) if nums else 30
    except Exception:
        return 30


# ═══════════════════════════════════
# Video Generation Status Tracker
# ═══════════════════════════════════

GENERATION_JOBS = {}  # 内存状态（生产环境应持久化到DB）

def submit_video_job(request: dict) -> dict:
    """提交视频生成任务（异步）"""
    job_id = f"vj-{hashlib.md5(str(time.time()).encode()).hexdigest()[:12]}"

    job = {
        "id": job_id,
        "status": "pending",
        "request": request,
        "submitted_at": datetime.now().isoformat()[:19],
        "estimated_cost": request.get("estimated_cost", {}),
        "provider": request["provider"],
        "result": None,
        "error": None,
    }

    # 真实异步处理: 后台线程模拟API调用
    GENERATION_JOBS[job_id] = job

    def _process_job():
        """后台线程: 模拟视频生成流程"""
        try:
            # 阶段1: 排队 → 处理中（模拟API排队）
            time.sleep(2)
            GENERATION_JOBS[job_id]["status"] = "processing"
            GENERATION_JOBS[job_id]["started_at"] = datetime.now().isoformat()[:19]

            # 阶段2: 模拟生成时长（实际调用即梦/剪映API）
            duration = request.get("duration", 30)
            wait = max(5, min(duration, 60))  # 5-60秒
            time.sleep(wait)

            # 阶段3: 完成
            GENERATION_JOBS[job_id]["status"] = "completed"
            GENERATION_JOBS[job_id]["completed_at"] = datetime.now().isoformat()[:19]
            GENERATION_JOBS[job_id]["result"] = {
                "video_url": f"https://video.cloudtech.local/{job_id}.mp4",
                "thumbnail": f"https://video.cloudtech.local/{job_id}_thumb.jpg",
                "duration_seconds": duration,
                "resolution": request.get("resolution", "1080p"),
                "file_size": f"{duration * 2}MB",
                "format": "mp4",
            }
        except Exception as e:
            GENERATION_JOBS[job_id]["status"] = "failed"
            GENERATION_JOBS[job_id]["error"] = str(e)

    threading.Thread(target=_process_job, daemon=True).start()

    return {
        "ok": True,
        "job_id": job_id,
        "status": "pending",
        "estimated_wait": f"{request.get('duration', 30) * 2}秒",
        "check_url": f"/api/video/job/{job_id}",
    }


def get_video_job(job_id: str) -> Optional[dict]:
    """查询视频生成任务状态"""
    return GENERATION_JOBS.get(job_id)


def list_video_jobs(status: str = "", limit: int = 20) -> list:
    """列出视频任务"""
    jobs = list(GENERATION_JOBS.values())
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    return sorted(jobs, key=lambda j: j["submitted_at"], reverse=True)[:limit]


# ═══════════════════════════════════
# Video Understanding Model
# 对标筷子: 视频理解模型 — 编-拍-剪-投-管全链路
# ═══════════════════════════════════

def analyze_video_content(video_path: str = "", script: dict = None) -> dict:
    """视频内容分析: 场景检测·标签提取·质量评估

    实际部署对接: 筷子视频理解模型 / CLIP / VideoMAE
    当前: 基于脚本元数据的启发式分析
    """
    if script:
        return _analyze_from_script(script)
    if video_path:
        return _analyze_from_file(video_path)
    return {"ok": False, "error": "请提供视频路径或脚本"}


def _analyze_from_script(script: dict) -> dict:
    """从脚本元数据推断视频特征"""
    scenes = script.get("scenes", [])
    prompt = script.get("prompt", "")
    mode = script.get("mode", "")

    # 场景类型检测
    scene_types = {
        "before_after": ["改造前", "改造后", "对比", "花费"],
        "material_review": ["开箱", "微距", "实验", "价格"],
        "room_tour": ["推门", "漫游", "细节", "尺寸"],
        "construction_diary": ["进度", "延时", "问题", "方案"],
    }
    detected_scenes = scene_types.get(mode, ["通用"])

    # 标签提取
    tags = []
    mode_tags = {
        "before_after": ["装修改造", "前后对比", "效果展示"],
        "material_review": ["材料测评", "选购指南", "建材"],
        "room_tour": ["空间展示", "设计案例", "漫游"],
        "construction_diary": ["施工日记", "工地实拍", "装修过程"],
    }
    tags.extend(mode_tags.get(mode, []))

    # 质量评估（基于分镜数量·描述详细度·素材匹配度）
    scene_count = len(scenes)
    prompt_length = len(prompt)
    asset_count = script.get("asset_count", 0)

    quality_score = min(10, (
        (3 if scene_count >= 5 else 1 if scene_count >= 3 else 0) +
        (3 if prompt_length > 500 else 2 if prompt_length > 200 else 1) +
        (2 if asset_count > 5 else 1 if asset_count > 0 else 0) +
        (2 if mode in scene_types else 0)
    ))

    return {
        "ok": True,
        "mode": mode,
        "scene_count": scene_count,
        "detected_scenes": detected_scenes,
        "tags": tags,
        "prompt_length": prompt_length,
        "asset_count": asset_count,
        "quality_score": quality_score,
        "quality_label": "优秀" if quality_score >= 7 else "良好" if quality_score >= 5 else "待优化",
        "duration": script.get("duration", "未知"),
        "bgm": script.get("bgm", ""),
    }


def _analyze_from_file(video_path: str) -> dict:
    """从视频文件分析（需ffprobe）"""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path],
            capture_output=True, text=True, timeout=30
        )
        info = json.loads(result.stdout)
        fmt = info.get("format", {})
        streams = info.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})

        return {
            "ok": True,
            "format": fmt.get("format_name", ""),
            "duration": round(float(fmt.get("duration", 0))),
            "size_mb": round(int(fmt.get("size", 0)) / 1024 / 1024, 1),
            "resolution": f"{video_stream.get('width','?')}x{video_stream.get('height','?')}",
            "codec": video_stream.get("codec_name", ""),
            "fps": eval(video_stream.get("r_frame_rate", "0/1")),
            "bitrate_kbps": round(int(fmt.get("bit_rate", 0)) / 1000),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "hint": "需要ffprobe (ffmpeg)"}


# ═══════════════════════════════════
# Bulk Video Production Pipeline
# ═══════════════════════════════════

def bulk_produce_videos(topics: list, mode: str = "before_after", provider: str = "jimeng") -> dict:
    """批量视频生产: 选题→脚本→API提交→追踪"""
    from video_engine import generate_video_script

    results = []
    for item in topics:
        topic_name = item.get("topic", item) if isinstance(item, dict) else item
        context = item.get("context", {}) if isinstance(item, dict) else {}

        # Step 1: 生成脚本
        script = generate_video_script(topic_name, mode, context)

        # Step 2: 构建API请求
        request = build_video_request(script, provider, context.get("options", {}))

        # Step 3: 提交任务
        job = submit_video_job(request)

        # Step 4: 视频理解分析
        analysis = analyze_video_content(script=script)

        results.append({
            "topic": topic_name,
            "script": {"mode": script["mode"], "duration": script["duration"], "scenes": len(script["scenes"])},
            "job": {"id": job["job_id"], "status": job["status"], "cost": request["estimated_cost"]},
            "analysis": {"quality_score": analysis["quality_score"], "tags": analysis["tags"]},
        })

    return {
        "total": len(results),
        "total_cost": round(sum(r["job"]["cost"]["amount"] for r in results), 2),
        "currency": "¥",
        "results": results,
    }
