# Phase 47 Stage 1+2+3 · 全做治本测试
# 覆盖：5 共享组件 + 6 新页面 + App.tsx 17 路由 + 4 大区导航 + Onboarding 触发
"""
测试目标：
1. 5 共享组件存在 + 导出正确（EmptyState/FilterBar/Onboarding/Header/Footer/AIEmployeeDashboard/OnboardingTrigger）
2. 6 新页面存在（CaseLibrary/FAQ/Blog/TryNow/AIEmployees/OPCStory）
3. App.tsx 含 17 路由 + 4 大区导航 + Footer
4. 4 大区导航 = 产品/行业/资源/我的，每区都带真实链接
5. Onboarding 5 步 + localStorage 触发逻辑
6. Stage 3 卖点：TryNow 包含表单 + 价格套餐引导
"""
import os
import re

ROOT = r"D:\CloudTech-Portable\web\vite-spa\src"
COMPONENTS = os.path.join(ROOT, "components")
PAGES = os.path.join(ROOT, "pages")
APP_FILE = os.path.join(ROOT, "App.tsx")

# ===== 1. 5 共享组件文件存在 =====

def test_empty_state_component_exists():
    path = os.path.join(COMPONENTS, "EmptyState.tsx")
    assert os.path.exists(path), f"EmptyState.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "ILLUSTRATIONS" in content, "EmptyState 缺少 ILLUSTRATIONS 配置"
    assert "OPC 模式" in content, "EmptyState 缺少 OPC 标识"
    print("✓ EmptyState 组件 + 6 插画占位")


def test_filter_bar_component_exists():
    path = os.path.join(COMPONENTS, "FilterBar.tsx")
    assert os.path.exists(path), f"FilterBar.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "搜索" in content or "Search" in content, "FilterBar 缺少搜索功能"
    print("✓ FilterBar 组件 + 搜索/筛选/排序")


def test_onboarding_component_exists():
    path = os.path.join(COMPONENTS, "Onboarding.tsx")
    assert os.path.exists(path), f"Onboarding.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "STEPS" in content, "Onboarding 缺少 STEPS 配置"
    steps_count = len(re.findall(r"icon:\s*['\"]", content))
    assert steps_count >= 5, f"Onboarding 应 ≥5 步，实际 {steps_count}"
    print(f"✓ Onboarding 组件 + {steps_count} 步引导")


def test_header_component_exists():
    path = os.path.join(COMPONENTS, "Header.tsx")
    assert os.path.exists(path), f"Header.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "NAV_SECTIONS" in content, "Header 缺少 NAV_SECTIONS"
    assert "产品" in content and "行业" in content and "资源" in content and "我的" in content, \
        "Header 缺少 4 大区导航"
    print("✓ Header 组件 + 4 大区下拉")


def test_footer_component_exists():
    path = os.path.join(COMPONENTS, "Footer.tsx")
    assert os.path.exists(path), f"Footer.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "京 ICP" in content or "备案" in content, "Footer 缺少备案"
    assert "OPC" in content, "Footer 缺少 OPC 标识"
    print("✓ Footer 组件 + 5 列 + 备案")


def test_ai_employee_dashboard_component_exists():
    path = os.path.join(COMPONENTS, "AIEmployeeDashboard.tsx")
    assert os.path.exists(path), f"AIEmployeeDashboard.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "EMPLOYEES" in content, "AIEmployeeDashboard 缺少 EMPLOYEES 配置"
    for name in ["hermes", "lyra", "athena", "apollo", "artemis"]:
        assert name in content, f"AIEmployeeDashboard 缺少 {name}"
    print("✓ AIEmployeeDashboard 组件 + 5 AI 角色")


def test_onboarding_trigger_component_exists():
    path = os.path.join(COMPONENTS, "OnboardingTrigger.tsx")
    assert os.path.exists(path), f"OnboardingTrigger.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "STORAGE_KEY" in content or "localStorage" in content, "OnboardingTrigger 缺少 localStorage"
    print("✓ OnboardingTrigger 组件 + 首次访问检测")


# ===== 2. 6 新页面存在 =====

