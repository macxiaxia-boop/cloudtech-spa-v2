"""SRT/VTT export from user-supplied timed segments, NOT speech recognition.

Consumes externally supplied, already-transcribed segments with timecodes.
Uses CloudTech's existing subtitle formatter to produce actual files' text.
No synthetic speech recognition, model call, or external API is attempted.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from adapters.transcribe.subtitle_formatter import SubtitleFormatter


class SubtitleInputError(ValueError):
    pass


def format_supplied_segments(segments: Any) -> dict:
    if not isinstance(segments, list) or not 1 <= len(segments) <= 2000:
        raise SubtitleInputError("segments must contain 1..2000 timestamped entries")
    clean = []
    last_end = 0
    total_text = 0
    for index, raw in enumerate(segments):
        if not isinstance(raw, dict):
            raise SubtitleInputError(f"segment[{index}] must be an object")
        start = raw.get("start_ms")
        end = raw.get("end_ms")
        value = raw.get("text")
        if (not isinstance(start, int) or isinstance(start, bool)
                or not isinstance(end, int) or isinstance(end, bool)
                or start < last_end or end <= start or end > 86_400_000):
            raise SubtitleInputError(
                f"segment[{index}] needs nonoverlapping ordered integer times (0..24h)"
            )
        if not isinstance(value, str):
            raise SubtitleInputError(f"segment[{index}] text must be a string")
        # Remove cue-structure line breaks and control characters, not words.
        text = " ".join("".join(
            ch if ch >= " " and ch != "\x7f" else " "
            for ch in value
        ).split())
        if not text:
            raise SubtitleInputError(f"segment[{index}] text cannot be empty")
        total_text += len(text)
        if total_text > 120_000:
            raise SubtitleInputError("total subtitle text exceeds 120000 chars")
        clean.append({"start_ms": start, "end_ms": end, "text": text})
        last_end = end

    source_bytes = json.dumps(
        clean, sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    formatters = SubtitleFormatter()
    return {
        "srt": formatters.to_srt(clean),
        "vtt": formatters.to_vtt(clean),
        "segment_count": len(clean),
        "duration_ms": last_end,
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source": "user_supplied_timestamped_transcript",
        "asr_performed": False,
        "model_called": False,
        "mock": False,
    }
