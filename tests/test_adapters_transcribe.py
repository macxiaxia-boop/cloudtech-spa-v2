"""tests/test_adapters_transcribe.py — CloudTech V4 WP-VIDEO-TRANSCRIBE adapter 测试"""
import os
import re
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.transcribe.asr_engine import transcribe, ASREngine
from adapters.transcribe.diarizer import diarize
from adapters.transcribe.frame_extractor import extract, FrameExtractor
from adapters.transcribe.subtitle_formatter import to_srt, to_vtt


# ─── ASR Engine ────────────────────────────────────────────────────────────────

class TestASREngine4Providers:
    """4 个 provider stub 均返回相同 typed contract"""

    @pytest.mark.parametrize("provider", [
        "doubao", "whisper_local", "kuaishou_asr", "jimeng_asr"
    ])
    def test_transcribe_returns_typed_contract(self, provider):
        result = transcribe("mock_video.mp4", language="zh", provider_hint=provider)
        assert isinstance(result, dict)
        assert "segments" in result
        assert "full_text" in result
        assert "language" in result
        assert "asr_engine" in result
        assert "word_count" in result
        assert result["mock"] is True

    @pytest.mark.parametrize("provider", [
        "doubao", "whisper_local", "kuaishou_asr", "jimeng_asr"
    ])
    def test_segments_3_items_with_required_fields(self, provider):
        result = transcribe("mock_video.mp4", provider_hint=provider)
        segs = result["segments"]
        assert len(segs) == 3
        for seg in segs:
            assert "start_ms" in seg
            assert "end_ms" in seg
            assert "text" in seg
            assert "speaker" in seg
            assert "confidence" in seg

    @pytest.mark.parametrize("provider", [
        "doubao", "whisper_local", "kuaishou_asr", "jimeng_asr"
    ])
    def test_asr_engine_field_value(self, provider):
        result = transcribe("mock_video.mp4", provider_hint=provider)
        assert result["asr_engine"] == provider

    def test_auto_defaults_to_doubao(self):
        result = transcribe("mock.mp4", provider_hint="auto")
        assert result["asr_engine"] == "doubao"

    def test_unknown_provider_falls_back_to_doubao(self):
        result = transcribe("mock.mp4", provider_hint="unknown_vendor")
        assert result["asr_engine"] == "doubao"

    def test_word_count_matches_full_text(self):
        result = transcribe("mock.mp4")
        assert result["word_count"] == len(result["full_text"])


# ─── Frame Extractor ──────────────────────────────────────────────────────────

class TestFrameExtractor:
    """ffmpeg 真实调用 (若 ffmpeg 不可用则跳过)"""

    @pytest.fixture
    def skip_if_no_ffmpeg(self):
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("ffmpeg 不在 PATH，跳过帧提取测试")

    def test_extract_returns_typed_contract(self, skip_if_no_ffmpeg, tmp_path):
        # 创建占位视频文件 (MMVideo 魔影工厂可生成的最小 mp4 头)
        dummy = tmp_path / "dummy.mp4"
        # 用 ffmpeg 生成 1 秒纯色视频
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
            "-c:v", "libx264", "-t", "1",
            str(dummy),
        ], capture_output=True, check=True)

        result = extract(str(dummy), count=4)

        assert isinstance(result, dict)
        assert "frames" in result
        assert "extracted_count" in result
        assert result["method"] == "ffmpeg"
        assert len(result["frames"]) == 4

    def test_extract_frames_have_required_fields(self, skip_if_no_ffmpeg, tmp_path):
        dummy = tmp_path / "dummy.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
            "-c:v", "libx264", "-t", "1",
            str(dummy),
        ], capture_output=True, check=True)

        result = extract(str(dummy), count=3)
        for frame in result["frames"]:
            assert "path" in frame
            assert "timestamp_ms" in frame
            assert "hash" in frame

    def test_extract_nonexistent_video_raises(self):
        with pytest.raises(FileNotFoundError):
            extract("nonexistent_video_file.mp4", count=3)

    def test_extract_negative_count(self, skip_if_no_ffmpeg, tmp_path):
        dummy = tmp_path / "dummy.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1",
            "-c:v", "libx264", "-t", "1",
            str(dummy),
        ], capture_output=True, check=True)
        result = extract(str(dummy), count=0)
        assert result["extracted_count"] == 0


# ─── Diarizer ─────────────────────────────────────────────────────────────────

class TestDiarizer:
    def test_diarize_adds_speaker(self):
        segments = [
            {"start_ms": 0, "end_ms": 1000, "text": "第一句", "speaker": "", "confidence": 0.9},
            {"start_ms": 1000, "end_ms": 2000, "text": "第二句", "speaker": "", "confidence": 0.9},
        ]
        result = diarize(segments)
        assert result[0]["speaker"] == "S1"
        assert result[1]["speaker"] == "S2"

    def test_diarize_alternates_s1_s2(self):
        segments = [{"start_ms": i*1000, "end_ms": (i+1)*1000,
                     "text": f"第{i}句", "speaker": "", "confidence": 0.9}
                   for i in range(6)]
        diarize(segments)
        speakers = [s["speaker"] for s in segments]
        assert speakers == ["S1", "S2", "S1", "S2", "S1", "S2"]


# ─── Subtitle Formatter ───────────────────────────────────────────────────────

class TestSubtitleFormatter:
    @pytest.fixture
    def sample_segments(self):
        return [
            {"start_ms": 0,    "end_ms": 3000,  "text": "欢迎观看。",    "speaker": "S1", "confidence": 0.95},
            {"start_ms": 3000, "end_ms": 7000,  "text": "今天聊 AI 最新发展。", "speaker": "S1", "confidence": 0.93},
            {"start_ms": 7000, "end_ms": 12000, "text": "有帮助请三连。",   "speaker": "S2", "confidence": 0.91},
        ]

    def test_srt_format_correct(self, sample_segments):
        srt = to_srt(sample_segments)
        lines = srt.split("\n")
        # 序号行
        assert "1" in lines[0]
        assert "-->" in lines[1]
        assert "00:00:00,000 --> 00:00:03,000" == lines[1]
        assert "欢迎观看。" == lines[2]

    def test_srt_three_entries(self, sample_segments):
        srt = to_srt(sample_segments)
        # 3 个序号
        assert srt.count("\n\n") >= 2
        entries = srt.strip().split("\n\n")
        assert len(entries) == 3

    def test_vtt_format_correct(self, sample_segments):
        vtt = to_vtt(sample_segments)
        lines = vtt.split("\n")
        assert lines[0] == "WEBVTT"
        assert "-->" in lines[2]
        assert "00:00:00.000 --> 00:00:03.000" == lines[2]

    def test_vtt_three_entries(self, sample_segments):
        vtt = to_vtt(sample_segments)
        entries = vtt.strip().split("\n\n")
        # entries[0] = "WEBVTT" header; entries[1..3] = 3 subtitle entries
        assert len(entries) == 4

    def test_srt_bom_free_utf8(self, sample_segments):
        srt = to_srt(sample_segments)
        assert not srt.startswith("﻿")

    def test_vtt_bom_free_utf8(self, sample_segments):
        vtt = to_vtt(sample_segments)
        assert not vtt.startswith("﻿")
