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
from fastapi import APIRouter, HTTPException, Body, Query, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from workflows.v4 import (
    V4Orchestrator, RunStatus, OperationRegistry,
    BudgetGate, CostClass, MediaGate, MediaGateError,
    IdempotencyStore, AssetResolver, AssetBindingError,
)
from workflows.v4.contract import validate_definition, validate_inputs, validate_input_cardinality, ContractError
from workflows.v4.paths import FLAGSHIP_PATHS, get_path, list_paths
from workflows.v4.audit_evidence import on_auth
from .auth import auth_required, AuthContext
from .p0_guard import (
    get_owned_run, scoped_idempotency_key, compatible_run_request,
    collect_role_values,
)


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
    改进: 多个关键词匹配时, 计分选最具体的 (更长关键词 + 更专属映射优先)
    """
    utterance_l = req.utterance.lower()

    # 关键词到路径映射 + 优先级 (数字越大越专属)
    KW = [
        ("博主", "WP-BLOGGER-RESEARCH", 3),
        ("主页", "WP-BLOGGER-RESEARCH", 3),
        ("homepage", "WP-BLOGGER-RESEARCH", 3),
        ("仿写", "WP-VIDEO-TRANSCRIBE", 4),
        ("video", "WP-VIDEO-TRANSCRIBE", 2),
        ("图文", "WP-ARTICLE-REWRITE", 4),
        ("article", "WP-ARTICLE-REWRITE", 2),
        ("装修", "WP-RENOVATION-FULL", 4),
        ("全屋", "WP-RENOVATION-FULL", 5),
        ("沙发", "WP-RENOVATION-FULL", 5),
        ("毛坯", "WP-GROWTH-VIDEO", 6),
        ("生长", "WP-GROWTH-VIDEO", 6),
        ("商品", "WP-PRODUCT-MARKETING", 3),
        ("产品", "WP-PRODUCT-MARKETING", 3),
        ("营销", "WP-PRODUCT-MARKETING", 4),
        ("视频", "WP-VIDEO-TRANSCRIBE", 1),  # 最后 (最不专属)
    ]

    scores: Dict[str, int] = {}
    matched_kw: Dict[str, str] = {}
    for kw, path_id, priority in KW:
        if kw in utterance_l:
            scores[path_id] = scores.get(path_id, 0) + priority
            matched_kw[path_id] = kw

    matched_id: Optional[str] = None
    if scores:
        matched_id = max(scores.keys(), key=lambda p: scores[p])

    # 候选: matched_id 排第一, 其余按 scores 排序
    candidates = []
    if matched_id:
        candidates.append({"path_id": matched_id, "match_keyword": matched_kw.get(matched_id), "rank": 1, "score": scores[matched_id]})
    for path_id, defn in FLAGSHIP_PATHS.items():
        if path_id != matched_id:
            s = scores.get(path_id, 0)
            candidates.append({"path_id": path_id, "match_keyword": matched_kw.get(path_id), "rank": 2 + s, "score": s})

    missing: List[str] = []
    if matched_id:
        defn = get_path(matched_id)
        provided = collect_role_values(req.input_refs)
        missing = validate_inputs(defn, provided)

    return ResolveResponse(
        matched_path_id=matched_id,
        candidates=candidates[:6],
        missing_roles=missing,
        reasoning=f"关键词计分匹配 {matched_id or '无'} (scores={scores}); 候选 {len(candidates)} 条",
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
def create_run(req: CreateRunRequest, ctx: AuthContext = Depends(auth_required)):
    """创建 workpath run; 检查路径 + 幂等"""
    tenant_id = ctx.tenant_id
    on_auth("n/a", ctx.tenant_id, ctx.user_id, "create_run")
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
    if req.scope != "tenant":
        raise HTTPException(422, "只允许 tenant scope")
    invalid_inputs = validate_input_cardinality(defn, req.input_bindings)
    if invalid_inputs:
        raise HTTPException(422, {"invalid_inputs": invalid_inputs})
    server_key = scoped_idempotency_key(tenant_id, req.idempotency_key)
    if server_key:
        hit = _orchestrator.idempotency.check(server_key)
        if hit and hit.run_id:
            old_run = get_owned_run(_orchestrator, hit.run_id, tenant_id)
            if not compatible_run_request(old_run, req):
                raise HTTPException(409, "相同幂等键对应不同请求")
            return {"run_id": old_run.run_id, "idempotent_hit": True,
                    "status": old_run.status.value}
    rec = _orchestrator.create_run(
        path_id=req.path_id,
        path_revision=req.revision,
        tenant_id=tenant_id,
        input_bindings=req.input_bindings,
        idempotency_key=server_key,
        project_id=req.project_id,
        conversation_id=req.conversation_id,
        budget_cap_cents=req.budget_cap_cents,
    )
    try:
        _orchestrator.transition(rec.run_id, RunStatus.INPUT_BOUND)
        _orchestrator.transition(rec.run_id, RunStatus.READY)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {
        "run_id": rec.run_id,
        "status": rec.status.value,
        "worker_connected": False,
        "execution_started": False,
        "storage": "VOLATILE_MEMORY",
    }


@router.get("/workpaths/runs")
def list_run_records(
    limit: int = Query(50, ge=1, le=100),
    ctx: AuthContext = Depends(auth_required),
):
    """Return actual in-process task records only, scoped to the authorized tenant."""
    runs = _orchestrator.list_runs(tenant_id=ctx.tenant_id, limit=limit)
    return {
        "items": [rec.to_dict() for rec in runs],
        "returned": len(runs),
        "storage": "VOLATILE_MEMORY",
        "worker_connected": False,
        "production_ready": False,
    }


@router.get("/workpaths/runs/{run_id}")
def get_run(run_id: str, ctx: AuthContext = Depends(auth_required)):
    rec = get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    return rec.to_dict()


@router.post("/workpaths/runs/{run_id}/approve")
def approve_run(run_id: str, req: ApproveRequest,
                ctx: AuthContext = Depends(auth_required)):
    rec = get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    if rec.status != RunStatus.REVIEW_REQUIRED:
        raise HTTPException(409, f"当前状态 {rec.status.value} 不需要审批")
    try:
        _orchestrator.transition(run_id, RunStatus.APPROVED)
    except Exception as e:
        raise HTTPException(400, str(e))
    return {"run_id": run_id, "checkpoint_id": req.checkpoint_id, "approved_budget_cents": req.approved_budget_cents, "status": "approved"}


@router.post("/workpaths/runs/{run_id}/resume")
def resume_run(run_id: str, req: ResumeRequest,
               ctx: AuthContext = Depends(auth_required)):
    """Actual worker requeue is not wired; never report a false success."""
    get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    raise HTTPException(501, "节点恢复未接入实际执行器；未重新执行或扣费")


@router.get("/workpaths/runs/{run_id}/export")
def export_run(run_id: str, ctx: AuthContext = Depends(auth_required)):
    rec = get_owned_run(_orchestrator, run_id, ctx.tenant_id)
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
def resolve_alias(req: ResolveAliasRequest, ctx: AuthContext = Depends(auth_required)):
    """图 1/图 6 = alias → asset_id+version_id"""
    try:
        binding = _resolver.resolve(
            tenant_id=ctx.tenant_id,
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
def bind_alias(req: BindAliasRequest, ctx: AuthContext = Depends(auth_required)):
    """Bind only into the authenticated tenant."""
    if req.tenant_id != ctx.tenant_id:
        raise HTTPException(403, "素材绑定租户不匹配")
    b = _resolver.bind(
        tenant_id=ctx.tenant_id,
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
def new_asset_version(asset_id: str, req: NewVersionRequest, ctx: AuthContext = Depends(auth_required)):
    """同一 alias 创建新版本 (沙发替换等) — parent_version_id 必须匹配"""
    # 校验 ctx.tenant_id == req.tenant_id (防越权)
    if req.tenant_id != ctx.tenant_id:
        raise HTTPException(403, f"[AUTH-006] tenant 越权: ctx={ctx.tenant_id} req={req.tenant_id}")
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
        "worker_connected": False,
        "run_storage": "VOLATILE_MEMORY",
        "production_ready": False,
    }
