"""
Phase 46 D41-44 — 行业落地页（SEO + 获客闭环）验收测试
=========================================================

验收标准:
  1. 2 个行业落地页文件存在: IndustryDecoration.tsx + IndustryMedical.tsx
  2. App.tsx 加 /industries/decoration + /industries/medical 路由
  3. 装企页含 5 步闭环 + 4 大指标 + 客户案例
  4. 医美页含 6 条监管红线 + 5 步闭环 + 4 大指标
  5. 导航栏加 装企 / 医美 入口
  6. Phase 45 D4-7 重点行业联动 (装企=重点/医美=兜底)
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
VITE_SPA_SRC = PROJECT_ROOT / "web" / "vite-spa" / "src"


# ══════════════ 文件存在性 ══════════════

def test_decoration_page_exists():
    p = VITE_SPA_SRC / "pages" / "IndustryDecoration.tsx"
    assert p.exists(), f"missing: {p}"


def test_medical_page_exists():
    p = VITE_SPA_SRC / "pages" / "IndustryMedical.tsx"
    assert p.exists(), f"missing: {p}"


# ══════════════ App.tsx 路由 ══════════════

def test_app_tsx_has_decoration_route():
    """App.tsx 含 /industries/decoration 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/industries/decoration"' in content
    assert "IndustryDecorationPage" in content


def test_app_tsx_has_medical_route():
    """App.tsx 含 /industries/medical 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/industries/medical"' in content
    assert "IndustryMedicalPage" in content


def test_navigation_links_to_industries():
    """App.tsx + Header.tsx 导航含装企 + 医美入口（Phase 47 导航迁到 Header）"""
    app = (VITE_SPA_SRC / "App.tsx").read_text(encoding="utf-8")
    header = (VITE_SPA_SRC / "components" / "Header.tsx").read_text(encoding="utf-8")
    content = app + header
    assert 'to="/industries/decoration"' in content or "to: '/industries/decoration'" in content
    assert 'to="/industries/medical"' in content or "to: '/industries/medical'" in content


# ══════════════ IndustryDecoration.tsx ══════════════

def test_decoration_5_step_pipeline():
    """装企页含 5 步闭环关键词"""
    p = VITE_SPA_SRC / "pages" / "IndustryDecoration.tsx"
    content = p.read_text(encoding="utf-8")
    expected = ["客户画像", "报价拆解", "获客内容", "工地直播", "AI 复盘"]
    for kw in expected:
        assert kw in content, f"缺关键词: {kw}"


def test_decoration_4_metrics():
    """装企页含 4 大指标"""
    p = VITE_SPA_SRC / "pages" / "IndustryDecoration.tsx"
    content = p.read_text(encoding="utf-8")
    assert "单条线索成本" in content
    assert "签约转化率" in content
    assert "单工长获客" in content
    assert "AI 复盘频率" in content


def test_decoration_customer_cases():
    """装企页含客户案例"""
    p = VITE_SPA_SRC / "pages" / "IndustryDecoration.tsx"
    content = p.read_text(encoding="utf-8")
    # 至少 1 个城市案例
    for city in ["成都", "杭州", "苏州"]:
        assert city in content, f"缺城市案例: {city}"


def test_decoration_phase45_d4_7_priority():
    """装企页标注 Phase 45 D4-7 重点"""
    p = VITE_SPA_SRC / "pages" / "IndustryDecoration.tsx"
    content = p.read_text(encoding="utf-8")
    assert "D4-7" in content
    assert "重点" in content


def test_decoration_cta_login_link():
    """装企页 CTA 链接到 /login"""
    p = VITE_SPA_SRC / "pages" / "IndustryDecoration.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'to="/login"' in content
    assert "7 天免费试用" in content


# ══════════════ IndustryMedical.tsx ══════════════

def test_medical_compliance_6_redlines():
    """医美页含 6 条监管红线"""
    p = VITE_SPA_SRC / "pages" / "IndustryMedical.tsx"
    content = p.read_text(encoding="utf-8")
    # 关键红线关键词
    expected = [
        "严禁承诺疗效",
        "严禁使用绝对化用语",
        "严禁对比其他机构贬损",
        "案例展示需脱敏",
        "价格透明",
        "知情同意书",
    ]
    for kw in expected:
        assert kw in content, f"缺合规红线: {kw}"


def test_medical_5_step_pipeline():
    """医美页含 5 步合规闭环"""
    p = VITE_SPA_SRC / "pages" / "IndustryMedical.tsx"
    content = p.read_text(encoding="utf-8")
    expected = ["客户画像", "种草内容", "术前合规问答", "案例展示", "AI 复盘"]
    for kw in expected:
        assert kw in content, f"缺关键词: {kw}"


def test_medical_4_metrics():
    """医美页含 4 大指标"""
    p = VITE_SPA_SRC / "pages" / "IndustryMedical.tsx"
    content = p.read_text(encoding="utf-8")
    assert "合规拦截" in content
    assert "术前 QA 准确率" in content
    assert "案例脱敏" in content


def test_medical_phase45_d4_7_fallback():
    """医美页标注 Phase 45 D4-7 兜底"""
    p = VITE_SPA_SRC / "pages" / "IndustryMedical.tsx"
    content = p.read_text(encoding="utf-8")
    assert "D4-7" in content
    assert "兜底" in content


def test_medical_regulatory_citation():
    """医美页含监管法规引用"""
    p = VITE_SPA_SRC / "pages" / "IndustryMedical.tsx"
    content = p.read_text(encoding="utf-8")
    assert "医疗广告管理办法" in content
    assert "医疗美容服务管理办法" in content


def test_medical_cta_login_link():
    """医美页 CTA 链接到 /login"""
    p = VITE_SPA_SRC / "pages" / "IndustryMedical.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'to="/login"' in content


# ══════════════ Phase 46 联动 ══════════════

def test_both_pages_have_seo_h1():
    """2 个落地页都有 H1 标签（SEO 关键）"""
    for page in ["IndustryDecoration.tsx", "IndustryMedical.tsx"]:
        p = VITE_SPA_SRC / "pages" / page
        content = p.read_text(encoding="utf-8")
        assert "<h1" in content, f"{page} 缺 H1"


def test_both_pages_have_arrow_right_cta():
    """2 个落地页都用 ArrowRight 图标（CTA 一致性）"""
    for page in ["IndustryDecoration.tsx", "IndustryMedical.tsx"]:
        p = VITE_SPA_SRC / "pages" / page
        content = p.read_text(encoding="utf-8")
        assert "ArrowRight" in content, f"{page} 缺 ArrowRight"
