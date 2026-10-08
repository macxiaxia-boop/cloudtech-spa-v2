"""Tests for WF-T-007 获客漏斗与周复盘 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t007_funnel import (
    run_funnel, FunnelInput, FunnelData, validate_json, validate_yaml,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_happy_healthy_funnel():
    inp = FunnelInput(
        tenant_id="zq-1", week_start="2026-10-06",
        current=FunnelData(impressions=10000, clicks=500, leads=50, quotes=15, contracts=5),
        last_week=FunnelData(impressions=8000, clicks=400, leads=40, quotes=12, contracts=4),
    )
    out = run_funnel(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["week_start"] == "2026-10-06"
    assert len(o["stages"]) == 5
    # overall = 5/10000 = 0.0005
    assert o["overall_conversion"] == pytest.approx(0.0005, abs=1e-6)


def test_alert_low_click_to_lead():
    inp = FunnelInput(
        tenant_id="zq-low", week_start="2026-10-06",
        current=FunnelData(impressions=10000, clicks=500, leads=10, quotes=5, contracts=2),
    )
    out = run_funnel(inp)
    alerts = out["output"]["drop_off_alerts"]
    # click→lead = 10/500 = 0.02 < 0.05 → 触发告警
    assert any("点击" in a and "线索" in a for a in alerts)


def test_alert_low_quote_to_contract():
    inp = FunnelInput(
        tenant_id="zq-low2", week_start="2026-10-06",
        current=FunnelData(impressions=10000, clicks=800, leads=100, quotes=50, contracts=5),
    )
    out = run_funnel(inp)
    alerts = out["output"]["drop_off_alerts"]
    # quote→contract = 5/50 = 0.1 < 0.2 → 告警
    assert any("报价" in a and "合同" in a for a in alerts)


def test_week_over_week_decline_alert():
    inp = FunnelInput(
        tenant_id="zq-decline", week_start="2026-10-06",
        current=FunnelData(impressions=5000, clicks=200, leads=20, quotes=8, contracts=2),
        last_week=FunnelData(impressions=10000, clicks=400, leads=40, quotes=16, contracts=4),
    )
    out = run_funnel(inp)
    alerts = out["output"]["drop_off_alerts"]
    # 各项都下降 50%, 应触发周环比告警
    assert any("周环比" in a for a in alerts)


def test_no_alert_when_growing():
    inp = FunnelInput(
        tenant_id="zq-up", week_start="2026-10-06",
        current=FunnelData(impressions=10000, clicks=600, leads=60, quotes=20, contracts=8),
        last_week=FunnelData(impressions=8000, clicks=400, leads=30, quotes=10, contracts=4),
    )
    out = run_funnel(inp)
    # 健康增长, 无告警
    assert out["output"]["drop_off_alerts"] == []
    assert "整体健康" in out["output"]["weekly_summary"]


def test_invalid_date_format_rejected():
    with pytest.raises(ValidationError):
        FunnelInput(
            tenant_id="zq-1", week_start="2026/10/06",
            current=FunnelData(),
        )


def test_top_priority_action_set():
    inp = FunnelInput(
        tenant_id="zq-prio", week_start="2026-10-06",
        current=FunnelData(impressions=10000, clicks=500, leads=10, quotes=5, contracts=1),
    )
    out = run_funnel(inp)
    # 有告警时 top_priority_action 是第一条告警
    assert out["output"]["top_priority_action"] != "维持当前节奏, 重点扩量 awareness"


def test_validate_json():
    res = validate_json('{"tenant_id":"zq-1","week_start":"2026-10-06","current":{"impressions":1000,"clicks":50}}')
    assert res["ok"] is True


def test_validate_json_bad_date():
    res = validate_json('{"tenant_id":"zq-1","week_start":"2026/10/06","current":{}}')
    assert res["ok"] is False


def test_validate_yaml():
    res = validate_yaml("tenant_id: zq-1\nweek_start: '2026-10-06'\ncurrent: {impressions: 1000}\n")
    assert res["ok"] is True


def test_validate_yaml_bad_date():
    res = validate_yaml("tenant_id: zq-1\nweek_start: '2026/10/06'\ncurrent: {}\n")
    assert res["ok"] is False


def test_tracker_records_run():
    inp = FunnelInput(
        tenant_id="zq-tr", week_start="2026-10-06",
        current=FunnelData(impressions=100, clicks=10, leads=2, quotes=1, contracts=1),
    )
    out = run_funnel(inp)
    run_id = out["run_id"]
    status = RunHistoryTracker.instance().get_status(run_id)
    assert status["status"] == "success"
    assert status["workflow_id"] == "WF-T-007"


def test_conversion_rates_chain():
    """验证 conversion_rate 链式: click/imp, lead/click, quote/lead, contract/quote"""
    inp = FunnelInput(
        tenant_id="zq-cr", week_start="2026-10-06",
        current=FunnelData(impressions=1000, clicks=100, leads=10, quotes=5, contracts=1),
    )
    out = run_funnel(inp)
    stages = {s["stage"]: s for s in out["output"]["stages"]}
    assert stages["impressions"]["conversion_rate"] == 1.0
    assert stages["clicks"]["conversion_rate"] == pytest.approx(0.1)
    assert stages["leads"]["conversion_rate"] == pytest.approx(0.1)
    assert stages["quotes"]["conversion_rate"] == pytest.approx(0.5)
    assert stages["contracts"]["conversion_rate"] == pytest.approx(0.2)
