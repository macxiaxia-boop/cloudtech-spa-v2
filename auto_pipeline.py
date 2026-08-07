"""
端到端自动化流水线 — Auto Pipeline
====================================
一键从选题→生成→混剪→发布→数据回流的无人值守流水线

对标筷子科技：编→拍→剪→投 全链路自动化
差异化：加「数据回流」和「知识库注入」形成闭环飞轮

用法:
    python auto_pipeline.py --topic "奶油风装修" --city 漳州 --area 100 --budget 15
"""
from cloudtech_app import DATA_DIR, OUTPUT_DIR

import json, os, time
import app_logger as _al
_log = _al.get_logger("auto_pipeline")
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

BASE = Path(__file__).parent
PIPELINE_LOG = DATA_DIR / "pipeline_logs"
PIPELINE_LOG.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 流水线阶段定义
# ═══════════════════════════════════

PIPELINE_STAGES = [
    {
        "id": "stage_1_knowledge",
        "name": "📚 知识注入",
        "description": "从装企知识库注入本地化数据（小区/风格/工价/政策）",
        "handler": "_stage_knowledge_injection",
    },
    {
        "id": "stage_2_content",
        "name": "📝 内容生成",
        "description": "生成多平台内容（小红书+抖音+公众号+视频脚本）",
        "handler": "_stage_content_generation",
    },
    {
        "id": "stage_3_video",
        "name": "🎬 视频生产",
        "description": "AI生成视频方案+混剪方案+数字人方案",
        "handler": "_stage_video_production",
    },
    {
        "id": "stage_4_publish",
        "name": "📤 一键分发",
        "description": "内容分发到小红书/抖音/公众号/视频号",
        "handler": "_stage_publish_distribution",
    },
    {
        "id": "stage_5_analytics",
        "name": "📊 数据回流",
        "description": "记录产出数据、更新知识库、优化下次策略",
        "handler": "_stage_data_feedback",
    },
]

# ═══════════════════════════════════
# 流水线编排
# ═══════════════════════════════════

