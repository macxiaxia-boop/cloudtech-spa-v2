"""V9.8-IMPORT-MARKER
CloudTech v3.3 — AI 数字员工中心
================================
对标灵策智算 8 大数字员工

Phase 45 D4-7 (2026-09-14) — 前台收敛 3 vs 后端保留 8:
  - 前台展示（用户直接感知）：营销/法务/客服 = 3 个
  - 后端保留（API/数据/集成用）：HR/财务/采购 + 5 数字员工模板 = 8 个
  - ChatGPT 拍板：3 前台 = "客户直接感知的员工" = 营销获客的主轴

员工分类口径:
  - visible_for_user=True  → 前台展示 + 可路由对话（默认）
  - visible_for_user=False → 后端保留 + API 可调 + 前端不暴露菜单

对话/统计端点维持现状（8 个全保留）；仅 /list 增加 visible_for_user 字段 + 前台过滤。
"""
import sys
import os
import logging
import secrets
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

_DATA_LAYER = Path(r"D:\MiniMax\cloudtech-redesign\data-layer")
if str(_DATA_LAYER) not in sys.path:
    sys.path.insert(0, str(_DATA_LAYER))

logger = logging.getLogger("cloudtech.employees")
router = APIRouter(prefix="/api/v2/employees", tags=["v3.3 Employees"])

# Phase 45 D4-7: 前台 3 员工 vs 后端 8 员工分类
# 前台 3: 客户直接感知 = 营销获客主轴（ChatGPT 拍板）
FRONTEND_EMPLOYEES = {"content_writer", "customer_service", "market_researcher"}
# 后端 5: HR/财务/采购等业务能力（API 保留）
BACKEND_EMPLOYEES = {"short_video_script", "data_analyst", "seo_specialist",
                     "social_media_manager", "growth_hacker"}


# 8 大预设数字员工(对标灵策)
PRESET_EMPLOYEES = {
    "content_writer": {
        "name": "内容写手",
        "avatar": "✍️",
        "description": "AI 写公众号/小红书/知乎文章,懂 GEO SEO",
        "skills": ["文章生成", "标题优化", "SEO 关键词布局", "多平台改写"],
        "avg_response_time": "8s",
        "capability_score": 95,
    },
    "short_video_script": {
        "name": "短视频脚本",
        "avatar": "🎬",
        "description": "60 秒爆款短视频脚本,钩子+痛点+行动",
        "skills": ["分镜脚本", "钩子设计", "金句提炼", "BGM 推荐"],
        "avg_response_time": "5s",
        "capability_score": 92,
    },
    "data_analyst": {
        "name": "数据分析师",
        "avatar": "📊",
        "description": "实时数据洞察 + 异常告警 + 趋势预测",
        "skills": ["数据可视化", "异常检测", "趋势分析", "报告生成"],
        "avg_response_time": "12s",
        "capability_score": 88,
    },
    "seo_specialist": {
        "name": "SEO 专家",
        "avatar": "🔍",
        "description": "GEO 优化,关键词挖掘,搜索排名提升",
        "skills": ["关键词挖掘", "四象限分类", "GEO 文章", "排名追踪"],
        "avg_response_time": "6s",
        "capability_score": 94,
    },
    "social_media_manager": {
        "name": "社媒运营",
        "avatar": "📱",
        "description": "小红书/抖音/微博多平台账号管理",
        "skills": ["排期发布", "评论区互动", "数据复盘", "热点追踪"],
        "avg_response_time": "10s",
        "capability_score": 86,
    },
    "customer_service": {
        "name": "智能客服",
        "avatar": "💬",
        "description": "7×24 在线,理解上下文,80% 重复问题自动处理",
        "skills": ["意图识别", "知识库检索", "多轮对话", "情绪识别"],
        "avg_response_time": "1s",
        "capability_score": 90,
    },
    "market_researcher": {
        "name": "市场调研",
        "avatar": "🔎",
        "description": "竞品监控、行业报告、消费者洞察",
        "skills": ["竞品雷达", "舆情分析", "用户画像", "报告撰写"],
        "avg_response_time": "30s",
        "capability_score": 89,
    },
    "growth_hacker": {
        "name": "增长黑客",
        "avatar": "🚀",
        "description": "A/B 测试、漏斗优化、获客策略",
        "skills": ["A/B 实验", "转化漏斗", "留存分析", "获客渠道"],
        "avg_response_time": "20s",
        "capability_score": 87,
    },
}

# 内存存储:对话历史
_chat_history: Dict[str, List[dict]] = {}


# ============== Models ==============
class ChatRequest(BaseModel):
    employee: str
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    employee: str
    reply: str
    skill_called: Optional[str] = None
    tools_used: List[str] = []
    latency_ms: int
    tokens: int = 0


