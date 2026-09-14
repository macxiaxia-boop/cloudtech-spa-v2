import { Routes, Route, Link } from 'react-router-dom';
import { MarketingPage } from './pages/Marketing';
import { PricingPage } from './pages/Pricing';
import { DashboardPage } from './pages/Dashboard';
import { SettingsPage } from './pages/Settings';
import { BillingPage } from './pages/Billing';
import { IndustryDecorationPage } from './pages/IndustryDecoration';
import { IndustryMedicalPage } from './pages/IndustryMedical';
import { ContentSOPPage } from './pages/ContentSOP';
import { ClientListPage } from './pages/ClientList';
import { DocumentsPage } from './pages/Documents';
import { MonitoringPage } from './pages/Monitoring';
import { CaseLibraryPage } from './pages/CaseLibrary';
import { FAQPage } from './pages/FAQ';
import { BlogPage } from './pages/Blog';
import { TryNowPage } from './pages/TryNow';
import { AIEmployeesPage } from './pages/AIEmployees';
import { OPCStoryPage } from './pages/OPCStory';
import { FunnelPage } from './pages/Funnel';
import { FEEmployeeMenu } from './components/FEEmployeeMenu';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { OnboardingTrigger } from './components/OnboardingTrigger';

// Phase 47: 全部做（Stage 1+2+3）— 17 页面 + 完整导航 + Onboarding + 新监控
// Phase 48.D84-87: Funnel + Revenue 接入 SPA（4 大补漏）
// 4 大区导航：产品 / 行业 / 资源 / 我的
// 路由:
//  /                              — 营销首页（4 关键数字嵌入）
//  /pricing                       — 定价（含 Revenue 预测表）
//  /try                           — 7 天试用（Stage 3 卖）
//  /employees                     — 5 AI 数字员工完整工时表
//  /funnel                        — 漏斗转化（5 状态机 + 4 洞察）
//  /industries/decoration         — 装企行业落地页（SEO）
//  /industries/medical            — 医美行业落地页（SEO + 合规）
//  /content-sop                   — 内容生产 SOP 工具
//  /cases                         — 10 客户案例库（5 装企 + 5 医美）
//  /blog                          — 博客（OPC 故事 + 行业洞察）
//  /faq                           — 帮助中心
//  /opc-story                     — 心之所向便是光的今天 · 创始人后台
//  /clients                       — 80 家客户清单
//  /documents                     — 公司文档中心
//  /monitoring                    — 监控与财务中心
//  /dashboard                     — 客户后台
//  /settings                      — 账号设置
//  /billing                       — 套餐切换
export default function App() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<MarketingPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/try" element={<TryNowPage />} />
          <Route path="/employees" element={<AIEmployeesPage />} />
          <Route path="/funnel" element={<FunnelPage />} />
          <Route path="/industries/decoration" element={<IndustryDecorationPage />} />
          <Route path="/industries/medical" element={<IndustryMedicalPage />} />
          <Route path="/content-sop" element={<ContentSOPPage />} />
          <Route path="/cases" element={<CaseLibraryPage />} />
          <Route path="/blog" element={<BlogPage />} />
          <Route path="/faq" element={<FAQPage />} />
          <Route path="/opc-story" element={<OPCStoryPage />} />
          <Route path="/clients" element={<ClientListPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/billing" element={<BillingPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      <Footer />
      <OnboardingTrigger />
    </div>
  );
}

function NotFound() {
  return (
    <div className="max-w-page mx-auto px-6 py-20 text-center">
      <h1 className="text-3xl font-bold mb-4">404 · 没找到这页</h1>
      <Link to="/" className="text-brand-500 hover:underline">返回首页</Link>
    </div>
  );
}
