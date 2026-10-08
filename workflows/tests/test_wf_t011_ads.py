"""Tests for WF-T-011 广告只读复盘与预算建议 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t011_ads import (
    run_ads, AdsInput, AdCampaign, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_healthy_portfolio():
    inp = AdsInput(
        tenant_id="zq-1", budget_total=50000, target_roi=2.0,
        campaigns=[
            AdCampaign(campaign_id="c1", name="主力投放", platform="douyin",
                       spend=10000, impressions=200000, clicks=2000,
                       conversions=100, revenue=30000),  # ROI=3
            AdCampaign(campaign_id="c2", name="次要投放", platform="xiaohongshu",
                       spend=5000, impressions=80000, clicks=800,
                       conversions=30, revenue=12000),  # ROI=2.4
        ],
    )
    out = run_ads(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["total_spend"] == 15000
    assert o["total_revenue"] == 42000
    # blended ROI = 42000/15000 = 2.8
    assert o["blended_roi"] == pytest.approx(2.8, abs=0.01)
    # 两个都 ≥ target_roi=2 → scale
    verdicts = [r["verdict"] for r in o["roi_by_campaign"]]
    assert verdicts == ["scale", "scale"]


def test_mixed_verdicts():
    inp = AdsInput(
        tenant_id="zq-mix", budget_total=20000, target_roi=2.0,
        campaigns=[
            AdCampaign(campaign_id="c1", name="盈利", platform="douyin",
                       spend=5000, conversions=20, revenue=15000),  # ROI=3
            AdCampaign(campaign_id="c2", name="持平", platform="xiaohongshu",
                       spend=3000, conversions=10, revenue=4000),   # ROI=1.33 (hold)
            AdCampaign(campaign_id="c3", name="亏损", platform="tencent",
                       spend=4000, conversions=5, revenue=2000),    # ROI=0.5 (pause)
        ],
    )
    out = run_ads(inp)
    verdicts = {r["campaign_id"]: r["verdict"] for r in out["output"]["roi_by_campaign"]}
    assert verdicts == {"c1": "scale", "c2": "hold", "c3": "pause"}


def test_low_roi_recommendation():
    inp = AdsInput(
        tenant_id="zq-low", budget_total=10000, target_roi=2.0,
        campaigns=[
            AdCampaign(campaign_id="c1", name="x", platform="douyin",
                       spend=8000, conversions=10, revenue=12000),  # ROI=1.5
        ],
    )
    out = run_ads(inp)
    recs = out["output"]["recommendations"]
    # blended ROI 1.5 < 2 → 应建议优化
    assert any("ROI" in r for r in recs)


def test_budget_reallocation_logic():
    inp = AdsInput(
        tenant_id="zq-alloc", budget_total=10000, target_roi=2.0,
        campaigns=[
            AdCampaign(campaign_id="c1", name="scale", platform="douyin",
                       spend=3000, conversions=10, revenue=9000),  # ROI=3
            AdCampaign(campaign_id="c2", name="pause", platform="xiaohongshu",
                       spend=4000, conversions=5, revenue=1000),   # ROI=0.25
        ],
    )
    out = run_ads(inp)
    realloc = out["output"]["budget_reallocation"]
    # paused_pool = 4000, scale_pool_base = 3000
    assert realloc["from_paused_pool"] == 4000
    assert realloc["keep_buffer"] == 2000  # 4000 * 0.5
    # to_scale_pool = 3000 + 4000*0.5 = 5000
    assert realloc["to_scale_pool"] == 5000


def test_cpa_calculation():
    inp = AdsInput(
        tenant_id="zq-cpa", budget_total=1000, target_roi=2.0,
        campaigns=[
            AdCampaign(campaign_id="c1", name="x", platform="douyin",
                       spend=1000, conversions=10, revenue=3000),
        ],
    )
    out = run_ads(inp)
    row = out["output"]["roi_by_campaign"][0]
    # CPA = 1000/10 = 100
    assert row["cpa"] == 100.0
    assert row["roi"] == 3.0


def test_zero_budget_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        AdsInput(
            tenant_id="zq-0", budget_total=0,
            campaigns=[AdCampaign(campaign_id="c1", name="x", platform="douyin", spend=0)],
        )


def test_empty_campaigns_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        AdsInput(tenant_id="zq-1", budget_total=1000, campaigns=[])


def test_invalid_platform_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        AdCampaign(campaign_id="c1", name="x", platform="weibo", spend=100)


def test_validate_json():
    res = validate_json(
        '{"tenant_id":"zq-1","budget_total":1000,"campaigns":[{"campaign_id":"c1","name":"x","platform":"douyin","spend":100}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json(
        '{"tenant_id":"zq-1","budget_total":0,"campaigns":[{"campaign_id":"c1","name":"x","platform":"douyin","spend":100}]}'
    )
    assert res["ok"] is False


def test_tracker_records_run():
    inp = AdsInput(
        tenant_id="zq-tr", budget_total=1000,
        campaigns=[AdCampaign(campaign_id="c1", name="x", platform="douyin",
                               spend=100, conversions=1, revenue=200)],
    )
    out = run_ads(inp)
    run_id = out["run_id"]
    status = RunHistoryTracker.instance().get_status(run_id)
    assert status["workflow_id"] == "WF-T-011"


def test_readonly_no_side_effects():
    """验证: 不会触发任何外部 API 调用 (mock 模式, 仅校验 input 完整执行)"""
    inp = AdsInput(
        tenant_id="zq-ros", budget_total=1000,
        campaigns=[AdCampaign(campaign_id="c1", name="x", platform="douyin",
                               spend=100, conversions=1, revenue=200)],
    )
    out = run_ads(inp)
    # 应有 success 返回, 不抛异常
    assert out["status"] == "success"
    # 没有外部副作用字段
    assert "external_api_called" not in str(out)
