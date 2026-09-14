"""Phase 46 D61-68 财务 + 监控 + 客户漏斗测试

覆盖：
- 2 Grafana 仪表盘 JSON 合法性
- Prometheus 告警规则 YAML 完整性
- 5 SaaS 选型调研文档
- 飞书 Webhook SOP
- 80 家客户漏斗监控配置
- Monitoring SPA 页组件
- App.tsx 路由 + 导航链接
- 红 #22 监控边界守护
"""
import json
import re
from pathlib import Path
import pytest

ROOT = Path("D:/CloudTech-Portable")
FINANCE = ROOT / "finance"
WEB_PAGES = ROOT / "web" / "vite-spa" / "src" / "pages"
WEB_APP = ROOT / "web" / "vite-spa" / "src" / "App.tsx"


# ─────────────────── 1. Grafana 仪表盘 ───────────────────

class TestGrafanaTechDashboard:
    def test_file_exists(self):
        assert (FINANCE / "grafana_dashboard_tech.json").exists()

    def test_valid_json(self):
        with open(FINANCE / "grafana_dashboard_tech.json", encoding="utf-8") as f:
            data = json.load(f)
        assert "panels" in data
        assert "title" in data

    def test_has_required_panels(self):
        with open(FINANCE / "grafana_dashboard_tech.json", encoding="utf-8") as f:
            data = json.load(f)
        panel_titles = [p["title"] for p in data["panels"]]
        # 必备 5 类技术健康面板
        assert any("延迟" in t for t in panel_titles), "缺 API 延迟面板"
        assert any("错误" in t for t in panel_titles), "缺错误率面板"
        assert any("数据库" in t or "DB" in t for t in panel_titles), "缺数据库面板"
        assert any("LLM" in t for t in panel_titles), "缺 LLM 面板"
        assert any("日志" in t for t in panel_titles), "缺日志面板"


class TestGrafanaBusinessDashboard:
    def test_file_exists(self):
        assert (FINANCE / "grafana_dashboard_business.json").exists()

    def test_valid_json(self):
        with open(FINANCE / "grafana_dashboard_business.json", encoding="utf-8") as f:
            data = json.load(f)
        assert "panels" in data

    def test_has_north_star_metrics(self):
        with open(FINANCE / "grafana_dashboard_business.json", encoding="utf-8") as f:
            data = json.load(f)
        panel_titles = [p["title"] for p in data["panels"]]
        # 北极星 4 指标
        assert any("MRR" in t for t in panel_titles), "缺 MRR 面板"
        assert any("客户" in t for t in panel_titles), "缺客户数面板"
        assert any("流失" in t for t in panel_titles), "缺流失率面板"
        assert any("NRR" in t or "留存" in t for t in panel_titles), "缺 NRR 面板"

    def test_has_funnel_panel(self):
        with open(FINANCE / "grafana_dashboard_business.json", encoding="utf-8") as f:
            data = json.load(f)
        panel_titles = [p["title"] for p in data["panels"]]
        assert any("漏斗" in t or "80" in t for t in panel_titles), "缺 80 家漏斗面板"


# ─────────────────── 2. Prometheus 告警 ───────────────────

class TestPrometheusAlerts:
    def test_file_exists(self):
        assert (FINANCE / "prometheus_alerts.yml").exists()

    def test_has_4_severity_levels(self):
        content = (FINANCE / "prometheus_alerts.yml").read_text(encoding="utf-8")
        for level in ["p0_critical", "p1_important", "p2_warning", "p3_reminder"]:
            assert f"name: {level}" in content, f"缺 {level} 告警组"

    def test_p0_includes_api_down(self):
        content = (FINANCE / "prometheus_alerts.yml").read_text(encoding="utf-8")
        assert "APIDown" in content, "P0 必含 APIDown"

    def test_p0_includes_security(self):
        content = (FINANCE / "prometheus_alerts.yml").read_text(encoding="utf-8")
        assert "SecurityBreach" in content, "P0 必含安全事件告警（红 #22）"

    def test_has_runbook_annotation(self):
        content = (FINANCE / "prometheus_alerts.yml").read_text(encoding="utf-8")
        assert "runbook:" in content, "缺 runbook 注解"


