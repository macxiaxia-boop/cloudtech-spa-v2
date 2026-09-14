"""Phase 46 M0 4 准备文档测试

覆盖：
- chart_of_accounts.md (50 子科目)
- company_charter_draft.md (10 章 50 条)
- fe_p5_final_jd.md (5 阶段 20 题)
- p0_8_clients.md (北京 6 + 上海 2 = 8 家)
"""
from pathlib import Path
import pytest

ROOT = Path("D:/CloudTech-Portable")
FINANCE = ROOT / "finance"
LEGAL = ROOT / "legal" / "license"
HR = ROOT / "hr"
MARKETING = ROOT / "marketing" / "scripts"


# ─────────────────── 1. chart_of_accounts.md ───────────────────

class TestChartOfAccounts:
    def test_file_exists(self):
        assert (FINANCE / "chart_of_accounts.md").exists()

    def test_has_13_categories(self):
        content = (FINANCE / "chart_of_accounts.md").read_text(encoding="utf-8")
        for cat in ["资产类", "负债类", "所有者权益类", "收入类", "成本类", "费用类", "利润类"]:
            assert cat in content, f"缺 {cat}"

    def test_has_50_subaccounts(self):
        content = (FINANCE / "chart_of_accounts.md").read_text(encoding="utf-8")
        # 计数以 1xxx / 2xxx / 3xxx / 5xxx / 6xxx / 8xxx 开头的科目（可含 - 前缀）
        import re
        subaccounts = re.findall(r"^\s*-?\s*(\d{4})\s+\S", content, re.MULTILINE)
        assert len(subaccounts) >= 50, f"子科目 {len(subaccounts)} < 50"

    def test_has_cities_in_receivable(self):
        content = (FINANCE / "chart_of_accounts.md").read_text(encoding="utf-8")
        for city in ["北京", "上海"]:
            assert city in content, f"缺 {city} 应收账款"

    def test_has_init_checklist(self):
        content = (FINANCE / "chart_of_accounts.md").read_text(encoding="utf-8")
        # 6 必配初始化
        assert "本位币" in content, "缺本位币配置"
        assert "会计准则" in content, "缺会计准则"
        assert "科目体系" in content, "缺科目体系"

    def test_has_invoice_templates(self):
        content = (FINANCE / "chart_of_accounts.md").read_text(encoding="utf-8")
        assert "增值税" in content, "缺发票模板"

    def test_red_22_user_approval(self):
        content = (FINANCE / "chart_of_accounts.md").read_text(encoding="utf-8")
        assert "用户必亲自" in content or "必用户亲自" in content, "缺红 #22 边界守护"


# ─────────────────── 2. company_charter_draft.md ───────────────────

class TestCompanyCharter:
    def test_file_exists(self):
        assert (LEGAL / "company_charter_draft.md").exists()

    def test_has_10_chapters(self):
        content = (LEGAL / "company_charter_draft.md").read_text(encoding="utf-8")
        # 10 章标题
        chapters = [f"第 {i} 章" for i in range(1, 11)]
        for ch in chapters:
            assert ch in content, f"缺{ch}"

    def test_has_50_articles(self):
        content = (LEGAL / "company_charter_draft.md").read_text(encoding="utf-8")
        import re
        articles = re.findall(r"第\s*(\d+)\s*条", content)
        # 去重后 ≥ 30 条
        unique = set(articles)
        assert len(unique) >= 30, f"章程条款 {len(unique)} < 30"

    def test_includes_industry_scope(self):
        content = (LEGAL / "company_charter_draft.md").read_text(encoding="utf-8")
        for scope in ["技术服务", "软件开发", "SaaS", "AI"]:
            assert scope in content, f"经营范围缺 {scope}"

    def test_includes_labor_compliance(self):
        content = (LEGAL / "company_charter_draft.md").read_text(encoding="utf-8")
        assert "劳动法" in content, "缺劳动法引用"

    def test_includes_capital(self):
        content = (LEGAL / "company_charter_draft.md").read_text(encoding="utf-8")
        # 注册资本 ¥100 万认缴 5 年
        assert "100 万" in content or "100万" in content, "缺注册资本"
        assert "认缴" in content, "缺认缴说明"

    def test_red_22_user_approval(self):
        content = (LEGAL / "company_charter_draft.md").read_text(encoding="utf-8")
        assert "用户必拍板" in content, "缺用户拍板项清单"
        # 不可逆闸门：扫脸
        assert "扫脸" in content, "缺 e窗通扫脸提示"


# ─────────────────── 3. fe_p5_final_jd.md ───────────────────

