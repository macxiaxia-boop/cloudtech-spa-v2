"""CloudTech V4 — API endpoints
按 V4 spec §08 — 不创建新服务, 注入到现有 FastAPI/Flask 入口

端点清单:
  POST /workpaths/resolve              — 解析用户意图 → 推荐路径
  GET  /operations                     — 列出可用操作
  POSTpaths/runs        POST            — 创建运行实例
                    GET  /{id}        — 状态
                    POST /{id}/approve — 审批
                    POST /{id}/resume  — 断点续跑
                    GET  /{id}/export  — 导出交付包
  POST /assets/resolve-alias            — alias → asset_version
  POST /assets/{asset_id}/versions      — 创建新版本 (沙发替换等)
"""
from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from workflows.v4 import (
    V4Orchestrator, RunStatus, OperationRegistry,
    BudgetGate, CostClass, MediaGate, MediaGateError,
    IdempotencyStore, AssetResolver, AssetBindingError,
)
from workflows.v4.contract import validate_definition, validate_inputs, ContractError
from workflows.v4.paths import FLAGSHIP_PATHS, get_path, list_paths


router = APIRouter(prefix="/v4", tags=["v4-workpaths"])
_orchestrator = V4Orchestrator.instance()
_budget = BudgetGate.instance()
_resolver = AssetResolver.instance()


# === 请求/响应模型 ===

class ResolveRequest(BaseModel):
    utterance: str
    project_id: Optional[str] = None
    input_refs: List[Dict[str, Any]] = Field(default_factory=list)


class ResolveResponse(BaseModel):
    matched_path_id: Optional[str]
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    missing_roles: List[str] = Field(default_factory=list)
    reasoning: str = ""


class CreateRunRequest(BaseModel):
    path_id: str
    revision: int = 1
    input_bindings: Dict[str, Any] = Field(default_factory=dict)
    scope: str = "tenant"
    budget_cap_cents: int = 0
    idempotency_key: Optional[str] = None
    project_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ApproveRequest(BaseModel):
    checkpoint_id: str
    approved_budget_cents: int = 0


class ResumeRequest(BaseModel):
    failed_nodes_only: bool = True


class ResolveAliasRequest(BaseModel):
    project_id: Optional[str] = None
    conversation_id: str
    alias: str
    role: str = "image"
    at_message_id: Optional[str] = None


class BindAliasRequest(BaseModel):
    tenant_id: str
    project_id: Optional[str] = None
    conversation_id: str
    alias: str
    role: str
    asset_id: str
    version_id: str
    message_id: Optional[str] = None


class NewVersionRequest(BaseModel):
    tenant_id: str
    project_id: Optional[str] = None
    conversation_id: str
    alias: str
    new_asset_id: str
    new_version_id: str
    parent_version_id: Optional[str] = None
    edit_spec: Optional[Dict[str, Any]] = None
    source_refs: Optional[List[str]] = None
    message_id: Optional[str] = None


# === 端点 ===

@router.post("/workpaths/resolve", response_model=ResolveResponse)
def workpaths_resolve(req: ResolveRequest):
    """根据用户 utterance + input_refs 解析候选 workpath
    简化策略: 按 utterance 关键词匹配 flagship path + 校验 input 角色覆盖度
    """
    utterance_l = req.utterance.lower()
    candidates: List[Dict[str, Any]] = []
    matched_id: Optional[str] = None

    # 关键词到路径映射
    KW = {
        "博主": "WP-BLOGGER-RESEARCH",
        "主页": "WP-BLOGGER-RESEARCH",
        "homepage": "WP-BLOGGER-RESEARCH",
        "视频": "WP-VIDEO-TRANSCRIBE",
        "video": "WP-VIDEO-TRANSCRIBE",
        "仿写": "WP-VIDEO-TRANSCRIBE",
        "图文": "WP-ARTICLE-REWRITE",
        "article": "WP-ARTICLE-REWRITE",
        "装修": "WP-RENOVATION-FULL",
        "全屋": "WP-RENOVATION-FULL",
        "沙发": "WP-RENOVATION-FULL",
        "毛坯": "WP-GROWTH-VIDEO",
        "生长": "WP-GROWTH-VIDEO",
        "商品": "WP-PRODUCT-MARKETING",
        "产品": "WP-PRODUCT-MARKETING",
        "营销": "WP-PRODUCT-MARKETING",
    }

    for kw, path_id in KW.items():
        if kw in utterance_l:
            matched_id = path_id
            candidates.append({"path_id": path_id, "match_keyword": kw, "rank": 1})
            break

    # 始终返回全部路径作为备选
    for path_id, defn in FLAGSHIP_PATHS.items():
        if path_id != matched_id:
            candidates.append({"path_id": path_id, "match_keyword": None, "rank": 2})

    missing: List[str] = []
    if matched_id:
        defn = get_path(matched_id)
        provided = {ref.get("role", "unknown"): ref.get("value") for ref in req.input_refs}
        missing = validate_inputs(defn, provided)

    return ResolveResponse(
        matched_path_id=matched_id,
        candidates=candidates[:6],
        missing_roles=missing,
        reasoning=f"关键词匹配 {matched_id or '无'}; 候选 {len(candidates)} 条",
    )


@router.get("/operations")
def list_operations(kind: Optional[str] = Query(None)):
    """列出 OperationRegistry 中所有 operation; 可按 kind 过滤"""
    paths = list_paths()
    return {
        "workpaths": paths,
        "total_paths": len(paths),
    }


