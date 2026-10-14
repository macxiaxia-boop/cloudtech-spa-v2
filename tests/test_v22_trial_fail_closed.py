"""Guard against restoring the publicly visible fake seven-day signup.

The signed SaaS AuthContext already has real register + /me verification.
This structural test ensures TryNow cannot silently create local mock identities.
The production registration/effectiveness test is a separate E2E gate.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web/vite-spa/src"
TRIAL = ROOT / "pages/TryNow.tsx"
AUTH = ROOT / "contexts/AuthContext.tsx"


def test_trial_submit_uses_signed_server_registration_without_local_fallback():
    source = TRIAL.read_text(encoding="utf-8")
    assert "const { register } = useAuth()" in source
    assert "const result = await register(" in source
    assert "if (!result.ok)" in source
    assert source.index("if (!result.ok)") < source.index("setSubmitted(true)")
    assert "AuthContext" in source
    for unsafe in (
        "ct_mock_", "mockToken", "ct_token", "ct_user_id", "V23_API",
        "localStorage.setItem", "setTimeout(() => navigate",
    ):
        assert unsafe not in source, unsafe


def test_trial_entitlements_never_inferred_from_registration():
    source = TRIAL.read_text(encoding="utf-8")
    assert "试用期限和套餐以后端授权为准" in source
    assert "企业注册不等于已获试用或生产权限" in source
    assert "已开通 7 天免费试用" not in source
    assert "5 AI 数字员工全功能（7 天免费）" not in source
    assert "form.sku_id" not in source
    assert "form.industry" not in source


def test_auth_context_verifies_signed_tenant_before_issuing_client_session():
    source = AUTH.read_text(encoding="utf-8")
    assert "await submitCredentials(endpoint, body)" in source
    assert "await verifySession(session.token)" in source
    assert "session.tenant_id !== verified.tenant_id" in source
    assert "sessionStorage.setItem(TOKEN_KEY, session.token)" in source
    assert source.index("await verifySession(session.token)") < source.index(
        "sessionStorage.setItem(TOKEN_KEY, session.token)"
    )
