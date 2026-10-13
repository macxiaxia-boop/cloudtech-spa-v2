"""Frame Extractor — 使用 ffmpeg 抽取关键帧 (本地 subprocess, 禁止调用网络)"""
import hashlib
import os
import subprocess
import tempfile
from typing import Literal

Frame = dict  # {path, timestamp_ms, hash}


def extract(video_path: str, count: int = 6) -> dict:
    """
    返回 {
        frames: list[Frame],
        extracted_count: int,
        method: 'ffmpeg',
    }

    - 实际调用 ffmpeg (假设用户机器已安装)
    - 失败显式 raise FileNotFoundError / RuntimeError，不静默吞错
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 检查 ffmpeg 是否在 PATH
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        raise FileNotFoundError(
            "ffmpeg 不在 PATH 中，请先安装 ffmpeg: https://ffmpeg.org/download.html"
        )
    except subprocess.CalledProcessError:
        raise RuntimeError("ffmpeg 可执行但调用失败")

    # 创建临时输出目录
    tmp_dir = tempfile.mkdtemp(prefix="ct_frames_")
    frames: list[Frame] = []

    for i in range(count):
        ts_ms = int(1000 * (i + 1) / (count + 1))  # 均匀分布
        out_path = os.path.join(tmp_dir, f"frame_{i:02d}.jpg")

        # -vf "select=eq(n\,N)" 抽第 N 帧; -vsync 0 避免重复帧号
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts_ms / 1000),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            out_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg 抽帧失败 (ts={ts_ms}ms): {result.stderr.strip()}"
            )

        file_hash = hashlib.md5(open(out_path, "rb").read()).hexdigest()
        frames.append({
            "path": out_path,
            "timestamp_ms": ts_ms,
            "hash": file_hash,
        })

    return {
        "frames": frames,
        "extracted_count": len(frames),
        "method": "ffmpeg",
    }


class FrameExtractor:
    def run(self, video_path: str, count: int = 6) -> dict:
        return extract(video_path, count)
