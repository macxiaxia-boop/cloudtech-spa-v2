"""CloudTech V4 — 原创脚本生成 (mock-only)"""
from typing import TypedDict


class GenerateResult(TypedDict):
    script_text: str
    hook: str
    body: str
    cta: str
    similarity_estimate: float
    novelty_markers: list[str]
    mock: bool


def _length_similarity(original: str, derivative: str) -> float:
    """长度相似度启发式"""
    if not original or not derivative:
        return 0.0
    r = len(derivative) / max(len(original), 1)
    return max(0.0, min(1.0, r))


def generate(
    structure: dict,
    target_audience: str,
    target_industry: str,
    original_transcript: str,
    provider=None,
) -> GenerateResult:
    """输入结构 + 受众 + 行业 → 原创脚本

    Args:
        structure: analyze() 返回的结构字典
        target_audience: 目标受众描述
        target_industry: 目标行业
        original_transcript: 原始转写文本
        provider: LLM provider(传入则用 LLM 推理)

    Returns:
        含 script_text / hook / body / cta / similarity_estimate / novelty_markers
    """
    if not structure:
        raise ValueError("structure 不能为空")
    if not target_audience:
        raise ValueError("target_audience 不能为空")

    # LLM 路径
    if provider is not None and provider.is_available():
        try:
            from adapters.llm import LLMRequest
            hook_text = structure.get("hook", {}).get("text", "")
            req = LLMRequest(
                prompt=f"基于结构:{structure}\n\n目标受众:{target_audience}\n目标行业:{target_industry}\n\n生成原创脚本。",
                system="你是原创脚本生成专家。生成与原文结构相似但内容原创的新脚本。",
                metadata={"task": "script", "audience": target_audience, "industry": target_industry},
            )
            resp = provider.generate(req)
            return GenerateResult(
                script_text=resp.text,
                hook=resp.text.split("\n\n")[0] if "\n\n" in resp.text else resp.text[:80],
                body="\n\n".join(resp.text.split("\n\n")[1:-1]) if "\n\n" in resp.text else "",
                cta=resp.text.split("\n\n")[-1] if "\n\n" in resp.text else "关注我",
                similarity_estimate=_length_similarity(original_transcript, resp.text),
                novelty_markers=[
                    f"audience:{target_audience}",
                    f"industry:{target_industry}",
                    "llm-derived",
                    f"provider:{provider.name}",
                ],
                mock=resp.mock,
            )
        except Exception:
            pass

    hook_tpl = (
        f"【{target_industry}】"
        f"{structure.get('hook', {}).get('text', '你知道吗')}，"
        f"其实很多人都不知道"
    )
    body_tpl = (
        f"对于{target_audience}来说，"
        f"最关键的是"
        f"{'、'.join([s['text'][:15] for s in structure.get('body_segments', [])[:3]] or ['找到正确的方法'])}。"
        f"今天我来给你详细拆解。"
    )
    cta_tpl = (
        f"如果你觉得有帮助，"
        f"赶紧关注我，"
        f"下期我们继续聊{target_industry}的核心干货。"
    )

    script_text = f"{hook_tpl}\n\n{body_tpl}\n\n{cta_tpl}"

    novelty_markers = [
        f"audience:{target_audience}",
        f"industry:{target_industry}",
        "mock-generation",
        f"template:{structure.get('structure_template', 'unknown')}",
    ]

    similarity_estimate = _length_similarity(original_transcript, script_text)

    return GenerateResult(
        script_text=script_text,
        hook=hook_tpl,
        body=body_tpl,
        cta=cta_tpl,
        similarity_estimate=similarity_estimate,
        novelty_markers=novelty_markers,
        mock=True,
    )


class OriginalScriptGenerator:
    """原创脚本生成器封装"""

    def generate(
        self, structure: dict, target_audience: str, target_industry: str, original_transcript: str
    ) -> GenerateResult:
        return generate(structure, target_audience, target_industry, original_transcript)