class AutoPipeline:
    """自动化流水线引擎"""

    def __init__(self, tenant_id: str = "zq-5bb59623", dry_run: bool = True):
        self.tenant_id = tenant_id
        self.dry_run = dry_run
        self.state = {}
        self.results = []
        self.started_at = datetime.now().isoformat()[:19]
        self.pipeline_id = f"pipe-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def run(self, input_data: dict, stages: List[str] = None) -> dict:
        """
        执行流水线

        input_data:
            topic: 主题
            city: 城市
            area: 面积
            budget: 预算
            style: 风格
            community: 小区名
            platforms: 发布平台列表
            video_provider: 视频生成提供商
            avatar_id: 数字人ID
            count: 批量生成数量
        """
        self.state = {"input": input_data, "dry_run": self.dry_run}
        selected_stages = stages or [s["id"] for s in PIPELINE_STAGES]

        for stage in PIPELINE_STAGES:
            if stage["id"] not in selected_stages:
                continue

            start_time = time.time()
            self.state["current_stage"] = stage["id"]
            _log.info(f"▶ {stage['name']} ...")

            try:
                handler = globals().get(stage["handler"])
                if handler:
                    result = handler(self)
                else:
                    result = {"ok": True, "stage": stage["id"], "message": f"阶段跳过: {stage['name']}"}

                elapsed = round(time.time() - start_time, 1)
                result["elapsed"] = elapsed
                result["stage"] = stage["id"]
                result["stage_name"] = stage["name"]
                self.results.append(result)

                status = "✅" if result.get("ok") else "❌"
                _log.info(f"  {status} 完成 ({elapsed}s)")
                if not result.get("ok"):
                    _log.warning(f"  错误: {result.get('error', '未知错误')}")

            except Exception as e:
                self.results.append({
                    "ok": False, "stage": stage["id"],
                    "stage_name": stage["name"],
                    "error": str(e),
                    "elapsed": round(time.time() - start_time, 1),
                })
                _log.error(f"  ❌ 异常: {e}")

        # 生成报告
        report = self._generate_report()
        self._save_log(report)

        return report

    def _generate_report(self) -> dict:
        ok_count = sum(1 for r in self.results if r.get("ok"))
        total = len(self.results)
        return {
            "pipeline_id": self.pipeline_id,
            "ok": ok_count == total,
            "started_at": self.started_at,
            "finished_at": datetime.now().isoformat()[:19],
            "total_stages": total,
            "success_stages": ok_count,
            "failed_stages": total - ok_count,
            "dry_run": self.dry_run,
            "input": self.state.get("input", {}),
            "stages": self.results,
            "output": self.state.get("output", {}),
            "summary": self._generate_summary(),
        }

    def _generate_summary(self) -> str:
        lines = [
            f"🚀 自动化流水线 #{self.pipeline_id}",
            f"时间: {self.started_at}",
            f"模式: {'模拟' if self.dry_run else '正式'}",
            "",
            "## 产出清单",
        ]

        output = self.state.get("output", {})
        if output.get("xiaohongshu"):
            lines.append(f"- 🟥 小红书: {output['xiaohongshu'].get('title', '')}")
        if output.get("douyin"):
            lines.append(f"- 🎵 抖音: {output['douyin'].get('title', '')}")
        if output.get("wechat"):
            lines.append(f"- 💚 公众号: {output['wechat'].get('title', '')}")
        if output.get("video"):
            v = output["video"]
            lines.append(f"- 🎬 视频: {v.get('template', '')} {v.get('duration', '')}")
        if output.get("digital_human"):
            lines.append(f"- 🤖 数字人: {output['digital_human'].get('avatar', '')}")

        lines.append(f"\n## 状态")
        for r in self.results:
            icon = "✅" if r.get("ok") else "❌"
            lines.append(f"{icon} {r.get('stage_name', r.get('stage', ''))} ({r.get('elapsed', 0)}s)")

        return "\n".join(lines)

    def _save_log(self, report: dict):
        log_file = PIPELINE_LOG / f"{self.pipeline_id}.json"
        log_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        _log.info(f"📋 报告已保存: {log_file}")


# ═══════════════════════════════════
# 阶段实现
# ═══════════════════════════════════

def _stage_knowledge_injection(pipeline: AutoPipeline) -> dict:
    """阶段1: 知识注入"""
    inp = pipeline.state["input"]
    city = inp.get("city", "漳州")
    style = inp.get("style", "现代简约")
    community = inp.get("community", "")

    knowledge_context = {}

    try:
        from zhuangqi_knowledge_v1 import (
            search_community, get_style_guide, estimate_budget,
            get_material_guide, get_local_issues, get_policies,
        )

        # 小区信息
        if community:
            comm_result = search_community(community)
            knowledge_context["community"] = comm_result.get("results", [])[:1]

        # 风格指南
        style_result = get_style_guide(style)
        if style_result.get("ok"):
            knowledge_context["style"] = style_result

        # 预算估算
        area = inp.get("area", 100)
        budget_result = estimate_budget(area, "舒适型", style)
        knowledge_context["budget"] = budget_result

        # 本地特有问题
        issues = get_local_issues()
        knowledge_context["local_issues"] = list(issues.get("issues", {}).keys())

        # 政策信息
        policies = get_policies()
        knowledge_context["policies_applicable"] = list(policies.get("policies", {}).keys())

        pipeline.state["knowledge"] = knowledge_context

        return {
            "ok": True,
            "knowledge_loaded": len(knowledge_context),
            "city": city,
            "style": style,
            "has_community_data": bool(community and knowledge_context.get("community")),
            "local_issues": knowledge_context.get("local_issues", []),
        }

    except Exception as e:
        return {"ok": False, "error": f"知识注入失败: {str(e)}"}


