"""WF-G-013 企业初始化 — 通用
===========================
输入: tenant_id, name, plan, cities, contacts[]
输出: created_tenant, default_workflows_enabled, resource_quotas, next_steps[]
"""
from __future__ import annotations
import secrets
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError, PLANS, DECORATION_CITIES


class Contact(BaseModel):
    name: str
    role: str = "admin"
    email: str
    phone: Optional[str] = None

    @field_validator("email")
    @classmethod
    def email_ok(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("邮箱格式错误")
        return v.lower().strip()


class TenantInitInput(BaseModel):
    tenant_id: Optional[str] = None  # 自动生成
    tenant_name: str = Field(..., min_length=2, max_length=100)
    plan: str = Field(default="starter")
    cities: List[str] = Field(default_factory=list)
    industry: str = Field(default="decoration")
    contacts: List[Contact] = Field(default_factory=list)
    workflow_id: str = Field(default="WF-G-013", pattern=r"^WF-G-\d{3}$")

    @field_validator("plan")
    @classmethod
    def plan_ok(cls, v):
        if v not in PLANS:
            raise ValueError(f"plan ∈ {PLANS}")
        return v

    @field_validator("industry")
    @classmethod
    def ind_ok(cls, v):
        if v not in ("decoration", "medical", "education", "catering", "retail"):
            raise ValueError("industry ∈ 5+2")
        return v


class TenantInitOutput(BaseModel):
    tenant_id: str
    tenant_name: str
    plan: str
    cities: List[str]
    default_workflows_enabled: List[str]
    resource_quotas: dict
    next_steps: List[str]


PLAN_QUOTAS = {
    "free": {"monthly_quota": 30, "seats": 1, "storage_kb": 102400},
    "starter": {"monthly_quota": 100, "seats": 3, "storage_kb": 512000},
    "pro": {"monthly_quota": 500, "seats": 10, "storage_kb": 2048000},
    "enterprise": {"monthly_quota": 5000, "seats": 50, "storage_kb": 10240000},
}


@run_workflow(workflow_id="WF-G-013", tenant_field="tenant_id")
def run_init(inp: TenantInitInput) -> TenantInitOutput:
    if not inp.tenant_name:
        raise WorkflowError("WF-G013-NAME", "tenant_name 必填")
    tid = inp.tenant_id or ("zq-" + secrets.token_hex(4))

    default_wf = ["WF-T-001", "WF-T-007", "WF-T-013", "WF-T-022"] if inp.plan in ("pro", "enterprise") else ["WF-T-001"]
    next_steps = [
        "建立首批选题 (WF-T-002)",
        "导入首批客户线索 (WF-T-005)",
        "开通日数据看板 (WF-T-007)",
    ]
    return TenantInitOutput(
        tenant_id=tid,
        tenant_name=inp.tenant_name,
        plan=inp.plan,
        cities=inp.cities,
        default_workflows_enabled=default_wf,
        resource_quotas=PLAN_QUOTAS[inp.plan],
        next_steps=next_steps,
    )


validate_json = lambda s: validate_workflow_json(s, TenantInitInput)
validate_yaml = lambda s: validate_workflow_yaml(s, TenantInitInput)