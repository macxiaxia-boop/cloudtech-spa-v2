"""Create a real, bounded local ZIP only from caller-selected artifacts.

This is a single-node local exporter, not proof that upstream content,
licensed media or provider outputs exist. It never fetches URLs or calls AI.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
import zipfile
from pathlib import Path

MAX_FILES = 100
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_SINGLE_BYTES = 8 * 1024 * 1024


class LocalZipExportError(ValueError):
    """Caller can correct a blocked export contract without retrying side effects."""


def _safe_member_name(name: object) -> str:
    if not isinstance(name, str) or not name or len(name) > 180:
        raise LocalZipExportError("archive entry name must be 1..180 characters")
    if "\\" in name or "\x00" in name or ":" in name or name.startswith("/"):
        raise LocalZipExportError("archive entry must use a relative POSIX path")
    parts = name.split("/")
    if any(part in ("", ".", "..") or part.endswith((" ", ".")) for part in parts):
        raise LocalZipExportError("archive entry contains an unsafe path segment")
    if len(parts) > 8:
        raise LocalZipExportError("archive entry path nesting exceeds 8 levels")
    if any(part.split(".")[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    } for part in parts):
        raise LocalZipExportError("archive entry contains a Windows device name")
    if name.casefold() == "manifest.json":
        raise LocalZipExportError("manifest.json is reserved for export evidence")
    return name


def _payload_bytes(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    if value is None or isinstance(value, (dict, list, bool, int, float)):
        try:
            return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                               allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
        except (ValueError, TypeError) as exc:
            raise LocalZipExportError("artifact value is not JSON serializable") from exc
    raise LocalZipExportError("artifact must be text, bytes or JSON-compatible data")


def export_zip(inputs: dict) -> dict:
    """Export explicit "files" mapping to a real ZIP with a SHA manifest.

    Provide an existing "output_dir" for persistent handoff. If omitted,
    writes to a new isolated temp directory, marked TEMPORARY in the result.
    Never implicitly archives arbitrary input fields, secret files or URLs.
    """
    if not isinstance(inputs, dict):
        raise LocalZipExportError("export input must be an object")
    files = inputs.get("files")
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise LocalZipExportError("files must be a nonempty mapping of at most 100 artifacts")
    members = []
    total = 0
    folded = set()
    for name, value in files.items():
        name = _safe_member_name(name)
        if name.casefold() in folded:
            raise LocalZipExportError("duplicate archive path on case-insensitive filesystems")
        folded.add(name.casefold())
        body = _payload_bytes(value)
        total += len(body)
        if len(body) > MAX_SINGLE_BYTES or total > MAX_TOTAL_BYTES:
            raise LocalZipExportError("artifact size exceeds the local export safety limit")
        members.append((name, body))
    output_dir = inputs.get("output_dir")
    if output_dir is None:
        folder = Path(tempfile.mkdtemp(prefix="cloudtech-export-"))
        storage = "LOCAL_TEMPORARY"
    else:
        if not isinstance(output_dir, str) or not output_dir.strip():
            raise LocalZipExportError("output_dir must be an existing directory path")
        folder = Path(output_dir)
        if not folder.is_dir():
            raise LocalZipExportError("output_dir does not exist or is not a directory")
        storage = "LOCAL_EXPLICIT_DIRECTORY"
    result_path = folder / f"cloudtech-{uuid.uuid4().hex}.zip"
    manifest_files = [
        {"name": name, "sha256": hashlib.sha256(body).hexdigest(), "size": len(body)}
        for name, body in sorted(members)
    ]
    manifest = (json.dumps({"schema": "cloudtech.local-zip.v1", "files": manifest_files},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    created = False
    try:
        with os.fdopen(os.open(str(result_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as target:
            created = True
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=6, allowZip64=False) as archive:
                for name, body in sorted(members):
                    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    archive.writestr(info, body, compress_type=zipfile.ZIP_DEFLATED)
                info = zipfile.ZipInfo("manifest.json", (1980, 1, 1, 0, 0, 0))
                archive.writestr(info, manifest, compress_type=zipfile.ZIP_DEFLATED)
            target.flush()
            os.fsync(target.fileno())
    except Exception:
        if created:
            result_path.unlink(missing_ok=True)
        raise
    archive_sha256 = hashlib.sha256(result_path.read_bytes()).hexdigest()
    return {"status": "completed", "mock": False, "package": str(result_path),
            "sha256": archive_sha256, "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "file_count": len(members), "files": manifest_files, "storage": storage,
            "provider_called": False, "production_ready": False}