def _stage_content_generation(pipeline: AutoPipeline) -> dict:
    """阶段2: 内容生成"""
    inp = pipeline.state["input"]
    knowledge = pipeline.state.get("knowledge", {})
    topic = inp.get("topic", "装修设计")
    city = inp.get("city", "漳州")
    style = inp.get("style", "现代简约")
    area = inp.get("area", 100)
    budget_val = inp.get("budget", 15)
    community = inp.get("community", "本地小区")

    output = {}
    platforms = inp.get("platforms", ["xiaohongshu", "douyin", "wechat_mp"])

    # 注入知识库上下文
    kb_context = ""
    if knowledge.get("budget"):
        b = knowledge["budget"]
        kb_context += f"装修预算参考: {b.get('total_range', (0,0))[0]/10000:.1f}-{b.get('total_range', (0,0))[1]/10000:.1f}万 | "
    if knowledge.get("style"):
        s = knowledge["style"]
        kb_context += f"风格要素: {', '.join(s.get('key_elements', []))} | "
    if knowledge.get("local_issues"):
        kb_context += f"本地注意事项: {', '.join(knowledge['local_issues'])}"

    try:
        from admin_dashboard import _deepseek_call

        for platform in platforms:
            platform_prompts = {
                "xiaohongshu": f"""你是装修博主。生成一篇小红书图文。

主题: {topic}
城市: {city} | 风格: {style} | 面积: {area}平 | 预算: {budget_val}万
{kb_context}

要求:
- 标题包含数字+emoji（如"花{budget_val}万装{area}平{style}风"）
- 正文分点（不超过500字）
- 以"如果你也在{city}装修，私信我拿完整清单"结尾
- 添加5-8个话题标签

直接输出完整内容，不要额外说明。""",

                "douyin": f"""你是抖音装修博主。生成一条口播脚本。

主题: {topic}
城市: {city} | 风格: {style} | 面积: {area}平 | 预算: {budget_val}万
{kb_context}

要求:
- 开头3秒用钩子（比如"在{city}装修{area}平需要多少钱？今天告诉你真相"）
- 8-12个口播段落，每段10-15秒
- 配合画面提示（如"[展示预算表]"）
- 结尾引导关注

直接输出完整脚本，不要额外说明。""",

                "wechat_mp": f"""你是装修自媒体编辑。生成一篇公众号科普文。

主题: {topic}
城市: {city} | 风格: {style} | 面积: {area}平 | 预算: {budget_val}万
{kb_context}

要求:
- 标题吸引点击
- 小标题分段（3-5段）
- 每段200-300字
- 包含实用干货和数据
- 1200-2000字

直接输出完整文章，不要额外说明。""",
            }

            prompt = platform_prompts.get(platform, "")
            if not prompt:
                continue

            sys_prompt = f"你是专业的{platform}内容创作者，专做装修领域。"
            content = _deepseek_call(sys_prompt, prompt, max_tokens=2000)

            output[platform] = {
                "title": _extract_title(content, platform),
                "content": content,
                "platform": platform,
            }

        pipeline.state["output"] = output
        return {"ok": True, "platforms_generated": list(output.keys()), "total_chars": sum(len(str(v)) for v in output.values())}

    except Exception as e:
        return {"ok": False, "error": f"内容生成失败: {str(e)}"}


