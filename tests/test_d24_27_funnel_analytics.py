"""
Phase 45 D24-27 — 销售漏斗聚合分析 + 自动复盘 验收测试
====================================================

验收标准:
  1. v3_172_funnel_analytics.py 存在 + 含 4 端点
  2. ACTIVE_INDUSTRIES={decoration,medical} + DEPRECATED_INDUSTRIES={education,catering,retail}
  3. STAGES=[consult,demo,trial,quote,signed] + STAGE_VALUE 加权
  4. /funnel/analytics 行业过滤 + ROI 估算 + Phase 45 标记
  5. /funnel/review 自动决策建议（含样本不足 / deprecated / 加注 等分支）
  6. /funnel/stages/breakdown 5 阶段计数
  7. /funnel/industries/{industry}/cohort 周聚合
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
DATA_LAYER = PROJECT_ROOT / "data-layer"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("v3_172_test", str(DATA_LAYER / "v3_172_funnel_analytics.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ══════════════ 模块结构 ══════════════

def test_module_loads(mod):
    """v3_172 模块可加载"""
    assert mod is not None
    assert hasattr(mod, "router")


def test_industry_constants(mod):
    """Phase 45 D4-7 行业常量对齐"""
    assert mod.ACTIVE_INDUSTRIES == {"decoration", "medical"}
    assert mod.DEPRECATED_INDUSTRIES == {"education", "catering", "retail"}
    assert mod.ALL_INDUSTRIES == {"decoration", "medical", "education", "catering", "retail"}


def test_stages_5(mod):
    """5 阶段定义"""
    assert mod.STAGES == ["consult", "demo", "trial", "quote", "signed"]
    assert mod.STAGE_LABELS == {
        "consult": "咨询",
        "demo": "演示",
        "trial": "试用",
        "quote": "报价",
        "signed": "签约",
    }


def test_stage_value_weighted(mod):
    """STAGE_VALUE 加权 + 单调递增"""
    weights = [mod.STAGE_VALUE[s] for s in mod.STAGES]
    assert weights == sorted(weights), "STAGE_VALUE 必须单调递增"
    assert weights[0] > 0
    assert weights[-1] > weights[0] * 100  # 签约价值 ≥ 100x 留资


# ══════════════ 端点注册 ══════════════

def test_router_has_4_endpoints(mod):
    """路由含 4 端点（检查 router.routes，FastAPI 子路由 path 含 prefix）"""
    paths = [r.path for r in mod.router.routes]
    # FastAPI router path 通常带 prefix
    full_paths = [mod.router.prefix + p for p in paths]
    expected_suffixes = ["/analytics", "/review", "/stages/breakdown", "/industries/{industry}/cohort"]
    for suffix in expected_suffixes:
        assert any(suffix in p for p in full_paths), f"缺端点: {suffix}, 实际: {full_paths}"


def test_router_prefix(mod):
    """路由前缀 /api/v2/sales/funnel"""
    assert mod.router.prefix == "/api/v2/sales/funnel"


# ══════════════ 数据加载（向后兼容） ══════════════

def test_load_leads_empty_no_file(mod, tmp_path, monkeypatch):
    """无 v10_leads.json 时返回空集"""
    monkeypatch.setattr(mod, "LEADS_PATH", tmp_path / "nope.json")
    d = mod._load_leads()
    assert "leads" in d
    assert d["leads"] == {}


def test_stage_conversion_empty(mod):
    """空 leads → 全 0 转化率"""
    c = mod._stage_conversion([])
    assert c["consult_to_demo"] == 0.0
    assert c["trial_to_quote"] == 0.0


def test_stage_conversion_with_data(mod):
    """模拟数据 → 转化率正确（cohort 算法：>= 当前阶段的 lead 都算 1）"""
    leads = [
        {"stage": "demo"},
        {"stage": "demo"},
        {"stage": "signed"},
        {"stage": "consult"},
        {"stage": "consult"},
    ]
    c = mod._stage_conversion(leads)
    # cohort 算法: 进过 stage s 的 lead 数 / 进过 stage s-1 的 lead 数
    # 5 个 lead 都进过 consult (>=consult); 进过 demo 的有 3 个 (2 demo + 1 signed)
    # 进过 trial 的有 1 个 (signed)
    # 进过 quote 的有 1 个 (signed)
    # 进过 signed 的有 1 个
    assert c["consult_to_demo"] == round(3/5, 4)  # 0.6
    assert c["demo_to_trial"] == round(1/3, 4)    # 0.3333
    assert c["trial_to_quote"] == round(1/1, 4)   # 1.0
    assert c["quote_to_signed"] == round(1/1, 4)  # 1.0


# ══════════════ FastAPI TestClient 端到端 ══════════════

def test_analytics_endpoint(mod):
    """GET /analytics 返回完整结构"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.get("/api/v2/sales/funnel/analytics?days=30")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "totals" in data
    assert "by_industry" in data
    assert "phase45_changes" in data
    # 5 行业都在
    assert set(data["by_industry"].keys()) == mod.ALL_INDUSTRIES


def test_analytics_industry_filter(mod):
    """GET /analytics?industry=education 触发 deprecated 警告"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.get("/api/v2/sales/funnel/analytics?industry=education")
    assert r.status_code == 200
    data = r.json()
    assert data["industry_filter"] == "education"
    assert data["deprecation_warning"] is not None
    assert "DEPRECATED" in data["deprecation_warning"]


def test_analytics_active_industry_no_warning(mod):
    """GET /analytics?industry=decoration 无 deprecated 警告"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.get("/api/v2/sales/funnel/analytics?industry=decoration")
    data = r.json()
    assert data["deprecation_warning"] is None
    assert data["by_industry"]["decoration"]["phase45_status"] == "active"


def test_review_endpoint(mod):
    """POST /review 返回决策建议"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.post("/api/v2/sales/funnel/review")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "reviews" in data
    # 5 行业都出 review
    assert len(data["reviews"]) == len(mod.ALL_INDUSTRIES)
    # education 必为 deprecated
    edu_review = next(r for r in data["reviews"] if r["industry"] == "education")
    assert edu_review["decision"] == "stop_investing"
    assert edu_review["phase45_status"] == "deprecated"
    assert edu_review["migration_target"] == "decoration"


def test_review_industry_filter(mod):
    """POST /review?industry=medical 单行业决策"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.post("/api/v2/sales/funnel/review?industry=medical")
    data = r.json()
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["industry"] == "medical"


def test_stages_breakdown_structure(mod):
    """GET /stages/breakdown 结构（生产有 186 leads 不验空，验结构）"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.get("/api/v2/sales/funnel/stages/breakdown")
    assert r.status_code == 200
    data = r.json()
    assert data["stages"] == mod.STAGES
    assert "breakdown" in data
    assert "total" in data
    assert data["total"] >= 0  # 生产有数据 >= 0
    # 5 阶段都在
    breakdown_stages = {b["stage"] for b in data["breakdown"]}
    assert breakdown_stages == set(mod.STAGES)


def test_cohort_industry_not_found(mod):
    """GET /industries/unknown/cohort → 404"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.get("/api/v2/sales/funnel/industries/unknown/cohort")
    assert r.status_code == 404


def test_cohort_valid_industry(mod):
    """GET /industries/decoration/cohort"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    r = client.get("/api/v2/sales/funnel/industries/decoration/cohort?days=90")
    assert r.status_code == 200
    data = r.json()
    assert data["industry"] == "decoration"
    assert data["phase45_status"] == "active"
    assert "cohort" in data
