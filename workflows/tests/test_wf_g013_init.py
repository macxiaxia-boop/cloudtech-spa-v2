"""Tests for WF-G-013 企业初始化 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g013_init import (
    run_init, TenantInitInput, Contact, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_init_starter_plan_minimal():
    inp = TenantInitInput(
        tenant_name="厦门装企A",
        plan="starter",
    )
    out = run_init(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["plan"] == "starter"
    assert o["default_workflows_enabled"] == ["WF-T-001"]
    assert o["resource_quotas"]["monthly_quota"] == 100
    assert o["resource_quotas"]["seats"] == 3
    assert len(o["next_steps"]) == 3


def test_init_pro_plan_more_workflows():
    inp = TenantInitInput(
        tenant_name="头部装企",
        plan="pro",
    )
    out = run_init(inp)
    assert out["status"] == "success"
    enabled = out["output"]["default_workflows_enabled"]
    assert "WF-T-001" in enabled
    assert "WF-T-007" in enabled
    assert "WF-T-013" in enabled
    assert "WF-T-022" in enabled
    assert out["output"]["resource_quotas"]["seats"] == 10


def test_init_enterprise_plan():
    inp = TenantInitInput(tenant_name="大型连锁装企", plan="enterprise")
    out = run_init(inp)
    assert out["output"]["resource_quotas"]["monthly_quota"] == 5000
    assert out["output"]["resource_quotas"]["seats"] == 50


def test_init_explicit_tenant_id():
    inp = TenantInitInput(tenant_id="zq-fixed-1", tenant_name="指定ID", plan="free")
    out = run_init(inp)
    assert out["output"]["tenant_id"] == "zq-fixed-1"


def test_init_auto_generated_tenant_id():
    inp = TenantInitInput(tenant_name="自动ID", plan="starter")
    out = run_init(inp)
    tid = out["output"]["tenant_id"]
    assert tid.startswith("zq-")
    assert len(tid) == 11  # zq- + 8 hex chars


def test_init_invalid_plan_rejected():
    with pytest.raises(ValidationError):
        TenantInitInput(tenant_name="测试", plan="platinum")


def test_init_invalid_industry_rejected():
    with pytest.raises(ValidationError):
        TenantInitInput(tenant_name="测试", industry="spacex")


def test_contact_invalid_email_rejected():
    with pytest.raises(ValidationError):
        TenantInitInput(
            tenant_name="测试",
            contacts=[Contact(name="张三", role="admin", email="not-an-email")],
        )


def test_contact_email_normalized_to_lower():
    inp = TenantInitInput(
        tenant_name="测试",
        contacts=[Contact(name="李四", email="  LiSi@Example.COM  ")],
    )
    assert inp.contacts[0].email == "lisi@example.com"


def test_init_with_cities():
    inp = TenantInitInput(
        tenant_name="多城市装企",
        plan="pro",
        cities=["厦门", "泉州", "福州"],
    )
    out = run_init(inp)
    assert out["output"]["cities"] == ["厦门", "泉州", "福州"]


def test_init_tenant_name_too_short_rejected():
    with pytest.raises(ValidationError):
        TenantInitInput(tenant_name="x")


def test_validate_json_ok():
    res = validate_json('{"tenant_name":"测试装企","plan":"starter"}')
    assert res["ok"] is True


def test_validate_json_missing_field():
    res = validate_json('{"plan":"starter"}')  # 缺 tenant_name
    assert res["ok"] is False
