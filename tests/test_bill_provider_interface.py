"""
BILL Provider Interface Tests — 8/8 (V6.2)
============================================
验证 Provider Adapter 抽象层:
  1.  BillingProvider ABC 不能直接实例化
  2.  MockProvider 正确实现 BillingProvider 接口
  3.  StripeProvider 正确实现 BillingProvider 接口
  4.  OpenAIProvider 正确实现 BillingProvider 接口
  5.  BillingEngine DI 接受所有 3 个 provider 实现
  6.  MockProvider.issue_callback 返回标准 ProviderCallback
  7.  Stripe/OpenAI 真接口存在但 live mode 下显式 raise, 不发真 HTTP
  8.  真接口含 __REAL_PROVIDER_CALL_NEEDED__ 标记, user 修 CC 后可启用

原则 (红线 #95 EXTEND):
  - 所有 3 个 provider 都走 mock 行为, 不依赖网络
  - 真接口有完整签名, 但 live 模式 raise NotImplementedError
  - 接口测试零外部依赖, 全部 in-process
"""
from __future__ import annotations

import sys
from decimal import Decimal

import pytest

# 允许在 tests/ 目录运行
sys.path.insert(0, r"D:\CloudTech-Portable")

from billing_real import (  # noqa: E402
    BillingEngine,
    BillingEvent,
    BillingProvider,
    Currency,
    MockProvider,
    OpenAIProvider,
    ProviderCallback,
    StripeProvider,
)


# ════════════════════════════════════════════════════════════
# Case 1: ABC instantiation fails
# ════════════════════════════════════════════════════════════
def test_case_01_abc_cannot_be_instantiated():
    """
    BillingProvider 是抽象基类 — 不允许直接实例化.
    强制所有实现都走 @abstractmethod 契约.
    """
    with pytest.raises(TypeError) as exc_info:
        BillingProvider()  # noqa: B017
    msg = str(exc_info.value)
    assert "abstract" in msg.lower(), f"unexpected error: {msg}"
    print("✓ Case 1: BillingProvider abstract instantiation blocked")


# ════════════════════════════════════════════════════════════
# Case 2: MockProvider implements interface
# ════════════════════════════════════════════════════════════
def test_case_02_mockprovider_implements_interface():
    """
    MockProvider 是 BillingProvider 的具体实现,
    可被 BillingEngine 注入, 并暴露完整接口.
    """
    p = MockProvider(name="mock_provider_a")
    assert isinstance(p, BillingProvider), "MockProvider must inherit BillingProvider"
    assert p.name == "mock_provider_a"
    # 接口 6 方法全部可达
    for attr in ("issue_callback", "replay", "deliver_count",
                 "issue_monthly_bill", "get_monthly_bill"):
        assert hasattr(p, attr) and callable(getattr(p, attr)), f"missing method: {attr}"
    print("✓ Case 2: MockProvider implements BillingProvider")


# ════════════════════════════════════════════════════════════
# Case 3: StripeProvider implements interface
# ════════════════════════════════════════════════════════════
def test_case_03_stripe_provider_implements_interface():
    """
    StripeProvider 是 BillingProvider 的 stub 实现,
    默认 mode='stub' 走 in-memory 行为, 不发真 HTTP.
    """
    p = StripeProvider(api_key="sk_test_dummy", mode="stub")
    assert isinstance(p, BillingProvider)
    assert p.name == "stripe"
    for attr in ("issue_callback", "replay", "deliver_count",
                 "issue_monthly_bill", "get_monthly_bill"):
        assert hasattr(p, attr) and callable(getattr(p, attr))
    print("✓ Case 3: StripeProvider implements BillingProvider (stub mode)")


# ════════════════════════════════════════════════════════════
# Case 4: OpenAIProvider implements interface
# ════════════════════════════════════════════════════════════
def test_case_04_openai_provider_implements_interface():
    """
    OpenAIProvider 是 BillingProvider 的 stub 实现,
    默认 mode='stub' 走 in-memory 行为, 不发真 HTTP.
    """
    p = OpenAIProvider(api_key="sk-dummy", mode="stub")
    assert isinstance(p, BillingProvider)
    assert p.name == "openai_billing"
    for attr in ("issue_callback", "replay", "deliver_count",
                 "issue_monthly_bill", "get_monthly_bill"):
        assert hasattr(p, attr) and callable(getattr(p, attr))
    print("✓ Case 4: OpenAIProvider implements BillingProvider (stub mode)")


