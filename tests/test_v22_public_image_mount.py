"""Regression for actual V22 image delivery, not merely Vite preview.

Extract and execute the exact static-mount AST from the Windows-dependent
gateway. Requests then use FastAPI's real TestClient/Starlette StaticFiles.
"""
import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "gateway_v22.py"


def public_image_app(tmp_path):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    assignment = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "public_images"
                              for t in node.targets))
    mount = next(node for node in ast.walk(tree)
                 if isinstance(node, ast.If)
                 and ast.unparse(node.test) == "public_images.is_dir()")
    compiled = compile(ast.fix_missing_locations(
        ast.Module(body=[assignment, mount], type_ignores=[])), str(SOURCE), "exec")
    app = FastAPI()
    namespace = {"DIST_DIR": tmp_path, "app": app, "StaticFiles": StaticFiles}
    exec(compiled, namespace)
    return app


def test_public_webp_and_legacy_jpeg_are_served_as_bytes(tmp_path):
    directory = tmp_path / "images" / "optimized"
    directory.mkdir(parents=True)
    payload = b"RIFF\x0a\x00\x00\x00WEBPVP8 "
    (directory / "ai-team-560.webp").write_bytes(payload)
    (tmp_path / "images" / "ai-team.jpeg").write_bytes(b"\xff\xd8\xff\xd9")
    client = TestClient(public_image_app(tmp_path))
    webp = client.get("/images/optimized/ai-team-560.webp")
    assert webp.status_code == 200 and webp.content == payload
    assert "image/webp" in webp.headers["content-type"]
    jpeg = client.get("/images/ai-team.jpeg")
    assert jpeg.status_code == 200 and jpeg.content == b"\xff\xd8\xff\xd9"
    assert "image/jpeg" in jpeg.headers["content-type"]


def test_unknown_public_file_fails_closed(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "private.txt").write_text("customer-secret")
    client = TestClient(public_image_app(tmp_path))
    r = client.get("/images/private.txt")
    assert r.status_code == 404
    assert "customer-secret" not in r.text


def test_missing_public_directory_does_not_mount(tmp_path):
    client = TestClient(public_image_app(tmp_path))
    assert client.get("/images/optimized/missing.webp").status_code == 404


def test_spa_fallback_exempts_image_prefix():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    assignment = next(node for node in tree.body
                      if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "SPA_EXEMPT"
                              for t in node.targets))
    exempt = ast.literal_eval(assignment.value)
    assert "/images/" in exempt
