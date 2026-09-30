/**
 * CloudTech App · 路由分流（v3 重构）
 *
 * 三套路由分流：
 * 1. 营销路由（marketing）: 用 Header/Footer 包装，marketing-first 布局
 * 2. 工作台路由（AppShell）: 用 BasicLayout 包装，左 sidebar + 顶 header
 * 3. 居中路由（centered）: 不套任何 layout（/login /register /workspace/select）
 *
 * 性能优化：WorkflowEditor + Workflows 懒加载（react.lazy + Suspense）
 * 错误边界：ErrorBoundary 包裹整个 App 防止单组件崩溃
 */
import { lazy, Suspense } from 'react';
import { Routes, Route, Outlet } from 'react-router-dom';
import { MarketingPage } from './pages/Marketing';
import { PricingPage } from './pages/Pricing';
import { DashboardPage } from './pages/Dashboard';
import { SettingsPage } from './pages/Settings';
import { BillingPage } from './pages/Billing';
import { IndustryDecorationPage } from './pages/IndustryDecoration';
import { ErrorBoundary } from './components/ErrorBoundary';

/* Lazy-load WorkflowEditor + Workflows (xyflow 67KB) */
const WorkflowsPage = lazy(() => import('./pages/Workflows').then((m) => ({ default: m.WorkflowsPage })));
const WorkflowEditorPage = lazy(() => import('./pages/WorkflowEditor').then((m) => ({ default: m.WorkflowEditorPage })));

/* Lazy-load 入口加载占位 */
function PageLoading() {
  return (
    <div className="flex items-center justify-center h-[calc(100vh-56px)]">
      <div className="text-sm text-[var(--text-secondary)]">加载中…</div>
    </div>
  );
}
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
import { AnalyticsPage } from './pages/Analytics';
import { SettingsSystemPage } from './pages/SettingsSystem';
import { SettingsTeamPage } from './pages/SettingsTeam';
import { ProfilePage } from './pages/Profile';
import { NotificationsPage } from './pages/Notifications';
import { AgentsPage } from './pages/Agents';
import { RequireAuth } from './components/Auth/RequireAuth';
import { NotFoundPage } from './pages/NotFoundPage';

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
  return <NotFoundPage />;
}

export default function App() {
  return (
    <ErrorBoundary>
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
      <Route path="/dashboard" element={<RequireAuth><BasicLayout><DashboardPage /></BasicLayout></RequireAuth>} />
      <Route path="/chat" element={<RequireAuth><BasicLayout showBreadcrumb={false}><ChatPage /></BasicLayout></RequireAuth>} />
      <Route path="/employees" element={<RequireAuth><BasicLayout><AIEmployeesPage /></BasicLayout></RequireAuth>} />
      <Route path="/employees/new" element={<RequireAuth><BasicLayout><AgentCreatePage /></BasicLayout></RequireAuth>} />
      <Route path="/employees/:id/edit" element={<RequireAuth><BasicLayout><AgentCreatePage /></BasicLayout></RequireAuth>} />
      <Route path="/tasks" element={<RequireAuth><BasicLayout><TasksPage /></BasicLayout></RequireAuth>} />
      <Route path="/knowledge" element={<RequireAuth><BasicLayout><KnowledgePage /></BasicLayout></RequireAuth>} />
      <Route path="/files" element={<RequireAuth><BasicLayout><FilesPage /></BasicLayout></RequireAuth>} />
      <Route path="/workflows" element={<RequireAuth><BasicLayout><Suspense fallback={<PageLoading />}><WorkflowsPage /></Suspense></BasicLayout></RequireAuth>} />
      <Route path="/workflows/new" element={<RequireAuth><BasicLayout showBreadcrumb={false}><Suspense fallback={<PageLoading />}><WorkflowEditorPage /></Suspense></BasicLayout></RequireAuth>} />
      <Route path="/workflows/:id" element={<RequireAuth><BasicLayout showBreadcrumb={false}><Suspense fallback={<PageLoading />}><WorkflowEditorPage /></Suspense></BasicLayout></RequireAuth>} />
      <Route path="/settings" element={<RequireAuth><BasicLayout><SettingsPage /></BasicLayout></RequireAuth>} />
      <Route path="/settings/models" element={<RequireAuth><BasicLayout><SettingsPage /></BasicLayout></RequireAuth>} />
      <Route path="/settings/team" element={<RequireAuth><BasicLayout><SettingsTeamPage /></BasicLayout></RequireAuth>} />
      <Route path="/settings/system" element={<RequireAuth><BasicLayout><SettingsSystemPage /></BasicLayout></RequireAuth>} />
      <Route path="/settings/billing" element={<RequireAuth><BasicLayout><BillingPage /></BasicLayout></RequireAuth>} />
      <Route path="/analytics" element={<RequireAuth><BasicLayout><AnalyticsPage /></BasicLayout></RequireAuth>} />
      <Route path="/profile" element={<RequireAuth><BasicLayout><ProfilePage /></BasicLayout></RequireAuth>} />
      <Route path="/notifications" element={<RequireAuth><BasicLayout><NotificationsPage /></BasicLayout></RequireAuth>} />
      <Route path="/monitoring" element={<RequireAuth><BasicLayout><MonitoringPage /></BasicLayout></RequireAuth>} />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
    </ErrorBoundary>
  );
}