# ════════════════════════════════════════════════════════════
# Case 5: BillingEngine DI accepts all 3 providers
# ════════════════════════════════════════════════════════════
def test_case_05_engine_di_accepts_all_three_providers():
    """
    BillingEngine 是 DI 容器 — 接受任何 BillingProvider 实现.
    验证 3 个 provider 都能被注入且不报错.
    """
    eng_mock = BillingEngine(provider=MockProvider(name="mock_a"))
    eng_stripe = BillingEngine(provider=StripeProvider(mode="stub"))
    eng_openai = BillingEngine(provider=OpenAIProvider(mode="stub"))
    # 3 个 engine 都暴露 _provider 字段
    assert eng_mock._provider.name == "mock_a"
    assert eng_stripe._provider.name == "stripe"
    assert eng_openai._provider.name == "openai_billing"
    # 3 个 engine 都有可用的账本/余额 (证明 provider 注入不影响 ledger)
    eng_mock.ensure_tenant("t1", initial_balance=Decimal("100"))
    bal = eng_mock.get_balance("t1")
    assert bal.available == Decimal("100")
    print("✓ Case 5: BillingEngine DI accepts MockProvider, StripeProvider, OpenAIProvider")


# ════════════════════════════════════════════════════════════
# Case 6: issue_callback contract returns ProviderCallback
# ════════════════════════════════════════════════════════════
def test_case_06_issue_callback_returns_provider_callback():
    """
    所有 provider 的 issue_callback 必须返回 ProviderCallback (Pydantic),
    字段契约统一 (charge_id/tenant_id/idempotency_key/amount/currency/provider/success).
    """
    p = MockProvider(name="mock_test")
    cb = p.issue_callback(
        tenant_id="tenant_007",
        idempotency_key="idem_007",
        amount=Decimal("25.50"),
        currency=Currency.USD,
        success=True,
    )
    assert isinstance(cb, ProviderCallback)
    assert cb.tenant_id == "tenant_007"
    assert cb.idempotency_key == "idem_007"
    assert cb.amount == Decimal("25.50")
    assert cb.currency == Currency.USD
    assert cb.provider == "mock_test"
    assert cb.success is True
    assert cb.charge_id.startswith("chg_")
    # 验证是 Pydantic v2 BaseModel (类型契约)
    from pydantic import BaseModel
    assert isinstance(cb, BaseModel), "ProviderCallback must be a Pydantic BaseModel"
    # model_dump 可用 (Pydantic 序列化)
    dumped = cb.model_dump()
    assert dumped["tenant_id"] == "tenant_007"
    assert dumped["provider"] == "mock_test"
    print("✓ Case 6: issue_callback returns ProviderCallback (Pydantic BaseModel) with contract fields")


# ════════════════════════════════════════════════════════════
# Case 7: Real providers (Stripe/OpenAI) do NOT call APIs in live mode either
# ════════════════════════════════════════════════════════════
def test_case_07_real_providers_no_api_call_in_any_mode():
    """
    关键安全约束 (红线):
      - stub 模式: 走 in-memory 行为 (等同 MockProvider)
      - live 模式: 立即 raise NotImplementedError, 不发任何 HTTP
    防止 user 在没有 key 的情况下误发真请求.
    """
    # Stub mode — in-memory
    s_stub = StripeProvider(mode="stub")
    cb_s = s_stub.issue_callback(
        tenant_id="t1", idempotency_key="k1",
        amount=Decimal("10"), currency=Currency.CNY,
    )
    assert cb_s.charge_id.startswith("chg_")
    # Live mode — raises
    s_live = StripeProvider(mode="live")
    with pytest.raises(NotImplementedError) as exc:
        s_live.issue_callback(
            tenant_id="t1", idempotency_key="k1",
            amount=Decimal("10"), currency=Currency.CNY,
        )
    assert "__REAL_PROVIDER_CALL_NEEDED__" in str(exc.value)
    # OpenAI 同理
    o_live = OpenAIProvider(mode="live")
    with pytest.raises(NotImplementedError) as exc:
        o_live.issue_callback(
            tenant_id="t1", idempotency_key="k1",
            amount=Decimal("10"), currency=Currency.CNY,
        )
    assert "__REAL_PROVIDER_CALL_NEEDED__" in str(exc.value)
    # replay/deliver_count/monthly 也 live mode raise
    with pytest.raises(NotImplementedError):
        s_live.replay(cb_s)
    with pytest.raises(NotImplementedError):
        s_live.deliver_count("chg_xxx")
    with pytest.raises(NotImplementedError):
        s_live.issue_monthly_bill(2026, 10, [])
    with pytest.raises(NotImplementedError):
        s_live.get_monthly_bill(2026, 10)
    print("✓ Case 7: StripeProvider/OpenAIProvider live mode raises, no HTTP issued")


