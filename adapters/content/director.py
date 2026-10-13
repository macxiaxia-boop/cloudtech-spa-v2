"""CloudTech V4 — 主编排器 (mock-only)"""
from typing import Optional, TypedDict

from .structure_analyzer import analyze, StructureAnalyzer
from .original_script_generator import generate, OriginalScriptGenerator
from .similarity_qc import review, SimilarityQC


class DirectorResult(TypedDict):
    script_text: str
    structure: dict
    qc_result: dict
    mode: str
    mock: bool


def direct(
    goal: str,
    audience: str,
    industry: str,
    source_transcript: Optional[str] = None,
    source_structure: Optional[dict] = None,
) -> DirectorResult:
    """主编排器：goal + 受众 → 串接 analyze → generate → review

    Args:
        goal: 创作目标描述
        audience: 目标受众
        industry: 目标行业
        source_transcript: 原始转写 (可选，缺则走纯原创 stub)
        source_structure: 预分结构 (可选)

    Returns:
        含 script_text / structure / qc_result / mode / mock=True
    """
    if not goal:
        raise ValueError("goal 不能为空")
    if not audience:
        raise ValueError("audience 不能为空")

    if source_transcript:
        # 有转写：走完整 pipeline
        if source_structure is None:
            structure = analyze([], source_transcript)
        else:
            structure = source_structure

        script_data = generate(structure, audience, industry, source_transcript)
        qc_result = review(source_transcript, script_data["script_text"], structure)

        return DirectorResult(
            script_text=script_data["script_text"],
            structure=structure,
            qc_result=qc_result,
            mode="rewrite",
            mock=True,
        )
    else:
        # 纯原创 stub
        stub_script = (
            f"【{industry}】{goal}。"
            f"今天来聊聊为什么这件事对{audience}特别重要。"
            f"如果你觉得有帮助，关注我，下期继续。"
        )
        return DirectorResult(
            script_text=stub_script,
            structure={"mock": True, "structure_template": "unknown"},
            qc_result={
                "similarity_score": 0.0,
                "ngram_overlap": 0.0,
                "flagged_phrases": [],
                "verdict": "pass",
                "notes": "纯原创模式，无原文对比",
                "mock": True,
            },
            mode="original",
            mock=True,
        )


class ContentDirector:
    """主编排器封装"""

    def direct(
        self,
        goal: str,
        audience: str,
        industry: str,
        source_transcript: Optional[str] = None,
        source_structure: Optional[dict] = None,
    ) -> DirectorResult:
        return direct(goal, audience, industry, source_transcript, source_structure)
