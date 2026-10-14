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
import hashlib
from workflows.v4.orchestrator import NodeRunRecord, RunStatusError
from workflows.v4.node_kinds import NodeKind

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


def _active_local_workers() -> int:
    store = getattr(_orchestrator, "_store", None)
    if store is None or getattr(store, "kind", "") != "SQLITE_LOCAL_DURABLE":
        return 0
    from workflows.v4.local_job_queue import LocalJobQueue
    return LocalJobQueue(store).active_workers()


# === 请求/响应模型 ===

class SuppliedArticleRequest(BaseModel):
    html: str = Field(min_length=1, max_length=1_800_000)
    source_url: str = Field(default="", max_length=2048)


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

@router.post("/article/extract-html")
def extract_supplied_article(
    req: SuppliedArticleRequest,
    ctx: AuthContext = Depends(auth_required),
):
    """Extract only caller-supplied HTML, no web fetch and no invented article."""
    from adapters.article.article_parser import parse_html
    try:
        result = parse_html(req.html, source_url=req.source_url)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {
        **result,
        "tenant_id": ctx.tenant_id,
        "saved": False,
        "provider_called": False,
        "permission_status": "rights_unknown_need_user_confirm",
    }


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


@router.get("/workpaths/capabilities")
def workpath_capabilities():
    """Read-only report, NOT a live provider availability claim."""
    from workflows.v4.capability_preflight import inspect_all_paths
    return inspect_all_paths()


@router.get("/workpaths/{path_id}/preflight")
def workpath_preflight(path_id: str):
    from workflows.v4.capability_preflight import inspect_path
    try:
        return inspect_path(path_id)
    except KeyError:
        raise HTTPException(404, f"unknown workpath: {path_id}") from None


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
    try:
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
    except Exception as exc:
        # SQLite unique idempotency conflicts are not 500s or new runs.
        if "different request" in str(exc):
            raise HTTPException(409, "相同幂等键对应不同请求") from exc
        raise HTTPException(503, "持久化任务存储暂不可用") from exc
    if rec.status != RunStatus.PLANNED:
        if not compatible_run_request(rec, req):
            raise HTTPException(409, "相同幂等键对应不同请求")
        return {
            "run_id": rec.run_id,
            "status": rec.status.value,
            "idempotent_hit": True,
            "worker_connected": _active_local_workers() > 0,
            "execution_started": False,
            "storage": _orchestrator.storage_kind,
        }
    # Multiple clients may POST the same idempotency key simultaneously.
    # Converge on READY rather than wrongly returning 400 when another
    # request has already completed one of the state transitions.
    observed = _orchestrator.get_run(rec.run_id)
    for before, after in (
        (RunStatus.PLANNED, RunStatus.INPUT_BOUND),
        (RunStatus.INPUT_BOUND, RunStatus.READY),
    ):
        if observed is not None and observed.status == before:
            try:
                _orchestrator.transition(rec.run_id, after)
            except RunStatusError:
                # A racing same-key caller may have moved state already;
                # re-read authoritative storage instead of claiming success.
                pass
        observed = _orchestrator.get_run(rec.run_id)
    if observed is None or observed.status not in (RunStatus.READY,):
        raise HTTPException(
            503, "任务创建状态尚未可靠收口；使用相同幂等键安全重试"
        )
    saved = observed
    return {
        "run_id": rec.run_id,
        "status": saved.status.value if saved else "UNKNOWN",
        "worker_connected": _active_local_workers() > 0,
        "execution_started": False,
        "storage": _orchestrator.storage_kind,
    }


@router.get("/workpaths/local-outputs")
def list_local_output_catalog(
    limit: int = Query(50, ge=1, le=100),
    ctx: AuthContext = Depends(auth_required),
):
    """Only persisted, receipt-verified metadata from the caller's tenant."""
    store = getattr(_orchestrator, "_store", None)
    if store is None or getattr(store, "kind", "") != "SQLITE_LOCAL_DURABLE":
        raise HTTPException(503, "当前没有可验证的持久化成果目录")
    from workflows.v4.local_output_projector import LocalOutputProjector
    projector = LocalOutputProjector(store)
    items = projector.list_for_tenant(ctx.tenant_id, limit=limit)
    return {
        "items": items, "returned": len(items),
        "source": "verified_local_outbox_catalog",
        "raw_customer_content_in_response": False,
        "production_ready": False,
    }


