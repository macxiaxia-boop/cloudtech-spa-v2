"""
多模型聚合框架 — Multi-Model Aggregation
对标InVideo 200+模型·筷子多模型调度·模型路由·切换·对比
"""
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
MODEL_DIR = Path("D:/个人文件/AI/云数科技/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 模型注册表(对标InVideo 200+ models)
# ═══════════════════════════════════
MODELS = {
    "text": {
        "deepseek-v4-pro": {"provider": "DeepSeek", "type": "text", "strength": "深度推理·长文", "cost_per_1k": 0.01},
        "deepseek-v4-flash": {"provider": "DeepSeek", "type": "text", "strength": "快速响应·短文", "cost_per_1k": 0.003},
    },
    "video": {
        "seedance-2.0": {"provider": "ByteDance", "type": "video", "strength": "1080P·商业级", "cost_per_sec": 0.8},
        "jimeng-video-1.5": {"provider": "ByteDance", "type": "video", "strength": "快速生成·社交", "cost_per_sec": 0.5},
        "kling-3.0": {"provider": "Kuaishou", "type": "video", "strength": "高保真·电影级", "cost_per_sec": 1.2},
        "runway-gen4": {"provider": "Runway", "type": "video", "strength": "创意控制·MotionBrush", "cost_per_sec": 1.5},
        "sora-2": {"provider": "OpenAI", "type": "video", "strength": "长视频·真实感", "cost_per_sec": 2.0},
    },
    "image": {
        "seedance-image": {"provider": "ByteDance", "type": "image", "strength": "装修风格渲染", "cost_per_img": 0.05},
        "dalle-4": {"provider": "OpenAI", "type": "image", "strength": "创意概念图", "cost_per_img": 0.08},
    },
    "voice": {
        "elevenlabs": {"provider": "ElevenLabs", "type": "voice", "strength": "自然语音·29语言", "cost_per_char": 0.001},
        "azure-tts": {"provider": "Azure", "type": "voice", "strength": "企业级·多角色", "cost_per_char": 0.0005},
    },
}


def list_models(model_type: str = "") -> list:
    """列出可用模型"""
    if model_type:
        return [{"id": k, **v} for k, v in MODELS.get(model_type, {}).items()]
    all_models = []
    for t, models in MODELS.items():
        for k, v in models.items():
            all_models.append({"id": k, "type": t, **v})
    return all_models


def route_model(task: str, budget: str = "balanced") -> dict:
    """智能模型路由: 根据任务类型·预算选择最优模型"""
    routing = {
        "social_post": {"model": "deepseek-v4-flash", "reason": "短文·快速"},
        "long_article": {"model": "deepseek-v4-pro", "reason": "深度·长文"},
        "video_ad": {"model": "seedance-2.0", "reason": "商业级1080P" if budget != "low" else "jimeng-video-1.5"},
        "video_social": {"model": "jimeng-video-1.5", "reason": "社交短视频·低成本"},
        "video_cinematic": {"model": "kling-3.0", "reason": "电影级画质"},
        "video_creative": {"model": "runway-gen4", "reason": "创意控制·MotionBrush"},
        "image_render": {"model": "seedance-image", "reason": "装修渲染专用"},
        "voice_narrator": {"model": "elevenlabs", "reason": "自然语音"},
        "voice_enterprise": {"model": "azure-tts", "reason": "企业级多角色"},
    }

    # Budget override
    if budget == "low":
        routing["video_ad"]["model"] = "jimeng-video-1.5"
        routing["voice_narrator"]["model"] = "azure-tts"

    route = routing.get(task, {"model": "deepseek-v4-flash", "reason": "默认路由"})
    model_id = route["model"]

    # Find model details
    for t, models in MODELS.items():
        if model_id in models:
            return {"task": task, "model_id": model_id, "model": models[model_id], "reason": route["reason"]}

    return {"task": task, "model_id": model_id, "reason": route["reason"]}


def compare_models(model_ids: list, task_desc: str = "") -> dict:
    """模型对比: 多个模型的优劣分析"""
    comparison = []
    for mid in model_ids:
        for t, models in MODELS.items():
            if mid in models:
                comparison.append({"id": mid, **models[mid]})

    # 计算最优
    def _cost(m):
        return m.get("cost_per_sec") or m.get("cost_per_1k") or m.get("cost_per_img") or m.get("cost_per_char") or 999
    best = min(comparison, key=_cost) if comparison else None

    return {
        "task": task_desc, "models_compared": len(comparison),
        "comparison": comparison,
        "recommended": best["id"] if best else None,
        "recommended_reason": f"成本最优: {best['provider']} {best['strength']}" if best else "",
    }


def get_model_stats() -> dict:
    """模型统计"""
    total = 0
    by_type = {}
    for t, models in MODELS.items():
        by_type[t] = len(models)
        total += len(models)
    return {"total_models": total, "by_type": by_type, "providers": len(set(m["provider"] for models in MODELS.values() for m in models.values()))}
