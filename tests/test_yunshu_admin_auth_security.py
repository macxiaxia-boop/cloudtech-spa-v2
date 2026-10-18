"""Security regression without Flask/bootstrap side effects."""
import ast
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

SOURCE = (Path(__file__).resolve().parents[1] / "admin_dashboard.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTIONS = {node.name: node for node in TREE.body if isinstance(node, ast.FunctionDef)}

def standalone(name, namespace):
    body = ast.Module(body=[FUNCTIONS[name]], type_ignores=[])
    ast.fix_missing_locations(body)
    exec(compile(body, "<security-test>", "exec"), namespace)
    return namespace[name]

def test_token_bucket_is_executable_and_throttles():
    clock = SimpleNamespace(now=0.0)
    limiter = standalone("_rate_limit", {
        "time": SimpleNamespace(monotonic=lambda: clock.now),
        "_rate_buckets": {},
    })
    assert limiter("alpha", limit=2, window=10) is True
    assert limiter("alpha", limit=2, window=10) is True
    assert limiter("alpha", limit=2, window=10) is False
    assert limiter("beta", limit=2, window=10) is True
    clock.now = 5.0
    assert limiter("alpha", limit=2, window=10) is True
    assert limiter("", limit=2, window=10) is False
    assert limiter("alpha", limit=0, window=10) is False

def test_admin_task_and_system_health_fail_closed():
    request = SimpleNamespace(path="/api/admin/tasks", method="GET", cookies={}, headers={})
    auth = standalone("_check_admin_auth", {"request": request})
    assert auth() is False
    request.method = "POST"
    assert auth() is False
    request.path = "/api/system/health"
    assert auth() is False
    request.path = "/health"
    assert auth() is True

def test_jwt_admin_still_passes_and_invalid_token_fails():
    request = SimpleNamespace(path="/api/admin/tasks", method="GET", cookies={}, headers={})
    auth = standalone("_check_admin_auth", {"request": request})
    fake_auth = ModuleType("auth")
    class AuthManager:
        def verify_jwt(self, token):
            return {"sub": "admin"} if token == "valid" else None
    fake_auth.AuthManager = AuthManager
    original = sys.modules.get("auth")
    sys.modules["auth"] = fake_auth
    try:
        request.headers = {"X-Admin-Token": "invalid"}
        assert auth() is False
        request.headers = {"X-Admin-Token": "valid"}
        assert auth() is True
    finally:
        if original is None:
            sys.modules.pop("auth", None)
        else:
            sys.modules["auth"] = original

def test_no_bypass_or_shipped_admin_secret():
    assert "cloudtech-admin-2026" not in SOURCE
    guard = ast.get_source_segment(SOURCE, FUNCTIONS["admin_guard"])
    assert 'if request.path == "/api/admin/tasks"' not in guard
    assert "return _rate_limit(f\"tenant:{tid}\"" in SOURCE
