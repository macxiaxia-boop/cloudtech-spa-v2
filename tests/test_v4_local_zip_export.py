"""Actual artifact bytes, integrity and safety tests (no external providers)."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from workflows.v4.local_zip_export import LocalZipExportError, export_zip


def test_real_zip_with_text_json_binary_manifest(tmp_path):
    contents = {"scripts/intro.txt": "你好 CloudTech", "meta/output.json": {"num": 3},
                "media/logo.bin": b"\x00\xfe\xff"}
    result = export_zip({"files": contents, "output_dir": str(tmp_path)})
    assert result["mock"] is False and result["status"] == "completed"
    assert result["file_count"] == 3 and result["provider_called"] is False
    assert result["production_ready"] is False
    blob = Path(result["package"]).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == result["sha256"]
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert z.testzip() is None
        assert set(z.namelist()) == {*contents, "manifest.json"}
        assert z.read("scripts/intro.txt").decode() == "你好 CloudTech"
        assert json.loads(z.read("meta/output.json"))["num"] == 3
        assert z.read("media/logo.bin") == b"\x00\xfe\xff"
        manifest = z.read("manifest.json")
        assert hashlib.sha256(manifest).hexdigest() == result["manifest_sha256"]
        for row in json.loads(manifest)["files"]:
            assert hashlib.sha256(z.read(row["name"])).hexdigest() == row["sha256"]


@pytest.mark.parametrize("name", ["../outside", "/tmp/x", "C:/x", "a\\b", "a//b",
                                  "a/../b", "a/./b", "manifest.json", "CON.txt", "a/", "a/.."])
def test_unsafe_archive_names_rejected(tmp_path, name):
    with pytest.raises(LocalZipExportError):
        export_zip({"files": {name: "data"}, "output_dir": str(tmp_path)})
    assert not list(tmp_path.iterdir())


def test_no_files_is_not_a_fake_success(tmp_path):
    with pytest.raises(LocalZipExportError):
        export_zip({"files": {}, "output_dir": str(tmp_path)})
    assert not list(tmp_path.iterdir())


def test_case_insensitive_collisions_rejected(tmp_path):
    with pytest.raises(LocalZipExportError):
        export_zip({"files": {"X.txt": "a", "x.TXT": "b"}, "output_dir": str(tmp_path)})


def test_invalid_output_directory_rejected(tmp_path):
    with pytest.raises(LocalZipExportError):
        export_zip({"files": {"a.txt": "data"}, "output_dir": str(tmp_path / "absent")})
    assert not (tmp_path / "absent").exists()


def test_oversized_file_fails_without_writes(tmp_path):
    with pytest.raises(LocalZipExportError):
        export_zip({"files": {"payload.bin": b"X" * (8 * 1024 * 1024 + 1)},
                    "output_dir": str(tmp_path)})
    assert not list(tmp_path.iterdir())


def test_nan_is_not_encoded_as_invalid_json(tmp_path):
    with pytest.raises(LocalZipExportError):
        export_zip({"files": {"values.json": {"n": float("nan")}},
                    "output_dir": str(tmp_path)})


def test_real_export_does_not_capture_unspecified_input_fields(tmp_path):
    result = export_zip({"files": {"authorized.txt": "yes"}, "secret_token": "DO_NOT_EXPORT",
                         "output_dir": str(tmp_path)})
    with zipfile.ZipFile(result["package"]) as z:
        assert b"DO_NOT_EXPORT" not in b"".join(z.read(n) for n in z.namelist())


def test_unique_output_never_overwrites_existing_zip(tmp_path):
    r1 = export_zip({"files": {"a.txt": "one"}, "output_dir": str(tmp_path)})
    r2 = export_zip({"files": {"a.txt": "two"}, "output_dir": str(tmp_path)})
    assert r1["package"] != r2["package"]
    with zipfile.ZipFile(r1["package"]) as z:
        assert z.read("a.txt") == b"one"


def test_temporary_storage_explicitly_labeled():
    r = export_zip({"files": {"a.txt": "temporary"}})
    assert r["storage"] == "LOCAL_TEMPORARY"
    with zipfile.ZipFile(r["package"]) as z:
        assert z.read("a.txt") == b"temporary"


def test_registry_dispatch_produces_real_zip(tmp_path):
    from workflows.v4.registry import OperationRegistry
    result = OperationRegistry().dispatch("export.zip", {
        "files": {"verified.txt": "actual output"}, "output_dir": str(tmp_path),
    })
    assert result["status"] == "completed" and result["mock"] is False
    with zipfile.ZipFile(result["package"]) as archive:
        assert archive.read("verified.txt") == b"actual output"


def test_registry_missing_artifact_fails_closed(tmp_path):
    from workflows.v4.registry import OperationRegistry
    result = OperationRegistry().dispatch("export.zip", {"output_dir": str(tmp_path)})
    assert result["status"] == "blocked" and result["mock"] is False
    assert result["error_code"] == "LOCAL_EXPORT_INVALID"
    assert not list(tmp_path.iterdir())
