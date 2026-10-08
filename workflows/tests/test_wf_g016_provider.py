"""Tests for WF-G-016 Provider 真实调用与对账 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g016_provider import (
    run_provider, ProviderInput, ProviderCall, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_provider_perfect_match_no_dispute():
    """reported == expected → 0 drift → no dispute"""
    inp = ProviderInput(
        tenant_id="zq-1",
        calls=[
            ProviderCall(
                call_id="c1", provider="deepseek", model="deepseek-chat",
                tokens_in=1000, tokens_out=2000,
                unit_price_in=0.001, unit_price_out=0.002,
                reported_cost_yuan=0.001 * 1 + 0.002 * 2,  # 0.005
            ),
        ],
        drift_threshold_pct=5.0,
    )
    out = run_provider(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["total_calls"] == 1
    assert o["reconciled"][0]["drift_pct"] == 0.0
    assert o["reconciled"][0]["dispute"] is False
    assert len(o["audit_disputes"]) == 0


def test_provider_large_drift_triggers_dispute():
    inp = ProviderInput(
        tenant_id="zq-1",
        calls=[
            ProviderCall(
                call_id="c1", provider="openai", model="gpt-4o",
                tokens_in=1000, tokens_out=2000,
                unit_price_in=0.01, unit_price_out=0.03,
                reported_cost_yuan=0.05,  # expected = 0.01+0.06=0.07, 报告少报 → drift < 0
            ),
        ],
        drift_threshold_pct=5.0,
    )
    out = run_provider(inp)
    o = out["output"]
    assert o["reconciled"][0]["dispute"] is True
    assert "c1" in o["audit_disputes"][0]
    # expected=0.07 reported=0.05, drift=-28.57%
    assert o["reconciled"][0]["drift_pct"] < 0


def test_provider_multiple_calls_aggregation():
    inp = ProviderInput(
        tenant_id="zq-1",
        calls=[
            ProviderCall(call_id="a", provider="deepseek", model="m1",
                         tokens_in=1000, tokens_out=1000,
                         unit_price_in=0.001, unit_price_out=0.002, reported_cost_yuan=0.003),
            ProviderCall(call_id="b", provider="openai", model="gpt-4o",
                         tokens_in=2000, tokens_out=2000,
                         unit_price_in=0.01, unit_price_out=0.02, reported_cost_yuan=0.06),
        ],
    )
    out = run_provider(inp)
    o = out["output"]
    assert o["total_calls"] == 2
    # total expected = 0.003 + 0.06 = 0.063
    assert o["total_expected_yuan"] == pytest.approx(0.06, abs=0.01)


def test_provider_usd_conversion():
    """用大额让 round 不至于变 0"""
    inp = ProviderInput(
        tenant_id="zq-1",
        fx_usd_yuan=7.2,
        calls=[
            ProviderCall(call_id="x", provider="mock", model="m",
                         tokens_in=100000, tokens_out=200000,
                         unit_price_in=0.001, unit_price_out=0.002, reported_cost_yuan=0.5),
        ],
    )
    out = run_provider(inp)
    o = out["output"]
    # expected = 100*0.001 + 200*0.002 = 0.5
    assert o["total_expected_yuan"] == pytest.approx(0.5, abs=0.01)
    # USD = 0.5/7.2 ≈ 0.0694 → round 2 位 = 0.07
    assert o["total_cost_usd"] == pytest.approx(0.07, abs=1e-2)


def test_provider_invalid_provider_rejected():
    with pytest.raises(ValidationError):
        ProviderCall(call_id="x", provider="unknown_provider", model="m",
                     tokens_in=10, tokens_out=10,
                     unit_price_in=0.01, unit_price_out=0.01)


def test_provider_empty_calls_rejected_pydantic():
    """min_length=1 → pydantic 直接拒"""
    with pytest.raises(ValidationError):
        ProviderInput(tenant_id="zq-1", calls=[])


def test_provider_fx_out_of_range():
    with pytest.raises(ValidationError):
        ProviderInput(tenant_id="zq-1", fx_usd_yuan=100.0)  # le=20


def test_provider_drift_just_under_threshold():
    """drift ~4% < 5% 阈值 → 不算 dispute"""
    inp = ProviderInput(
        tenant_id="zq-1",
        drift_threshold_pct=5.0,
        calls=[
            ProviderCall(call_id="c", provider="deepseek", model="m",
                         tokens_in=10000, tokens_out=0,
                         unit_price_in=0.01, unit_price_out=0.01, reported_cost_yuan=0.104),
            # expected = 0.1, reported = 0.104, drift ≈ +4.0% — 不超阈值
        ],
    )
    out = run_provider(inp)
    assert out["output"]["reconciled"][0]["dispute"] is False


def test_provider_drift_just_above_threshold():
    """drift ~5.5% > 5% 阈值 → 算 dispute"""
    inp = ProviderInput(
        tenant_id="zq-1",
        drift_threshold_pct=5.0,
        calls=[
            ProviderCall(call_id="c", provider="deepseek", model="m",
                         tokens_in=10000, tokens_out=0,
                         unit_price_in=0.01, unit_price_out=0.01, reported_cost_yuan=0.1055),
        ],
    )
    out = run_provider(inp)
    assert out["output"]["reconciled"][0]["dispute"] is True


def test_provider_audit_dispute_message_format():
    inp = ProviderInput(
        tenant_id="zq-1",
        calls=[
            ProviderCall(call_id="ZZZ", provider="doubao", model="m",
                         tokens_in=1000, tokens_out=1000,
                         unit_price_in=0.001, unit_price_out=0.002,
                         reported_cost_yuan=0.001),  # 极低，巨大漂移
        ],
    )
    out = run_provider(inp)
    msg = out["output"]["audit_disputes"][0]
    assert "ZZZ" in msg
    assert "drift" in msg


def test_provider_reported_greater_than_expected_positive_drift():
    """reported > expected → drift > 0"""
    inp = ProviderInput(
        tenant_id="zq-1",
        calls=[
            ProviderCall(call_id="over", provider="openai", model="m",
                         tokens_in=1000, tokens_out=0,
                         unit_price_in=0.01, unit_price_out=0.01,
                         reported_cost_yuan=0.02),  # expected=0.01, reported=0.02 → +100%
        ],
    )
    out = run_provider(inp)
    assert out["output"]["reconciled"][0]["drift_pct"] > 0


def test_validate_json_ok():
    res = validate_json('{"tenant_id":"zq-1","calls":[{"call_id":"c1","provider":"mock","model":"m","tokens_in":10,"tokens_out":10,"unit_price_in":0.01,"unit_price_out":0.01}]}')
    assert res["ok"] is True