# ─────────────────── 3. 飞书 Webhook SOP ───────────────────

class TestFeishuWebhookSetup:
    def test_file_exists(self):
        assert (FINANCE / "feishu_webhook_setup.md").exists()

    def test_has_4_channels(self):
        content = (FINANCE / "feishu_webhook_setup.md").read_text(encoding="utf-8")
        for ch in ["feishu_robot_critical", "feishu_robot_important", "feishu_robot_warning", "feishu_robot_reminder"]:
            assert ch in content, f"缺 {ch} 通道"

    def test_has_5_step_sop(self):
        content = (FINANCE / "feishu_webhook_setup.md").read_text(encoding="utf-8")
        for step in ["步骤 1", "步骤 2", "步骤 3", "步骤 4", "步骤 5"]:
            assert step in content, f"缺 {step}"

    def test_red_22_boundary_declared(self):
        content = (FINANCE / "feishu_webhook_setup.md").read_text(encoding="utf-8")
        assert "红 #22" in content or "红线 #22" in content or "红线" in content, "缺红 #22 边界守护"

    def test_has_alertmanager_yaml(self):
        content = (FINANCE / "feishu_webhook_setup.md").read_text(encoding="utf-8")
        assert "alertmanager.yml" in content, "缺 AlertManager 配置示例"


# ─────────────────── 4. SaaS 选型 ───────────────────

class TestSaasSelection:
    def test_file_exists(self):
        assert (FINANCE / "saas_selection.md").exists()

    def test_has_5_categories(self):
        content = (FINANCE / "saas_selection.md").read_text(encoding="utf-8")
        # 至少含 5 类别标题
        assert content.count("###") >= 5, "选型文档 < 5 类"

    def test_has_recommendation(self):
        content = (FINANCE / "saas_selection.md").read_text(encoding="utf-8")
        assert "推荐" in content, "缺推荐"

    def test_includes_jingdou(self):
        content = (FINANCE / "saas_selection.md").read_text(encoding="utf-8")
        assert "金蝶" in content, "财务 SaaS 推荐金蝶"

    def test_includes_feishu_hr(self):
        content = (FINANCE / "saas_selection.md").read_text(encoding="utf-8")
        assert "飞书人事" in content, "HR 推荐飞书人事"

    def test_has_cost_estimation(self):
        content = (FINANCE / "saas_selection.md").read_text(encoding="utf-8")
        # M1 总成本估算
        assert "¥" in content and "小计" in content, "缺成本估算表"


# ─────────────────── 5. 客户漏斗监控 ───────────────────

class TestClientFunnelMonitoring:
    def test_file_exists(self):
        assert (FINANCE / "client_funnel_monitoring.md").exists()

    def test_has_5_status_machine(self):
        content = (FINANCE / "client_funnel_monitoring.md").read_text(encoding="utf-8")
        for status in ["pending", "contacted", "demo_scheduled", "trial", "signed"]:
            assert status in content, f"缺 {status} 状态"

    def test_has_sql_schema(self):
        content = (FINANCE / "client_funnel_monitoring.md").read_text(encoding="utf-8")
        assert "CREATE TABLE" in content, "缺表结构 SQL"
        assert "client_outreach" in content, "缺 client_outreach 表"

    def test_has_4_metrics(self):
        content = (FINANCE / "client_funnel_monitoring.md").read_text(encoding="utf-8")
        assert content.count("指标") >= 4, "监控指标 < 4"

    def test_red_22_p0_must_call_user(self):
        content = (FINANCE / "client_funnel_monitoring.md").read_text(encoding="utf-8")
        assert "P0" in content and "亲自" in content, "P0 必用户亲自打（红 #22）"


# ─────────────────── 6. Monitoring SPA 页 ───────────────────