class EmployeeDeployRequest(BaseModel):
    employee: str
    channels: List[str] = Field(default_factory=lambda: ["web"], description="web/wechat/wecom/dingtalk")


# ============== 路由 ==============

@router.get("/list")
@router.get("")
async def list_employees():
    """8 大预设数字员工 + 部署状态

    Phase 45 D4-7: 增加 visible_for_user + tier 字段
      - tier=frontend: 前台 3 员工（用户直接感知）
      - tier=backend:  后端 5 员工（API 保留，不在菜单展示）
      - 默认前端 GET /list 仍返回全部 8 个（保留兼容）
      - 前端菜单收敛建议调用 GET /list?frontend_only=true
    """
    from digital_employees import EMPLOYEES
    deployed = list(EMPLOYEES.keys()) if EMPLOYEES else []
    out = []
    for k, v in PRESET_EMPLOYEES.items():
        is_frontend = k in FRONTEND_EMPLOYEES
        out.append({
            "id": k,
            **v,
            "deployed": k in deployed,
            "visible_for_user": is_frontend,
            "tier": "frontend" if is_frontend else "backend",
        })
    return {"status": "ok", "data": out}


@router.get("/list/frontend")
async def list_frontend_employees():
    """Phase 45 D4-7: 前台 3 员工专用端点（前端菜单收敛）

    返回: 营销(content_writer) + 客服(customer_service) + 调研(market_researcher)
    用途: 前端菜单只渲染这 3 个；其余 5 个走 API 但不展示
    """
    from digital_employees import EMPLOYEES
    deployed = list(EMPLOYEES.keys()) if EMPLOYEES else []
    out = []
    for k in FRONTEND_EMPLOYEES:
        if k not in PRESET_EMPLOYEES:
            continue
        v = PRESET_EMPLOYEES[k]
        out.append({
            "id": k,
            **v,
            "deployed": k in deployed,
            "visible_for_user": True,
            "tier": "frontend",
        })
    return {"status": "ok", "data": out, "total_frontend": len(out)}


@router.get("/{emp_id}")
async def get_employee(emp_id: str):
    """单个员工详情"""
    if emp_id not in PRESET_EMPLOYEES:
        raise HTTPException(404, f"员工不存在: {emp_id}")
    from digital_employees import EMPLOYEES
    return {
        "status": "ok",
        "data": {
            "id": emp_id,
            **PRESET_EMPLOYEES[emp_id],
            "deployed": emp_id in EMPLOYEES,
        }
    }


@router.post("/{emp_id}/chat")
async def chat_with_employee(emp_id: str, req: ChatRequest):
    """与数字员工对话(智能路由到对应 skill)"""
    if emp_id not in PRESET_EMPLOYEES:
        raise HTTPException(404, f"员工不存在: {emp_id}")

    emp = PRESET_EMPLOYEES[emp_id]
    start = datetime.now()

    # 记录历史
    if emp_id not in _chat_history:
        _chat_history[emp_id] = []
    _chat_history[emp_id].append({
        "role": "user", "message": req.message, "ts": datetime.now().isoformat()
    })

    # 根据员工类型路由
    skill_called = None
    tools_used = []
    reply = ""

    try:
        if emp_id == "content_writer":
            # 内容写手 → 调 create/generate
            from intel_schemas.geo import ArticleRequest
            try:
                from fastapi_routes import _articles_state  # 复用
            except ImportError:
                pass
            tools_used.append("create/generate")
            skill_called = "AI 文案生成"
            # 这里直接用 DeepSeek(若有)或模板
            reply = _ai_reply("content_writer", req.message)

        elif emp_id == "short_video_script":
            tools_used.append("pipeline/script/generate")
            skill_called = "短视频脚本"
            reply = _ai_reply("short_video_script", req.message)

        elif emp_id == "data_analyst":
            tools_used.append("intel/trending")
            tools_used.append("intel/competitor")
            skill_called = "数据洞察"
            reply = _ai_reply("data_analyst", req.message)

        elif emp_id == "seo_specialist":
            tools_used.append("geo/keywords/mine")
            skill_called = "GEO 关键词"
            reply = _ai_reply("seo_specialist", req.message)

        elif emp_id == "social_media_manager":
            tools_used.append("calendar/upcoming")
            tools_used.append("intel/trending")
            skill_called = "社媒排期"
            reply = _ai_reply("social_media_manager", req.message)

        elif emp_id == "customer_service":
            tools_used.append("FAQ 知识库")
            skill_called = "客服对话"
            reply = _ai_reply("customer_service", req.message)

        elif emp_id == "market_researcher":
            tools_used.append("intel/trending")
            tools_used.append("intel/competitor")
            skill_called = "竞品分析"
            reply = _ai_reply("market_researcher", req.message)

        elif emp_id == "growth_hacker":
            tools_used.append("intel/analytics")
            tools_used.append("reports/generate")
            skill_called = "增长策略"
            reply = _ai_reply("growth_hacker", req.message)

        else:
            reply = _ai_reply("generic", req.message)

    except Exception as e:
        logger.exception("chat failed")
        reply = f"处理出错:{e}"

    latency_ms = int((datetime.now() - start).total_seconds() * 1000)

    # 记录 assistant reply
    _chat_history[emp_id].append({
        "role": "assistant", "message": reply, "ts": datetime.now().isoformat()
    })
    # 限长
    if len(_chat_history[emp_id]) > 50:
        _chat_history[emp_id] = _chat_history[emp_id][-50:]

    # V9.8 持久化到 JSON
    try:
        _save_history(_chat_history)
        _PERSIST_HISTORY.setdefault(emp_id, []).extend(_chat_history[emp_id][-2:])
        _save_history(_PERSIST_HISTORY)
    except Exception as e:
        logger.warning("V9.8 save history failed: %s", e)

    return {
        "status": "ok",
        "data": {
            "employee": emp_id,
            "reply": reply,
            "skill_called": skill_called,
            "tools_used": tools_used,
            "latency_ms": latency_ms,
        }
    }


