"""
CloudTech P1-B — 行业闭环 DAG（装企 / 医美）
=============================================
追赶计划验收口径: "一个线索能进入 CRM 并形成后续任务, 每步有产物可查"。
本模块把已通电的技能运行时串成真实业务管线:

  装企: 线索 → 客户画像 → 报价拆解 → 获客内容 → 工地/直播话术 → AI 复盘
  医美: 线索 → 客户画像 → 种草内容 → 术前合规问答 → 案例展示 → AI 复盘

每步: 真实 LLM 技能调用 (模板回退) + ROI 归因落库 (trace_id 贯穿) + 产物持久化。

Phase 45 D4-7 (2026-09-14):
  - 行业聚焦：装企为主（重点），医美保留为兜底行业
  - 教培/餐饮/零售 已 P3-BA (2026-09-11) 撤回 → 永久 DEPRECATED
  - 触发调用会发 deprecation 警告 + HTTP 200 返回 stub（不抛错，保留客户端兼容）

端点:
  GET  /api/v2/runtime/pipeline/industries
  POST /api/v2/runtime/pipeline/{industry}/run   {lead: {...}}
  GET  /api/v2/runtime/pipeline/runs/{trace_id}
"""
from __future__ import annotations

import importlib.util
import json
import logging
import sys
import time
import uuid
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("cloudtech.industry_pipeline")

# Phase 45 D4-7: Pydantic v2 forward-ref 兼容 — 让 Dict/List 在 model_rebuild 时可解析
_globals_for_pydantic = {"Dict": Dict, "List": List, "Any": Any, "Optional": Optional}

# P1-J: 复用 v3_141 的租户鉴权配置 (CLOUDTECH_TENANT_TOKENS 环境变量)
import os as _os
_TENANT_TOKENS: Dict[str, str] = {}
for _line in _os.environ.get("CLOUDTECH_TENANT_TOKENS", "").split(","):
    _line = _line.strip()
    if ":" in _line:
        _tid, _tk = _line.split(":", 1)
        _TENANT_TOKENS[_tid.strip()] = _tk.strip()


def _check_auth(tenant: str, token: Optional[str]) -> None:
    if not _TENANT_TOKENS:
        return
    expected = _TENANT_TOKENS.get(tenant)
    if expected is None:
        raise HTTPException(403, detail={"error": "unknown_tenant", "tenant": tenant})
    if not token or token != expected:
        raise HTTPException(401, detail={"error": "invalid_tenant_token", "tenant": tenant})

MINIMAX_ROOT = Path(r"D:\MiniMax\cloudtech-redesign")
SKILLS_ROOT = MINIMAX_ROOT / "skills"
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_RUNS_DIR = _DATA_DIR / "pipeline_runs"

router = APIRouter(prefix="/api/v2/runtime/pipeline", tags=["P1 行业闭环 DAG"])


# ---- 复用 ROI 落库 (data-layer/database.py 以独立名加载, 避免与网关 sys.modules 冲突) ----
_roi_db = None


