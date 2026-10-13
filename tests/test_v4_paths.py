"""V4 paths contract validation 测试"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workflows.v4.contract import validate_definition, validate_inputs, ContractError, InputSpec, StepSpec
from workflows.v4.paths import FLAGSHIP_PATHS, get_path, list_paths
from workflows.v4.media_gate import MediaGate, MediaGateError


def test_six_flagship_paths_registered():
    assert len(FLAGSHIP_PATHS) == 6
    print(f"[OK] flagship paths count = {len(FLAGSHIP_PATHS)}")


def test_each_path_has_min_steps():
    for pid, defn in FLAGSHIP_PATHS.items():
        assert len(defn.steps) >= 3, f"{pid} 步骤数过少 ({len(defn.steps)})"
    print("[OK] each_path_min_3_steps")


def test_each_path_has_quality_gates():
    for pid, defn in FLAGSHIP_PATHS.items():
        assert len(defn.quality_gates) >= 1, f"{pid} 缺质量门"
    print("[OK] each_path_has_quality_gates")


def test_each_path_has_recovery():
    for pid, defn in FLAGSHIP_PATHS.items():
        assert "retry_failed_only" in defn.recovery or defn.recovery, f"{pid} 缺 recovery"
    print("[OK] each_path_has_recovery")


def test_media_steps_pass_gate():
    """每个含 MEDIA_GENERATE 节点的路径, 必须通过 MediaGate"""
    for pid, defn in FLAGSHIP_PATHS.items():
        for step in defn.steps:
            if step.cost_class == "METERED_MEDIA":
                try:
                    MediaGate.check(step.operation, step.cost_class)
                except MediaGateError as e:
                    raise AssertionError(f"{pid}/{step.id} 媒体门禁失败: {e}")
    print("[OK] all_media_steps_pass_gate")


def test_input_validation_missing_role():
    defn = get_path("WP-BLOGGER-RESEARCH")
    missing = validate_inputs(defn, {"homepage_url": "x"})  # 缺 target_industry
    assert any("target_industry" in m for m in missing)
    print(f"[OK] missing_role_detected → {missing}")


def test_input_validation_complete():
    defn = get_path("WP-BLOGGER-RESEARCH")
    provided = {"homepage_url": "x", "target_industry": "decoration"}
    missing = validate_inputs(defn, provided)
    assert missing == []
    print("[OK] complete_inputs_no_missing")


def test_revision_consistency():
    for pid, defn in FLAGSHIP_PATHS.items():
        assert defn.revision >= 1
        assert defn.id == pid
    print("[OK] revision>=1 + id_consistency")


def test_evidence_field_present():
    for pid, defn in FLAGSHIP_PATHS.items():
        assert defn.evidence, f"{pid} 缺 evidence"
    print("[OK] each_path_has_evidence")


def test_billing_policy_valid():
    valid = {"FREE_LOCAL", "METERED_NONMEDIA", "METERED_MEDIA", "EXTERNAL_WRITE", "MIXED"}
    for pid, defn in FLAGSHIP_PATHS.items():
        assert defn.billing_policy in valid, f"{pid} billing_policy={defn.billing_policy} 非法"
    print("[OK] billing_policy_valid")


def test_serialization_round_trip():
    for pid, defn in FLAGSHIP_PATHS.items():
        d = defn.to_dict()
        restored = validate_definition(d)
        assert restored.id == pid
        assert restored.revision == defn.revision
        assert len(restored.steps) == len(defn.steps)
    print("[OK] serialization_round_trip")


if __name__ == "__main__":
    test_six_flagship_paths_registered()
    test_each_path_has_min_steps()
    test_each_path_has_quality_gates()
    test_each_path_has_recovery()
    test_media_steps_pass_gate()
    test_input_validation_missing_role()
    test_input_validation_complete()
    test_revision_consistency()
    test_evidence_field_present()
    test_billing_policy_valid()
    test_serialization_round_trip()
    print("\n=== ALL PATHS CONTRACT TESTS PASSED ===")