@router.get("/workpaths/local-outputs/{run_id}")
def get_local_output_by_run(
    run_id: str,
    ctx: AuthContext = Depends(auth_required),
):
    """Read a single receipt-verified output, never unauthenticated raw content."""
    get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    store = getattr(_orchestrator, "_store", None)
    if store is None or getattr(store, "kind", "") != "SQLITE_LOCAL_DURABLE":
        raise HTTPException(503, "当前没有可验证的持久化成果目录")
    from workflows.v4.local_output_projector import LocalOutputProjector
    item = LocalOutputProjector(store).get_for_tenant_run(ctx.tenant_id, run_id)
    if item is None:
        raise HTTPException(404, "该租户任务尚无经核验并 ACK 的成果")
    return {
        "item": item,
        "source": "verified_local_outbox_catalog",
        "raw_customer_content_in_response": False,
        "production_ready": False,
    }


@router.get("/workpaths/runs")
def list_run_records(
    limit: int = Query(50, ge=1, le=100),
    ctx: AuthContext = Depends(auth_required),
):
    """Return tenant-scoped actual records from configured storage."""
    runs = _orchestrator.list_runs(tenant_id=ctx.tenant_id, limit=limit)
    return {
        "items": [rec.to_dict() for rec in runs],
        "returned": len(runs),
        "storage": _orchestrator.storage_kind,
        "worker_connected": _active_local_workers() > 0,
        "production_ready": False,
        "active_local_workers": _active_local_workers(),
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


@router.post("/workpaths/runs/{run_id}/enqueue-local")
def enqueue_local_workpath(run_id: str, ctx: AuthContext = Depends(auth_required)):
    """Authorize enqueue only. Actual execution is a separate local worker."""
    get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    store = getattr(_orchestrator, "_store", None)
    if store is None or getattr(store, "kind", "") != "SQLITE_LOCAL_DURABLE":
        raise HTTPException(503, "本地任务队列必须先配置单机 SQLite 事务存储")
    from workflows.v4.local_job_queue import LocalJobQueue
    from workflows.v4.sqlite_run_store import RunStoreError
    try:
        queued = LocalJobQueue(store).enqueue(run_id, ctx.tenant_id)
    except RunStoreError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {
        **queued, "queued_only": True, "worker_invoked": False,
        "storage": "SQLITE_LOCAL_DURABLE",
        "provider_called": False,
    }


@router.get("/workpaths/runs/{run_id}/local-queue")
def local_queue_status(run_id: str, ctx: AuthContext = Depends(auth_required)):
    """Tenant-safe view of a real queue row; never assume a live worker."""
    get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    store = getattr(_orchestrator, "_store", None)
    if store is None or getattr(store, "kind", "") != "SQLITE_LOCAL_DURABLE":
        raise HTTPException(503, "当前没有可查询的持久化本地任务队列")
    from workflows.v4.local_job_queue import LocalJobQueue
    state = LocalJobQueue(store).get_state(run_id, ctx.tenant_id)
    if state is None:
        raise HTTPException(404, "该任务没有入队记录")
    return {"run_id": run_id, **state, "worker_connected": _active_local_workers() > 0}


@router.post("/workpaths/runs/{run_id}/execute-local")
def execute_local_workpath(run_id: str, ctx: AuthContext = Depends(auth_required)):
    """Execute the ONE safe, deterministic HTML extraction workpath.

    This is synchronous LOCAL processing only, not an LLM, RPA, billing
    worker, scheduler or general DAG executor. Database commits are handled
    by the existing V4 orchestrator when staged SQLite is enabled.
    """
    rec = get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    if rec.path_id != "WP-LOCAL-ARTICLE-EXTRACT":
        raise HTTPException(422, "该路径尚无可安全执行的本地 Worker")
    if rec.status == RunStatus.COMPLETED:
        return {
            "run_id": run_id, "status": rec.status.value,
            "idempotent_hit": True, "worker_type": "SYNCHRONOUS_LOCAL_ONLY",
            "nodes": [n.to_dict() for n in rec.nodes],
        }
    if rec.status != RunStatus.READY:
        raise HTTPException(409, "任务非 READY；需人工核对状态，不得自动重复执行")

    html = rec.input_bindings.get("html")
    if not isinstance(html, str) or not html.strip():
        raise HTTPException(422, "没有提供用户授权的 HTML 原文")
    if len(html.encode("utf-8")) > 1_800_000:
        raise HTTPException(422, "HTML 输入超过 1.8MB 限制")
    source_url = rec.input_bindings.get("source_url") or ""
    if not isinstance(source_url, str) or len(source_url) > 2048:
        raise HTTPException(422, "source_url 无效")

    try:
        # A durable status transition is the claim. Concurrent callers may
        # observe RUNNING but MUST NOT create a second provider side effect.
        _orchestrator.transition(run_id, RunStatus.RUNNING)
    except RunStatusError as exc:
        raise HTTPException(409, "任务已被其他执行请求接管") from exc
    try:
        node = NodeRunRecord(
            node_id="html_parse", node_kind=NodeKind.TRANSFORM,
            operation="article.html_parse", requires={}, produces={},
            input_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
            cost_class="FREE_LOCAL",
        )
        _orchestrator.add_node(run_id, node)
        _orchestrator.mark_node_running(run_id, node.node_id)
        from adapters.article.article_parser import parse_html
        result = parse_html(html, source_url=source_url)
        _orchestrator.mark_node_done(
            run_id, node.node_id, result, cost_cents=0,
            provider_name="local_html_parser", cost_class="FREE_LOCAL",
        )
        _orchestrator.transition(run_id, RunStatus.COMPLETED)
    except Exception:
        # Never claim success or silently restart uncertain runs.
        current = _orchestrator.get_run(run_id)
        if current and current.status == RunStatus.RUNNING:
            if any(n.node_id == "html_parse" and n.status == RunStatus.RUNNING
                   for n in current.nodes):
                try:
                    _orchestrator.mark_node_failed(
                        run_id, "html_parse", "LOCAL_EXECUTION_ERROR",
                        "Local extraction failed; inspect operator logs",
                    )
                except Exception:
                    pass
            try:
                _orchestrator.transition(run_id, RunStatus.FAILED)
            except Exception:
                pass
        raise HTTPException(503, "本地处理失败或完成记录不确定；未自动重试")
    saved = _orchestrator.get_run(run_id)
    return {
        "run_id": run_id, "status": saved.status.value,
        "worker_type": "SYNCHRONOUS_LOCAL_ONLY",
        "provider_called": False, "cost_cents": 0,
        "storage": _orchestrator.storage_kind,
        "nodes": [n.to_dict() for n in saved.nodes],
    }


@router.post("/workpaths/runs/{run_id}/reconcile-local")
def reconcile_completed_local_workpath(
    run_id: str, ctx: AuthContext = Depends(auth_required),
):
    """Repair only a proven committed LOCAL result after status-write interruption.

    No provider is re-called, no charge or new node is generated. A run that
    lacks a committed receipt is left uncertain for operator review.
    """
    record = get_owned_run(_orchestrator, run_id, ctx.tenant_id)
    if record.path_id != "WP-LOCAL-ARTICLE-EXTRACT":
        raise HTTPException(422, "此操作只支持零外部副作用的本地提取路径")
    if record.status == RunStatus.COMPLETED:
        return {"run_id": run_id, "status": "COMPLETED", "reconciled": False}
    if record.status != RunStatus.RUNNING:
        raise HTTPException(409, "任务未处于可安全核对的状态")
    store = getattr(_orchestrator, "_store", None)
    if store is None or getattr(store, "kind", "") != "SQLITE_LOCAL_DURABLE":
        raise HTTPException(409, "缺少持久化回执凭证；不能自动宣称任务已完成")
    if len(record.nodes) != 1:
        raise HTTPException(409, "节点数不符合已审核的单节点本地执行契约")
    node = record.nodes[0]
    source_html = record.input_bindings.get("html")
    if not isinstance(source_html, str):
        raise HTTPException(409, "缺少原始内容哈希核验材料")
    expected_hash = hashlib.sha256(source_html.encode("utf-8")).hexdigest()
    output = node.output_ref
    valid = (
        node.node_id == "html_parse"
        and node.operation == "article.html_parse"
        and node.status == RunStatus.COMPLETED
        and node.node_kind == NodeKind.TRANSFORM
        and node.cost_cents == 0
        and record.budget_spent_cents == 0
        and node.provider_name == "local_html_parser"
        and node.provider_req_id is None
        and node.input_hash == expected_hash
        and isinstance(output, dict)
        and output.get("content_sha256") == expected_hash
        and output.get("mock") is False
        and store.receipt_count(run_id) == 1
    )
    if not valid:
        raise HTTPException(409, "缺少完整、无付费副作用的完成证据；禁止自动重试")
    try:
        _orchestrator.transition(run_id, RunStatus.COMPLETED)
    except RunStatusError as exc:
        raise HTTPException(409, "任务状态在核对期间变化；需重新读取") from exc
    return {
        "run_id": run_id, "status": "COMPLETED", "reconciled": True,
        "provider_recalled": False, "new_charge_cents": 0,
    }


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
        "worker_connected": _active_local_workers() > 0,
        "run_storage": _orchestrator.storage_kind,
        "production_ready": False,
    }
