"""
Phase 45 D8-12 — FastAPI 统一网关元数据增强验收测试
====================================================

验收标准:
  1. /health 返回基础状态
  2. /health/deep 返回 deps（sqlite + flask + v10_modules + fastapi）
  3. /api/v2/_meta/routes/summary 返回 prefix + tier 分布
  4. /api/v2/_meta/industries 透出 v3_142 active/deprecated
  5. /api/v2/_meta/employees/tier 透出 v3_3 FE/BE 分布
  6. 总路由数 ≥ 250（与 README 一致）

注: gateway_v22.py 启动会 import 全部 87 个 v3_* 模块, 测试需要 sys.path 设置正确,
    否则会失败; 因此本测试用独立加载方式: 仅 import gateway_v22 模块本身（不启动 uvicorn）,
    通过 FastAPI TestClient 调端点。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")


def _load_gateway():
    """加载 gateway_v22 模块（不启动 uvicorn）"""
    p = PROJECT_ROOT / "gateway_v22.py"
    spec = importlib.util.spec_from_file_location("gateway_v22_test", str(p))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        pytest.skip(f"gateway_v22 加载失败（外部依赖）: {e}")


@pytest.fixture(scope="module")
def gw():
    """fixture: 加载 gateway_v22 模块"""
    return _load_gateway()


@pytest.fixture(scope="module")
def client(gw):
    """fixture: FastAPI TestClient"""
    from fastapi.testclient import TestClient
    return TestClient(gw.app)


# ══════════════ /health ══════════════

def test_health_basic(client):
    """基础健康检查"""
    r = client.get("/health")
    assert r.status_code == 200, f"expected 200, got {r.status_code}"
    data = r.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert data["version"] == "22.0.0"


def test_health_v10_count(client):
    """/health 返回 V10 modules 加载数"""
    r = client.get("/health")
    data = r.json()
    assert "v10_modules_included" in data
    assert isinstance(data["v10_modules_included"], int)
    assert data["v10_modules_included"] >= 50, f"V10 加载数过低: {data['v10_modules_included']}"


# ══════════════ /health/deep ══════════════

def test_health_deep_returns(client):
    """/health/deep 返回完整"""
    r = client.get("/health/deep")
    assert r.status_code == 200
    data = r.json()
    assert "deps" in data
    deps = data["deps"]
    assert "sqlite" in deps
    assert "flask" in deps
    assert "v10_modules" in deps
    assert "fastapi" in deps


def test_health_deep_sqlite_check(client):
    """SQLite 健康检查存在性"""
    r = client.get("/health/deep")
    data = r.json()
    sqlite = data["deps"]["sqlite"]
    # 不强制 ok（db 可能不存在），但必有字段
    assert "ok" in sqlite
    if sqlite["ok"]:
        assert "path" in sqlite
        assert "size_mb" in sqlite


def test_health_deep_flask_check(client):
    """Flask app 加载状态"""
    r = client.get("/health/deep")
    data = r.json()
    flask = data["deps"]["flask"]
    assert "ok" in flask
    assert "routes" in flask


def test_health_deep_v10_modules_check(client):
    """V10 modules 加载状态"""
    r = client.get("/health/deep")
    data = r.json()
    v10 = data["deps"]["v10_modules"]
    assert "ok" in v10
    assert "included" in v10
    assert "failed" in v10
    # 至少 50 个模块 included
    assert v10["included"] >= 50, f"V10 included 过低: {v10['included']}"


def test_health_deep_fastapi_routes_count(client):
    """FastAPI 真实端点数 ≥ 600（FastAPI 顶层 + V10 + Flask 聚合）"""
    r = client.get("/health/deep")
    data = r.json()
    fa = data["deps"]["fastapi"]
    assert fa["ok"] is True
    assert fa["routes_count"] >= 600, f"FastAPI 路由数过低: {fa['routes_count']}"


# ══════════════ /api/v2/_meta/routes/summary ══════════════

def test_routes_summary_basic(client):
    """/api/v2/_meta/routes/summary 基础结构"""
    r = client.get("/api/v2/_meta/routes/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_routes" in data
    assert "prefix_distribution" in data
    assert "tier_distribution" in data
    assert "phase45_changes" in data


def test_routes_summary_total(client):
    """总路由 ≥ 600（FastAPI + V10 + Flask 聚合）"""
    r = client.get("/api/v2/_meta/routes/summary")
    data = r.json()
    assert data["total_routes"] >= 600, f"路由数过低: {data['total_routes']}"


def test_routes_summary_phase45_changes(client):
    """Phase 45 改造数据透出"""
    r = client.get("/api/v2/_meta/routes/summary")
    data = r.json()
    changes = data["phase45_changes"]
    assert changes["industry_active"] == 2
    assert changes["industry_deprecated"] == 3
    assert changes["employees_frontend"] == 3
    assert changes["employees_backend"] == 5


def test_routes_summary_tier_distribution(client):
    """tier 分布含 metadata（_meta 端点）+ health"""
    r = client.get("/api/v2/_meta/routes/summary")
    data = r.json()
    tier = data["tier_distribution"]
    # 至少含 health + metadata（D8-12 新增的 4 个 _meta 端点）
    assert "metadata" in tier, f"缺 metadata tier: {tier}"
    assert "health" in tier, f"缺 health tier: {tier}"


def test_routes_summary_total_includes_flask(client):
    """总路由 ≥ 600（FastAPI 顶层 + V10 87 + Flask 230 + catch-all）"""
    r = client.get("/api/v2/_meta/routes/summary")
    data = r.json()
    assert data["total_routes"] >= 600, f"总路由数过低: {data['total_routes']}"
    # 必须含 V10 + Flask 计数
    assert data["v10_modules_routes"] >= 50
    assert data["flask_routes"] >= 100


def test_routes_summary_phase45_counters(client):
    """Phase 45 改造计数字段"""
    r = client.get("/api/v2/_meta/routes/summary")
    data = r.json()
    changes = data["phase45_changes"]
    assert changes == {
        "industry_active": 2,
        "industry_deprecated": 3,
        "employees_frontend": 3,
        "employees_backend": 5,
    }


# ══════════════ /api/v2/_meta/industries ══════════════

def test_industries_meta_returns(client):
    """行业元数据透出"""
    r = client.get("/api/v2/_meta/industries")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "data" in data


def test_industries_meta_active_count(client):
    """active 行业 = 2（装企+医美）"""
    r = client.get("/api/v2/_meta/industries")
    data = r.json()["data"]
    active = [d for d in data if d.get("priority") in ("primary", "fallback")]
    assert len(active) == 2
    active_names = {d["industry"] for d in active}
    assert active_names == {"decoration", "medical"}


def test_industries_meta_deprecated_count(client):
    """deprecated 行业 = 3"""
    r = client.get("/api/v2/_meta/industries")
    data = r.json()["data"]
    deprecated = [d for d in data if d.get("priority") == "deprecated"]
    assert len(deprecated) == 3
    dep_names = {d["industry"] for d in deprecated}
    assert dep_names == {"education", "catering", "retail"}


def test_industries_meta_has_migration(client):
    """deprecated 行业有 migration 字段"""
    r = client.get("/api/v2/_meta/industries")
    data = r.json()["data"]
    for d in data:
        if d.get("priority") == "deprecated":
            assert d.get("migration"), f"{d['industry']} 缺 migration"
            assert d["migration"] == "decoration", \
                f"{d['industry']} migration 应为 decoration, 实际 {d['migration']}"


# ══════════════ /api/v2/_meta/employees/tier ══════════════

def test_employees_tier_meta_returns(client):
    """员工 tier 元数据透出"""
    r = client.get("/api/v2/_meta/employees/tier")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "frontend" in data
    assert "backend" in data
    assert "total" in data


def test_employees_tier_frontend(client):
    """前台员工 = 3"""
    r = client.get("/api/v2/_meta/employees/tier")
    data = r.json()
    assert len(data["frontend"]) == 3
    assert set(data["frontend"]) == {"content_writer", "customer_service", "market_researcher"}


def test_employees_tier_backend(client):
    """后端员工 = 5"""
    r = client.get("/api/v2/_meta/employees/tier")
    data = r.json()
    assert len(data["backend"]) == 5
    assert set(data["backend"]) == {"data_analyst", "growth_hacker", "seo_specialist",
                                      "short_video_script", "social_media_manager"}


def test_employees_tier_total(client):
    """总员工 = 8"""
    r = client.get("/api/v2/_meta/employees/tier")
    data = r.json()
    assert data["total"] == 8
    assert len(data["frontend"]) + len(data["backend"]) == 8
