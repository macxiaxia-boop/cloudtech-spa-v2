"""V22 -> V23 gateway failure semantics, tested against the actual source function.

The gateway imports optional Windows/Flask modules at import time. Extracting the
unmodified AST function here allows isolated network-failure regressions in CI
without inventing a second forwarding implementation.
"""
import ast
import io
import json
from pathlib import Path
from unittest.mock import patch
import urllib.error

from fastapi.responses import JSONResponse

GATEWAY = Path(__file__).resolve().parents[1] / "gateway_v22.py"


def _actual_forward():
    tree = ast.parse(GATEWAY.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name == "_try_forward_v23"]
    assert len(nodes) == 1, "The V23 routing source changed; review contract."
    mod = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    scope = {
        "V23_FORWARD_URL": "http://127.0.0.1:7791",
        "V23_FORWARD_TIMEOUT": 0.1,
        "JSONResponse": JSONResponse,
    }
    exec(compile(mod, str(GATEWAY), "exec"), scope)
    return scope["_try_forward_v23"]


def _upstream_error(code, body=b"private customer data", headers=None):
    return urllib.error.HTTPError(
        "http://127.0.0.1:7791/api/v2/private/run", code,
        "upstream failure", headers or {}, io.BytesIO(body)
    )


def test_forwards_real_4xx_5xx_without_masking_or_private_bodies():
    fwd = _actual_forward()
    for status in (401, 403, 404, 422, 429, 500, 503):
        with patch("urllib.request.urlopen", side_effect=_upstream_error(status)):
            response = fwd("private/run", "POST", b'{"task":"run"}')
        assert response is not None
        assert response.status_code == status
        assert response.headers["x-cloudtech-upstream"] == "v23"
        result = json.loads(response.body)
        assert result == {
            "status": "error", "error": "v23_upstream_http_error",
            "upstream_status": status, "stub": False
        }
        assert b"private customer data" not in response.body


def test_retry_after_propagated_only_for_safe_throttling():
    fwd = _actual_forward()
    for header, expected in (("120", "120"), ("999999", None), ("anything", None)):
        error = _upstream_error(429, headers={"Retry-After": header})
        with patch("urllib.request.urlopen", side_effect=error):
            response = fwd("ratelimited")
        assert response.status_code == 429
        assert response.headers.get("retry-after") == expected


def test_transport_error_preserves_existing_fallback_without_fake_success():
    fwd = _actual_forward()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        assert fwd("unavailable") is None