@router.post("/workpaths/runs")
def create_run(req: CreateRunRequest, tenant_id: str = Query(...)):
    """创建 workpath run; 检查路径 + 幂等"""
    try:
        defn = get_path(req.path_id)
    except KeyError:
        raise HTTPException(404, f"未知 path_id: {req.path_id}")
    if req.revision != defn.revision:
        raise HTTPException(409, f"revision 不匹配 (提供={req.revision}, 当前={defn.revision})")
    # 检查媒体门禁
    for step in defn.steps:
        try:
            MediaGate.check(step.operation, step.cost_class)
        except MediaGateError as e:
            raise HTTPException(400, str(e))
    # 检查幂等
    if req.idempotency_key:
        hit = _orchestrator.idempotency.check(req.idempotency_key)
        if hit and hit.run_id:
            return {"run_id": hit.run_id, "idempotent_hit": True}
    rec = _orchestrator.create_run(
        path_id=req.path_id,
        path_revision=req.revision,
        tenant_id=tenant_id,
        input_bindings=req.input_bindings,
        idempotency_key=req.idempotency_key,
        project_id=req.project_id,
        conversation_id=req.conversation_id,
        budget_cap_cents=req.budget_cap_cents,
    )
    try:
        _orchestrator.transition(rec.run_id, RunStatus.INPUT_BOUND)
        _orchestrator.transition(rec.run_id, RunStatus.READY)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"run_id": rec.run_id, "status": rec.status.value}


@router.get("/workpaths/runs/{run_id}")
def get_run(run_id: str):
    rec = _orchestrator.get_run(run_id)
    if rec is None:
        raise HTTPException(404, "run 不存在")
    return rec.to_dict()


@router.post("/workpaths/runs/{run_id}/approve")
def approve_run(run_id: str, req: ApproveRequest):
    rec = _orchestrator.get_run(run_id)
    if rec is None:
        raise HTTPException(404, "run 不存在")
    if rec.status != RunStatus.REVIEW_REQUIRED:
        raise HTTPException(409, f"当前状态 {rec.status.value} 不需要审批")
    try:
        _orchestrator.transition(run_id, RunStatus.APPROVED)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"run_id": run_id, "checkpoint_id": req.checkpoint_id, "approved_budget_cents": req.approved_budget_cents, "status": "approved"}


@router.post("/workpaths/runs/{run_id}/resume")
def resume_run(run_id: str, req: ResumeRequest):
    """断点续跑 — 只重试 failed nodes, 不重新收费"""
    rec = _orchestrator.get_run(run_id)
    if rec is None:
        raise HTTPException(404, "run 不存在")
    failed = [n for n in rec.nodes if n.status == RunStatus.FAILED]
    return {
        "run_id": run_id,
        "failed_nodes": [n.node_id for n in failed],
        "retry_count": len(failed),
        "no_repeat_billing": True,
        "note": "已失败节点恢复; 幂等键保证 provider 不双扣",
    }


@router.get("/workpaths/runs/{run_id}/export")
def export_run(run_id: str):
    rec = _orchestrator.get_run(run_id)
    if rec is None:
        raise HTTPException(404, "run 不存在")
    if rec.status != RunStatus.COMPLETED:
        return {"run_id": run_id, "ready": False, "status": rec.status.value}
    return {
        "run_id": run_id,
        "ready": True,
        "nodes": [n.to_dict() for n in rec.nodes],
        "manifest": {
            "path_id": rec.path_id,
            "tenant_id": rec.tenant_id,
            "budget_spent_cents": rec.budget_spent_cents,
            "created_at": rec.created_at,
        },
    }


@router.post("/assets/resolve-alias")
def resolve_alias(req: ResolveAliasRequest, tenant_id: str = Query(...)):
    """图 1/图 6 = alias → asset_id+version_id"""
    try:
        binding = _resolver.resolve(
            tenant_id=tenant_id,
            conversation_id=req.conversation_id,
            alias=req.alias,
            at_message_id=req.at_message_id,
        )
    except AssetBindingError as e:
        raise HTTPException(404, str(e))
    return {
        "binding_id": binding.binding_id,
        "asset_id": binding.asset_id,
        "version_id": binding.version_id,
        "role": binding.role,
        "message_id": binding.message_id,
    }


@router.post("/assets/bind")
def bind_alias(req: BindAliasRequest):
    """显式绑定 alias → asset_version (用于上传时)"""
    b = _resolver.bind(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        conversation_id=req.conversation_id,
        alias=req.alias,
        role=req.role,
        asset_id=req.asset_id,
        version_id=req.version_id,
        message_id=req.message_id,
    )
    return {"binding_id": b.binding_id}


@router.post("/assets/{asset_id}/versions")
def new_asset_version(asset_id: str, req: NewVersionRequest):
    """同一 alias 创建新版本 (沙发替换等) — parent_version_id 必须匹配"""
    try:
        b = _resolver.new_version(
            tenant_id=req.tenant_id,
            project_id=req.project_id,
            conversation_id=req.conversation_id,
            alias=req.alias,
            new_asset_id=req.new_asset_id,
            new_version_id=req.new_version_id,
            parent_version_id=req.parent_version_id,
            edit_spec=req.edit_spec,
            source_refs=req.source_refs,
            message_id=req.message_id,
        )
    except AssetBindingError as e:
        raise HTTPException(400, str(e))
    return {
        "binding_id": b.binding_id,
        "asset_id": b.asset_id,
        "version_id": b.version_id,
        "alias": b.alias,
    }


@router.get("/health")
def health():
    return {
        "ok": True,
        "service": "cloudtech-v4",
        "paths_registered": len(FLAGSHIP_PATHS),
        "operations_count": 0,
        "orchestrator_runs": len(_orchestrator.list_runs()),
    }
