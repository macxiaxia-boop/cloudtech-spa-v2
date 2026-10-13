"""Diarizer — 说话人识别 stub (mock-only)"""
from typing import Literal

Segment = dict  # {start_ms, end_ms, text, speaker, confidence}


def diarize(segments: list[Segment]) -> list[Segment]:
    """
    为每段添加 speaker 字段 (mock: 交替 S1/S2)。

    返回添加了 speaker 的 segments 列表 (原地修改 + 返回同一对象)。
    """
    speakers = ["S1", "S2"]
    for i, seg in enumerate(segments):
        seg["speaker"] = speakers[i % len(speakers)]
    return segments


class Diarizer:
    def run(self, segments: list[Segment]) -> list[Segment]:
        return diarize(segments)
