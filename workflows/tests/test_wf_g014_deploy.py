"""Tests for WF-G-014 部署数字员工 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g014_deploy import (
    run_deploy, DeployInput, EmployeeConfig, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_deploy_dev_sandbox_basic():
    inp = DeployInput(
        tenant_id="zq-1",
        employees=[
            EmployeeConfig(type="content_writer", capabilities=["seo", "rewrite"]),
            EmployeeConfig(type="customer_service", capabilities=["faq", "handoff"]),
        ],
        sandbox="dev",
    )
    out = run_deploy(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["deployed_count"] == 2
    assert o["failed_count"] == 0
    assert o["rollout_summary"]["sandbox"] == "dev"
    assert o["rollout_summary"]["ok_rate"] == 1.0


def test_deploy_staging_ok():
    inp = DeployInput(
        tenant_id="zq-staging",
        sandbox="staging",
        employees=[EmployeeConfig(type="data_analyst", capabilities=["kpi", "funnel"])],
    )
    out = run_deploy(inp)
    assert out["output"]["deployed_count"] == 1
    assert out["output"]["deployed"][0]["sandbox"] == "staging"


def test_deploy_prod_requires_zq_prefix():
    inp = DeployInput(
        tenant_id="acme-corp",  # 缺 zq- 前缀
        sandbox="prod",
        employees=[EmployeeConfig(type="content_writer")],
    )
    out = run_deploy(inp)
    assert out["status"] == "failed"
    assert "WF-G014-PROD-TID" in out["error"]["code"]


def test_deploy_prod_with_zq_prefix_ok():
    inp = DeployInput(
        tenant_id="zq-acme",
        sandbox="prod",
        employees=[EmployeeConfig(type="content_writer", capabilities=["seo"])],
    )
    out = run_deploy(inp)
    assert out["output"]["deployed_count"] == 1
    assert out["output"]["deployed"][0]["sandbox"] == "prod"


def test_invalid_employee_type_rejected():
    with pytest.raises(ValidationError):
        DeployInput(
            tenant_id="zq-1",
            employees=[EmployeeConfig(type="magic_ai_employee")],
        )


def test_invalid_sandbox_rejected():
    with pytest.raises(ValidationError):
        DeployInput(
            tenant_id="zq-1",
            sandbox="production",  # 应为 prod
            employees=[EmployeeConfig(type="content_writer")],
        )


def test_too_many_capabilities_dev_fails_one():
    """dev sandbox 下 capabilities > 5 的员工会部署失败 (mock 偶发失败)"""
    inp = DeployInput(
        tenant_id="zq-1",
        sandbox="dev",
        employees=[
            EmployeeConfig(type="content_writer", capabilities=["a", "b", "c", "d", "e", "f"]),  # 6 caps -> 失败
            EmployeeConfig(type="customer_service", capabilities=["faq"]),  # 正常
        ],
    )
    out = run_deploy(inp)
    o = out["output"]
    assert o["deployed_count"] == 1
    assert o["failed_count"] == 1
    assert o["rollout_summary"]["ok_rate"] == 0.5


def test_empty_employees_rejected():
    with pytest.raises(ValidationError):
        DeployInput(tenant_id="zq-1", employees=[])


def test_employee_id_format():
    inp = DeployInput(
        tenant_id="zq-1",
        employees=[EmployeeConfig(type="compliance", capabilities=["audit"])],
    )
    out = run_deploy(inp)
    eid = out["output"]["deployed"][0]["employee_id"]
    assert eid.startswith("emp-compliance-")


def test_deployed_at_present():
    inp = DeployInput(
        tenant_id="zq-1",
        employees=[EmployeeConfig(type="scheduler")],
    )
    out = run_deploy(inp)
    assert "deployed_at" in out["output"]["deployed"][0]
    assert "T" in out["output"]["deployed"][0]["deployed_at"]  # ISO8601


def test_rate_limit_bounds():
    with pytest.raises(ValidationError):
        EmployeeConfig(type="content_writer", rate_limit_per_min=0)  # ge=1
    with pytest.raises(ValidationError):
        EmployeeConfig(type="content_writer", rate_limit_per_min=1001)  # le=1000


def test_validate_json_ok():
    res = validate_json('{"tenant_id":"zq-1","sandbox":"dev","employees":[{"type":"content_writer","capabilities":["seo"]}]}')
    assert res["ok"] is True
