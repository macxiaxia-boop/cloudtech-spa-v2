"""Gateway V22 regression: unimplemented API mutations may not appear successful.

Load the actual gateway helper source by AST to avoid importing its Windows-only
legacy runtime dependencies into Linux CI. This tests real function bodies,
not copied mock implementations.
"""
import ast
import os
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "gateway_v22.py"


class Response:
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


def helpers(environment: dict[str, str]):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    keep = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in {"_CLOUDTECH_DEPLOYMENT", "_STUBS_STRICT"}
            for target in node.targets
        ):
            keep.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in {"v10_stub_data", "_stub_response"}:
            keep.append(node)
    assert len(keep) == 4, "gateway source contract changed; review the test"
    module = ast.fix_missing_locations(ast.Module(body=keep, type_ignores=[]))
    ns = {"_os": os, "JSONResponse": Response}
    with patch.dict(os.environ, environment, clear=True):
        exec(compile(module, str(SOURCE), "exec"), ns)
    return ns["_stub_response"], ns["_STUBS_STRICT"]


def test_default_mode_is_fail_closed():
    respond, strict = helpers({})
    assert strict
    got = respond("projects/run")
    assert got.status_code == 404
    assert got.content["error"] == "not_implemented"


def test_explicit_local_demo_only_allows_marked_get():
    respond, strict = helpers({"CLOUDTECH_ENV": "development", "CLOUDTECH_STUBS": "mark"})
    assert not strict
    result = respond("reports/list", method="GET")
    assert result.status_code == 200
    assert result.content["stub"] is True
    for verb in ("POST", "PUT", "DELETE"):
        result = respond("billing/charge", method=verb)
        assert result.status_code == 404
        assert result.content["stub"] is True
        assert result.content["method"] == verb
        assert result.content["error"] == "not_implemented"


def test_production_and_staging_ignore_demo_override():
    for deployment in ("production", "prod", "staging"):
        respond, strict = helpers({"CLOUDTECH_ENV": deployment, "CLOUDTECH_STUBS": "mark"})
        assert strict
        for verb in ("GET", "POST"):
            result = respond("billing/charge", method=verb)
            assert result.status_code == 404


def test_legacy_v4_environment_also_closes_demo_mode():
    respond, strict = helpers({"V4_ENV": "production", "CLOUDTECH_STUBS": "mark"})
    assert strict
    assert respond("anything").status_code == 404
