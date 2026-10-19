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
    namespace = {"request": request, "g": SimpleNamespace()}
    standalone("_is_admin_route", namespace)
    auth = standalone("_check_admin_auth", namespace)
    assert auth() is False
    request.method = "POST"
    assert auth() is False
    request.path = "/api/system/health"
    assert auth() is False
    request.path = "/health"
    assert auth() is True

def test_jwt_admin_still_passes_and_invalid_token_fails():
    request = SimpleNamespace(path="/api/admin/tasks", method="GET", cookies={}, headers={})
    namespace = {"request": request, "g": SimpleNamespace()}
    standalone("_is_admin_route", namespace)
    auth = standalone("_check_admin_auth", namespace)
    fake_auth = ModuleType("auth")
    class AuthManager:
        def verify_jwt(self, token):
            if token == "valid":
                return {"sub": "admin", "role": "admin", "tenant_id": "tenant-a"}
            if token == "viewer":
                return {"sub": "viewer", "role": "viewer", "tenant_id": "tenant-a"}
            return None
    fake_auth.AuthManager = AuthManager
    original = sys.modules.get("auth")
    sys.modules["auth"] = fake_auth
    try:
        request.headers = {"X-Admin-Token": "invalid"}
        assert auth() is False
        request.headers = {"X-Admin-Token": "viewer"}
        assert auth() is False
        request.headers = {"X-Admin-Token": "valid"}
        assert auth() is True
        request.path = "/api/admin/tasks.css"
        request.headers = {"X-Admin-Token": "viewer"}
        assert auth() is False
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


def test_admin_task_endpoint_is_tenant_isolated():
    """Run the exact Flask route body against two fake tenant records."""
    import copy
    import time

    class Conn:
        def execute(self, sql):
            assert "CREATE TABLE IF NOT EXISTS tasks" in sql
        def commit(self):
            pass

    class Database:
        conn = Conn()
        inserts = []
        def fetch_all(self, sql, params):
            assert "WHERE tenant_id = ?" in sql
            assert params == ("tenant-a",)
            return [
                {"id": "a1", "tenant_id": "tenant-a"},
            ]
        def insert(self, table, values):
            assert table == "tasks"
            self.inserts.append(dict(values))

    db = Database()
    mock_module = ModuleType("database")
    mock_module.get_db = lambda: db
    previous = sys.modules.get("database")
    sys.modules["database"] = mock_module
    try:
        req = SimpleNamespace(method="GET", get_json=lambda silent=True: {})
        g = SimpleNamespace(yunshu_admin_claims={"role": "admin", "tenant_id": "tenant-a"})
        node = __import__("copy").deepcopy(FUNCTIONS["api_admin_tasks"])
        node.decorator_list = []
        namespace = {"request": req, "g": g, "jsonify": lambda x: x, "time": time}
        module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
        exec(compile(module, "<tenant-isolation-test>", "exec"), namespace)
        api = namespace["api_admin_tasks"]

        result = api()
        assert result["tenant_id"] == "tenant-a"
        assert result["task_count"] == 1
        assert result["tasks"][0]["tenant_id"] == "tenant-a"

        req.method = "POST"
        req.get_json = lambda silent=True: {"id": "intruder", "tenant_id": "tenant-b"}
        denied = api()
        assert denied[1] == 403
        assert db.inserts == []

        req.get_json = lambda silent=True: {"id": "forged", "status": "done"}
        assert api()[1] == 422
        assert db.inserts == []

        req.get_json = lambda silent=True: {"id": "allowed", "status": "pending"}
        created = api()
        assert created["status"] == "ok"
        assert len(db.inserts) == 1
        assert db.inserts[0]["tenant_id"] == "tenant-a"

        g.yunshu_admin_claims = {}
        assert api()[1] == 403
    finally:
        if previous is None:
            sys.modules.pop("database", None)
        else:
            sys.modules["database"] = previous
