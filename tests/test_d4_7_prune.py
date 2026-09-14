"""
Phase 45 D4-7 — 砍端点/行业/员工 验收测试
=============================================

验收标准:
  1. v3_142 行业：active=2（装企+医美），deprecated=3（教培/餐饮/零售）
  2. v3_3 员工：FRONTEND_EMPLOYEES 包含 3 个，BACKEND_EMPLOYEES 包含 5 个
  3. v3_142 deprecated 行业调用不抛错，返回 status=deprecated
  4. v3_142 active 行业（decoration）返回完整步骤
  5. v3_3 /list 包含 visible_for_user + tier 字段
  6. v3_3 /list/frontend 返回 3 个员工
  7. v3_142 /industries 接口包含 priority 字段
"""
from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
DATA_LAYER = PROJECT_ROOT / "data-layer"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(DATA_LAYER))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def v142():
    # 修复 Pydantic v2 + from __future__ import annotations 的 forward-ref 问题：
    # 必须在 _load 之前把 typing 符号注入到模块 __dict__，因为 v3_142 用 from typing import ...
    # 但 Pydantic 解析 forward-ref 时查找模块 globals，看不到 Dict
    import typing as _typing
    import sys as _sys

    # 先预加载模块
    mod = _load("v3_142_test", DATA_LAYER / "v3_142_industry_pipeline.py")

    # 强制把 typing.Dict/List/Any 注入到模块 globals（即使是 from X import Y 的引用）
    for name in ("Dict", "List", "Any", "Optional", "Tuple", "Set", "FrozenSet"):
        if not hasattr(mod, name):
            setattr(mod, name, getattr(_typing, name))

    # 重建 Pydantic 模型
    try:
        mod.PipelineRunRequest.model_rebuild()
    except Exception as e:
        # 如果还是失败，尝试把 typing 全量注入
        for k, v in vars(_typing).items():
            if not k.startswith("_") and not hasattr(mod, k):
                try:
                    setattr(mod, k, v)
                except Exception:
                    pass
        mod.PipelineRunRequest.model_rebuild()

    return mod


@pytest.fixture(scope="module")
def v3():
    return _load("v3_3_test", DATA_LAYER / "v3_3_employees_routes.py")


# ============ v3_142 行业测试 ============

def test_v142_active_count(v142):
    """active 行业数 = 2（装企 + 医美）"""
    active = [k for k, v in v142.PIPELINES.items() if v and not v.get("deprecated")]
    assert len(active) == 2, f"expected 2 active, got {active}"


def test_v142_active_set(v142):
    """active = {decoration, medical}"""
    active = {k for k, v in v142.PIPELINES.items() if v and not v.get("deprecated")}
    assert active == {"decoration", "medical"}, f"expected {{decoration, medical}}, got {active}"


def test_v142_deprecated_count(v142):
    """deprecated 行业数 = 3"""
    deprecated = {k for k, v in v142.PIPELINES.items() if v and v.get("deprecated")}
    assert len(deprecated) == 3, f"expected 3 deprecated, got {deprecated}"


def test_v142_deprecated_set(v142):
    """deprecated = {education, catering, retail}"""
    deprecated = {k for k, v in v142.PIPELINES.items() if v and v.get("deprecated")}
    assert deprecated == {"education", "catering", "retail"}, \
        f"expected {{education, catering, retail}}, got {deprecated}"


def test_v142_deprecated_industries_constant(v142):
    """DEPRECATED_INDUSTRIES 集合与 PIPELINES 一致"""
    assert hasattr(v142, "DEPRECATED_INDUSTRIES"), "missing DEPRECATED_INDUSTRIES"
    assert v142.DEPRECATED_INDUSTRIES == {"education", "catering", "retail"}


def test_v142_decoration_steps(v142):
    """装企管线有 4 步"""
    decoration = v142.PIPELINES["decoration"]
    assert len(decoration["steps"]) == 4
    step_keys = [s[0] for s in decoration["steps"]]
    assert step_keys == ["lead_profile", "quote", "content", "live_script"]


def test_v142_medical_steps(v142):
    """医美管线有 4 步"""
    medical = v142.PIPELINES["medical"]
    assert len(medical["steps"]) == 4
    step_keys = [s[0] for s in medical["steps"]]
    assert step_keys == ["lead_profile", "content", "pre_op_qa", "case"]


def test_v142_deprecated_have_metadata(v142):
    """deprecated 行业有完整元数据（since/removal/label）"""
    for k in ["education", "catering", "retail"]:
        cfg = v142.PIPELINES[k]
        assert cfg.get("deprecated") is True, f"{k} missing deprecated=True"
        assert cfg.get("deprecation_since"), f"{k} missing deprecation_since"
        assert cfg.get("deprecation_removal"), f"{k} missing deprecation_removal"
        assert cfg.get("label"), f"{k} missing label"


