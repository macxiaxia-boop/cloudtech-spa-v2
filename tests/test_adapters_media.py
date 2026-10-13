"""adapters.media 集成测试 — 全 mock，0 真实 API 调用"""
import pytest
from workflows.v4.budget import BudgetGate, CostClass
from workflows.v4.idempotency import IdempotencyStore
from workflows.v4.media_gate import MediaGateError

from adapters.media import MediaAdapter, MediaRequest, MediaResponse, ProviderError
from adapters.media.provider_registry import (
    ProviderRegistry, JimengProvider, YihookProvider,
    KlingProvider, DoubaoSeedreamProvider,
)
from adapters.media.media_gate_integration import dispatch


@pytest.fixture
def registry():
    return ProviderRegistry()


@pytest.fixture
def budget_gate():
    bg = BudgetGate()
    bg.reset()
    return bg


@pytest.fixture
def idem_store():
    store = IdempotencyStore()
    store.clear()
    return store


@pytest.fixture
def adapter(registry, budget_gate, idem_store):
    return MediaAdapter(registry, budget_gate, idem_store)


def make_req(operation, tenant_id="t1", idempotency_key=None, estimated_cost_cents=30):
    return MediaRequest(
        operation=operation,
        inputs={"prompt": "test prompt"},
        tenant_id=tenant_id,
        idempotency_key=idempotency_key or f"idem_{operation}",
        estimated_cost_cents=estimated_cost_cents,
        cost_class="METERED_MEDIA",
    )


# ── provider stubs ───────────────────────────────────────────────────────────

class TestJimengProvider:
    def test_image_generate(self):
        req = make_req("image.generate")
        resp = JimengProvider().dispatch(req)
        assert resp.provider == "jimeng"
        assert resp.operation == "image.generate"
        assert len(resp.output_assets) == 1
        assert resp.mock is True
        assert resp.request_id.startswith("mock_")

    def test_image_edit(self):
        req = make_req("image.edit")
        resp = JimengProvider().dispatch(req)
        assert resp.provider == "jimeng"
        assert resp.operation == "image.edit"

    def test_image_inpaint(self):
        req = make_req("image.inpaint")
        resp = JimengProvider().dispatch(req)
        assert resp.provider == "jimeng"
        assert resp.operation == "image.inpaint"

    def test_unsupported_operation(self):
        req = make_req("video.generate")
        with pytest.raises(ProviderError):
            JimengProvider().dispatch(req)


class TestYihookProvider:
    def test_image_generate(self):
        req = make_req("image.generate")
        resp = YihookProvider().dispatch(req)
        assert resp.provider == "yihook"
        assert resp.operation == "image.generate"
        assert resp.mock is True


class TestKlingProvider:
    def test_video_generate(self):
        req = make_req("video.generate", estimated_cost_cents=150)
        resp = KlingProvider().dispatch(req)
        assert resp.provider == "kling"
        assert resp.operation == "video.generate"
        assert resp.output_assets[0]["mime"] == "video/mp4"

    def test_video_extend(self):
        req = make_req("video.extend", estimated_cost_cents=150)
        resp = KlingProvider().dispatch(req)
        assert resp.operation == "video.extend"

    def test_video_image_to_video(self):
        req = make_req("video.image_to_video", estimated_cost_cents=150)
        resp = KlingProvider().dispatch(req)
        assert resp.operation == "video.image_to_video"

    def test_duration_out_of_range(self):
        req = MediaRequest(
            operation="video.generate",
            inputs={"duration_sec": 999},
            tenant_id="t1",
            idempotency_key="k",
            estimated_cost_cents=150,
        )
        with pytest.raises(ProviderError, match="duration_sec"):
            KlingProvider().dispatch(req)


class TestDoubaoSeedreamProvider:
    def test_image_generate(self):
        req = make_req("image.generate")
        resp = DoubaoSeedreamProvider().dispatch(req)
        assert resp.provider == "doubao_seedream"
        assert resp.operation == "image.generate"


# ── media_gate integration ───────────────────────────────────────────────────

class TestMediaGateIntegration:
    def test_allowed_operation_passes(self, registry):
        req = make_req("image.generate")
        resp = dispatch(req, registry)
        assert resp.mock is True

    def test_deny_chat(self, registry):
        req = make_req("chat")
        with pytest.raises(MediaGateError):
            dispatch(req, registry)

    def test_deny_qa(self, registry):
        req = make_req("qa")
        with pytest.raises(MediaGateError):
            dispatch(req, registry)

    def test_deny_transcribe(self, registry):
        req = make_req("transcribe")
        with pytest.raises(MediaGateError):
            dispatch(req, registry)

    def test_deny_embedding(self, registry):
        req = make_req("embedding")
        with pytest.raises(MediaGateError):
            dispatch(req, registry)

    def test_deny_generic_completion(self, registry):
        req = make_req("generic_completion")
        with pytest.raises(MediaGateError):
            dispatch(req, registry)

    def test_deny_analyze(self, registry):
        req = make_req("analyze")
        with pytest.raises(MediaGateError):
            dispatch(req, registry)


# ── idempotency ──────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_same_key_returns_same_request_id(self, adapter):
        req = make_req("image.generate", idempotency_key="idem_key_123")
        resp1 = adapter.request(req)
        resp2 = adapter.request(req)
        assert resp1.request_id == resp2.request_id


# ── budget ───────────────────────────────────────────────────────────────────

class TestBudget:
    def test_over_cap_raises(self, budget_gate, idem_store):
        adapter = MediaAdapter(ProviderRegistry(), budget_gate, idem_store)
        req = make_req("image.generate", estimated_cost_cents=99_999)
        with pytest.raises(Exception, match="BG-002"):
            adapter.request(req)

    def test_release_on_failure(self, budget_gate, idem_store):
        adapter = MediaAdapter(ProviderRegistry(), budget_gate, idem_store)
        req = make_req("image.generate", estimated_cost_cents=50)
        adapter.request(req)


# ── end-to-end adapter ───────────────────────────────────────────────────────

class TestMediaAdapterE2E:
    def test_e2e_image_generate(self, adapter):
        req = make_req("image.generate")
        resp = adapter.request(req)
        assert resp.mock is True
        assert resp.request_id.startswith("mock_")
        assert resp.provider in ("jimeng", "yihook", "doubao_seedream")

    def test_e2e_video_generate(self, adapter):
        req = make_req("video.generate", estimated_cost_cents=150)
        resp = adapter.request(req)
        assert resp.operation == "video.generate"
        assert resp.mock is True

    def test_e2e_video_image_to_video_duration(self, adapter):
        req = MediaRequest(
            operation="video.image_to_video",
            inputs={"duration_sec": 30},
            tenant_id="t1",
            idempotency_key="idem_vi2v",
            estimated_cost_cents=150,
        )
        resp = adapter.request(req)
        assert resp.operation == "video.image_to_video"
        assert resp.output_assets[0]["duration_sec"] == 30