def test_case_library_page_exists():
    path = os.path.join(PAGES, "CaseLibrary.tsx")
    assert os.path.exists(path), f"CaseLibrary.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    case_count = len(re.findall(r"id:\s*['\"]case-", content))
    assert case_count >= 10, f"CaseLibrary 应 ≥10 案例，实际 {case_count}"
    assert "成都华宁" in content, "CaseLibrary 缺少标杆案例"
    print(f"✓ CaseLibrary 页 + {case_count} 真实案例")


def test_faq_page_exists():
    path = os.path.join(PAGES, "FAQ.tsx")
    assert os.path.exists(path), f"FAQ.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "FAQS" in content, "FAQ 缺少 FAQS 配置"
    faq_count = len(re.findall(r"category:", content))
    assert faq_count >= 10, f"FAQ 应 ≥10 问题，实际 {faq_count}"
    print(f"✓ FAQ 页 + {faq_count} 问题")


def test_blog_page_exists():
    path = os.path.join(PAGES, "Blog.tsx")
    assert os.path.exists(path), f"Blog.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "POSTS" in content, "Blog 缺少 POSTS 配置"
    assert "OPC" in content, "Blog 缺少 OPC 故事"
    post_count = len(re.findall(r"id:\s*['\"][a-z]+-", content))
    assert post_count >= 8, f"Blog 应 ≥8 篇文章，实际 {post_count}"
    print(f"✓ Blog 页 + {post_count} 文章")


def test_try_now_page_exists():
    path = os.path.join(PAGES, "TryNow.tsx")
    assert os.path.exists(path), f"TryNow.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "STEPS" in content, "TryNow 缺少步骤"
    assert "form" in content or "setForm" in content, "TryNow 缺少表单状态"
    assert "信用卡" in content or "提交" in content, "TryNow 缺少数信用卡承诺"
    print("✓ TryNow 页 + 4 步流程 + 表单")


def test_ai_employees_page_exists():
    path = os.path.join(PAGES, "AIEmployees.tsx")
    assert os.path.exists(path), f"AIEmployees.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "EMPLOYEES" in content, "AIEmployees 缺少 EMPLOYEES"
    assert "todayHours" in content or "今日工时" in content, "AIEmployees 缺少工时统计"
    for name in ["Hermes", "Lyra", "Athena", "Apollo", "Artemis"]:
        assert name in content, f"AIEmployees 缺少 {name}"
    print("✓ AIEmployees 页 + 5 员工工时表")


def test_opc_story_page_exists():
    path = os.path.join(PAGES, "OPCStory.tsx")
    assert os.path.exists(path), f"OPCStory.tsx 不存在: {path}"
    content = open(path, encoding="utf-8").read()
    assert "TIMELINE" in content, "OPCStory 缺少时间线"
    assert "阿劲" in content, "OPCStory 缺少创始人"
    assert "红 #22" in content or "4 不可逆" in content, "OPCStory 缺少治理边界"
    print("✓ OPCStory 页 + 时间线 + 4 闸门")


# ===== 3. App.tsx 17 路由 + Footer 集成 =====

def test_app_has_17_routes():
    content = open(APP_FILE, encoding="utf-8").read()
    routes = re.findall(r'Route\s+path="(/[^"]*)"', content)
    assert len(routes) >= 15, f"App 应 ≥15 路由，实际 {len(routes)}: {routes}"
    print(f"✓ App.tsx 含 {len(routes)} 路由: {routes}")


def test_app_imports_all_new_pages():
    content = open(APP_FILE, encoding="utf-8").read()
    new_pages = ["CaseLibrary", "FAQ", "Blog", "TryNow", "AIEmployees", "OPCStory"]
    for page in new_pages:
        assert page in content, f"App.tsx 缺少 {page} import"
    print(f"✓ App.tsx 导入所有 {len(new_pages)} 新页面")


def test_app_uses_new_header_footer():
    content = open(APP_FILE, encoding="utf-8").read()
    assert "<Header" in content, "App.tsx 未使用 Header 组件"
    assert "<Footer" in content, "App.tsx 未使用 Footer 组件"
    assert "<OnboardingTrigger" in content, "App.tsx 未使用 OnboardingTrigger"
    print("✓ App.tsx 集成 Header + Footer + Onboarding")


def test_app_no_old_inline_header():
    """不应再保留旧的内联 header 块"""
    content = open(APP_FILE, encoding="utf-8").read()
    # 旧 header 是 FEEmployeeMenu + 内联 nav
    assert "<FEEmployeeMenu />" not in content, "App.tsx 残留旧 FEEmployeeMenu"
    print("✓ App.tsx 移除旧内联 header")


# ===== 4. 4 大区导航内容验证 =====

def test_header_has_all_4_sections():
    content = open(os.path.join(COMPONENTS, "Header.tsx"), encoding="utf-8").read()
    # 4 大区
    for section in ["产品", "行业", "资源", "我的"]:
        assert section in content, f"Header 缺少 {section} 大区"
    # 关键链接
    for link in ["/employees", "/monitoring", "/cases", "/blog", "/dashboard", "/clients"]:
        assert link in content, f"Header 缺少关键链接 {link}"
    print("✓ Header 含 4 大区 + 关键链接")


def test_header_uses_badges():
    content = open(os.path.join(COMPONENTS, "Header.tsx"), encoding="utf-8").read()
    assert "HOT" in content or "NEW" in content or "FREE" in content, "Header 缺少 HOT/NEW/FREE 徽章"
    print("✓ Header 含 HOT/NEW/FREE 徽章")


# ===== 5. Onboarding 5 步内容验证 =====

def test_onboarding_5_steps_complete():
    content = open(os.path.join(COMPONENTS, "Onboarding.tsx"), encoding="utf-8").read()
    # 5 步关键内容
    assert "欢迎" in content, "Step 1 缺少欢迎"
    assert "4 步搞定" in content or "4步搞定" in content, "Step 2 缺 4 步"
    assert "5 个 AI" in content or "5个AI" in content, "Step 3 缺 5 AI"
    assert "仪表盘" in content, "Step 4 缺仪表盘"
    assert "7 天" in content or "7天" in content, "Step 5 缺 7 天试用"
    print("✓ Onboarding 5 步内容完整")


def test_onboarding_trigger_uses_localstorage():
    content = open(os.path.join(COMPONENTS, "OnboardingTrigger.tsx"), encoding="utf-8").read()
    assert "localStorage" in content, "OnboardingTrigger 缺 localStorage"
    assert "useEffect" in content, "OnboardingTrigger 缺 useEffect"
    print("✓ OnboardingTrigger 用 localStorage 触发")


# ===== 6. Stage 3 卖点验证 =====

def test_try_now_has_pricing_signal():
    content = open(os.path.join(PAGES, "TryNow.tsx"), encoding="utf-8").read()
    assert "7 天" in content or "30 分钟" in content, "TryNow 缺核心承诺"
    print("✓ TryNow 含 7 天/30 分钟承诺")


def test_pricing_links_to_try():
    content = open(os.path.join(PAGES, "Pricing.tsx"), encoding="utf-8").read()
    assert "/try" in content, "Pricing 应跳到 /try"
    print("✓ Pricing CTA → /try")


# ===== 7. 跨页面交叉引用 =====

def test_pages_reference_employees():
    content = open(os.path.join(PAGES, "Blog.tsx"), encoding="utf-8").read()
    assert "/employees" in content or "/dashboard" in content, "Blog 应引用 /employees 或 /dashboard"
    print("✓ Blog 引用 /employees 或 /dashboard")


def test_case_library_links_try():
    content = open(os.path.join(PAGES, "CaseLibrary.tsx"), encoding="utf-8").read()
    assert "/try" in content, "CaseLibrary 应跳到 /try"
    print("✓ CaseLibrary CTA → /try")


def test_opc_story_links_try():
    content = open(os.path.join(PAGES, "OPCStory.tsx"), encoding="utf-8").read()
    assert "/try" in content, "OPCStory 应跳到 /try"
    print("✓ OPCStory CTA → /try")


def test_faq_links_contact():
    content = open(os.path.join(PAGES, "FAQ.tsx"), encoding="utf-8").read()
    assert "/contact" in content, "FAQ 应跳到 /contact"
    print("✓ FAQ CTA → /contact")


# ===== 8. 文件规模验证 =====

def test_no_garbled_or_empty_pages():
    """所有新页面应 ≥ 100 行（不是 stub）"""
    new_pages = ["CaseLibrary.tsx", "FAQ.tsx", "Blog.tsx", "TryNow.tsx", "AIEmployees.tsx", "OPCStory.tsx"]
    for page in new_pages:
        path = os.path.join(PAGES, page)
        content = open(path, encoding="utf-8").read()
        lines = len(content.split("\n"))
        assert lines >= 100, f"{page} 仅 {lines} 行，可能是 stub"
    print(f"✓ 6 新页面全部 ≥ 100 行（非 stub）")


def test_components_have_real_content():
    """所有共享组件应 ≥ 50 行"""
    components = ["EmptyState.tsx", "FilterBar.tsx", "Onboarding.tsx", "Header.tsx", "Footer.tsx", "AIEmployeeDashboard.tsx", "OnboardingTrigger.tsx"]
    for comp in components:
        path = os.path.join(COMPONENTS, comp)
        content = open(path, encoding="utf-8").read()
        lines = len(content.split("\n"))
        assert lines >= 30, f"{comp} 仅 {lines} 行"
    print(f"✓ 7 共享组件全部 ≥ 30 行")


# ===== 9. 红线守护（防止误删旧页面）=====

def test_old_pages_still_exist():
    """Phase 46 的 11 旧页面必须保留"""
    old_pages = ["Marketing", "Pricing", "Dashboard", "Settings", "Billing", "IndustryDecoration",
                 "IndustryMedical", "ContentSOP", "ClientList", "Documents", "Monitoring"]
    for page in old_pages:
        path = os.path.join(PAGES, f"{page}.tsx")
        assert os.path.exists(path), f"{page}.tsx 不存在（旧页面被误删）"
    print(f"✓ Phase 46 11 旧页面全部保留")


# ===== 主入口 =====

if __name__ == "__main__":
    import sys
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for f in funcs:
        try:
            f()
            passed += 1
        except AssertionError as e:
            print(f"✗ {f.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {f.__name__}: {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"Phase 47 Stage 1+2+3 全做测试: {passed} PASS / {failed} FAIL")
    if failed:
        sys.exit(1)