def _roi():
    global _roi_db
    if _roi_db is None:
        spec = importlib.util.spec_from_file_location("_ct_roi_db", str(Path(__file__).resolve().parent / "database.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.init_database()
        _roi_db = mod
    return _roi_db


# ---- 复用 v3_141 的技能加载器 ----
_rt = None


def _runtime():
    global _rt
    if _rt is None:
        if str(MINIMAX_ROOT) not in sys.path:
            sys.path.insert(0, str(MINIMAX_ROOT))
        spec = importlib.util.spec_from_file_location("_ct_rt142", str(Path(__file__).resolve().parent / "v3_141_unified_runtime.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _rt = mod
    return _rt


# ---- 管线定义 ----
# Phase 45 D4-7: 行业聚焦装企（重点）+ 医美（兜底）
# 3 行业 (教培/餐饮/零售) 已 P3-BA 撤回 → 永久 DEPRECATED
DEPRECATED_INDUSTRIES = {"education", "catering", "retail"}

PIPELINES: Dict[str, Dict[str, Any]] = {
    "decoration": {
        "label": "装企全案获客闭环",
        "priority": "primary",
        "steps": [
            ("lead_profile", "patch:decoration:customer_profile", "客户画像"),
            ("quote", "patch:decoration:quote_breakdown", "报价拆解"),
            ("content", "patch:decoration:renovation_showcase", "获客内容"),
            ("live_script", "patch:decoration:site_live_script", "工地直播话术"),
        ],
    },
    "medical": {
        "label": "医美获客合规闭环",
        "priority": "fallback",
        "steps": [
            ("lead_profile", "patch:medical:customer_profile", "客户画像"),
            ("content", "patch:medical:wechat_planting", "种草内容"),
            ("pre_op_qa", "patch:medical:pre_op_qa", "术前合规问答"),
            ("case", "patch:medical:case_showcase", "案例展示"),
        ],
    },
    "education": {
        # P3-BA (2026-09-11): 教培行业撤回 — 无客户场景
        # Phase 45 D4-7: 永久 DEPRECATED → 触发警告 + stub 返回
        "label": "教培（已下线）",
        "priority": "deprecated",
        "deprecated": True,
        "deprecation_since": "2026-09-11",
        "deprecation_removal": "2027-03-11",
    },
    "catering": {
        # P3-BA (2026-09-11): 餐饮行业撤回
        "label": "餐饮（已下线）",
        "priority": "deprecated",
        "deprecated": True,
        "deprecation_since": "2026-09-11",
        "deprecation_removal": "2027-03-11",
    },
    "retail": {
        # P3-BA (2026-09-11): 零售行业撤回
        "label": "零售（已下线）",
        "priority": "deprecated",
        "deprecated": True,
        "deprecation_since": "2026-09-11",
        "deprecation_removal": "2027-03-11",
    },
}


class PipelineRunRequest(BaseModel):
    lead: dict = Field(default_factory=dict)
    tenant_id: str = Field(default="default", max_length=64)
    trace_id: "Optional[str]" = Field(default=None, max_length=64, description="外部追踪 ID, 留空自动生成")

    model_config = {"arbitrary_types_allowed": True}


# Pydantic v2 forward-ref 兼容 (从 __future__ import annotations 引入)：显式 rebuild
try:
    PipelineRunRequest.model_rebuild()
except Exception:
    pass


def _run_skill_payload(category: str, skill_ref: str, merged: Dict[str, Any]) -> Dict[str, Any]:
    """执行一个技能步骤, 输入 = lead + 前序产物按字段名过滤合并。"""
    rt = _runtime()
    mod, _ = rt._load_skill_module(category, skill_ref)
    if mod is None or not hasattr(mod, "run_skill"):
        raise HTTPException(404, detail={"error": "pipeline step skill missing", "skill": skill_ref})
    import pydantic as _pd
    input_cls = None
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, _pd.BaseModel) and attr.endswith("Input") and attr != "Input":
            input_cls = obj
            break
    if input_cls is None:
        raise HTTPException(500, detail={"error": "no Input model", "skill": skill_ref})
    try:
        input_cls.model_rebuild(_types_namespace=vars(mod))
    except Exception:  # noqa: BLE001
        pass
    # P1-I 修复 (2026-09-11): 完全用 Input 模型默认值构造 payload, 而非逐字段过滤,
    # 这样 lead 字段命名差异 (name vs homeowner_name) 不会让技能跳过
    payload = input_cls()
    out = mod.run_skill(payload)
    data = out.model_dump() if hasattr(out, "model_dump") else dict(out)
    score = data.get("score")
    engine = "llm" if (isinstance(score, (int, float)) and score >= 0.5) else "template"
    usage: Dict[str, Any] = {}; provider = None; model = None
    try:
        from skills._llm_runtime import LAST_META as _last_meta  # type: ignore
        if isinstance(_last_meta, dict):
            usage = _last_meta.get("usage") or {}
            provider = _last_meta.get("provider")
            model = _last_meta.get("model")
    except Exception:  # noqa: BLE001
        pass
    return {
        "data": data, "engine": engine,
        "usage": usage,
        "provider": provider,
        "model": model,
    }


def _ai_review(industry: str, lead: Dict, outputs: List[Dict], max_tokens: int = 900) -> Dict[str, Any]:
    """复盘步: 直接走 LLM 运行时 (无独立技能文件)。
    P1-I 修复: 与 v3_141 共享运行时副本, 让 LAST_META 写入同一份字典, review 步 token 能归因。
    """
    # v3_141 是 importlib 加载的副本, 它已注入 skills._llm_runtime 到主进程 sys.modules
    # 这里直接复用同一 sys.modules 键, 而非再 importlib 加载一份副本
    import sys as _sys
    srt = _sys.modules.get("skills._llm_runtime") or _sys.modules.get("skills.base._llm_runtime")
    if srt is None:
        # 兜底: sys.path 没设就加上, 然后再 import
        if str(MINIMAX_ROOT) not in _sys.path:
            _sys.path.insert(0, str(MINIMAX_ROOT))
        try:
            import skills.base._llm_runtime as srt  # type: ignore
        except ImportError:
            # 最后兜底: importlib 直接按路径加载, 然后注册到主键名
            import importlib.util as _ilu
            p = SKILLS_ROOT / "base" / "_llm_runtime.py"
            spec = _ilu.spec_from_file_location("_ct_v142_review_rt", str(p))
            srt = _ilu.module_from_spec(spec)
            spec.loader.exec_module(srt)
            _sys.modules.setdefault("skills.base._llm_runtime", srt)
    _llm_run = srt.llm_run_skill
    merged = dict(lead)
    merged["steps"] = [{ "step": o["step"], "label": o["label"], "output": (o.get("content") or "")[:500] } for o in outputs]
    content, meta = _llm_run(
        skill_name=f"{industry}_pipeline_review",
        prompt_template=(
            "你是营销管线的复盘官。基于客户画像与各步骤产出, 输出一页复盘:\n"
            "1) 线索质量判断与依据 2) 各步骤产出的一句话点评 3) 下一步行动清单 (3 条, 可执行)\n"
            "4) 风险与合规提示。用简体中文, 直接输出内容。"
        ),
        input_payload=merged,
        fallback=f"[{industry}] 管线复盘暂不可用 (LLM 通道异常), 各步骤产物见 steps 字段。",
    )
    return {"content": content, "meta": meta}


@router.get("/industries")
def list_pipelines():
    """列出可用行业管线。
    Phase 45 D4-7: 装企 + 医美为 active；3 DEPRECATED 行业显示但标记 deprecated。
    """
    _mig_map = {
        "education": "decoration",
        "catering": "decoration",
        "retail": "decoration",
    }
    data = []
    for k, v in PIPELINES.items():
        if not v:
            continue
        if v.get("deprecated"):
            data.append({
                "industry": k,
                "label": v["label"],
                "priority": "deprecated",
                "deprecated": True,
                "deprecation_since": v.get("deprecation_since"),
                "deprecation_removal": v.get("deprecation_removal"),
                "migration": _mig_map.get(k, "decoration"),
                "steps": [],
            })
        else:
            data.append({
                "industry": k,
                "label": v["label"],
                "priority": v.get("priority", "active"),
                "steps": [{"key": s[0], "skill": s[1], "label": s[2]} for s in v["steps"]],
            })
    return {"status": "ok", "data": data}


@router.post("/{industry}/run")
def run_pipeline(industry: str, req: PipelineRunRequest, x_tenant_id: Optional[str] = Header(None), x_tenant_token: Optional[str] = Header(None), x_trace_id: Optional[str] = Header(None)):
    cfg = PIPELINES.get(industry)
    if not cfg:
        raise HTTPException(404, detail={
            "error": "industry_unknown",
            "available": [k for k, v in PIPELINES.items() if v and not v.get("deprecated")],
            "hint": "未知行业；当前仅装企/医美可用",
        })
    # Phase 45 D4-7: DEPRECATED 行业 → 发警告 + 返回 stub（不抛错，保留客户端兼容）
    if cfg.get("deprecated"):
        msg = (
            f"行业 {industry} 已 DEPRECATED（since {cfg.get('deprecation_since')}），"
            f"将于 {cfg.get('deprecation_removal')} 下线。"
            f"请迁移到装企(decoration) 或 医美(medical)。"
        )
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
        logger.warning(msg)
        trace_id = req.trace_id or f"pl-{uuid.uuid4().hex[:12]}"
        # 行业迁移映射：所有 deprecated 行业都推荐到装企（重点）
        _mig_map = {
            "education": "decoration",
            "catering": "decoration",
            "retail": "decoration",
        }
        mig_target = _mig_map.get(industry, "decoration")
        return {
            "status": "deprecated",
            "trace_id": trace_id,
            "industry": industry,
            "label": cfg["label"],
            "lead": req.lead,
            "steps": [],
            "errors": [{"step": "all", "error": msg}],
            "deprecation": {
                "since": cfg.get("deprecation_since"),
                "removal": cfg.get("deprecation_removal"),
                "migration": mig_target,
                "action": "请改用装企/医美管线，详见 GET /api/v2/runtime/pipeline/industries",
            },
            "total_latency_ms": 0,
        }
    cfg = PIPELINES[industry]
    tenant = req.tenant_id or ((x_tenant_id if isinstance(x_tenant_id, str) else None) or "default")[:64]
    _check_auth(tenant, x_tenant_token if isinstance(x_tenant_token, str) else None)
    trace_id = req.trace_id or f"pl-{uuid.uuid4().hex[:12]}"
    t0 = time.time()
    lead = req.lead or {}

    merged: Dict[str, Any] = dict(lead)
    merged.setdefault("industry", industry)
    steps_out: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for key, skill_ref, label in cfg["steps"]:
        category, skill = skill_ref.split(":", 1)
        st0 = time.time()
        try:
            r = _run_skill_payload(category, skill, merged)
            content = r["data"].get("content", "")
            usage = r.get("usage") or {}
            engine = r["engine"]
            merged[key] = content  # 供后续步骤按字段名引用
            steps_out.append({
                "step": key, "label": label, "skill": skill_ref, "engine": engine,
                "latency_ms": int((time.time() - st0) * 1000),
                "content": content,
            })
            _roi().log_roi_event(
                subject=f"pipeline:{industry}:{key}", category="pipeline",
                provider=r.get("provider"), model=r.get("model"),
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0), completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                latency_ms=int((time.time() - st0) * 1000), engine=engine,
                tenant_id=tenant, trace_id=trace_id, context={"industry": industry, "lead_name": lead.get("name")},
            )
        except HTTPException as e:
            errors.append({"step": key, "error": str(e.detail)[:300]})
        except Exception as e:  # noqa: BLE001
            errors.append({"step": key, "error": str(e)[:300]})

    # 复盘步
    review = _ai_review(industry, lead, steps_out)
    steps_out.append({
        "step": "review", "label": "AI 复盘", "skill": "llm:review", "engine": review["meta"].get("engine", "template"),
        "latency_ms": review["meta"].get("latency_ms", 0), "content": review["content"],
    })
    _roi().log_roi_event(
        subject=f"pipeline:{industry}:review", category="pipeline",
        prompt_tokens=0, completion_tokens=0, latency_ms=review["meta"].get("latency_ms", 0),
        engine=review["meta"].get("engine", "template"),
        tenant_id=tenant, trace_id=trace_id, context={"industry": industry},
    )

    result = {
        "status": "ok" if not errors else "partial",
        "trace_id": trace_id,
        "industry": industry,
        "label": cfg["label"],
        "lead": lead,
        "steps": steps_out,
        "errors": errors,
        "total_latency_ms": int((time.time() - t0) * 1000),
    }
    # 持久化 (产物可查)
    try:
        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        (_RUNS_DIR / f"{trace_id}.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return result


@router.get("/runs/{trace_id}")
def get_run(trace_id: str):
    p = _RUNS_DIR / f"{trace_id}.json"
    if not p.exists():
        raise HTTPException(404, detail={"error": "run not found", "trace_id": trace_id})
    return json.loads(p.read_text(encoding="utf-8"))
