"""
Phase 46 D31-37 — 多租户 + 配额 + 计费验收测试
=============================================

验收标准:
  1. v3_174_billing_quotas.py 存在 + 3 档套餐
  2. 行业/员工常量对齐 v3_142/v3_3
  3. /plans 返回 free/pro/enterprise
  4. /tenants/{tid}/usage 计算当月用量 + 配额余量
  5. /usage/record 写入 jsonl + 立即返回累计
  6. /tenants/{tid}/upgrade 切换 plan（admin secret）
  7. 鉴权: tenant token 校验
  8. 行业非法 / 员工非法 → 400
  9. Phase 45 D4-7 联动: deprecated 行业调用被记录 + 警告
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
DATA_LAYER = PROJECT_ROOT / "data-layer"


@pytest.fixture(scope="module")
def mod(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("billing_test")
    os.environ["CLOUDTECH_DATA_DIR"] = str(tmp)
    spec = importlib.util.spec_from_file_location(
        "v3_174_test",
        str(DATA_LAYER / "v3_174_billing_quotas.py"),
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # 重定向数据路径到 tmp
    m.DATA_DIR = tmp
    m.USAGE_PATH = tmp / "usage.jsonl"
    m.TENANTS_PATH = tmp / "tenants.json"
    yield m


# ══════════════ 模块结构 ══════════════

def test_module_loads(mod):
    assert mod is not None
    assert hasattr(mod, "router")


def test_industry_constants(mod):
    """Phase 45 D4-7 行业对齐"""
    assert mod.ACTIVE_INDUSTRIES == {"decoration", "medical"}
    assert mod.DEPRECATED_INDUSTRIES == {"education", "catering", "retail"}


def test_employee_constants(mod):
    """Phase 45 D4-7 员工对齐"""
    assert mod.FRONTEND_EMPLOYEES == {"content_writer", "customer_service", "market_researcher"}
    assert mod.BACKEND_EMPLOYEES == {
        "short_video_script", "data_analyst", "seo_specialist",
        "social_media_manager", "growth_hacker",
    }


def test_plans_3_tiers(mod):
    """3 档套餐"""
    assert set(mod.PLANS.keys()) == {"free", "pro", "enterprise"}
    # free < pro < enterprise
    assert mod.PLANS["free"]["price_yuan"] == 0
    assert mod.PLANS["pro"]["price_yuan"] == 499
    assert mod.PLANS["enterprise"]["price_yuan"] == 2_499
    # pro ≥ free 的 calls/tokens
    assert mod.PLANS["pro"]["monthly_calls"] > mod.PLANS["free"]["monthly_calls"]
    assert mod.PLANS["pro"]["monthly_tokens"] > mod.PLANS["free"]["monthly_tokens"]


# ══════════════ 路由 ══════════════

def test_router_endpoints(mod):
    """路由注册"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(mod.router)
    suffixes = [
        "/plans",
        "/tenants/{tenant_id}/usage",
        "/tenants/{tenant_id}/quota",
        "/tenants/{tenant_id}/upgrade",
        "/usage/record",
        "/tenants",
        "/invoices",
    ]
    paths = [r.path for r in mod.router.routes if hasattr(r, "path")]
    for suffix in suffixes:
        assert any(p.endswith(suffix) for p in paths), f"缺端点: {suffix}, 实际: {paths}"


def test_router_prefix(mod):
    assert mod.router.prefix == "/api/v2/billing"


# ══════════════ FastAPI 端到端 ══════════════

@pytest.fixture
def client(mod):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def test_plans_endpoint(client):
    """GET /plans 返回 3 档"""
    r = client.get("/api/v2/billing/plans")
    assert r.status_code == 200
    data = r.json()
    assert "plans" in data
    assert set(data["plans"].keys()) == {"free", "pro", "enterprise"}
    assert "phase45_changes" in data


def test_usage_default_tenant(client, mod):
    """GET /tenants/default/usage 默认租户 pro 套餐"""
    r = client.get("/api/v2/billing/tenants/default/usage")
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "default"
    assert data["plan"] == "pro"
    assert data["plan_label"] == "专业版"
    assert data["quota"]["calls"] == 5_000
    assert data["quota"]["tokens"] == 2_000_000


def test_usage_invalid_tenant_404(client):
    """未知租户 → 404"""
    r = client.get("/api/v2/billing/tenants/unknown/usage")
    assert r.status_code == 404