class TestMonitoringPage:
    def test_file_exists(self):
        assert (WEB_PAGES / "Monitoring.tsx").exists()

    def test_exports_monitoring_page(self):
        content = (WEB_PAGES / "Monitoring.tsx").read_text(encoding="utf-8")
        assert "export function MonitoringPage" in content

    def test_has_4_alert_levels(self):
        content = (WEB_PAGES / "Monitoring.tsx").read_text(encoding="utf-8")
        for level in ["P0", "P1", "P2", "P3"]:
            assert level in content, f"缺 {level} 告警级别"

    def test_has_5_funnel_stages(self):
        content = (WEB_PAGES / "Monitoring.tsx").read_text(encoding="utf-8")
        for stage in ["待触达", "已联系", "已约演示", "试用中", "已签约"]:
            assert stage in content, f"缺漏斗 {stage}"

    def test_has_red_22_banner(self):
        content = (WEB_PAGES / "Monitoring.tsx").read_text(encoding="utf-8")
        assert "红 #22" in content or "红线 #22" in content, "缺红 #22 边界 banner"

    def test_has_5_saas_stack(self):
        content = (WEB_PAGES / "Monitoring.tsx").read_text(encoding="utf-8")
        for cat in ["金蝶", "飞书人事", "Grafana", "阿里云", "ICP"]:
            assert cat in content, f"缺 {cat} 选型"


# ─────────────────── 7. App.tsx 路由 ───────────────────

class TestAppRoutes:
    def test_monitoring_imported(self):
        content = (WEB_APP).read_text(encoding="utf-8")
        assert "MonitoringPage" in content, "MonitoringPage 未 import"

    def test_monitoring_route(self):
        content = (WEB_APP).read_text(encoding="utf-8")
        assert 'path="/monitoring"' in content, "缺 /monitoring 路由"

    def test_navigation_link(self):
        content = (WEB_APP).read_text(encoding="utf-8")
        assert 'to="/monitoring"' in content, "导航缺 /monitoring 链接"

    def test_all_previous_routes_preserved(self):
        content = (WEB_APP).read_text(encoding="utf-8")
        for route in ["/", "/pricing", "/dashboard", "/settings", "/billing", "/clients", "/documents"]:
            assert f'path="{route}"' in content, f"缺 {route} 路由"


# ─────────────────── 8. 红 #22 监控边界守护 ───────────────────

class TestRedLine22MonitoringBoundary:
    """所有 D61-68 监控 + 财务文档必含红 #22 必拍板项"""

    @pytest.mark.parametrize("filename,boundary_keyword", [
        ("saas_selection.md", "用户拍板"),
        ("feishu_webhook_setup.md", "用户拍板"),
        ("client_funnel_monitoring.md", "用户拍板"),
    ])
    def test_docs_declare_red22_user_approval(self, filename, boundary_keyword):
        content = (FINANCE / filename).read_text(encoding="utf-8")
        assert boundary_keyword in content, f"{filename} 缺{boundary_keyword}边界守护"

    def test_monitoring_spa_declare_red22(self):
        content = (WEB_PAGES / "Monitoring.tsx").read_text(encoding="utf-8")
        assert "红 #22" in content, "Monitoring SPA 缺红 #22 banner"

    def test_red22_distinguishes_internal_vs_external(self):
        """红 #22 必区分内部 AI 可做 vs 外部必用户拍板"""
        for fn in ["saas_selection.md", "feishu_webhook_setup.md", "client_funnel_monitoring.md"]:
            content = (FINANCE / fn).read_text(encoding="utf-8")
            assert "AI" in content or "内部" in content, f"{fn} 缺内部 vs 外部区分"


# ─────────────────── 9. 与 Phase 46 段 1-3 闭环 ───────────────────

class TestPhase46Closure:
    def test_phase_46_segment_4_complete(self):
        """段 4 必含 7 项产出"""
        required_files = [
            "finance/grafana_dashboard_tech.json",
            "finance/grafana_dashboard_business.json",
            "finance/prometheus_alerts.yml",
            "finance/feishu_webhook_setup.md",
            "finance/saas_selection.md",
            "finance/client_funnel_monitoring.md",
            "web/vite-spa/src/pages/Monitoring.tsx",
        ]
        for f in required_files:
            assert (ROOT / f).exists(), f"缺 {f}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
