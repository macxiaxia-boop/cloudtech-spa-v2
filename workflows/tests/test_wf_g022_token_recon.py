"""Tests for WF-G-022 月度 Token 成本对账 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g022_token_recon import (
    run_token_recon, TokenReconInput, DailyUsage, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_basic_by_provider_aggregation():
    inp = TokenReconInput(
        tenant_id="zq-1",
        month="2026-09",
        daily_usage=[
            DailyUsage(date="2026-09-01", provider="deepseek", tokens=100000, cost_yuan=1.0),
            DailyUsage(date="2026-09-01", provider="openai", tokens=50000, cost_yuan=5.0),
            DailyUsage(date="2026-09-02", provider="deepseek", tokens=200000, cost_yuan=2.0),
        ],
    )
    out = run_token_recon(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["month"] == "2026-09"
    by_p = {r["provider"]: r for r in o["by_provider"]}
    assert by_p["deepseek"]["tokens"] == 300000
    assert by_p["deepseek"]["cost_yuan"] == 3.0
    assert by_p["openai"]["tokens"] == 50000
    assert o["total_tokens"] == 350000
    assert o["total_cost_yuan"] == 8.0


def test_cost_usd_conversion():
    inp = TokenReconInput(
        tenant_id="zq-1",
        month="2026-09",
        fx_usd_yuan=7.0,
        daily_usage=[
            DailyUsage(date="2026-09-01", provider="deepseek", tokens=100, cost_yuan=7.0),
        ],
    )
    out = run_token_recon(inp)
    rows = {r["provider"]: r for r in out["output"]["by_provider"]}
    assert rows["deepseek"]["cost_usd"] == 1.0  # 7.0 / 7.0


def test_anomaly_detection_on_spike():
    inp = TokenReconInput(
        tenant_id="zq-1",
        month="2026-09",
        anomaly_pct=50.0,
        daily_usage=[
            DailyUsage(date=f"2026-09-{d:02d}", provider="deepseek", tokens=100, cost_yuan=1.0)
            for d in range(1, 8)
        ] + [
            # day 8 暴涨 3 倍 → 应触发异常告警
            DailyUsage(date="2026-09-08", provider="deepseek", tokens=100, cost_yuan=3.0),
        ],
    )
    out = run_token_recon(inp)
    o = out["output"]
    assert any("deepseek" in a for a in o["anomalies"])


def test_no_anomaly_when_within_threshold():
    inp = TokenReconInput(
        tenant_id="zq-1",
        month="2026-09",
        daily_usage=[
            DailyUsage(date=f"2026-09-{d:02d}", provider="openai", tokens=100, cost_yuan=10.0)
            for d in range(1, 8)
        ],
    )
    out = run_token_recon(inp)
    assert out["output"]["anomalies"] == []


def test_short_history_skips_anomaly():
    """< 3 日数据不应触发异常检测 (避免误报)"""
    inp = TokenReconInput(
        tenant_id="zq-1",
        month="2026-09",
        daily_usage=[
            DailyUsage(date="2026-09-01", provider="openai", tokens=100, cost_yuan=1.0),
            DailyUsage(date="2026-09-02", provider="openai", tokens=100, cost_yuan=999.0),
        ],
    )
    out = run_token_recon(inp)
    assert out["output"]["anomalies"] == []


def test_invalid_provider_rejected():
    with pytest.raises(ValidationError):
        DailyUsage(date="2026-09-01", provider="random_model", tokens=1, cost_yuan=0.1)


def test_invalid_date_format_rejected():
    with pytest.raises(ValidationError):
        DailyUsage(date="2026/09/01", provider="openai", tokens=1, cost_yuan=0.1)


def test_invalid_month_format_rejected():
    with pytest.raises(ValidationError):
        TokenReconInput(
            tenant_id="zq-1",
            month="2026/09",
            daily_usage=[DailyUsage(date="2026-09-01", provider="openai", tokens=1, cost_yuan=0.1)],
        )


def test_empty_usage_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        TokenReconInput(tenant_id="zq-1", month="2026-09", daily_usage=[])


def test_validate_json_ok():
    res = validate_json(
        '{"tenant_id":"zq-1","month":"2026-09",'
        '"daily_usage":[{"date":"2026-09-01","provider":"openai","tokens":100,"cost_yuan":1.0}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1","month":"2026-09","daily_usage":[]}')
    assert res["ok"] is False


def test_tracker_records_run():
    inp = TokenReconInput(
        tenant_id="zq-tr",
        month="2026-09",
        daily_usage=[DailyUsage(date="2026-09-01", provider="openai", tokens=100, cost_yuan=1.0)],
    )
    out = run_token_recon(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-G-022", tenant_id="zq-tr")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"