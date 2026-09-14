"""
Phase 46 D45-52 — 内容生产 SOP 工具页 + 80 家客户清单验收测试
================================================================

验收标准:
  1. ContentSOP.tsx 含 Phase 41-44 4 主题模板 + 决策树 + 红线引用
  2. ClientList.tsx 含 50 装企 + 30 医美 = 80 家清单
  3. App.tsx 加 /content-sop + /clients 路由
  4. 客户清单含红 #22 触达边界提示
  5. 装企/医美按城市分布合理
  6. OPC 模式边界守护正确标注
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
VITE_SPA_SRC = PROJECT_ROOT / "web" / "vite-spa" / "src"


# ══════════════ 文件存在性 ══════════════

def test_content_sop_exists():
    p = VITE_SPA_SRC / "pages" / "ContentSOP.tsx"
    assert p.exists(), f"missing: {p}"


def test_client_list_exists():
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    assert p.exists(), f"missing: {p}"


# ══════════════ App.tsx 路由 ══════════════

def test_app_tsx_has_content_sop_route():
    """App.tsx 含 /content-sop 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/content-sop"' in content
    assert "ContentSOPPage" in content


def test_app_tsx_has_clients_route():
    """App.tsx 含 /clients 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/clients"' in content
    assert "ClientListPage" in content


def test_navigation_links_to_sop_and_clients():
    """App.tsx 导航含 SOP 入口"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'to="/content-sop"' in content


# ══════════════ ContentSOP.tsx ══════════════

def test_content_sop_has_4_phase_templates():
    """ContentSOP 含 Phase 41-44 4 主题模板"""
    p = VITE_SPA_SRC / "pages" / "ContentSOP.tsx"
    content = p.read_text(encoding="utf-8")
    for phase in ["Phase 41", "Phase 42", "Phase 43", "Phase 44"]:
        assert phase in content, f"缺主题: {phase}"


def test_content_sop_decision_tree():
    """ContentSOP 含决策树（主题类型 + 压缩比例）"""
    p = VITE_SPA_SRC / "pages" / "ContentSOP.tsx"
    content = p.read_text(encoding="utf-8")
    assert "金句型" in content
    assert "实战派深度型" in content
    assert "< 30%" in content
    assert "> 50%" in content


def test_content_sop_winner_assignment():
    """ContentSOP 含派最优结果（金句→2.0/实战派→1.0）"""
    p = VITE_SPA_SRC / "pages" / "ContentSOP.tsx"
    content = p.read_text(encoding="utf-8")
    # Phase 41 → 2.0
    # Phase 42-44 → 1.0
    assert "派 2.0" in content
    assert "派 1.0" in content


def test_content_sop_redline_references():
    """ContentSOP 含红线 #15.5 + #16 引用"""
    p = VITE_SPA_SRC / "pages" / "ContentSOP.tsx"
    content = p.read_text(encoding="utf-8")
    assert "#15.5" in content
    assert "#16" in content


def test_content_sop_compression_ratios():
    """ContentSOP 含 4 主题压缩比例"""
    p = VITE_SPA_SRC / "pages" / "ContentSOP.tsx"
    content = p.read_text(encoding="utf-8")
    assert "-15%" in content
    assert "-55%" in content
    assert "-51%" in content
    assert "-57%" in content


def test_content_sop_score_format():
    """ContentSOP 含双轨评分（95+95+100）"""
    p = VITE_SPA_SRC / "pages" / "ContentSOP.tsx"
    content = p.read_text(encoding="utf-8")
    assert "95+95+100" in content


# ══════════════ ClientList.tsx ══════════════

def test_client_list_has_80_clients():
    """ClientList 含 80 家客户（50 装企 + 30 医美）"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")

    # 装企 ID 计数（D-XX-XXX 格式）
    deco_count = content.count("'D-")
    medi_count = content.count("'M-")
    assert deco_count == 50, f"装企应为 50 家，实际 {deco_count}"
    assert medi_count == 30, f"医美应为 30 家，实际 {medi_count}"
    assert deco_count + medi_count == 80


def test_client_list_decoration_cities():
    """装企覆盖 14 个城市"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    expected_cities = ["北京", "上海", "广州", "深圳", "成都", "杭州", "苏州",
                       "武汉", "南京", "重庆", "西安", "天津", "长沙", "青岛"]
    for city in expected_cities:
        assert city in content, f"装企缺城市: {city}"


def test_client_list_medical_cities():
    """医美覆盖 14 个城市"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    expected_cities = ["北京", "上海", "广州", "深圳", "成都", "杭州",
                       "武汉", "南京", "重庆", "西安", "长沙", "青岛", "苏州"]
    for city in expected_cities:
        assert city in content, f"医美缺城市: {city}"


def test_client_list_status_default_pending():
    """所有客户默认状态 = pending"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    # pending 是默认值
    assert "status: 'pending'" in content
    # 不应该有 signed/trial 等已被触达的状态
    assert "status: 'signed'" not in content
    assert "status: 'trial'" not in content


def test_client_list_red22_warning():
    """ClientList 含红 #22 触达边界提示"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    assert "红线 #22" in content or "红 #22" in content
    assert "用户拍板" in content
    assert "实际拨打" in content or "加微信" in content or "发短信" in content


def test_client_list_status_labels():
    """ClientList 含 5 种状态标签"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    expected = ["待触达", "已联系", "已约演示", "试用中", "已签约"]
    for label in expected:
        assert label in content, f"缺状态标: {label}"


def test_client_list_has_contact_info():
    """ClientList 含联系人 + 电话字段"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    assert "contact" in content
    assert "phone" in content
    assert "联系人" in content
    assert "电话" in content


def test_client_list_table_format():
    """ClientList 用表格展示"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    assert "<table" in content
    assert "<thead" in content
    assert "<tbody" in content
    assert "<tr" in content


def test_client_list_statistics_section():
    """ClientList 顶部含统计区"""
    p = VITE_SPA_SRC / "pages" / "ClientList.tsx"
    content = p.read_text(encoding="utf-8")
    assert "decoClients" in content
    assert "mediClients" in content
    assert "cityCount" in content
    assert "topCities" in content


# ══════════════ Phase 46 联动 ══════════════

def test_phase46_opc_mode_3_pages():
    """D41-44 + D45-52 = 4 新页面都有 OPC 边界守护"""
    opc_pages = ["IndustryDecoration.tsx", "IndustryMedical.tsx",
                 "ContentSOP.tsx", "ClientList.tsx"]
    for page in opc_pages:
        p = VITE_SPA_SRC / "pages" / page
        content = p.read_text(encoding="utf-8")
        # 至少有 CTA 或 footer 或红色 #22 提示（OPC 边界）
        assert any(kw in content for kw in ["OPC", "红 #22", "用户拍板", "免费试用"]), \
            f"{page} 缺 OPC 边界标识"


def test_phase46_total_pages():
    """Phase 46 D17-52 累计页面数 ≥ 9"""
    pages_dir = VITE_SPA_SRC / "pages"
    page_files = list(pages_dir.glob("*.tsx"))
    assert len(page_files) >= 9, f"页面数应为 ≥ 9，实际 {len(page_files)}: {[p.name for p in page_files]}"


def test_phase46_footer_consistency():
    """App.tsx footer OPC 标记"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert "OPC" in content
    assert "1 人 + AI" in content
