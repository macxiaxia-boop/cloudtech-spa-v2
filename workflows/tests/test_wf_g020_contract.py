"""Tests for WF-G-020 合同陪跑验收 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g020_contract import (
    run_contract, ContractInput, Clause, Milestone, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_pass_verdict_low_risk():
    inp = ContractInput(
        tenant_id="zq-1",
        contract_id="ct-1",
        clauses=[
            Clause(cid="c1", text="明确约定首付款 30%", type="payment"),
            Clause(cid="c2", text="交付日期明确约定", type="delivery"),
        ],
    )
    out = run_contract(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["verdict"] == "pass"
    assert o["total_risk_score"] == 0


def test_high_risk_penalty_clause_detected():
    inp = ContractInput(
        tenant_id="zq-1",
        contract_id="ct-2",
        clauses=[
            Clause(cid="c1", text="违约金 30%", type="penalty"),
        ],
    )
    out = run_contract(inp)
    o = out["output"]
    assert any(c["risk_level"] == "high" for c in o["clause_checks"])
    assert o["verdict"] in ("conditional", "reject")


def test_reject_verdict_many_high_risks():
    inp = ContractInput(
        tenant_id="zq-1",
        contract_id="ct-3",
        clauses=[
            Clause(cid=f"c{i}", text="违约金条款", type="penalty")
            for i in range(5)
        ],
    )
    out = run_contract(inp)
    assert out["output"]["verdict"] == "reject"


def test_milestone_progress_counts():
    inp = ContractInput(
        tenant_id="zq-1",
        contract_id="ct-4",
        clauses=[Clause(cid="c1", text="标准付款条款", type="payment")],
        milestones=[
            Milestone(mid="m1", name="设计", due_date="2099-12-31", completed=True),
            Milestone(mid="m2", name="施工", due_date="2099-12-31", completed=False),
            Milestone(mid="m3", name="验收", due_date="2099-12-31", completed=False),
        ],
    )
    out = run_contract(inp)
    mp = out["output"]["milestone_progress"]
    assert mp["completed"] == 1
    assert mp["pending"] == 2


def test_invalid_clause_type_rejected():
    with pytest.raises(ValidationError):
        Clause(cid="c1", text="条款", type="unknown_type")


def test_empty_clauses_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        ContractInput(tenant_id="zq-1", contract_id="ct", clauses=[])


def test_clause_text_min_length():
    with pytest.raises(ValidationError):
        Clause(cid="c1", text="")


def test_validate_json_ok():
    res = validate_json(
        '{"tenant_id":"zq-1","contract_id":"ct-1",'
        '"clauses":[{"cid":"c1","text":"付款条款","type":"payment"}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1"}')  # 缺 contract_id/clauses
    assert res["ok"] is False


def test_tracker_records_run():
    inp = ContractInput(
        tenant_id="zq-tr",
        contract_id="ct",
        clauses=[Clause(cid="c1", text="标准条款", type="payment")],
    )
    out = run_contract(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-G-020", tenant_id="zq-tr")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"