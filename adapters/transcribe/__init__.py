"""CloudTech V4 — 视频转写 adapters (mock-only, 禁止调用真实 ASR API)"""
from .asr_engine import transcribe, ASREngine
from .frame_extractor import extract, FrameExtractor
from .diarizer import diarize, Diarizer
from .subtitle_formatter import to_srt, to_vtt, SubtitleFormatter

__all__ = [
    "ASREngine", "transcribe",
    "FrameExtractor", "extract",
    "Diarizer", "diarize",
    "SubtitleFormatter", "to_srt", "to_vtt",
]
