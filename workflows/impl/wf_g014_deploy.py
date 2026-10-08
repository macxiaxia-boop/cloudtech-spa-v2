"""WF-G-014 部署数字员工 — 通用
===========================
输入: tenant_id, employees[] (员工类型 + 启用配置), sandbox (dev/staging/prod)
输出: deployed[] (含 employee_id, status, sandbox, capabilities), rollout_summary
"""
from __future__ import annotations
import secrets
from typing import List
from pydantic import BaseModel, Field, field_validator
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError

EMPLOYEE_TYPES = ("content_writer", "customer_service", "market_researcher",
                  "data_analyst", "compliance", "scheduler", "lead_assignor")


class EmployeeConfig(BaseModel):
    type: str
    enabled: bool = True
    capabilities: List[str] = Field(default_factory=list)
    rate_limit_per_min: int = Field(default=20, ge=1, le=1000)

    @field_validator("type")
    @classmethod
    def t_ok(cls, v):
        if v not in EMPLOYEE_TYPES:
            raise ValueError(f"type ∈ {EMPLOYEE_TYPES}")
        return v


class DeployInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    employees: List[EmployeeConfig] = Field(..., min_length=1, max_length=20)
    sandbox: str = Field(default="dev")
    workflow_id: str = Field(default="WF-G-014", pattern=r"^WF-G-\d{3}$")

    @field_validator("sandbox")
    @classmethod
    def sb_ok(cls, v):
        if v not in ("dev", "staging", "prod"):
            raise ValueError("sandbox ∈ {dev, staging, prod}")
        return v


class DeployedEmployee(BaseModel):
    employee_id: str
    type: str
    status: str
    sandbox: str
    capabilities: List[str]
    deployed_at: str


class DeployOutput(BaseModel):
    deployed_count: int
    failed_count: int
    deployed: List[DeployedEmployee]
    rollout_summary: dict


@run_workflow(workflow_id="WF-G-014", tenant_field="tenant_id")
def run_deploy(inp: DeployInput) -> DeployOutput:
    if inp.sandbox == "prod" and not inp.tenant_id.startswith("zq-"):
        raise WorkflowError("WF-G014-PROD-TID", "生产环境 tenant_id 必须以 zq- 开头")
    deployed: List[DeployedEmployee] = []
    failed = 0
    for emp in inp.employees:
        eid = f"emp-{emp.type}-{secrets.token_hex(3)}"
        try:
            # mock 部署 (模拟偶发失败)
            if inp.sandbox == "dev" and len(emp.capabilities) > 5:
                raise WorkflowError("WF-G014-CAP", f"能力过多: {len(emp.capabilities)}")
            deployed.append(DeployedEmployee(
                employee_id=eid,
                type=emp.type,
                status="active",
                sandbox=inp.sandbox,
                capabilities=emp.capabilities,
                deployed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            ))
        except WorkflowError:
            failed += 1

    summary = {
        "sandbox": inp.sandbox,
        "ok_rate": round(len(deployed) / max(len(inp.employees), 1), 3),
        "total_capabilities": sum(len(d.capabilities) for d in deployed),
    }
    return DeployOutput(
        deployed_count=len(deployed),
        failed_count=failed,
        deployed=deployed,
        rollout_summary=summary,
    )


validate_json = lambda s: validate_workflow_json(s, DeployInput)
validate_yaml = lambda s: validate_workflow_yaml(s, DeployInput)