def test_v142_deprecated_call_returns_stub(v142):
    """deprecated 行业调用返回 status=deprecated 而非 404
    注: 单元测试直接调 run_pipeline 函数，避开 FastAPI TestClient 的 Pydantic 模型
    rebuild 问题（生产用 FastAPI app 注册时无此问题）。
    """
    req = v142.PipelineRunRequest(lead={"name": "test"}, tenant_id="default")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = v142.run_pipeline("education", req)

    assert result["status"] == "deprecated", f"expected status=deprecated, got {result['status']}"
    assert "deprecation" in result, "missing deprecation info"
    assert result["deprecation"]["migration"], "missing migration hint"
    # DeprecationWarning 应触发
    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1, "deprecated 行业应触发 DeprecationWarning"


def test_v142_unknown_industry_404(v142):
    """未知行业调用 run_pipeline 抛 HTTPException(404)"""
    from fastapi import HTTPException
    req = v142.PipelineRunRequest(lead={}, tenant_id="default")
    with pytest.raises(HTTPException) as exc_info:
        v142.run_pipeline("foobar", req)
    assert exc_info.value.status_code == 404


def test_v142_industries_endpoint(v142):
    """list_pipelines 返回 priority + 完整 active/deprecated 列表"""
    result = v142.list_pipelines()
    assert "data" in result
    data = result["data"]
    # 应包含 active + deprecated 两类
    has_active = any(d.get("priority") in ("primary", "fallback") for d in data)
    has_deprecated = any(d.get("priority") == "deprecated" for d in data)
    assert has_active, "缺少 active 行业"
    assert has_deprecated, "缺少 deprecated 行业"
    # Deprecated 行业不应有 steps
    for d in data:
        if d.get("priority") == "deprecated":
            assert d["steps"] == [], f"{d['industry']} deprecated 应无 steps"


def test_v142_industries_endpoint(v142):
    """list_pipelines 返回 priority + 完整 active/deprecated 列表"""
    result = v142.list_pipelines()
    assert "data" in result
    data = result["data"]
    # 应包含 active + deprecated 两类
    has_active = any(d.get("priority") in ("primary", "fallback") for d in data)
    has_deprecated = any(d.get("priority") == "deprecated" for d in data)
    assert has_active, "缺少 active 行业"
    assert has_deprecated, "缺少 deprecated 行业"
    # Deprecated 行业不应有 steps
    for d in data:
        if d.get("priority") == "deprecated":
            assert d["steps"] == [], f"{d['industry']} deprecated 应无 steps"


# ============ v3_3 员工测试 ============

def test_v3_frontend_count(v3):
    """FRONTEND_EMPLOYEES = 3"""
    assert hasattr(v3, "FRONTEND_EMPLOYEES")
    assert len(v3.FRONTEND_EMPLOYEES) == 3


def test_v3_backend_count(v3):
    """BACKEND_EMPLOYEES = 5"""
    assert hasattr(v3, "BACKEND_EMPLOYEES")
    assert len(v3.BACKEND_EMPLOYEES) == 5


def test_v3_total_8(v3):
    """FRONTEND + BACKEND = 8 = PRESET_EMPLOYEES"""
    total = len(v3.FRONTEND_EMPLOYEES | v3.BACKEND_EMPLOYEES)
    assert total == len(v3.PRESET_EMPLOYEES) == 8


def test_v3_frontend_in_preset(v3):
    """前台 3 员工全在 PRESET_EMPLOYEES"""
    assert v3.FRONTEND_EMPLOYEES <= set(v3.PRESET_EMPLOYEES.keys())


def test_v3_backend_in_preset(v3):
    """后端 5 员工全在 PRESET_EMPLOYEES"""
    assert v3.BACKEND_EMPLOYEES <= set(v3.PRESET_EMPLOYEES.keys())


def test_v3_frontend_disjoint_backend(v3):
    """前台 vs 后端互斥"""
    assert v3.FRONTEND_EMPLOYEES.isdisjoint(v3.BACKEND_EMPLOYEES)


def test_v3_list_includes_tier_field(v3):
    """GET /list 包含 visible_for_user + tier 字段"""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(v3.router)
    client = TestClient(app)
    resp = client.get("/api/v2/employees/list")
    assert resp.status_code == 200
    employees = resp.json()["data"]
    assert len(employees) == 8
    for emp in employees:
        assert "visible_for_user" in emp, f"{emp['id']} 缺 visible_for_user"
        assert "tier" in emp, f"{emp['id']} 缺 tier"
        assert emp["tier"] in ("frontend", "backend")


def test_v3_frontend_list_endpoint(v3):
    """GET /list/frontend 返回 3 个员工"""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(v3.router)
    client = TestClient(app)
    resp = client.get("/api/v2/employees/list/frontend")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_frontend"] == 3
    assert len(data["data"]) == 3
    for emp in data["data"]:
        assert emp["visible_for_user"] is True
        assert emp["tier"] == "frontend"
