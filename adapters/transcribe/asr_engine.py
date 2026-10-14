"""ASR Engine — 4 个 provider stub (mock-only, 禁止调用真实 ASR API)"""
import hashlib
import os
from typing import Literal

Segment = dict  # {start_ms, end_ms, text, speaker, confidence}


def _mock_segments() -> list[Segment]:
    """统一返回 3 段样本字幕 (0-3000 / 3000-7000 / 7000-12000 ms)"""
    return [
        {"start_ms": 0,    "end_ms": 3000,  "text": "欢迎观看本期内容。",      "speaker": "S1", "confidence": 0.95},
        {"start_ms": 3000, "end_ms": 7000,  "text": "今天我们一起来探讨 AI 的最新发展。", "speaker": "S1", "confidence": 0.93},
        {"start_ms": 7000, "end_ms": 12000, "text": "如果你觉得有帮助，请一键三连。",     "speaker": "S2", "confidence": 0.91},
    ]


def transcribe(
    media_path_or_url: str,
    language: str = "zh",
    provider_hint: str = "auto",
) -> dict:
    """
    返回 {
        segments: list[Segment],
        full_text: str,
        language: str,
        asr_engine: str,   # '<provider>'
        word_count: int,
        mock: True,
    }

    4 provider stub: doubao / whisper_local / kuaishou_asr / jimeng_asr
    - provider_hint='auto' 默认为 doubao
    - 所有 provider 均返回 _mock_segments()，mock=True
    """
    # This implementation generates fixed synthetic subtitles, not real ASR.
    # Prevent an API caller from believing it transcribed the supplied media.
    if not (
        os.environ.get("CLOUDTECH_ENV", "").lower() in {"test", "development"}
        and os.environ.get("CLOUDTECH_ALLOW_MOCK_ASR") == "1"
    ):
        raise RuntimeError(
            "[ASR-MOCK-403] Real ASR provider not connected; mock transcription disabled"
        )
    providers = ["doubao", "whisper_local", "kuaishou_asr", "jimeng_asr"]
    if provider_hint == "auto":
        provider = "doubao"
    elif provider_hint in providers:
        provider = provider_hint
    else:
        # 未知 provider，回退到 doubao
        provider = "doubao"

    segments = _mock_segments()
    full_text = " ".join(s["text"] for s in segments)
    word_count = len(full_text)

    return {
        "segments": segments,
        "full_text": full_text,
        "language": language,
        "asr_engine": provider,
        "word_count": word_count,
        "mock": True,
    }


class ASREngine:
    """暴露给外部的 ASR Engine wrapper"""
    def run(self, media_path_or_url: str, language: str = "zh",
            provider_hint: str = "auto") -> dict:
        return transcribe(media_path_or_url, language, provider_hint)
