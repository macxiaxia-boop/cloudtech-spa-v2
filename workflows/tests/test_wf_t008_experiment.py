"""Tests for WF-T-008 实验对照与 SOP 候选 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t008_experiment import (
    run_experiment, ExperimentInput, Experiment, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_winner_b_when_significant():
    inp = ExperimentInput(
        tenant_id="zq-1",
        experiments=[
            Experiment(
                name="落地页颜色 A/B", hypothesis="红色按钮提高 20% 转化",
                variant_a="蓝色", variant_b="红色",
                sample_size=500, metric_a=10.0, metric_b=15.0,
            ),
        ],
    )
    out = run_experiment(inp)
    assert out["status"] == "success"
    r = out["output"]["results"][0]
    assert r["winner"] == "B"
    assert r["lift_pct"] > 0
    assert len(out["output"]["sop_candidates"]) == 1
    assert "红色" in out["output"]["sop_candidates"][0]["title"]


def test_winner_a_when_a_better():
    inp = ExperimentInput(
        tenant_id="zq-1",
        experiments=[
            Experiment(
                name="文案 A/B", hypothesis="短标题更好",
                variant_a="短标题", variant_b="长标题",
                sample_size=400, metric_a=20.0, metric_b=8.0,
            ),
        ],
    )
    out = run_experiment(inp)
    r = out["output"]["results"][0]
    assert r["winner"] == "A"
    assert r["lift_pct"] > 100  # 大幅领先


def test_inconclusive_when_small_sample():
    inp = ExperimentInput(
        tenant_id="zq-1",
        experiments=[
            Experiment(
                name="小样本", hypothesis="X 更好",
                variant_a="A", variant_b="B",
                sample_size=20, metric_a=5.0, metric_b=6.0,
            ),
        ],
    )
    out = run_experiment(inp)
    r = out["output"]["results"][0]
    assert r["winner"] == "inconclusive"
    assert r["sample_adequate"] is False
    assert out["output"]["sop_candidates"] == []  # 不足不生成 SOP


def test_multiple_experiments():
    inp = ExperimentInput(
        tenant_id="zq-multi",
        experiments=[
            Experiment(name="E1", hypothesis="h1", variant_a="A", variant_b="B",
                       sample_size=300, metric_a=10, metric_b=14),
            Experiment(name="E2", hypothesis="h2", variant_a="A", variant_b="B",
                       sample_size=50, metric_a=5, metric_b=5.5),
            Experiment(name="E3", hypothesis="h3", variant_a="A", variant_b="B",
                       sample_size=400, metric_a=8, metric_b=3),
        ],
    )
    out = run_experiment(inp)
    assert out["output"]["total"] == 3
    winners = [r["winner"] for r in out["output"]["results"]]
    # E1 显著 B 胜, E2 样本不足, E3 显著 A 胜
    assert "B" in winners and "A" in winners and "inconclusive" in winners


def test_empty_experiments_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        ExperimentInput(tenant_id="zq-1", experiments=[])


def test_invalid_sample_size_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        Experiment(
            name="x", hypothesis="h", variant_a="A", variant_b="B",
            sample_size=0, metric_a=1, metric_b=2,
        )


def test_sop_candidate_confidence():
    inp = ExperimentInput(
        tenant_id="zq-conf",
        experiments=[
            Experiment(name="高置信", hypothesis="h", variant_a="A", variant_b="B",
                       sample_size=1000, metric_a=10, metric_b=20),
        ],
    )
    out = run_experiment(inp)
    sop = out["output"]["sop_candidates"][0]
    # 高样本 + 大差距 → high or medium confidence
    assert sop["confidence"] in ("high", "medium")


def test_validate_json():
    res = validate_json(
        '{"tenant_id":"zq-1","experiments":[{"name":"E1","hypothesis":"h","variant_a":"A","variant_b":"B","sample_size":100,"metric_a":1.0,"metric_b":2.0}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1","experiments":[]}')
    assert res["ok"] is False


def test_tracker_records_run():
    inp = ExperimentInput(
        tenant_id="zq-tr",
        experiments=[
            Experiment(name="E1", hypothesis="h", variant_a="A", variant_b="B",
                       sample_size=200, metric_a=5, metric_b=8),
        ],
    )
    out = run_experiment(inp)
    run_id = out["run_id"]
    status = RunHistoryTracker.instance().get_status(run_id)
    assert status["workflow_id"] == "WF-T-008"
    assert status["status"] == "success"


def test_p_value_decreases_with_sample():
    """大样本 → 更小 p_value"""
    inp_small = ExperimentInput(
        tenant_id="zq-s",
        experiments=[Experiment(name="E", hypothesis="h", variant_a="A", variant_b="B",
                                sample_size=50, metric_a=10, metric_b=15)],
    )
    inp_large = ExperimentInput(
        tenant_id="zq-l",
        experiments=[Experiment(name="E", hypothesis="h", variant_a="A", variant_b="B",
                                sample_size=2000, metric_a=10, metric_b=15)],
    )
    p_small = run_experiment(inp_small)["output"]["results"][0]["p_value_estimate"]
    p_large = run_experiment(inp_large)["output"]["results"][0]["p_value_estimate"]
    assert p_large <= p_small
