"""
Phase 45 D17-23 — SaaS 官网 React 脚手架验收测试
===============================================

验收标准:
  1. web/vite-spa/ 目录存在
  2. 关键配置文件齐: package.json + vite.config.ts + tailwind.config.js + tsconfig.json
  3. 入口文件: index.html + src/main.tsx + src/App.tsx
  4. 页面组件: Marketing.tsx + Pricing.tsx
  5. FE 3 员工菜单: FEEmployeeMenu.tsx 含 content_writer/customer_service/market_researcher
  6. 行业聚焦: Marketing.tsx 含 装企 + 医美 (decoration + medical)
  7. 行业 deprecated 提示: Marketing.tsx 含 教培/餐饮/零售 deprecated 字样
  8. Phase 45 D4-7 改造: 后端 5 员工 hidden 在 FE 菜单
  9. README 文档
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
VITE_SPA = PROJECT_ROOT / "web" / "vite-spa"


# ══════════════ 目录与配置 ══════════════

def test_vite_spa_dir_exists():
    """vite-spa 脚手架目录存在"""
    assert VITE_SPA.exists(), f"missing: {VITE_SPA}"
    assert VITE_SPA.is_dir()


def test_package_json_exists():
    """package.json 存在 + 含 React 18 + Vite 5"""
    p = VITE_SPA / "package.json"
    assert p.exists()
    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["name"] == "cloudtech-saas-website"
    assert "react" in data["dependencies"]
    assert data["dependencies"]["react"].startswith("^18")
    assert "vite" in data["devDependencies"]
    assert "tailwindcss" in data["devDependencies"]
    assert "lucide-react" in data["dependencies"]


def test_vite_config_exists():
    """vite.config.ts 存在 + 端口 5098 + 代理 /api/v2"""
    p = VITE_SPA / "vite.config.ts"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "5098" in content
    assert "/api/v2" in content
    assert "5099" in content  # 代理到 gateway


def test_tailwind_config_exists():
    """tailwind.config.js 存在 + brand 色板"""
    p = VITE_SPA / "tailwind.config.js"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "brand" in content
    assert "#0066FF" in content


def test_tsconfig_exists():
    """tsconfig.json + tsconfig.node.json 存在"""
    assert (VITE_SPA / "tsconfig.json").exists()
    assert (VITE_SPA / "tsconfig.node.json").exists()
    content = (VITE_SPA / "tsconfig.json").read_text(encoding="utf-8")
    assert "@/*" in content
    assert "react-jsx" in content


# ══════════════ 入口文件 ══════════════

def test_index_html_exists():
    """index.html 入口"""
    p = VITE_SPA / "index.html"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "<div id=\"root\">" in content
    assert "src/main.tsx" in content
    assert "CloudTech" in content


def test_main_tsx_exists():
    """main.tsx 入口（React 18 createRoot + BrowserRouter）"""
    p = VITE_SPA / "src" / "main.tsx"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "createRoot" in content
    assert "BrowserRouter" in content


def test_app_tsx_exists():
    """App.tsx 路由表"""
    p = VITE_SPA / "src" / "App.tsx"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "Routes" in content
    assert 'path="/"' in content
    assert 'path="/pricing"' in content
    assert "FEEmployeeMenu" in content


# ══════════════ 页面 ══════════════

def test_marketing_page_exists():
    """Marketing.tsx 营销首页"""
    p = VITE_SPA / "src" / "pages" / "Marketing.tsx"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "MarketingPage" in content


def test_pricing_page_exists():
    """Pricing.tsx 定价页"""
    p = VITE_SPA / "src" / "pages" / "Pricing.tsx"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "PricingPage" in content
    assert "¥499" in content or "499" in content


# ══════════════ Phase 45 D4-7 改造点 ══════════════

def test_fe_employee_menu_contains_3_ids():
    """FEEmployeeMenu 含 3 个员工 id"""
    p = VITE_SPA / "src" / "components" / "FEEmployeeMenu.tsx"
    content = p.read_text(encoding="utf-8")
    for emp_id in ["content_writer", "customer_service", "market_researcher"]:
        assert emp_id in content, f"缺 FE 员工: {emp_id}"


def test_marketing_uses_2_active_industries():
    """Marketing.tsx 含 decoration + medical"""
    p = VITE_SPA / "src" / "pages" / "Marketing.tsx"
    content = p.read_text(encoding="utf-8")
    assert "decoration" in content
    assert "medical" in content


def test_marketing_warns_deprecated_industries():
    """Marketing.tsx 含 deprecated 行业提示"""
    p = VITE_SPA / "src" / "pages" / "Marketing.tsx"
    content = p.read_text(encoding="utf-8")
    assert "deprecated" in content.lower()
    # 提到 3 个废弃行业
    for ind in ["教培", "餐饮", "零售"]:
        assert ind in content, f"deprecated 行业提示缺: {ind}"


def test_fe_menu_hides_backend_5():
    """FE 菜单不暴露后端 5 员工（D4-7 收敛）"""
    p = VITE_SPA / "src" / "components" / "FEEmployeeMenu.tsx"
    content = p.read_text(encoding="utf-8")
    # FE 菜单不应该列 BE 员工
    for be_id in ["short_video_script", "data_analyst", "seo_specialist",
                  "social_media_manager", "growth_hacker"]:
        # 后端员工 id 不应出现在 FE 菜单数据
        assert be_id not in content.split("FE_EMPLOYEES")[1].split("]")[0], \
            f"FE 菜单泄漏 BE 员工: {be_id}"


def test_marketing_phase45_brand_pill():
    """Marketing.tsx 含 Phase 45 品牌标签"""
    p = VITE_SPA / "src" / "pages" / "Marketing.tsx"
    content = p.read_text(encoding="utf-8")
    assert "Phase 45" in content
    assert "数字员工" in content


# ══════════════ 文档 ══════════════

def test_readme_exists():
    """README.md 文档"""
    p = VITE_SPA / "README.md"
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "Phase 45" in content
    assert "D17-23" in content
    assert "D4-7" in content  # 引用 D4-7 砍端点
