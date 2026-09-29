/**
 * CloudTech App · 路由分流（v3 重构）
 *
 * 三套路由分流：
 * 1. 营销路由（marketing）: 用 Header/Footer 包装，marketing-first 布局
 * 2. 工作台路由（AppShell）: 用 BasicLayout 包装，左 sidebar + 顶 header
 * 3. 居中路由（centered）: 不套任何 layout（/login /register /workspace/select）
 */
import { Routes, Route, Link, Outlet } from 'react-router-dom';
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

import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { OnboardingTrigger } from './components/OnboardingTrigger';
import { BasicLayout } from './components/AppShell/BasicLayout';
import { WorkspaceSelectorPage } from './pages/WorkspaceSelect';
import { LoginPage } from './pages/Login';
import { RegisterPage } from './pages/Register';
import { ChatPage } from './pages/Chat';
import { TasksPage } from './pages/Tasks';
import { AgentCreatePage } from './pages/AgentCreate';
import { KnowledgePage } from './pages/Knowledge';
import { FilesPage } from './pages/Files';
import { WorkflowsPage } from './pages/Workflows';
import { WorkflowEditorPage } from './pages/WorkflowEditor';
import { AnalyticsPage } from './pages/Analytics';
import { SettingsSystemPage } from './pages/SettingsSystem';
import { SettingsTeamPage } from './pages/SettingsTeam';
import { ProfilePage } from './pages/Profile';
import { NotificationsPage } from './pages/Notifications';
import { AgentsPage } from './pages/Agents';

/* ───── Layout: Marketing（marketing Header/Footer） ───── */
function MarketingLayout() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
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

export default function App() {
  return (
    <Routes>
      {/* 营销路由（marketing Header/Footer）*/}
      <Route element={<MarketingLayout />}>
        <Route path="/" element={<MarketingPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/try" element={<TryNowPage />} />
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
        <Route path="/billing" element={<BillingPage />} />
      </Route>

      {/* 居中路由（全屏居中卡片，不套 layout）*/}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/workspace/select" element={<WorkspaceSelectorPage />} />

      {/* 工作台路由（BasicLayout · children prop 模式）*/}
      <Route path="/dashboard" element={<BasicLayout><DashboardPage /></BasicLayout>} />
      <Route path="/chat" element={<BasicLayout showBreadcrumb={false}><ChatPage /></BasicLayout>} />
      <Route path="/employees" element={<BasicLayout><AgentsPage /></BasicLayout>} />
      <Route path="/employees/new" element={<BasicLayout><AgentCreatePage /></BasicLayout>} />
      <Route path="/employees/:id/edit" element={<BasicLayout><AgentCreatePage /></BasicLayout>} />
      <Route path="/tasks" element={<BasicLayout><TasksPage /></BasicLayout>} />
      <Route path="/knowledge" element={<BasicLayout><KnowledgePage /></BasicLayout>} />
      <Route path="/files" element={<BasicLayout><FilesPage /></BasicLayout>} />
      <Route path="/workflows" element={<BasicLayout><WorkflowsPage /></BasicLayout>} />
      <Route path="/workflows/new" element={<BasicLayout showBreadcrumb={false}><WorkflowEditorPage /></BasicLayout>} />
      <Route path="/workflows/:id" element={<BasicLayout showBreadcrumb={false}><WorkflowEditorPage /></BasicLayout>} />
      <Route path="/settings" element={<BasicLayout><SettingsPage /></BasicLayout>} />
      <Route path="/settings/models" element={<BasicLayout><SettingsPage /></BasicLayout>} />
      <Route path="/settings/team" element={<BasicLayout><SettingsTeamPage /></BasicLayout>} />
      <Route path="/settings/system" element={<BasicLayout><SettingsSystemPage /></BasicLayout>} />
      <Route path="/settings/billing" element={<BasicLayout><BillingPage /></BasicLayout>} />
      <Route path="/analytics" element={<BasicLayout><AnalyticsPage /></BasicLayout>} />
      <Route path="/profile" element={<BasicLayout><ProfilePage /></BasicLayout>} />
      <Route path="/notifications" element={<BasicLayout><NotificationsPage /></BasicLayout>} />
      <Route path="/monitoring" element={<BasicLayout><MonitoringPage /></BasicLayout>} />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