def _stage_video_production(pipeline: AutoPipeline) -> dict:
    """阶段3: 视频生产"""
    inp = pipeline.state["input"]
    output = pipeline.state.get("output", {})
    topic = inp.get("topic", "装修设计")
    style = inp.get("style", "现代简约")
    provider = inp.get("video_provider", "mock")
    template = inp.get("video_template", "before_after")

    video_results = {}

    try:
        # AI视频生成
        from video_engine import generate_video_from_content, ai_generate_video
        video_result = generate_video_from_content(
            title=f"{style}{topic}",
            content=output.get("xiaohongshu", {}).get("content", topic),
            provider=provider,
            template=template,
        )
        video_results["ai_video"] = {
            "ok": video_result.get("ok"),
            "template": template,
            "provider": provider,
            "script": video_result.get("script", {}).get("prompt", "")[:300],
        }

        # 混剪方案
        from video_mixer import mix_video, list_templates
        mix_plan = mix_video([], template=template, dry_run=True)
        video_results["mix_plan"] = {
            "ok": mix_plan.get("ok"),
            "template": template,
            "duration": mix_plan.get("plan", {}).get("total_duration", 0),
        }

        # 数字人方案
        avatar_id = inp.get("avatar_id")
        if avatar_id:
            try:
                from digital_human import generate_digital_human_video
                dh_script = output.get("douyin", {}).get("content", topic)
                dh_result = generate_digital_human_video(
                    script=dh_script[:1000],
                    avatar_id=avatar_id,
                    provider="mock",
                )
                video_results["digital_human"] = dh_result
            except Exception:
                import logging; logging.getLogger(__name__).warning("Suppressed exception", exc_info=True)

        # 合并到输出
        if "output" not in pipeline.state:
            pipeline.state["output"] = {}
        pipeline.state["output"]["video"] = video_results

        return {
            "ok": True,
            "ai_video": video_results.get("ai_video", {}).get("ok"),
            "mix_plan": video_results.get("mix_plan", {}).get("ok"),
            "has_digital_human": "digital_human" in video_results,
        }

    except Exception as e:
        return {"ok": False, "error": f"视频生产失败: {str(e)}"}


def _stage_publish_distribution(pipeline: AutoPipeline) -> dict:
    """阶段4: 一键分发"""
    output = pipeline.state.get("output", {})
    inp = pipeline.state["input"]
    platforms = inp.get("platforms", ["xiaohongshu", "douyin"])

    publish_results = []

    try:
        from platform_publisher import distribute_content

        # 构建分发内容
        content_for_dist = {
            "title": inp.get("topic", "装修设计"),
            "content": output.get("xiaohongshu", {}).get("content", "") or output.get("wechat_mp", {}).get("content", ""),
            "images": inp.get("images", []),
            "video": output.get("video", {}).get("ai_video", {}).get("path"),
            "tags": _generate_tags(inp),
        }

        result = distribute_content(
            content_for_dist,
            platforms=platforms,
            dry_run=pipeline.dry_run,
        )
        publish_results = result.get("results", [])

        if "output" not in pipeline.state:
            pipeline.state["output"] = {}
        pipeline.state["output"]["publish"] = {
            "platforms": platforms,
            "total": result.get("total", 0),
            "success": result.get("success", 0),
        }

        return {"ok": True, "published_to": platforms, "success_count": result.get("success", 0)}

    except Exception as e:
        return {"ok": False, "error": f"发布失败: {str(e)}"}


