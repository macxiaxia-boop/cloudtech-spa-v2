"""Tests for WF-T-010 直播活动准备和复盘 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t010_live import (
    run_live, LivePrepInput, LiveProduct, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_prep_with_all_ok():
    inp = LivePrepInput(
        tenant_id="zq-1", activity_name="双十一直播", planned_start="2026-10-20T19:00:00",
        target_gmv=100000, host="zhinan",
        products=[LiveProduct(sku="sku1", name="主推套餐A", price=9999, stock=100)],
        mode="prep",
    )
    out = run_live(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["mode"] == "prep"
    assert o["retrospective"] is None
    # host 设定 + gmv 设定 + 库存 >0 → 3 项 ok
    statuses = [p["status"] for p in o["prep_checklist"]]
    assert statuses.count("ok") == 3


def test_prep_with_risks():
    inp = LivePrepInput(
        tenant_id="zq-bad", activity_name="无主播", planned_start="2026-10-20T19:00:00",
        target_gmv=0, host="unknown",
        products=[LiveProduct(sku="sku1", name="空库存", price=100, stock=0)],
        mode="prep",
    )
    out = run_live(inp)
    assert out["status"] == "success"
    flags = out["output"]["risk_flags"]
    # 缺主播、缺目标、库存为 0 → 至少 3 个告警
    assert len(flags) >= 3
    statuses = [p["status"] for p in out["output"]["prep_checklist"]]
    assert statuses.count("risk") >= 3


def test_retro_high_attainment():
    inp = LivePrepInput(
        tenant_id="zq-1", activity_name="复盘A", planned_start="2026-10-20T19:00:00",
        target_gmv=10000, host="zhinan",
        products=[LiveProduct(sku="s1", name="A", price=100, stock=10)],
        mode="retro",
        peak_watchers=500, orders=80, actual_gmv=12000,
    )
    out = run_live(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["retrospective"]["orders"] == 80
    assert o["estimated_attainment"] == pytest.approx(1.2, abs=1e-3)
    assert "复制剧本" in o["improvements"][0]


def test_retro_low_attainment_improvements():
    inp = LivePrepInput(
        tenant_id="zq-low", activity_name="不及格直播", planned_start="2026-10-20T19:00:00",
        target_gmv=100000, host="zhinan",
        products=[LiveProduct(sku="s1", name="A", price=100, stock=10)],
        mode="retro",
        peak_watchers=200, orders=10, actual_gmv=30000,
    )
    out = run_live(inp)
    # attainment 0.3 < 0.6
    assert out["output"]["estimated_attainment"] < 0.6
    assert any("预热" in x for x in out["output"]["improvements"])


def test_retro_mid_attainment_suggestion():
    inp = LivePrepInput(
        tenant_id="zq-mid", activity_name="中段直播", planned_start="2026-10-20T19:00:00",
        target_gmv=100000, host="zhinan",
        products=[LiveProduct(sku="s1", name="A", price=100, stock=10)],
        mode="retro",
        peak_watchers=500, orders=40, actual_gmv=75000,
    )
    out = run_live(inp)
    # 0.6 <= 0.75 < 0.9
    assert 0.6 <= out["output"]["estimated_attainment"] < 0.9
    assert any("上架节奏" in x for x in out["output"]["improvements"])


def test_retro_missing_actual_gmv_fails():
    inp = LivePrepInput(
        tenant_id="zq-bad", activity_name="缺数据", planned_start="2026-10-20T19:00:00",
        target_gmv=1000, host="a",
        products=[LiveProduct(sku="s1", name="A", price=100, stock=10)],
        mode="retro",
        # 缺 actual_gmv
    )
    out = run_live(inp)
    assert out["status"] == "failed"
    assert "WF-T010-RETRO" in out["error"]["code"]


def test_empty_products_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        LivePrepInput(
            tenant_id="zq-1", activity_name="x活动", planned_start="2026-10-20T19:00:00",
            host="a", products=[],
        )


def test_invalid_mode_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        LivePrepInput(
            tenant_id="zq-1", activity_name="测试直播", planned_start="2026-10-20T19:00:00",
            host="a", products=[LiveProduct(sku="s1", name="A", price=100, stock=10)],
            mode="invalid",
        )


def test_validate_json():
    res = validate_json(
        '{"tenant_id":"zq-1","activity_name":"测试","planned_start":"2026-10-20T19:00:00","host":"a","products":[{"sku":"s1","name":"A","price":100,"stock":10}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1","activity_name":"x","planned_start":"2026-10-20T19:00:00","host":"a","products":[{"sku":"s1","name":"A","price":100,"stock":10}]}')
    assert res["ok"] is False  # activity_name 太短


def test_conversion_rate_in_retro():
    inp = LivePrepInput(
        tenant_id="zq-cr", activity_name="转化率测试", planned_start="2026-10-20T19:00:00",
        target_gmv=1000, host="a",
        products=[LiveProduct(sku="s1", name="A", price=100, stock=10)],
        mode="retro",
        peak_watchers=200, orders=20, actual_gmv=2000,
    )
    out = run_live(inp)
    # conversion = 20/200 = 0.1
    assert out["output"]["retrospective"]["conversion_rate"] == pytest.approx(0.1, abs=1e-3)


def test_activity_name_min_length():
    """activity_name 必须 >= 2 字符"""
    with pytest.raises(ValidationError):
        LivePrepInput(
            tenant_id="zq-1", activity_name="x", planned_start="2026-10-20T19:00:00",
            host="a", products=[LiveProduct(sku="s1", name="A", price=100, stock=10)],
        )
