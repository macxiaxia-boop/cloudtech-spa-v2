"""Tests for WF-G-018 会议纪要形成任务 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g018_meeting import (
    run_meeting, MeetingInput, Transcript, Utterance, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def _basic_transcript(texts=("需要跟进", "OK 决定")):
    return Transcript(
        meeting_id="mtg-1",
        title="周会",
        duration_min=30,
        utterances=[Utterance(speaker=f"speaker-{i}", text=t) for i, t in enumerate(texts)],
    )


def test_happy_path_with_decisions_and_actions():
    inp = MeetingInput(
        tenant_id="zq-1",
        transcript=_basic_transcript(("决定本周完成 demo", "需要张三跟进客户对接")),
    )
    out = run_meeting(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["meeting_id"] == "mtg-1"
    assert len(o["decisions"]) >= 1
    assert len(o["action_items"]) >= 1
    # 没有 auto_create → 不生成 task id
    assert o["created_task_ids"] == []


def test_auto_create_generates_task_ids():
    inp = MeetingInput(
        tenant_id="zq-1",
        auto_create=True,
        transcript=_basic_transcript(("需要立刻处理紧急客诉", "安排后续沟通")),
    )
    out = run_meeting(inp)
    o = out["output"]
    assert len(o["created_task_ids"]) == len(o["action_items"])
    assert all(tid.startswith("task-mtg-1-") for tid in o["created_task_ids"])


def test_p0_priority_for_urgent():
    inp = MeetingInput(
        tenant_id="zq-1",
        transcript=_basic_transcript(("需要立刻处理服务器宕机",)),
    )
    out = run_meeting(inp)
    actions = out["output"]["action_items"]
    assert len(actions) == 1
    assert actions[0]["priority"] == "P0"
    assert actions[0]["due"] == "T+3"


def test_p1_priority_default():
    inp = MeetingInput(
        tenant_id="zq-1",
        transcript=_basic_transcript(("需要跟进客户问题",)),
    )
    out = run_meeting(inp)
    actions = out["output"]["action_items"]
    assert actions[0]["priority"] == "P1"
    assert actions[0]["due"] == "T+7"


def test_summary_includes_meeting_metadata():
    inp = MeetingInput(
        tenant_id="zq-1",
        transcript=_basic_transcript(),
    )
    out = run_meeting(inp)
    summary = out["output"]["summary"]
    assert "周会" in summary
    assert "30 分钟" in summary
    assert "2 位参会者" in summary


def test_empty_utterances_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        Transcript(meeting_id="m", title="t", utterances=[])


def test_duration_validation():
    with pytest.raises(ValidationError):
        Transcript(meeting_id="m", title="t", duration_min=0, utterances=[Utterance(speaker="s", text="x")])


def test_utterance_text_too_short_rejected():
    with pytest.raises(ValidationError):
        Utterance(speaker="s", text="")


def test_validate_json_ok():
    res = validate_json(
        '{"tenant_id":"zq-1","transcript":{"meeting_id":"m","title":"t","duration_min":30,'
        '"utterances":[{"speaker":"s","text":"需要跟进"}]}}'
    )
    assert res["ok"] is True


def test_validate_json_bad():
    res = validate_json('{"tenant_id":"zq-1"}')  # missing transcript
    assert res["ok"] is False


def test_tracker_records_run():
    inp = MeetingInput(tenant_id="zq-tr", transcript=_basic_transcript(("决定 X",)))
    out = run_meeting(inp)
    runs = RunHistoryTracker.instance().list_runs(workflow_id="WF-G-018", tenant_id="zq-tr")
    assert len(runs) == 1
    assert runs[0]["status"] == "success"