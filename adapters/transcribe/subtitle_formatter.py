"""Subtitle Formatter — 输出 SRT / VTT (mock-only)"""
from typing import Literal

Segment = dict  # {start_ms, end_ms, text, speaker, confidence}


def _ms_to_srt_time(ms: int) -> str:
    """毫秒 → SRT 时间格式 00:00:00,000"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    micro = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{micro:03d}"


def _ms_to_vtt_time(ms: int) -> str:
    """毫秒 → VTT 时间格式 00:00:00.000"""
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    micro = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{micro:03d}"


def to_srt(segments: list[Segment]) -> str:
    """
    将 segments 转为 SRT 格式字符串 (BOM-free UTF-8)。

    SRT 格式:
    1
    00:00:00,000 --> 00:03:00,000
    文本行

    空行分隔。
    """
    lines: list[str] = []
    for i, seg in enumerate(segments, 1):
        start = _ms_to_srt_time(seg["start_ms"])
        end   = _ms_to_srt_time(seg["end_ms"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")   # 空行
    return "\n".join(lines)


def to_vtt(segments: list[Segment]) -> str:
    """
    将 segments 转为 WebVTT 格式字符串 (BOM-free UTF-8)。

    VTT 格式:
    WEBVTT

    00:00:00.000 --> 00:03:00.000
    文本行

    空行分隔。
    """
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _ms_to_vtt_time(seg["start_ms"])
        end   = _ms_to_vtt_time(seg["end_ms"])
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")   # 空行
    return "\n".join(lines)


class SubtitleFormatter:
    def to_srt(self, segments: list[Segment]) -> str:
        return to_srt(segments)

    def to_vtt(self, segments: list[Segment]) -> str:
        return to_vtt(segments)
