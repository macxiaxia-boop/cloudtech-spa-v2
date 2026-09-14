"""
Phase 46 D53-60 — 公司文档中心（合同/HR/财务/营业执照）验收测试
=================================================================

验收标准:
  1. 16 份文档就位（7 法务 + 5 HR + 2 财务 + 2 营销）
  2. Documents.tsx 列出全部 16 份文档
  3. App.tsx 加 /documents 路由
  4. 5 类合同模板齐
  5. 3 类 JD（FE/BE/内容）+ Offer + 招聘 SOP
  6. 财务模型 + 监控仪表盘配置
  7. 营业执照 + 注册流程图
  8. 2 营销外呼脚本（装企/医美）
  9. 红 #22 边界守护正确标注
"""
from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(r"D:\CloudTech-Portable")
VITE_SPA_SRC = PROJECT_ROOT / "web" / "vite-spa" / "src"


# ══════════════ 16 份文档存在性 ══════════════

# ─── 法务 7 ───
def test_customer_service_agreement_exists():
    p = PROJECT_ROOT / "legal" / "contracts" / "customer_service_agreement.md"
    assert p.exists(), f"missing: {p}"


def test_nda_exists():
    p = PROJECT_ROOT / "legal" / "contracts" / "nda.md"
    assert p.exists(), f"missing: {p}"


def test_dpa_exists():
    p = PROJECT_ROOT / "legal" / "contracts" / "data_processing_agreement.md"
    assert p.exists(), f"missing: {p}"


def test_medical_redlines_exists():
    p = PROJECT_ROOT / "legal" / "medical_compliance_redlines.md"
    assert p.exists(), f"missing: {p}"


def test_legal_checklist_exists():
    p = PROJECT_ROOT / "legal" / "contracts" / "legal_review_checklist.md"
    assert p.exists(), f"missing: {p}"


def test_business_license_exists():
    p = PROJECT_ROOT / "legal" / "license" / "business_license_checklist.md"
    assert p.exists(), f"missing: {p}"


def test_registration_flow_exists():
    p = PROJECT_ROOT / "legal" / "license" / "registration_flow.md"
    assert p.exists(), f"missing: {p}"


# ─── HR 5 ───
def test_jd_fe_exists():
    p = PROJECT_ROOT / "hr" / "jd_fe_engineer.md"
    assert p.exists(), f"missing: {p}"


def test_jd_be_exists():
    p = PROJECT_ROOT / "hr" / "jd_be_engineer.md"
    assert p.exists(), f"missing: {p}"


def test_jd_content_exists():
    p = PROJECT_ROOT / "hr" / "jd_content_marketing.md"
    assert p.exists(), f"missing: {p}"


def test_offer_template_exists():
    p = PROJECT_ROOT / "hr" / "offer_template.md"
    assert p.exists(), f"missing: {p}"


def test_hiring_sop_exists():
    p = PROJECT_ROOT / "hr" / "hiring_sop.md"
    assert p.exists(), f"missing: {p}"


# ─── 财务 2 ───
def test_financial_model_exists():
    p = PROJECT_ROOT / "finance" / "financial_model.md"
    assert p.exists(), f"missing: {p}"


def test_monitoring_dashboard_exists():
    p = PROJECT_ROOT / "finance" / "monitoring_dashboard.md"
    assert p.exists(), f"missing: {p}"


# ─── 营销 2 ───
def test_outreach_decoration_exists():
    p = PROJECT_ROOT / "marketing" / "scripts" / "outreach_decoration.md"
    assert p.exists(), f"missing: {p}"


def test_outreach_medical_exists():
    p = PROJECT_ROOT / "marketing" / "scripts" / "outreach_medical.md"
    assert p.exists(), f"missing: {p}"


# ══════════════ Documents.tsx ══════════════

def test_documents_page_exists():
    p = VITE_SPA_SRC / "pages" / "Documents.tsx"
    assert p.exists(), f"missing: {p}"


def test_app_tsx_has_documents_route():
    """App.tsx 含 /documents 路由"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'path="/documents"' in content
    assert "DocumentsPage" in content


def test_navigation_links_to_documents():
    """App.tsx 导航含文档入口"""
    p = VITE_SPA_SRC / "App.tsx"
    content = p.read_text(encoding="utf-8")
    assert 'to="/documents"' in content


def test_documents_lists_all_16():
    """Documents.tsx 列出全部 16 份文档"""
    p = VITE_SPA_SRC / "pages" / "Documents.tsx"
    content = p.read_text(encoding="utf-8")
    # 法务 7
    for kw in ["customer_service_agreement", "nda", "data_processing_agreement",
               "medical_compliance_redlines", "legal_review_checklist",
               "business_license_checklist", "registration_flow"]:
        assert kw in content, f"缺法务文档: {kw}"
    # HR 5
    for kw in ["jd_fe_engineer", "jd_be_engineer", "jd_content_marketing",
               "offer_template", "hiring_sop"]:
        assert kw in content, f"缺 HR 文档: {kw}"
    # 财务 2
    for kw in ["financial_model", "monitoring_dashboard"]:
        assert kw in content, f"缺财务文档: {kw}"
    # 营销 2
    for kw in ["outreach_decoration", "outreach_medical"]:
        assert kw in content, f"缺营销文档: {kw}"


def test_documents_has_4_categories():
    """Documents.tsx 含 4 类别分组"""
    p = VITE_SPA_SRC / "pages" / "Documents.tsx"
    content = p.read_text(encoding="utf-8")
    for cat in ["legal", "hr", "finance", "marketing"]:
        assert cat in content, f"缺类别: {cat}"


def test_documents_red22_summary():
    """Documents.tsx 含红 #22 总览"""
    p = VITE_SPA_SRC / "pages" / "Documents.tsx"
    content = p.read_text(encoding="utf-8")
    assert "红线 #22" in content or "红 #22" in content
    assert "必用户拍板" in content