def _stage_data_feedback(pipeline: AutoPipeline) -> dict:
    """阶段5: 数据回流"""
    inp = pipeline.state["input"]

    feedback = {
        "pipeline_id": pipeline.pipeline_id,
        "timestamp": datetime.now().isoformat()[:19],
        "dry_run": pipeline.dry_run,
        "input_summary": {
            "topic": inp.get("topic"),
            "city": inp.get("city"),
            "style": inp.get("style"),
            "area": inp.get("area"),
        },
        "stages_completed": [r["stage"] for r in pipeline.results if r.get("ok")],
        "knowledge_notes": _generate_knowledge_notes(pipeline),
    }

    # 保存反馈数据
    feedback_dir = BASE / "data" / "pipeline_feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = feedback_dir / f"feedback_{pipeline.pipeline_id}.json"
    feedback_file.write_text(json.dumps(feedback, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "feedback_saved": str(feedback_file),
        "knowledge_notes": feedback["knowledge_notes"],
    }


# ═══════════════════════════════════
# 辅助函数
# ═══════════════════════════════════

def _extract_title(content: str, platform: str) -> str:
    """从生成内容中提取标题"""
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("```"):
            # 小红书/抖音标题通常是第一行
            if platform in ("xiaohongshu", "douyin"):
                return line[:100]
    return lines[0][:100] if lines else "装修设计"


def _generate_tags(inp: dict) -> List[str]:
    """根据输入生成标签"""
    tags = ["装修", "装修设计"]
    city = inp.get("city", "")
    style = inp.get("style", "")
    if city: tags.append(f"{city}装修")
    if style: tags.append(f"{style}风")
    tags.append("装修灵感")
    tags.append("装修避坑")
    return tags


def _generate_knowledge_notes(pipeline: AutoPipeline) -> str:
    """生成知识记录"""
    inp = pipeline.state["input"]
    return (
        f"主题 '{inp.get('topic')}' 在 '{inp.get('city')}' 使用 '{inp.get('style')}' 风格。"
        f"面积 {inp.get('area')} 平，预算 {inp.get('budget')} 万。"
        f"模式: {'模拟' if pipeline.dry_run else '正式'}。"
    )


# ═══════════════════════════════════
# 快捷一键函数
# ═══════════════════════════════════

def one_click_produce(
    topic: str,
    city: str = "漳州",
    area: int = 100,
    budget: int = 15,
    style: str = "现代简约",
    community: str = "",
    platforms: List[str] = None,
    dry_run: bool = True,
) -> dict:
    """
    一键生产：5个阶段全部执行

    这是面向用户的最简入口：
    >>> one_click_produce("奶油风装修", city="漳州", area=100, budget=15)
    """
    pipeline = AutoPipeline(dry_run=dry_run)
    return pipeline.run({
        "topic": topic,
        "city": city,
        "area": area,
        "budget": budget,
        "style": style,
        "community": community,
        "platforms": platforms or ["xiaohongshu", "douyin", "wechat_mp"],
        "video_provider": "mock",
        "video_template": "before_after",
    })


def quick_video_publish(
    topic: str,
    city: str = "漳州",
    style: str = "现代简约",
    dry_run: bool = True,
) -> dict:
    """快速视频+发布（跳过知识注入和数据分析）"""
    pipeline = AutoPipeline(dry_run=dry_run)
    return pipeline.run(
        {
            "topic": topic, "city": city, "area": 100,
            "style": style, "budget": 15,
            "platforms": ["xiaohongshu", "douyin"],
            "video_provider": "mock",
            "video_template": "before_after",
        },
        stages=["stage_2_content", "stage_3_video", "stage_4_publish"],
    )


def list_pipeline_history(limit: int = 10) -> list:
    """查看历史流水线记录"""
    logs = sorted(PIPELINE_LOG.glob("pipe-*.json"), reverse=True)
    history = []
    for f in logs[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            history.append({
                "id": data.get("pipeline_id"),
                "time": data.get("started_at"),
                "ok": data.get("ok"),
                "stages": f"{data.get('success_stages', 0)}/{data.get('total_stages', 0)}",
                "topic": data.get("input", {}).get("topic"),
                "dry_run": data.get("dry_run"),
            })
        except Exception:
            import logging; logging.getLogger(__name__).warning("Suppressed exception", exc_info=True)
    return history


# ═══════════════════════════════════
# CLI 测试
# ═══════════════════════════════════

if __name__ == "__main__":
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "奶油风装修"
    city = sys.argv[2] if len(sys.argv) > 2 else "漳州"

    _log.info(f"🚀 云数科技自动流水线")
    _log.info(f"主题: {topic} | 城市: {city}")
    _log.info(f"{'='*50}")

    result = one_click_produce(topic, city=city, area=100, budget=15, dry_run=True)

    _log.info(f"\n{'='*50}")
    _log.info(result.get("summary", ""))
    _log.info(f"\n完成: {result['success_stages']}/{result['total_stages']} 阶段成功")
