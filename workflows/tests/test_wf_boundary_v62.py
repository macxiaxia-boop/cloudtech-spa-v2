"""V6.2 boundary case tests for workflow modules (Galois/74).

Adds 8 cross-workflow boundary cases:
- Empty / oversized input handling
- Unicode tenant_ids
- Negative numbers
- Extreme sample sizes
- Idempotency under repeat runs

Per the WF-T-001 DiagnosisInput pydantic model:
  - tenant_id must match ^zq-
  - target_revenue must be > 0
  - current_revenue must be >= 0
  - sample_size must be 1..500
  - industry must be in {decoration, medical, education, catering, retail}
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from workflows.base import RunHistoryTracker


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_workflow_runs_with_empty_tenant_id_rejected():
    """Empty tenant_id rejected by pydantic (ValidationError) — no crash."""
    from workflows.impl.wf_t001_diagnosis import run_diagnosis, DiagnosisInput
    raised = False
    try:
        DiagnosisInput(tenant_id="", industry="decoration", target_revenue=1000)
    except Exception:
        raised = True  # pydantic.ValidationError or similar
    assert raised, "expected ValidationError for empty tenant_id"


def test_workflow_runs_with_unicode_tenant_id():
    """Unicode in zq-prefixed tenant_id must round-trip."""
    from workflows.impl.wf_t001_diagnosis import run_diagnosis, DiagnosisInput
    inp = DiagnosisInput(
        tenant_id="zq-客户_中文_🏠_001",
        industry="decoration",
        target_revenue=100000, current_revenue=50000,
    )
    out = run_diagnosis(inp)
    assert out["status"] == "success"
    assert inp.tenant_id == "zq-客户_中文_🏠_001"  # round-trip via input


def test_workflow_with_extreme_sample_size_capped():
    """sample_size > 500 rejected by pydantic (no crash)."""
    from workflows.impl.wf_t001_diagnosis import DiagnosisInput
    raised = False
    try:
        DiagnosisInput(
            tenant_id="zq-extreme", industry="decoration",
            target_revenue=1000000, sample_size=1_000_000,
        )
    except Exception:
        raised = True
    assert raised, "expected ValidationError for sample_size > 500"


def test_workflow_with_zero_target_revenue_rejected():
    """target_revenue=0 rejected (gt=0)."""
    from workflows.impl.wf_t001_diagnosis import DiagnosisInput
    raised = False
    try:
        DiagnosisInput(
            tenant_id="zq-zero-tgt", industry="decoration",
            target_revenue=0,
        )
    except Exception:
        raised = True
    assert raised, "expected ValidationError for target_revenue=0"


def test_workflow_with_negative_revenue_rejected():
    """Negative current_revenue rejected (ge=0)."""
    from workflows.impl.wf_t001_diagnosis import DiagnosisInput
    raised = False
    try:
        DiagnosisInput(
            tenant_id="zq-neg-rev", industry="decoration",
            target_revenue=100000, current_revenue=-50000,
        )
    except Exception:
        raised = True
    assert raised, "expected ValidationError for negative revenue"


def test_workflow_idempotency_same_input_same_output():
    """Same input -> same output (deterministic)."""
    from workflows.impl.wf_t001_diagnosis import run_diagnosis, DiagnosisInput
    inp = DiagnosisInput(
        tenant_id="zq-idem-1", industry="medical",
        target_revenue=1000000, current_revenue=300000, sample_size=100,
    )
    out1 = run_diagnosis(inp)
    out2 = run_diagnosis(inp)
    for key in ("diagnosis_score", "funnel_health", "revenue_gap_pct"):
        assert out1["output"][key] == out2["output"][key]


def test_workflow_validate_json_empty_object():
    """validate_json on empty {} -> ok=False (required fields missing)."""
    from workflows.impl.wf_t001_diagnosis import validate_json
    res = validate_json("{}")
    assert res["ok"] is False


def test_workflow_validate_yaml_malformed():
    """validate_yaml on garbage -> ok=False (no exception)."""
    from workflows.impl.wf_t001_diagnosis import validate_yaml
    res = validate_yaml("@#$%^&*INVALID@@YAML@@:::")
    assert res["ok"] is False
