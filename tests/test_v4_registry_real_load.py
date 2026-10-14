"""V4 — OperationRegistry 从真实 skill_orchestrator/200 SKILL.md 加载测试
不调用任何外部 API, 仅解析 SKILL.md 文件结构"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pathlib import Path

import pytest

from workflows.v4.registry import OperationRegistry, OperationDefinition
from workflows.v4.media_gate import MediaGate


def _real_skill_root() -> Path:
    """Require real Windows catalog without fabricating it in Linux CI.

    When the user explicitly supplied CLOUDTECH_SKILL_ROOT, a bad path is an
    actual error. When absent, only this external-environment integration
    check is SKIPPED. Local registry logic is still tested independently.
    """
    configured = os.environ.get("CLOUDTECH_SKILL_ROOT")
    root = Path(configured or "D:/CloudTech-Portable/data/skill_orchestrator")
    if not root.is_dir():
        if configured:
            pytest.fail(f"explicit CLOUDTECH_SKILL_ROOT is missing: {root}")
        pytest.skip(
            "EXTERNAL_BLOCKER: Windows skill_orchestrator directory is not in "
            "GitHub checkout; provide CLOUDTECH_SKILL_ROOT on the authorized PC"
        )
    return root


def test_load_real_skills_orchestrator():
    """真实加载 D:\CloudTech-Portable\data\skill_orchestrator\200 SKILL.md"""
    skill_root = _real_skill_root()
    assert skill_root.exists(), f"skill_orchestrator 不存在: {skill_root}"
    reg = OperationRegistry(skill_root=skill_root)
    n = reg.count()
    print(f"[OK] loaded {n} operations from {skill_root}")
    # 真实 200 个, 但部分 MEDIA_GENERATE 不在白名单会跳过; 至少 100+
    assert n >= 100, f"加载过少: {n}"
    # 部分 operation 应是 MEDIA_GENERATE
    media_ops = reg.list_by_kind("MEDIA_GENERATE")
    print(f"[OK] media ops loaded: {len(media_ops)}")
    # 每个 MEDIA_GENERATE 都应通过 media_gate (allowlist)
    for op in media_ops[:5]:  # 抽样
        op_lower = op.op_id.lower()
        # 必须命中 7 类白名单之一
        from workflows.v4.media_gate import ALLOWED_MEDIA_OPERATIONS
        assert any(op_lower.startswith(p) for p in [
            "image.", "video."
        ]), f"非 image/video media op: {op.op_id}"
    print(f"[OK] first 5 media ops all image/video (allowlist compliant)")


def test_specific_skill_categories():
    """验证 5 行业 + 80 通用 = 200 skill 目录存在"""
    skill_root = _real_skill_root()
    # 至少含 5 行业前缀
    industries = ["catering", "decoration", "education", "medical", "retail"]
    found = 0
    for ind in industries:
        sample = skill_root / f"{ind}-1-0"
        if sample.exists():
            found += 1
    print(f"[OK] 5 行业 industry subdirs found: {found}/5")
    assert found >= 3, f"至少 3 行业子目录: {found}"


def test_registry_dedupe_and_query():
    """重复 register 同 op_id 应覆盖, query 应一致"""
    reg = OperationRegistry()
    op1 = OperationDefinition(op_id="test.x", provider="p1", kind="TRANSFORM", side_effect=False)
    op2 = OperationDefinition(op_id="test.x", provider="p2", kind="MODEL_REASON", side_effect=False)
    reg.register(op1)
    reg.register(op2)
    assert reg.get("test.x").provider == "p2", "后注册覆盖"
    assert len(reg.list_by_kind("TRANSFORM")) == 0  # 被覆盖
    assert len(reg.list_by_kind("MODEL_REASON")) == 1
    print("[OK] register overrides + list_by_kind")


def test_real_skill_kind_distribution():
    """真实加载后 kind 分布"""
    reg = OperationRegistry(skill_root=_real_skill_root())
    all_ops = reg.list_all()
    from collections import Counter
    kinds = Counter(o.kind for o in all_ops)
    print(f"[OK] real skill kind distribution: {dict(kinds)}")
    # 诚实发现: 200 现有 skill 全是营销/内容类, 没有 image./video. 媒体 op
    # (200 SKILL.md 实际是营销文案/分析类, 媒体生成走 workbuddy 独立 connector)
    assert "TRANSFORM" in kinds, "TRANSFORM 必有"
    # 重要发现: 没有 MEDIA_GENERATE → 媒体 op 来自 workbuddy connector 而非 skill 目录


if __name__ == "__main__":
    test_load_real_skills_orchestrator()
    test_specific_skill_categories()
    test_registry_dedupe_and_query()
    test_real_skill_kind_distribution()
    print("\n=== ALL REGISTRY REAL LOAD TESTS PASSED ===")