class TestFeP5FinalJD:
    def test_file_exists(self):
        assert (HR / "fe_p5_final_jd.md").exists()

    def test_salary_range(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        assert "25,000" in content or "25K" in content or "¥25" in content, "缺月薪范围下限"
        assert "35,000" in content or "35K" in content or "¥35" in content, "缺月薪范围上限"

    def test_equity_terms(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        assert "期权" in content, "缺期权"
        # 0.1-0.3% + 4 年 vesting + 1 年 cliff
        assert "0.1" in content and "0.3" in content, "缺期权比例"
        assert "vesting" in content or "归属" in content, "缺 vesting 条款"
        assert "cliff" in content or "悬崖" in content, "缺 cliff 条款"

    def test_5_stage_interview(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        for stage in ["阶段 1", "阶段 2", "阶段 3", "阶段 4", "阶段 5"]:
            assert stage in content, f"缺{stage}"

    def test_5_code_questions(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        # 5 道代码题（React/TS/Vite/状态管理/AI 流式）
        assert "React 性能" in content, "缺 React 性能题"
        assert "TypeScript 体操" in content or "DeepReadonly" in content, "缺 TS 体操题"
        assert "Vite" in content, "缺 Vite 配置题"

    def test_5_architecture_questions(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        assert "多租户" in content, "缺多租户架构题"

    def test_5_business_questions(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        assert "客户成功" in content or "试用" in content, "缺客户成功题"

    def test_5_resume_questions(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        assert "5 道问答题" in content, "缺简历问答题节"

    def test_red_22_user_approval(self):
        content = (HR / "fe_p5_final_jd.md").read_text(encoding="utf-8")
        assert "用户必签字" in content or "必用户签字" in content, "缺 offer 签字提示"
        assert "录用" in content, "缺录用决定提示"
        assert "红 #22" in content or "红线" in content, "缺红 #22 边界守护"


# ─────────────────── 4. p0_8_clients.md ───────────────────

class TestP08Clients:
    def test_file_exists(self):
        assert (MARKETING / "p0_8_clients.md").exists()

    def test_has_8_p0_clients(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        # 8 家 P0
        import re
        # 表格中找编号 1-8
        rows = re.findall(r"\|\s*(\d+)\s*\|", content)
        nums = sorted(set(int(r) for r in rows if 1 <= int(r) <= 8))
        assert 1 in nums and 8 in nums, f"P0 编号缺 1 或 8: {nums}"

    def test_beijing_first(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        # 北京为主场
        assert "北京" in content, "缺北京"
        # 北京 ≥ 5 家
        beijing_count = content.count("北京")
        assert beijing_count >= 5, f"北京出现 {beijing_count} 次 < 5"

    def test_decoration_and_medical(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        for ind in ["装企", "医美"]:
            assert ind in content, f"缺行业 {ind}"

    def test_7_step_sop(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        # 7 步 SOP
        assert "D1: 准备" in content, "缺 D1"
        assert "D2: 第一通" in content, "缺 D2"
        assert "D7" in content or "D6-D7" in content, "缺 D6/D7"

    def test_8_pitch_scripts(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        # 8 套切入话术
        scripts = content.count("套切入话术")
        assert scripts >= 2, "缺 8 套话术总结"

    def test_medical_compliance_script(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        # 医美合规话术必含 6 红线之一
        for kw in ["医疗广告管理办法", "医疗美容服务管理办法"]:
            assert kw in content, f"医美合规缺 {kw}"

    def test_red_22_user_must_call(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        assert "用户亲自打" in content, "缺用户亲自打"
        assert "100%" in content, "缺 100% 触达目标"

    def test_funnel_metrics(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        # 4 阶段漏斗（demo / 试用 / 签约 + 触达状态 pending）
        for stage in ["pending", "demo", "试用", "签约"]:
            assert stage in content, f"缺漏斗 {stage}"

    def test_mrr_target(self):
        content = (MARKETING / "p0_8_clients.md").read_text(encoding="utf-8")
        # MRR 目标
        assert "MRR" in content, "缺 MRR"
        assert "¥" in content, "缺金额目标"


# ─────────────────── 5. 4 准备文档交叉引用 ───────────────────

class TestM0PrepCrossRefs:
    """4 M0 准备文档互相引用 + 与 Phase 46 文档链接"""

    def test_action_plan_references_all_4_preps(self):
        plan = (ROOT / "decision_cards" / "M0_action_plan_2026-09-14.md").read_text(encoding="utf-8")
        for ref in ["company_charter_draft", "chart_of_accounts", "fe_p5_final_jd", "p0_8_clients"]:
            assert ref in plan, f"行动计划缺 {ref} 引用"

    def test_decisions_references_all_4_preps(self):
        dec = (ROOT / "decision_cards" / "M0_decisions_2026-09-14.md").read_text(encoding="utf-8")
        for ref in ["company_charter_draft", "chart_of_accounts", "fe_p5_final_jd", "p0_8_clients"]:
            assert ref in dec, f"决策卡缺 {ref} 引用"

    def test_prep_docs_mention_decision_cards(self):
        # 至少 1 准备文档引用 decision_cards
        refs = 0
        for f in ["chart_of_accounts.md", "company_charter_draft.md", "fe_p5_final_jd.md", "p0_8_clients.md"]:
            content = (ROOT / (
                "finance/" + f if "chart_of_accounts" in f else
                "legal/license/" + f if "company_charter" in f else
                "hr/" + f if "fe_p5_final" in f else
                "marketing/scripts/" + f
            )).read_text(encoding="utf-8")
            if "decision_cards" in content or "M0_decisions" in content:
                refs += 1
        assert refs >= 2, f"仅 {refs} 准备文档引用 decision_cards（应 ≥ 2）"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