# ══════════════ 合同模板内容 ══════════════

def test_customer_service_agreement_sla_section():
    """主服务协议含 SLA + 数据归属 + 红线 #22 触达边界"""
    p = PROJECT_ROOT / "legal" / "contracts" / "customer_service_agreement.md"
    content = p.read_text(encoding="utf-8")
    assert "SLA" in content
    assert "数据归属" in content
    assert "红 #22" in content or "红线 #22" in content


def test_nda_has_compensation():
    """NDA 含违约金条款"""
    p = PROJECT_ROOT / "legal" / "contracts" / "nda.md"
    content = p.read_text(encoding="utf-8")
    assert "违约金" in content
    assert "500,000" in content or "伍拾万元" in content


def test_dpa_cites_laws():
    """DPA 引用个人信息保护法"""
    p = PROJECT_ROOT / "legal" / "contracts" / "data_processing_agreement.md"
    content = p.read_text(encoding="utf-8")
    assert "个人信息保护法" in content
    assert "数据安全法" in content


def test_medical_redlines_6_categories():
    """医美 6 条合规红线全列"""
    p = PROJECT_ROOT / "legal" / "medical_compliance_redlines.md"
    content = p.read_text(encoding="utf-8")
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


def test_legal_checklist_35_items():
    """法务审查清单 35 项"""
    p = PROJECT_ROOT / "legal" / "contracts" / "legal_review_checklist.md"
    content = p.read_text(encoding="utf-8")
    # 5 类 × 7+ 平均 = 35
    assert "8 项" in content  # 主服务
    assert "6 项" in content  # NDA
    assert "9 项" in content  # DPA
    assert "7 项" in content  # Offer
    assert "5 项" in content  # 营业执照


# ══════════════ HR 文档内容 ══════════════

def test_jd_fe_has_3_levels():
    """FE JD 含 P5/P6/P7 三档"""
    p = PROJECT_ROOT / "hr" / "jd_fe_engineer.md"
    content = p.read_text(encoding="utf-8")
    for level in ["P5", "P6", "P7"]:
        assert level in content, f"缺级别: {level}"


def test_jd_be_has_fastapi_stack():
    """BE JD 含 FastAPI/PostgreSQL 栈"""
    p = PROJECT_ROOT / "hr" / "jd_be_engineer.md"
    content = p.read_text(encoding="utf-8")
    assert "FastAPI" in content
    assert "PostgreSQL" in content


def test_jd_content_has_phase_41_44():
    """内容运营 JD 引用 Phase 41-44"""
    p = PROJECT_ROOT / "hr" / "jd_content_marketing.md"
    content = p.read_text(encoding="utf-8")
    # 范围写法 "Phase 41-44" 也接受
    assert "Phase 41-44" in content or all(
        phase in content for phase in ["Phase 41", "Phase 42", "Phase 43", "Phase 44"]
    ), "缺 Phase 41-44 引用"


def test_offer_template_4_attachments():
    """Offer 模板含 4 件套"""
    p = PROJECT_ROOT / "hr" / "offer_template.md"
    content = p.read_text(encoding="utf-8")
    for att in ["岗位 JD", "薪酬结构表", "试用期考核标准", "NDA 保密协议"]:
        assert att in content, f"缺附件: {att}"


def test_hiring_sop_5_phases():
    """招聘 SOP 含 5 阶段"""
    p = PROJECT_ROOT / "hr" / "hiring_sop.md"
    content = p.read_text(encoding="utf-8")
    assert "阶段 1" in content
    assert "阶段 2" in content
    assert "阶段 3" in content
    assert "阶段 4" in content
    assert "阶段 5" in content


def test_hiring_sop_red22_boundary():
    """招聘 SOP 含红 #22 边界守护"""
    p = PROJECT_ROOT / "hr" / "hiring_sop.md"
    content = p.read_text(encoding="utf-8")
    assert "必用户拍板" in content
    assert "AI 可主动干" in content


# ══════════════ 财务文档内容 ══════════════

