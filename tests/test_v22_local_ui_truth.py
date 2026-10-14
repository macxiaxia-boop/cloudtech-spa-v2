"""CloudTech UI route safety contract for two actual local workpaths.

Structural regression only. Interactive browser E2E and staging Worker runtime
are separate release gates. We do not infer INTEGRATED from a source scan.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "web/vite-spa/src"
UI = ROOT / "pages/LocalWorkPaths.tsx"


def test_both_local_paths_are_reachable_only_via_authenticated_route():
    app = (ROOT / "App.tsx").read_text(encoding="utf8")
    sidebar = (ROOT / "components/AppShell/AppSidebar.tsx").read_text(encoding="utf8")
    assert 'path="/workflows/local"' in app
    assert 'RequireAuth><BasicLayout' in app.split('path="/workflows/local"')[1][:160]
    assert "LocalWorkPathsPage" in app
    assert "href: '/workflows/local'" in sidebar


def test_ui_requires_real_worker_and_independently_acked_artifacts():
    source = UI.read_text(encoding="utf8")
    for required in (
        "WP-LOCAL-ARTICLE-ANALYZE",
        "WP-LOCAL-SUBTITLE-EXPORT",
        "budget_cap_cents: 0",
        "workPathClient.createRun(",
        "workPathClient.enqueueLocalRun(",
        "workPathClient.getLocalOutputByRun(id)",
        "verified_local_outbox_catalog",
        "raw_customer_content_in_response",
        "getLocalQueueStatus(id)",
        "Worker 未连接",
        "createObjectURL",
        "revokeObjectURL",
        "TextEncoder",
    ):
        assert required in source, required
    assert "setVerified(result)" in source
    assert source.index("result.source !== 'verified_local_outbox_catalog'") < (
        source.index("setVerified(result)")
    )
    assert "独立成果验真" in source
    assert "未完成 / 等待 Outbox 独立验真" in source


def test_ui_never_fakes_asr_generation_or_publishing():
    source = UI.read_text(encoding="utf8")
    assert "这不是 ASR" in source
    assert "AI 改写" in source
    for bad in ("ct_mock_", "mockToken", "Math.random()", "localStorage.setItem("):
        assert bad not in source
    assert "已入队" not in source or "不代表已执行" in source
