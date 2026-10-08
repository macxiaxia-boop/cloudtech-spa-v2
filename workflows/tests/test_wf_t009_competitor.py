"""Tests for WF-T-009 同城竞品观察 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t009_competitor import (
    run_competitors, CompetitorInput, Competitor, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_inactive_competitor_detected():
    inp = CompetitorInput(
        tenant_id="zq-1", cities=["厦门"], lookback_days=14,
        competitors=[
            Competitor(company="沉睡公司A", platforms=["douyin"], last_update_days=30,
                       estimated_followers=2000),
        ],
    )
    out = run_competitors(inp)
    assert out["status"] == "success"
    signals = out["output"]["signals"]
    assert signals[0]["type"] == "inactive"
    assert signals[0]["severity"] == "info"


def test_high_threat_recent_launch():
    inp = CompetitorInput(
        tenant_id="zq-1", cities=["厦门"], lookback_days=14,
        competitors=[
            Competitor(company="激进派A", platforms=["douyin"], last_update_days=1),
            Competitor(company="激进派B", platforms=["xiaohongshu"], last_update_days=2),
        ],
    )
    out = run_competitors(inp)
    assert out["output"]["threat_level"] == "high"
    assert all(s["severity"] == "high" for s in out["output"]["signals"])


def test_medium_threat_single_launch():
    inp = CompetitorInput(
        tenant_id="zq-1", cities=["厦门"], lookback_days=14,
        competitors=[
            Competitor(company="一家新动作", platforms=["douyin"], last_update_days=1),
            Competitor(company="稳定派", platforms=["douyin"], last_update_days=10),
        ],
    )
    out = run_competitors(inp)
    assert out["output"]["threat_level"] == "medium"


def test_promo_signal():
    inp = CompetitorInput(
        tenant_id="zq-1", cities=["厦门"], lookback_days=14,
        competitors=[
            Competitor(company="打折公司", platforms=["douyin"], last_update_days=5, notes="折扣促销"),
        ],
    )
    out = run_competitors(inp)
    s = out["output"]["signals"][0]
    assert s["type"] == "promo"
    assert s["severity"] == "medium"


def test_low_threat_content_only():
    inp = CompetitorInput(
        tenant_id="zq-1", cities=["厦门"], lookback_days=14,
        competitors=[
            Competitor(company="常规公司", platforms=["douyin"], last_update_days=10, notes="日常更新"),
        ],
    )
    out = run_competitors(inp)
    assert out["output"]["threat_level"] == "low"
    s = out["output"]["signals"][0]
    assert s["type"] == "content"


def test_opportunity_for_small_followers():
    inp = CompetitorInput(
        tenant_id="zq-1", cities=["厦门"], lookback_days=14,
        competitors=[
            Competitor(company="小号公司", platforms=["douyin"], last_update_days=10,
                       estimated_followers=500),
            Competitor(company="大号公司", platforms=["douyin"], last_update_days=10,
                       estimated_followers=50000),
        ],
    )
    out = run_competitors(inp)
    opps = out["output"]["opportunities"]
    # 仅小号公司触发机会
    assert any("小号公司" in o for o in opps)
    assert not any("大号公司" in o for o in opps)


def test_empty_cities_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        CompetitorInput(
            tenant_id="zq-1", cities=[], competitors=[
                Competitor(company="x", last_update_days=5),
            ],
        )


def test_empty_competitors_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        CompetitorInput(tenant_id="zq-1", cities=["厦门"], competitors=[])


def test_validate_json():
    res = validate_json(
        '{"tenant_id":"zq-1","cities":["厦门"],"competitors":[{"company":"x","last_update_days":5}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1","cities":[],"competitors":[{"company":"x","last_update_days":5}]}')
    assert res["ok"] is False


def test_tracker_records_run():
    inp = CompetitorInput(
        tenant_id="zq-tr", cities=["厦门"], competitors=[
            Competitor(company="x", last_update_days=5),
        ],
    )
    out = run_competitors(inp)
    run_id = out["run_id"]
    status = RunHistoryTracker.instance().get_status(run_id)
    assert status["workflow_id"] == "WF-T-009"


def test_total_signals_match_competitors():
    inp = CompetitorInput(
        tenant_id="zq-n", cities=["厦门"],
        competitors=[
            Competitor(company="A", last_update_days=1),
            Competitor(company="B", last_update_days=5),
            Competitor(company="C", last_update_days=20),
        ],
    )
    out = run_competitors(inp)
    assert out["output"]["total_signals"] == 3