def test_financial_model_3_plans():
    """财务模型含 3 档套餐"""
    p = PROJECT_ROOT / "finance" / "financial_model.md"
    content = p.read_text(encoding="utf-8")
    for plan in ["免费版", "专业版", "企业版"]:
        assert plan in content, f"缺套餐: {plan}"


def test_financial_model_mrr_targets():
    """财务模型含 M1/M3/M6/M12 MRR 预测"""
    p = PROJECT_ROOT / "finance" / "financial_model.md"
    content = p.read_text(encoding="utf-8")
    for milestone in ["M1", "M3", "M6", "M12"]:
        assert milestone in content, f"缺里程碑: {milestone}"
    assert "MRR" in content
    assert "ARR" in content


def test_financial_model_x01_f01_section():
    """财务模型含 X01/F01 SaaS 选型"""
    p = PROJECT_ROOT / "finance" / "financial_model.md"
    content = p.read_text(encoding="utf-8")
    assert "X01/F01" in content or "SaaS 选型" in content


def test_monitoring_dashboard_4_levels():
    """监控仪表盘 P0/P1/P2/P3 四级告警"""
    p = PROJECT_ROOT / "finance" / "monitoring_dashboard.md"
    content = p.read_text(encoding="utf-8")
    for level in ["P0", "P1", "P2", "P3"]:
        assert level in content, f"缺告警级别: {level}"


# ══════════════ 营业执照 ══════════════

def test_business_license_5_must_fill():
    """营业执照 5 类必填信息"""
    p = PROJECT_ROOT / "legal" / "license" / "business_license_checklist.md"
    content = p.read_text(encoding="utf-8")
    for kw in ["公司名称", "注册资本", "经营范围", "法人", "股东", "注册地址"]:
        assert kw in content, f"缺必填项: {kw}"


def test_registration_flow_m0_m1_m2():
    """注册流程 M0/M1/M2 三阶段"""
    p = PROJECT_ROOT / "legal" / "license" / "registration_flow.md"
    content = p.read_text(encoding="utf-8")
    assert "M0" in content
    assert "M1" in content
    assert "M2" in content


# ══════════════ 营销脚本 ══════════════

def test_outreach_decoration_4_levels():
    """装企外呼脚本 P0/P1/P2/P3 分级"""
    p = PROJECT_ROOT / "marketing" / "scripts" / "outreach_decoration.md"
    content = p.read_text(encoding="utf-8")
    for level in ["P0", "P1", "P2", "P3"]:
        assert level in content, f"缺优先级: {level}"


def test_outreach_medical_compliance_warning():
    """医美外呼脚本含合规警告"""
    p = PROJECT_ROOT / "marketing" / "scripts" / "outreach_medical.md"
    content = p.read_text(encoding="utf-8")
    assert "6 条监管红线" in content or "医美行业特殊要求" in content


# ══════════════ Phase 46 联动 ══════════════

def test_total_documents_count():
    """D53-60 共 16 份文档"""
    legal = list((PROJECT_ROOT / "legal").rglob("*.md"))
    hr = list((PROJECT_ROOT / "hr").rglob("*.md"))
    finance = list((PROJECT_ROOT / "finance").rglob("*.md"))
    marketing = list((PROJECT_ROOT / "marketing" / "scripts").rglob("*.md"))
    total = len(legal) + len(hr) + len(finance) + len(marketing)
    assert total >= 16, f"文档总数应为 ≥ 16，实际 {total} (legal={len(legal)} hr={len(hr)} finance={len(finance)} marketing={len(marketing)})"


def test_all_documents_have_red22_section():
    """所有文档含红 #22 必拍板小节"""
    docs_to_check = [
        "legal/contracts/customer_service_agreement.md",
        "legal/contracts/nda.md",
        "legal/contracts/data_processing_agreement.md",
        "legal/medical_compliance_redlines.md",
        "legal/contracts/legal_review_checklist.md",
        "legal/license/business_license_checklist.md",
        "legal/license/registration_flow.md",
        "hr/jd_fe_engineer.md",
        "hr/jd_be_engineer.md",
        "hr/jd_content_marketing.md",
        "hr/offer_template.md",
        "hr/hiring_sop.md",
        "finance/financial_model.md",
        "finance/monitoring_dashboard.md",
        "marketing/scripts/outreach_decoration.md",
        "marketing/scripts/outreach_medical.md",
    ]
    for rel_path in docs_to_check:
        p = PROJECT_ROOT / rel_path
        content = p.read_text(encoding="utf-8")
        assert "红 #22" in content or "红线 #22" in content, f"{rel_path} 缺红 #22 守护小节"


def test_phase46_total_pages():
    """Phase 46 累计页面数 ≥ 10"""
    pages_dir = VITE_SPA_SRC / "pages"
    page_files = list(pages_dir.glob("*.tsx"))
    assert len(page_files) >= 10, f"页面数应为 ≥ 10，实际 {len(page_files)}: {[p.name for p in page_files]}"