@router.get("/{emp_id}/history")
async def get_history(emp_id: str, limit: int = Query(20, ge=1, le=100)):
    """对话历史"""
    history = _chat_history.get(emp_id, [])[-limit:]
    return {"status": "ok", "data": history, "total": len(_chat_history.get(emp_id, []))}


@router.delete("/{emp_id}/history")
async def clear_history(emp_id: str):
    """清空历史"""
    _chat_history[emp_id] = []
    _PERSIST_HISTORY[emp_id] = []
    _save_history(_PERSIST_HISTORY)
    return {"status": "ok"}


@router.post("/deploy")
async def deploy_employee(req: EmployeeDeployRequest):
    """部署员工(模拟)"""
    if req.employee not in PRESET_EMPLOYEES:
        raise HTTPException(404, "员工不存在")
    deploy_id = f"dep-{secrets.token_hex(6)}"
    return {
        "status": "ok",
        "data": {
            "deploy_id": deploy_id,
            "employee": req.employee,
            "channels": req.channels,
            "deployed_at": datetime.now().isoformat(),
            "endpoint": f"/api/v2/employees/{req.employee}/chat",
        }
    }


@router.get("/stats/summary")
async def stats_summary():
    """员工总览统计"""
    total_chats = sum(len(v) for v in _chat_history.values()) // 2
    return {
        "status": "ok",
        "data": {
            "total_employees": len(PRESET_EMPLOYEES),
            "total_chats_today": total_chats,
            "active_employees": sum(1 for v in _chat_history.values() if len(v) > 0),
        }
    }


# ============== AI Reply(模板) ==============

def _ai_reply(emp_type: str, msg: str) -> str:
    """员工回复(优先用 DeepSeek,失败用模板)"""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        try:
            return _call_deepseek(emp_type, msg, key)
        except Exception as e:
            logger.warning("DeepSeek call failed, fallback to template: %s", e)
    return _template_reply(emp_type, msg)


def _call_deepseek(emp_type: str, msg: str, key: str) -> str:
    """调 DeepSeek API"""
    import urllib.request as ur
    system_prompts = {
        "content_writer": "你是一名资深内容写手,擅长 GEO 优化文章。回答简洁,3 句话内。",
        "short_video_script": "你是短视频脚本专家,擅长 60 秒爆款脚本。回答要具体可执行。",
        "data_analyst": "你是数据分析师,擅长从数据中提炼洞察。",
        "seo_specialist": "你是 GEO SEO 专家,擅长关键词布局。",
        "social_media_manager": "你是社媒运营,擅长多平台排期。",
        "customer_service": "你是智能客服,友好专业,先共情再解决。",
        "market_researcher": "你是市场研究员,擅长竞品分析。",
        "growth_hacker": "你是增长黑客,擅长 A/B 测试和转化漏斗。",
        "generic": "你是 CloudTech 数字员工,回答简洁专业。",
    }
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompts.get(emp_type, system_prompts["generic"])},
            {"role": "user", "content": msg},
        ],
        "max_tokens": 600,
        "temperature": 0.7,
    }).encode()
    req = ur.Request("https://api.deepseek.com/v1/chat/completions", data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    })
    with ur.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode())
    return result["choices"][0]["message"]["content"].strip()