def test_record_usage_active_industry(client, mod):
    """POST /usage/record active 行业"""
    r = client.post(
        "/api/v2/billing/usage/record",
        params={
            "tenant_id": "default",
            "category": "pipeline_run",
            "calls": 1,
            "tokens": 500,
            "industry": "decoration",
            "employee": "content_writer",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["calls"] == 1
    assert data["tokens"] == 500
    assert "usage_id" in data
    assert mod.USAGE_PATH.exists()


def test_record_usage_deprecated_industry_warn(client, mod):
    """POST /usage/record deprecated 行业 → 写入 + 警告"""
    r = client.post(
        "/api/v2/billing/usage/record",
        params={
            "tenant_id": "default",
            "category": "pipeline_run",
            "calls": 1,
            "industry": "education",
        },
    )
    assert r.status_code == 200
    # 但 usage 端点应显示 deprecated 计数
    r2 = client.get("/api/v2/billing/tenants/default/usage")
    data = r2.json()
    assert data["usage"]["by_industry_deprecated"] >= 1
    assert data["phase45_warnings"]["deprecated_industry_calls"] >= 1


def test_record_usage_invalid_industry(client):
    """POST /usage/record 行业非法 → 400"""
    r = client.post(
        "/api/v2/billing/usage/record",
        params={"tenant_id": "default", "category": "x", "industry": "fake_ind"},
    )
    assert r.status_code == 400


def test_record_usage_invalid_employee(client):
    """POST /usage/record 员工非法 → 400"""
    r = client.post(
        "/api/v2/billing/usage/record",
        params={"tenant_id": "default", "category": "x", "employee": "fake_emp"},
    )
    assert r.status_code == 400


def test_record_usage_aggregates(client, mod):
    """POST 多次 → 用量聚合"""
    # 清理
    if mod.USAGE_PATH.exists():
        mod.USAGE_PATH.unlink()

    for i in range(3):
        client.post("/api/v2/billing/usage/record", params={
            "tenant_id": "default",
            "category": "employee_call",
            "calls": 1,
            "tokens": 100,
            "employee": "content_writer",
        })

    r = client.get("/api/v2/billing/tenants/default/usage")
    data = r.json()
    assert data["usage"]["calls"] == 3
    assert data["usage"]["tokens"] == 300
    assert data["usage"]["by_category"]["employee_call"] == 3


def test_upgrade_plan(client, mod):
    """POST /tenants/{tid}/upgrade 切换 plan"""
    r = client.post(
        "/api/v2/billing/tenants/default/upgrade",
        params={"plan_id": "enterprise"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["old_plan"] == "pro"
    assert data["new_plan"] == "enterprise"
    assert data["price_yuan"] == 2_499

    # 验证已切换
    r2 = client.get("/api/v2/billing/tenants/default/usage")
    assert r2.json()["plan"] == "enterprise"


def test_upgrade_invalid_plan(client):
    """POST /upgrade plan 非法 → 400"""
    r = client.post(
        "/api/v2/billing/tenants/default/upgrade",
        params={"plan_id": "fake_plan"},
    )
    assert r.status_code == 400


def test_upgrade_unknown_tenant(client):
    """POST /upgrade 租户不存在 → 404"""
    r = client.post(
        "/api/v2/billing/tenants/nope/upgrade",
        params={"plan_id": "pro"},
    )
    assert r.status_code == 404


def test_list_tenants_admin(client, mod):
    """GET /tenants admin 列表"""
    r = client.get("/api/v2/billing/tenants")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    tenant_ids = {t["tenant_id"] for t in data["tenants"]}
    assert "default" in tenant_ids


def test_invoices_placeholder(client):
    """GET /invoices 占位（红 #22 守门）"""
    r = client.get("/api/v2/billing/invoices?tenant_id=default")
    assert r.status_code == 200
    data = r.json()
    assert "invoices" in data
    assert data["invoices"] == []
    assert "红 #22" in data["note"] or "金税" in data["note"]


# ══════════════ 工具函数 ══════════════

def test_check_tenant_token_valid(mod):
    """token 正确放行"""
    mod._check_tenant_token("default", None)  # demo 模式


def test_check_tenant_token_invalid_tenant(mod):
    """未知租户 → 404"""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        mod._check_tenant_token("nonexistent", None)
    assert exc.value.status_code == 404


def test_record_usage_writes_jsonl(mod):
    """_record_usage 写文件"""
    if mod.USAGE_PATH.exists():
        mod.USAGE_PATH.unlink()
    mod._record_usage("default", "test", calls=5, tokens=100, industry="decoration")
    assert mod.USAGE_PATH.exists()
    content = mod.USAGE_PATH.read_text(encoding="utf-8").strip()
    assert '"calls": 5' in content or '"calls":5' in content
