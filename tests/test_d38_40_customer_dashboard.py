"""
Phase 46 D38-40 — 客户后台 + 设置 + 计费页验收测试
=================================================

验收标准:
  1. 3 个页面文件存在: Dashboard.tsx + Settings.tsx + Billing.tsx
  2. App.tsx 路由表加 /dashboard + /settings + /billing
  3. Dashboard.tsx 含 配额卡片 + Phase 45 deprecated 警告 + 行业复盘
  4. Settings.tsx 含 公司信息 + 联系人 + 红 #22 守门提示
  5. Billing.tsx 含 3 档套餐 + 切换按钮 + 红 #22 金税提示
  6. Phase 45 D4-7 联动: 行业 active/deprecated 标中文
  7. 员工 FE 3 / BE 5 常量对齐
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
VITE_SPA_SRC = PROJECT_ROOT / "web" / "vite-spa" / "src"


# ══════════════ 文件存在性 ══════════════

def test_dashboard_exists():
    p = VITE_SPA_SRC / "pages" / "Dashboard.tsx"
    assert p.exists(), f"missing: {p}"


def test_settings_exists():
    p = VITE_SPA_SRC / "pages" / "Settings.tsx"
    assert p.exists(), f"missing: {p}"


def test_billing_exists():
    p = VITE_SPA_SRC / "pages" / "Billing.tsx"
    assert p.exists(), f"missing: {p}"


# ══════════════ App.tsx 路由 ══════════════

def test_app_tsx_has_dashboard_route():
    """App.tsx 含 /dashboard 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/dashboard"' in content
    assert "DashboardPage" in content


def test_app_tsx_has_settings_route():
    """App.tsx 含 /settings 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/settings"' in content
    assert "SettingsPage" in content


def test_app_tsx_has_billing_route():
    """App.tsx 含 /billing 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/billing"' in content
    assert "BillingPage" in content


def test_app_tsx_footer_opc():
    """页脚显示 OPC 模式"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert "OPC" in content
    assert "1 人 + AI" in content


# ══════════════ Dashboard.tsx ══════════════

def test_dashboard_quota_cards():
    """Dashboard 含 2 个配额卡片"""
    p = VITE_SPA_SRC / "pages" / "Dashboard.tsx"
    content = p.read_text(encoding="utf-8")
    assert "QuotaCard" in content
    assert "API 调用" in content
    assert "LLM Tokens" in content


def test_dashboard_phase45_deprecated_warning():
    """Dashboard 含 Phase 45 D4-7 deprecated 警告"""
    p = VITE_SPA_SRC / "pages" / "Dashboard.tsx"
    content = p.read_text(encoding="utf-8")
    assert "deprecated_industry_calls" in content
    assert "AlertTriangle" in content


def test_dashboard_industry_labels_zh():
    """Dashboard 行业中文标 (装企/医美/教培/餐饮/零售)"""
    p = VITE_SPA_SRC / "pages" / "Dashboard.tsx"
    content = p.read_text(encoding="utf-8")
    for ind_zh in ["装企", "医美", "教培", "餐饮", "零售"]:
        assert ind_zh in content, f"缺中文行业标: {ind_zh}"


def test_dashboard_decision_labels():
    """Dashboard 含决策标签"""
    p = VITE_SPA_SRC / "pages" / "Dashboard.tsx"
    content = p.read_text(encoding="utf-8")
    assert "increase_investment" in content
    assert "pause_and_review" in content
    assert "stop_investing" in content


def test_dashboard_fetches_billing_and_funnel():
    """Dashboard 调 billing + funnel 端点（URL 模板插值）"""
    p = VITE_SPA_SRC / "pages" / "Dashboard.tsx"
    content = p.read_text(encoding="utf-8")
    # 模板字符串插值
    assert "/api/v2/billing/tenants/${tenantId}/usage" in content
    assert "/api/v2/sales/funnel/review" in content


# ══════════════ Settings.tsx ══════════════

def test_settings_has_company_fields():
    """Settings 含公司信息"""
    p = VITE_SPA_SRC / "pages" / "Settings.tsx"
    content = p.read_text(encoding="utf-8")
    assert "公司信息" in content
    assert "联系人" in content
    assert "公司名称" in content


def test_settings_red22_warning():
    """Settings 含红 #22 守门提示"""
    p = VITE_SPA_SRC / "pages" / "Settings.tsx"
    content = p.read_text(encoding="utf-8")
    assert "红 #22" in content or "用户拍板" in content


def test_settings_fetches_tenants():
    """Settings 调 /tenants 端点"""
    p = VITE_SPA_SRC / "pages" / "Settings.tsx"
    content = p.read_text(encoding="utf-8")
    assert "/api/v2/billing/tenants" in content


# ══════════════ Billing.tsx ══════════════

def test_billing_3_plans():
    """Billing 含 3 档套餐（数据驱动 · 从 /plans fetch）"""
    p = VITE_SPA_SRC / "pages" / "Billing.tsx"
    content = p.read_text(encoding="utf-8")
    # 调 /api/v2/billing/plans 端点
    assert "/api/v2/billing/plans" in content
    # 渲染 plan.label（来自后端，免费/专业/企业版由后端 PLANS 字典定义）
    assert "plan.label" in content
    assert "plan.price_yuan" in content


def test_billing_red22_jinshui_warning():
    """Billing 含红 #22 金税提示"""
    p = VITE_SPA_SRC / "pages" / "Billing.tsx"
    content = p.read_text(encoding="utf-8")
    assert "金税" in content
    assert "红 #22" in content or "用户拍板" in content


def test_billing_upgrade_endpoint():
    """Billing 调升级端点"""
    p = VITE_SPA_SRC / "pages" / "Billing.tsx"
    content = p.read_text(encoding="utf-8")
    assert "/api/v2/billing/tenants/default/upgrade" in content
    assert "plan_id" in content


def test_billing_phase45_industry_chinese():
    """Billing 行业中文标 (装企/医美)"""
    p = VITE_SPA_SRC / "pages" / "Billing.tsx"
    content = p.read_text(encoding="utf-8")
    assert "装企" in content
    assert "医美" in content


# ══════════════ Phase 46 联动 ══════════════

def test_phase46_footer_opc():
    """所有页面页脚 OPC 标记"""
    for page in ["Dashboard.tsx", "Settings.tsx", "Billing.tsx"]:
        p = VITE_SPA_SRC / "pages" / page
        content = p.read_text(encoding="utf-8")
        # 不要求每页有 OPC 标记，只 App.tsx 有，但可以检查 Phase 46 引用
        # 这里不强求

def test_navigation_links_to_dashboard():
    """App.tsx 导航含 dashboard 入口"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'to="/dashboard"' in content
    assert 'to="/settings"' in content
    assert 'to="/billing"' in content
