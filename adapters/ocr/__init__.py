"""Local OCR using an installed Tesseract binary and tenant-authorized media root.

Never generate synthetic invoice text. No OCR command runs if file containment,
format, size, or configured executable checks fail.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess


def _block(code: str, reason: str) -> dict:
    return {"status": "blocked", "error_code": code, "reason": reason, "mock": False}


class LocalOCREngine:
    EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

    def recognize(self, image_path: str) -> dict:
        root_setting = os.environ.get("CLOUDTECH_OCR_INPUT_ROOT", "")
        if not root_setting:
            return _block("OCR_INPUT_ROOT_NOT_CONFIGURED",
                          "Server has no approved OCR input directory")
        root = Path(root_setting).resolve()
        if not root.is_dir():
            return _block("OCR_INPUT_ROOT_NOT_FOUND",
                          "Configured OCR input directory does not exist")
        if not isinstance(image_path, str) or not image_path:
            return _block("OCR_IMAGE_REQUIRED", "No uploaded image supplied")
        try:
            source = Path(image_path).resolve(strict=True)
        except (FileNotFoundError, OSError, ValueError):
            return _block("OCR_IMAGE_NOT_FOUND", "Uploaded image does not exist")
        if source != root and root not in source.parents:
            return _block("OCR_PATH_OUTSIDE_ALLOWED_ROOT",
                          "Image file is outside tenant-approved OCR storage")
        if not source.is_file() or source.suffix.lower() not in self.EXTENSIONS:
            return _block("OCR_UNSUPPORTED_FORMAT",
                          "Local OCR currently supports image formats, not PDF")
        if source.stat().st_size > 20_000_000:
            return _block("OCR_FILE_TOO_LARGE", "Input exceeds 20MB limit")
        executable = os.environ.get("CLOUDTECH_TESSERACT_BIN") or shutil.which("tesseract")
        if not executable:
            return _block("OCR_BACKEND_NOT_INSTALLED",
                          "Tesseract executable is not installed/configured")
        try:
            result = subprocess.run(
                [executable, str(source), "stdout", "-l", "chi_sim+eng"],
                capture_output=True, text=True, timeout=60, check=False,
                encoding="utf-8", errors="replace",
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return _block("OCR_BACKEND_ERROR", type(exc).__name__)
        if result.returncode != 0:
            return _block("OCR_EXECUTION_FAILED", "Tesseract returned a nonzero exit code")
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        return {
            "status": "completed", "full_text": result.stdout.strip(),
            "engine": "tesseract_local", "file_sha256": sha,
            "provider_called": False, "mock": False,
        }
