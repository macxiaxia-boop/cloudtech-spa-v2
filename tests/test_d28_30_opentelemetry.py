"""
Phase 45 D28-30 — OpenTelemetry + 业务指标埋点验收测试
======================================================

验收标准:
  1. v3_173_opentelemetry.py 存在 + 含 4 端点
  2. ACTIVE/DEPRECATED/FRONTEND/BACKEND 常量对齐 v3_142 + v3_3
  3. OTEL_STATE 含 enabled/exporter/spans_recorded 等
  4. trace_business_event() 返回 trace_id
  5. /_otel/status 返回完整 OTel 状态
  6. /_otel/spans 注入 span（带 industry + employee 校验）
  7. /_otel/metrics 聚合（按 category/industry/employee_tier）
  8. /_otel/spans/clear 清空文件
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
DATA_LAYER = PROJECT_ROOT / "data-layer"


@pytest.fixture(scope="module")
def mod(tmp_path_factory):
    # 隔离 OTEL 数据到 tmp，避免污染生产
    tmp = tmp_path_factory.mktemp("otel_test")
    import os
    os.environ["CLOUDTECH_DATA_DIR"] = str(tmp)
    spec = importlib.util.spec_from_file_location(
        "v3_173_test",
        str(DATA_LAYER / "v3_173_opentelemetry.py"),
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    # 重定向 SPANS_PATH / METRICS_PATH 到 tmp
    m.SPANS_PATH = tmp / "spans.jsonl"
    m.METRICS_PATH = tmp / "metrics.jsonl"
    m.DATA_DIR = tmp

    # helper: 清理 span + metric 文件
    def _clear():
        if m.SPANS_PATH.exists():
            m.SPANS_PATH.unlink()
        if m.METRICS_PATH.exists():
            m.METRICS_PATH.unlink()
        m.OTEL_STATE["spans_recorded"] = 0
        m.OTEL_STATE["metrics_recorded"] = 0
        m.OTEL_STATE["last_span_at"] = None
    m.clear_spans_via_endpoint = _clear

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


def test_otel_state_fields(mod):
    """OTEL_STATE 字段齐全"""
    required = {"enabled", "exporter", "endpoint", "service_name",
                "service_version", "spans_recorded", "metrics_recorded",
                "last_span_at"}
    assert required.issubset(mod.OTEL_STATE.keys())
    assert mod.OTEL_STATE["service_name"] == "cloudtech-saas"


# ══════════════ 路由 ══════════════

def test_router_has_4_endpoints(mod):
    """4 端点注册（直接遍历 router.routes）"""
    paths = [r.path for r in mod.router.routes if hasattr(r, "path")]
    # router.path 通常含前缀 /api/v2/_otel
    expected_suffixes = ["/status", "/spans", "/metrics", "/spans/clear"]
    for suffix in expected_suffixes:
        assert any(p.endswith(suffix) for p in paths), f"缺端点: {suffix}, 实际: {paths}"


def test_router_prefix(mod):
    assert mod.router.prefix == "/api/v2/_otel"


# ══════════════ trace_business_event ══════════════

def test_trace_returns_id(mod):
    """trace_business_event 返回 trace_id"""
    tid = mod.trace_business_event(
        category="pipeline", name="decoration.run",
        industry="decoration", employee="content_writer",
    )
    assert isinstance(tid, str)
    assert len(tid) == 16


def test_trace_records_span_file(mod):
    """trace_business_event 写入 spans.jsonl"""
    before = mod.OTEL_STATE["spans_recorded"]
    mod.trace_business_event(category="test", name="hello")
    assert mod.OTEL_STATE["spans_recorded"] == before + 1
    assert mod.SPANS_PATH.exists()


def test_trace_attributes_active(mod):
    """active 行业的 span 标记 industry_active=True"""
    mod.clear_spans_via_endpoint()
    mod.trace_business_event(
        category="pipeline", name="test",
        industry="decoration", employee="content_writer",
    )
    # 读最后一行 span
    last = mod.SPANS_PATH.read_text(encoding="utf-8").strip().splitlines()[-1]
    import json
    span = json.loads(last)
    assert span["attributes"]["industry_active"] is True
    assert span["attributes"]["industry_deprecated"] is False
    assert span["attributes"]["employee_tier"] == "frontend"


def test_trace_attributes_deprecated(mod):
    """deprecated 行业的 span 标记"""
    mod.clear_spans_via_endpoint()
    mod.trace_business_event(
        category="pipeline", name="test", industry="education",
    )
    last = mod.SPANS_PATH.read_text(encoding="utf-8").strip().splitlines()[-1]
    import json
    span = json.loads(last)
    assert span["attributes"]["industry_deprecated"] is True
    assert span["attributes"]["industry_active"] is False


def test_trace_attributes_backend_employee(mod):
    """backend 员工 tier 标注"""
    mod.clear_spans_via_endpoint()
    mod.trace_business_event(category="emp", name="x", employee="data_analyst")
    last = mod.SPANS_PATH.read_text(encoding="utf-8").strip().splitlines()[-1]
    import json
    span = json.loads(last)
    assert span["attributes"]["employee_tier"] == "backend"


# ══════════════ FastAPI 端点 ══════════════

@pytest.fixture
def client(mod):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    return TestClient(app)


def test_status_endpoint(client):
    """GET /status 完整结构"""
    r = client.get("/api/v2/_otel/status")
    assert r.status_code == 200
    data = r.json()
    assert "service_name" in data
    assert "exporter" in data
    assert "phase45_changes" in data
    # Phase 45 联动
    assert "decoration" in data["phase45_changes"]["active_industries"]


def test_inject_span_valid(client, mod):
    """POST /spans 注入 span"""
    mod.clear_spans_via_endpoint()
    r = client.post(
        "/api/v2/_otel/spans",
        params={
            "category": "pipeline",
            "name": "decoration.run",
            "industry": "medical",
            "employee": "customer_service",
            "tenant_id": "test_tenant",
            "duration_ms": 200,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["industry"] == "medical"
    assert data["employee"] == "customer_service"
    assert data["duration_ms"] == 200
    assert len(data["trace_id"]) == 16


def test_inject_span_invalid_industry(client):
    """POST /spans 行业非法 → 400"""
    r = client.post(
        "/api/v2/_otel/spans",
        params={"category": "x", "name": "y", "industry": "unknown_ind"},
    )
    assert r.status_code == 400


def test_inject_span_invalid_employee(client):
    """POST /spans 员工非法 → 400"""
    r = client.post(
        "/api/v2/_otel/spans",
        params={"category": "x", "name": "y", "employee": "fake_employee"},
    )
    assert r.status_code == 400


def test_metrics_empty(client, mod):
    """GET /metrics 空数据"""
    mod.clear_spans_via_endpoint()
    r = client.get("/api/v2/_otel/metrics?days=1")
    assert r.status_code == 200
    data = r.json()
    assert data["total_events"] == 0


def test_metrics_aggregation(client, mod):
    """GET /metrics 聚合（注入 3 个 span 后验证）"""
    mod.clear_spans_via_endpoint()
    # 注入 3 个 span
    client.post("/api/v2/_otel/spans", params={
        "category": "pipeline", "name": "decoration.run",
        "industry": "decoration", "employee": "content_writer",
    })
    client.post("/api/v2/_otel/spans", params={
        "category": "pipeline", "name": "medical.run",
        "industry": "medical", "employee": "data_analyst",
    })
    client.post("/api/v2/_otel/spans", params={
        "category": "funnel", "name": "decoration.lead",
        "industry": "decoration",
    })

    r = client.get("/api/v2/_otel/metrics?days=1")
    data = r.json()
    assert data["total_events"] == 3
    assert data["by_category"]["pipeline"] == 2
    assert data["by_category"]["funnel"] == 1
    assert data["by_industry"]["active"]["decoration"] == 2
    assert data["by_industry"]["active"]["medical"] == 1
    assert data["by_employee_tier"]["frontend"]["content_writer"] == 1
    assert data["by_employee_tier"]["backend"]["data_analyst"] == 1


def test_clear_endpoint(client, mod):
    """POST /spans/clear 清空"""
    # 先注入
    client.post("/api/v2/_otel/spans", params={"category": "x", "name": "y"})
    assert mod.SPANS_PATH.exists()

    r = client.post("/api/v2/_otel/spans/clear")
    assert r.status_code == 200
    assert r.json()["cleared"] is True
    assert not mod.SPANS_PATH.exists()
    assert not mod.METRICS_PATH.exists()


# ══════════════ helper（已挂在 mod fixture 中）══════════════
# mod.clear_spans_via_endpoint() — 测试间清理 span + metric 文件
