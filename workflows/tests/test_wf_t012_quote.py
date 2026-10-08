"""Tests for WF-T-012 客户问题归类与报价辅助 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_t012_quote import (
    run_quote, QuoteInput, CustomerQuestion, PricingConfig, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_pricing_question_with_area():
    inp = QuoteInput(
        tenant_id="zq-1",
        questions=[
            CustomerQuestion(qid="q1", content="装修大概多少钱？",
                             city="厦门", declared_intent="pricing", room_area_sqm=80.0),
        ],
    )
    out = run_quote(inp)
    assert out["status"] == "success"
    cat = out["output"]["categorized"][0]
    assert cat["detected_type"] == "pricing"
    # 有 room_area > 0 → 生成报价草稿
    drafts = out["output"]["quote_drafts"]
    assert len(drafts) == 1
    assert drafts[0]["qid"] == "q1"
    # base = 1500 * 80 * 1.0 = 120000
    # price_low = 120000*0.85 = 102000
    # price_high = 120000*1.15 = 138000
    assert drafts[0]["price_low"] == 102000.0
    assert drafts[0]["price_high"] == 138000.0


def test_timeline_classification():
    inp = QuoteInput(
        tenant_id="zq-1",
        questions=[
            CustomerQuestion(qid="q1", content="装修一般要几个月？", city="厦门"),
        ],
    )
    out = run_quote(inp)
    cat = out["output"]["categorized"][0]
    assert cat["detected_type"] == "timeline"


def test_urgency_high():
    inp = QuoteInput(
        tenant_id="zq-1",
        questions=[
            CustomerQuestion(qid="q1", content="我急着要马上装修", city="厦门"),
        ],
    )
    out = run_quote(inp)
    assert out["output"]["categorized"][0]["urgency"] == "high"


def test_urgency_low():
    inp = QuoteInput(
        tenant_id="zq-1",
        questions=[
            CustomerQuestion(qid="q1", content="先了解了解再说", city="厦门"),
        ],
    )
    out = run_quote(inp)
    assert out["output"]["categorized"][0]["urgency"] == "low"


def test_renovation_included_full_package():
    inp = QuoteInput(
        tenant_id="zq-1",
        pricing_config=PricingConfig(base_per_sqm=1500, renovation_included=True, city_modifier=1.2),
        questions=[
            CustomerQuestion(qid="q1", content="全包多少钱？", city="厦门", room_area_sqm=100.0),
        ],
    )
    out = run_quote(inp)
    draft = out["output"]["quote_drafts"][0]
    # 全包 should include 主材
    assert "主材" in draft["includes"]
    assert "全包" in draft["package_name"]
    # base = 1500*100*1.2 = 180000
    assert draft["price_low"] == 153000.0  # 180000*0.85
    assert draft["price_high"] == 207000.0  # 180000*1.15


def test_legal_question():
    """纯法律问题: 不含 timeline 关键词"""
    inp = QuoteInput(
        tenant_id="zq-1",
        questions=[
            CustomerQuestion(qid="q1", content="合同条款有问题，违约责任怎么算？", city="厦门"),
        ],
    )
    out = run_quote(inp)
    cat = out["output"]["categorized"][0]
    assert cat["detected_type"] == "legal"


def test_other_fallback():
    inp = QuoteInput(
        tenant_id="zq-1",
        questions=[
            CustomerQuestion(qid="q1", content="你们家是做什么的？", city="厦门"),
        ],
    )
    out = run_quote(inp)
    assert out["output"]["categorized"][0]["detected_type"] == "other"


def test_no_draft_when_no_area():
    inp = QuoteInput(
        tenant_id="zq-1",
        questions=[
            CustomerQuestion(qid="q1", content="价格多少", city="厦门", room_area_sqm=0),
        ],
    )
    out = run_quote(inp)
    # 检测到 pricing 但 area=0 → 不生成 draft
    assert out["output"]["quote_drafts"] == []


def test_empty_questions_rejected_by_pydantic():
    with pytest.raises(ValidationError):
        QuoteInput(tenant_id="zq-1", questions=[])


def test_validate_json():
    res = validate_json(
        '{"tenant_id":"zq-1","questions":[{"qid":"q1","content":"价格","city":"厦门"}]}'
    )
    assert res["ok"] is True


def test_validate_json_bad_content():
    res = validate_json(
        '{"tenant_id":"zq-1","questions":[{"qid":"q1","content":"x","city":"厦门"}]}'
    )
    assert res["ok"] is False  # content min_length=2


def test_multiple_questions():
    inp = QuoteInput(
        tenant_id="zq-multi",
        questions=[
            CustomerQuestion(qid="q1", content="价格？", room_area_sqm=80),
            CustomerQuestion(qid="q2", content="多久？"),
            CustomerQuestion(qid="q3", content="设计？"),
        ],
    )
    out = run_quote(inp)
    assert out["output"]["total"] == 3
    # 只有 q1 满足 pricing+area → 1 draft
    assert len(out["output"]["quote_drafts"]) == 1