# ════════════════════════════════════════════════════════════
# Case 8: Real providers expose __REAL_PROVIDER_CALL_NEEDED__ marker
# ════════════════════════════════════════════════════════════
def test_case_08_real_providers_have_real_call_marker():
    """
    真实接口接入点必须显式标记 `__REAL_PROVIDER_CALL_NEEDED__`,
    确保 user 修 CC 后能 grep 到这些点, 知道哪里需要替换为真 HTTP 调用.
    """
    # 类属性可读 (用户/审计能直接看到接入位)
    assert hasattr(StripeProvider, "__REAL_PROVIDER_CALL_NEEDED__"), \
        "StripeProvider missing __REAL_PROVIDER_CALL_NEEDED__"
    assert hasattr(OpenAIProvider, "__REAL_PROVIDER_CALL_NEEDED__"), \
        "OpenAIProvider missing __REAL_PROVIDER_CALL_NEEDED__"
    # MockProvider 不需要这个 marker (纯 in-memory, 无真调接入位)
    assert not hasattr(MockProvider, "__REAL_PROVIDER_CALL_NEEDED__"), \
        "MockProvider should NOT have __REAL_PROVIDER_CALL_NEEDED__"
    # 标记内容必须是字符串且非空
    s_marker = StripeProvider.__REAL_PROVIDER_CALL_NEEDED__
    o_marker = OpenAIProvider.__REAL_PROVIDER_CALL_NEEDED__
    assert isinstance(s_marker, str) and len(s_marker) > 20
    assert isinstance(o_marker, str) and len(o_marker) > 20
    # 标记应包含关键提示词 (便于 grep)
    for keyword in ("__REAL_PROVIDER_CALL_NEEDED__", "未启用", "user", "修", "CC", "API_KEY", "mode='live'"):
        assert keyword in s_marker, f"StripeProvider marker missing keyword: {keyword}"
        assert keyword in o_marker, f"OpenAIProvider marker missing keyword: {keyword}"
    # 验证 BillingEngine 集成: 用 stub 模式 StripeProvider 跑完整流程
    eng = BillingEngine(provider=StripeProvider(mode="stub"))
    eng.ensure_tenant("t_stripe", initial_balance=Decimal("100"))
    cb = eng._provider.issue_callback(
        tenant_id="t_stripe",
        idempotency_key="k_stripe_001",
        amount=Decimal("15.00"),
        currency=Currency.CNY,
    )
    assert cb.charge_id.startswith("chg_")
    assert cb.provider == "stripe"
    print("✓ Case 8: Real providers carry __REAL_PROVIDER_CALL_NEEDED__ marker for CC enablement")


# ════════════════════════════════════════════════════════════
# 入口: pytest 自动发现 + 直接 python 跑也支持
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # 直接跑 — 输出可见
    test_case_01_abc_cannot_be_instantiated()
    test_case_02_mockprovider_implements_interface()
    test_case_03_stripe_provider_implements_interface()
    test_case_04_openai_provider_implements_interface()
    test_case_05_engine_di_accepts_all_three_providers()
    test_case_06_issue_callback_returns_provider_callback()
    test_case_07_real_providers_no_api_call_in_any_mode()
    test_case_08_real_providers_have_real_call_marker()
    print()
    print("=" * 60)
    print("  8/8 V6.2 Provider Adapter Interface tests PASSED")
    print("=" * 60)
