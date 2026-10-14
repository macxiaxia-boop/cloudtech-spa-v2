"""PR1 auth truth invariant until a real server-signed session is integrated.

Source-level guard complements the actual Vite build and Lighthouse browser CI.
It is NOT a replacement for a live identity-provider integration test.
"""
from pathlib import Path

AUTH = Path(__file__).resolve().parents[1] / "web/vite-spa/src/contexts/AuthContext.tsx"


def test_legacy_pr1_never_mints_fake_admin_login():
    source = AUTH.read_text(encoding="utf-8")
    assert "role: 'admin'" not in source
    assert "mockUser" not in source
    assert "return { ok: true }" not in source
    assert "setUser(savedUser)" not in source
    assert "saveToStorage(STORAGE_KEYS.user, mockUser)" not in source


def test_legacy_pr1_login_and_registration_explicitly_fail_closed():
    source = AUTH.read_text(encoding="utf-8")
    assert "const login = useCallback(async" in source
    assert "const register = useCallback(async" in source
    assert "登录尚未接通受信任的服务端身份验证" in source
    assert "注册尚未接通受信任的服务端账号创建接口" in source
    assert source.count("ok: false") >= 2


def test_public_shell_does_not_restore_unsigned_auth_or_probe_on_mount():
    source = AUTH.read_text(encoding="utf-8")
    assert "loadFromStorage" not in source
    assert "checkBackendHealth().then(" not in source
    assert "saveToStorage(STORAGE_KEYS.user, null);" in source
    # An explicit manual health refresh does not establish authentication.
    assert "const refreshBackend = useCallback(async () =>" in source
