"""Tests for WF-T-006 线索跟进提醒 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t006_followup import (
    run_followup, FollowupInput, FollowupEntry, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_overdue_detection():
    inp = FollowupInput(
        tenant_id="zq-1", sla_hours=24,
        now_iso="2026-10-08T12:00:00+00:00",
        leads=[
            FollowupEntry(lead_name="老客户A", last_contact_at="2026-10-06T10:00:00+00:00",
                          assigned_to="alice", status="open"),
        ],
    )
    out = run_followup(inp)
    assert out["status"] == "success"
    assert out["output"]["overdue"] == 1
    assert out["output"]["reminders"][0]["reminder_type"] == "overdue"
    assert out["output"]["reminders"][0]["suggested_action"] == "立即电话回访 (已超时)"


def test_due_soon_detection():
    inp = FollowupInput(
        tenant_id="zq-1", sla_hours=24,
        now_iso="2026-10-08T12:00:00+00:00",
        leads=[
            # 距 last 约 20 小时 (>24*0.75=18, <24)
            FollowupEntry(lead_name="待回访B", last_contact_at="2026-10-07T16:00:00+00:00",
                          assigned_to="bob", status="open"),
        ],
    )
    out = run_followup(inp)
    assert out["status"] == "success"
    assert out["output"]["due_soon"] == 1
    assert out["output"]["reminders"][0]["reminder_type"] == "due_soon"


def test_closed_lead_ignored():
    inp = FollowupInput(
        tenant_id="zq-1", sla_hours=24,
        now_iso="2026-10-08T12:00:00+00:00",
        leads=[
            FollowupEntry(lead_name="已成交", last_contact_at="2026-10-01T00:00:00+00:00",
                          assigned_to="alice", status="closed"),
        ],
    )
    out = run_followup(inp)
    # closed 状态不计入
    assert out["output"]["total"] == 0
    assert out["output"]["overdue"] == 0
    assert out["output"]["due_soon"] == 0


def test_mixed_statuses():
    inp = FollowupInput(
        tenant_id="zq-mix", sla_hours=24,
        now_iso="2026-10-08T12:00:00+00:00",
        leads=[
            # overdue: 84 小时 (3.5天)
            FollowupEntry(lead_name="overdue1", last_contact_at="2026-10-05T00:00:00+00:00",
                          assigned_to="alice", status="open"),
            # due_soon: 19 小时 (>18, <24)  (2026-10-07T17:00:00 → 2026-10-08T12:00:00)
            FollowupEntry(lead_name="due_soon1", last_contact_at="2026-10-07T17:00:00+00:00",
                          assigned_to="bob", status="open"),
            # on_track: 6 小时
            FollowupEntry(lead_name="on_track1", last_contact_at="2026-10-08T06:00:00+00:00",
                          assigned_to="carol", status="open"),
        ],
    )
    out = run_followup(inp)
    o = out["output"]
    assert o["overdue"] == 1
    assert o["due_soon"] == 1
    assert o["on_track"] == 1
    assert o["total"] == 3


def test_empty_leads_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        FollowupInput(tenant_id="zq-1", sla_hours=24, leads=[])


def test_invalid_now_iso_fails():
    inp = FollowupInput(
        tenant_id="zq-bad", sla_hours=24,
        now_iso="not-a-date",
        leads=[FollowupEntry(lead_name="x", last_contact_at="2026-10-08T00:00:00+00:00",
                              assigned_to="alice")],
    )
    out = run_followup(inp)
    assert out["status"] == "failed"
    assert "WF-T006-NOW" in out["error"]["code"]


def test_sla_hours_lower_bound_rejected():
    with pytest.raises(ValidationError):
        FollowupInput(tenant_id="zq-1", sla_hours=0,
                       leads=[FollowupEntry(lead_name="x", last_contact_at="2026-10-08T00:00:00+00:00",
                                             assigned_to="a")])


def test_validate_json():
    res = validate_json('{"tenant_id":"zq-1","sla_hours":24,"leads":[{"lead_name":"x","last_contact_at":"2026-10-08T00:00:00Z","assigned_to":"a"}]}')
    assert res["ok"] is True


def test_validate_json_bad_sla():
    res = validate_json('{"tenant_id":"zq-1","sla_hours":0,"leads":[{"lead_name":"x","last_contact_at":"2026-10-08T00:00:00Z","assigned_to":"a"}]}')
    assert res["ok"] is False


def test_stage_preserved_in_reminder():
    inp = FollowupInput(
        tenant_id="zq-stage", sla_hours=12,
        now_iso="2026-10-08T12:00:00+00:00",
        leads=[
            FollowupEntry(lead_name="决策阶段", last_contact_at="2026-10-07T00:00:00+00:00",
                          assigned_to="alice", status="open", stage="decision"),
        ],
    )
    out = run_followup(inp)
    assert out["output"]["reminders"][0]["stage"] == "decision"


def test_lost_status_also_ignored():
    inp = FollowupInput(
        tenant_id="zq-lost", sla_hours=24,
        now_iso="2026-10-08T12:00:00+00:00",
        leads=[
            FollowupEntry(lead_name="流失", last_contact_at="2026-10-01T00:00:00+00:00",
                          assigned_to="alice", status="lost"),
        ],
    )
    out = run_followup(inp)
    assert out["output"]["total"] == 0
