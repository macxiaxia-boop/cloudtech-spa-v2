"""CloudTech V4 — 内容二创 adapters (mock-only, 禁止调用真实 LLM API)"""
from .structure_analyzer import StructureAnalyzer, analyze
from .original_script_generator import OriginalScriptGenerator, generate
from .similarity_qc import SimilarityQC, review
from .director import ContentDirector, direct

__all__ = [
    "StructureAnalyzer", "analyze",
    "OriginalScriptGenerator", "generate",
    "SimilarityQC", "review",
    "ContentDirector", "direct",
]