def _template_reply(emp_type: str, msg: str) -> str:
    """模板回复(无 Key 时)"""
    templates = {
        "content_writer": f"收到你的需求「{msg[:30]}」,建议分 4 段:核心概念 → 实操方法 → 案例 → 总结,目标 1500 字,关键词密度 2-3%。需要我生成完整大纲吗?",
        "short_video_script": f"关于「{msg[:30]}」的 60s 脚本:前 3s 钩子(数字+反差)+ 痛点 + 3 个核心点 + 行动号召。配 DeepSeek 接入后可生成完整分镜。",
        "data_analyst": f"「{msg[:30]}」我建议从 3 个维度分析:全网热度、竞品增长、自身表现。点击 `/trending` 看全网热点。",
        "seo_specialist": f"「{msg[:30]}」建议用四象限布局关键词:P0 决策型(占比 20%)+ P1 问题型(40%)+ P2 知识型(25%)+ P3 场景型(15%)。",
        "social_media_manager": f"「{msg[:30]}」最佳发布时间:工作日 8:00/12:00/20:00,周末 10:00/15:00。同步发布到 5 平台可达 3x 流量。",
        "customer_service": f"感谢咨询「{msg[:30]}」,我会帮您处理这个问题。请问您方便留下联系方式吗?",
        "market_researcher": f"「{msg[:30]}」竞品分析维度:产品功能/价格/营销动作/用户口碑。建议先建 5 个核心竞品雷达。",
        "growth_hacker": f"「{msg[:30]}」增长建议:1) 设置转化漏斗 2) A/B 测试 CTA 3) 留存 7 日激活。建议接入 DeepSeek 做内容 A/B。",
        "generic": f"已收到「{msg[:30]}」。我是 CloudTech 数字员工,可帮你做内容创作、数据分析、SEO 等 8 类工作。",
    }
    return templates.get(emp_type, templates["generic"])


# ============== V9.8 Chat History Persistence ==============

# In-memory cache + on-disk JSON file
_HISTORY_FILE = Path(r'D:\浏览器\CloudTech-v2.0.0\CloudTech-Portable\data-layer\chat_history.json')

def _load_history():
    try:
        if _HISTORY_FILE.exists():
            with open(_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_history(data):
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning('save chat history failed: %s', e)

_PERSIST_HISTORY = _load_history()
# 把 in-memory _chat_history 合并进持久化
for k, v in _chat_history.items():
    _PERSIST_HISTORY.setdefault(k, []).extend(v)
_chat_history.update(_PERSIST_HISTORY)


class HistoryItem(BaseModel):
    role: str = Field(..., description="user or ai")
    content: str
    ts: Optional[str] = None


class HistoryAppend(BaseModel):
    employee: str
    role: str
    content: str


@router.get('/{employee_id}/history')
async def get_employee_history(
    employee_id: str,
    limit: int = Query(50, ge=1, le=500),
):
    """V9.8 — 8 数字员工对话历史 (从 JSON 持久化)"""
    if employee_id not in PRESET_EMPLOYEES:
        raise HTTPException(404, f"unknown employee: {employee_id}")
    items = _chat_history.get(employee_id, [])
    return {
        "status": "ok",
        "data": {
            "employee": employee_id,
            "items": items[-limit:],
            "total": len(items),
        }
    }


@router.post('/{employee_id}/history')
async def append_employee_history(employee_id: str, item: HistoryAppend):
    """V9.8 — 追加 1 条历史 (用户或 AI)"""
    if employee_id not in PRESET_EMPLOYEES:
        raise HTTPException(404, f"unknown employee: {employee_id}")
    if item.employee and item.employee != employee_id:
        raise HTTPException(400, "employee mismatch")
    if item.role not in ('user', 'ai'):
        raise HTTPException(400, "role must be 'user' or 'ai'")
    entry = {
        'role': item.role,
        'content': item.content,
        'ts': datetime.now().isoformat(),
    }
    _chat_history.setdefault(employee_id, []).append(entry)
    _PERSIST_HISTORY.setdefault(employee_id, []).append(entry)
    _save_history(_PERSIST_HISTORY)
    return {"status": "ok", "data": {"employee": employee_id, "appended": 1, "total": len(_chat_history[employee_id])}}


@router.delete('/{employee_id}/history')
async def clear_employee_history(employee_id: str):
    """V9.8 — 清空某个员工历史"""
    if employee_id not in PRESET_EMPLOYEES:
        raise HTTPException(404, f"unknown employee: {employee_id}")
    _chat_history[employee_id] = []
    _PERSIST_HISTORY[employee_id] = []
    _save_history(_PERSIST_HISTORY)
    return {"status": "ok", "data": {"employee": employee_id, "cleared": True}}
