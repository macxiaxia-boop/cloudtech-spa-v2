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
import { lazy, Suspense, useEffect, type ComponentType } from 'react';
import { Routes, Route, Outlet } from 'react-router-dom';
import { MarketingPage } from './pages/Marketing';




/**
 * Existing Lynxce source lives on the user's Windows machine but has not
 * been synchronized to this GitHub tree. Do not replace its functionality
 * with invented implementations and do not break the whole CloudTech build.
 *
 * Vite discovers the original index.tsx/index.ts dynamically when present.
 * In the incomplete checkout a clear unavailable state is rendered instead.
 */
const optionalLynxceModules = import.meta.glob<Record<string, unknown>>(
  './pages/lynxce/index.{ts,tsx}'
);

function LynxceSourceUnavailable() {
  return (
    <main className="mx-auto max-w-3xl p-8" role="status">
      <h1 className="text-xl font-semibold">此功能暂不可用</h1>
      <p className="mt-3 text-sm text-muted-foreground">
        当前部署的 CloudTech 版本尚未包含这一功能的页面源码。
        未执行任何 AI 生成或外部任务；请联系管理员同步原有模块。
      </p>
    </main>
  );
}

function optionalLynxcePage(exportName: string) {
  return lazy(async () => {
    const loader = optionalLynxceModules['./pages/lynxce/index.tsx']
      ?? optionalLynxceModules['./pages/lynxce/index.ts'];
    if (!loader) return { default: LynxceSourceUnavailable };
    const module = await loader();
    const component = module[exportName];
    if (typeof component !== 'function') {
      return { default: LynxceSourceUnavailable };
    }
    return { default: component as ComponentType };
  });
}

const LynxceIndex = optionalLynxcePage('LynxceIndex');
const LynxceChatPage = optionalLynxcePage('LynxceChatPage');
const LynxceDrawPage = optionalLynxcePage('LynxceDrawPage');
const LynxceMjPage = optionalLynxcePage('LynxceMjPage');
const LynxceVideoPage = optionalLynxcePage('LynxceVideoPage');
const LynxceMusicPage = optionalLynxcePage('LynxceMusicPage');
const LynxceEffectsPage = optionalLynxcePage('LynxceEffectsPage');
const LynxceStudyPage = optionalLynxcePage('LynxceStudyPage');
const LynxceAppsPage = optionalLynxcePage('LynxceAppsPage');
const LynxceSquarePage = optionalLynxcePage('LynxceSquarePage');
const LynxceAssetsPage = optionalLynxcePage('LynxceAssetsPage');
const LynxceViralPage = optionalLynxcePage('LynxceViralPage');
const LynxceLeadsPage = optionalLynxcePage('LynxceLeadsPage');
const LynxceMePage = optionalLynxcePage('LynxceMePage');
const LynxceAdminPage = optionalLynxcePage('LynxceAdminPage');

import { ErrorBoundary } from './components/ErrorBoundary';

/* Feature routes load only when visited. Never bundle the entire back office
 * into login/marketing; preserve existing route paths and authorization gates.
 */
const PricingPage = lazy(() => import('./pages/Pricing').then(m => ({ default: m.PricingPage })));
const DashboardPage = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.DashboardPage })));
const SettingsPage = lazy(() => import('./pages/Settings').then(m => ({ default: m.SettingsPage })));
const BillingPage = lazy(() => import('./pages/Billing').then(m => ({ default: m.BillingPage })));
const IndustryDecorationPage = lazy(() => import('./pages/IndustryDecoration').then(m => ({ default: m.IndustryDecorationPage })));
const IndustryMedicalPage = lazy(() => import('./pages/IndustryMedical').then(m => ({ default: m.IndustryMedicalPage })));
const ContentSOPPage = lazy(() => import('./pages/ContentSOP').then(m => ({ default: m.ContentSOPPage })));
const ClientListPage = lazy(() => import('./pages/ClientList').then(m => ({ default: m.ClientListPage })));
const DocumentsPage = lazy(() => import('./pages/Documents').then(m => ({ default: m.DocumentsPage })));
const MonitoringPage = lazy(() => import('./pages/Monitoring').then(m => ({ default: m.MonitoringPage })));
const CaseLibraryPage = lazy(() => import('./pages/CaseLibrary').then(m => ({ default: m.CaseLibraryPage })));
const FAQPage = lazy(() => import('./pages/FAQ').then(m => ({ default: m.FAQPage })));
const BlogPage = lazy(() => import('./pages/Blog').then(m => ({ default: m.BlogPage })));
const TryNowPage = lazy(() => import('./pages/TryNow').then(m => ({ default: m.TryNowPage })));
const AIEmployeesPage = lazy(() => import('./pages/AIEmployees').then(m => ({ default: m.AIEmployeesPage })));
const OPCStoryPage = lazy(() => import('./pages/OPCStory').then(m => ({ default: m.OPCStoryPage })));
const FunnelPage = lazy(() => import('./pages/Funnel').then(m => ({ default: m.FunnelPage })));
const WorkspaceSelectorPage = lazy(() => import('./pages/WorkspaceSelect').then(m => ({ default: m.WorkspaceSelectorPage })));
const RegisterPage = lazy(() => import('./pages/Register').then(m => ({ default: m.RegisterPage })));
const ChatPage = lazy(() => import('./pages/Chat').then(m => ({ default: m.ChatPage })));
const TasksPage = lazy(() => import('./pages/Tasks').then(m => ({ default: m.TasksPage })));
const AgentCreatePage = lazy(() => import('./pages/AgentCreate').then(m => ({ default: m.AgentCreatePage })));
const KnowledgePage = lazy(() => import('./pages/Knowledge').then(m => ({ default: m.KnowledgePage })));
const FilesPage = lazy(() => import('./pages/Files').then(m => ({ default: m.FilesPage })));
const AnalyticsPage = lazy(() => import('./pages/Analytics').then(m => ({ default: m.AnalyticsPage })));
const SettingsSystemPage = lazy(() => import('./pages/SettingsSystem').then(m => ({ default: m.SettingsSystemPage })));
const SettingsTeamPage = lazy(() => import('./pages/SettingsTeam').then(m => ({ default: m.SettingsTeamPage })));
const ProfilePage = lazy(() => import('./pages/Profile').then(m => ({ default: m.ProfilePage })));
const NotificationsPage = lazy(() => import('./pages/Notifications').then(m => ({ default: m.NotificationsPage })));
const AgentsPage = lazy(() => import('./pages/Agents').then(m => ({ default: m.AgentsPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));

/* Lazy-load WorkflowEditor + Workflows (xyflow 67KB) */
const LocalWorkPathsPage = lazy(() => import('./pages/LocalWorkPaths').then(m => ({ default: m.LocalWorkPathsPage })));
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













import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { OnboardingTrigger } from './components/OnboardingTrigger';
const BasicLayout = lazy(() => import('./components/AppShell/BasicLayout').then(m => ({ default: m.BasicLayout })));

const LoginPage = lazy(() => import('./pages/Login').then(m => ({ default: m.LoginPage })));












import { RequireAuth } from './components/Auth/RequireAuth';


/* ───── ThemeInitializer · 全局 dark mode 初始化 (R360) ─────
 * Marketing 路由没有 AppHeader/ThemeToggle，所以这里兜底初始化
 * 工作台路由 ThemeToggle 也会再调一次 (幂等)
 */
function ThemeInitializer() {
  useEffect(() => {
    try {
      const saved = localStorage.getItem('ct.theme');
      const theme = (saved === 'light' || saved === 'dark') ? saved
        : (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.classList.toggle('dark', theme === 'dark');
      localStorage.setItem('ct.theme', theme);
    } catch { /* ignore */ }
  }, []);
  return null;
}

/* ───── Layout: Marketing（marketing Header/Footer） ───── */
function MarketingLayout() {
  return (
    <div className="min-h-screen bg-card flex flex-col">
      <Header />
      <main className="flex-1">
        <Suspense fallback={<PageLoading />}>
          <Outlet />
        </Suspense>
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
      {/* R367 全局 ThemeInitializer · 覆盖 Login/Register/WorkspaceSelect 等 centered route (治本 Login dark class 缺失) */}
      <ThemeInitializer />
      <Suspense fallback={<PageLoading />}>
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
        <Route path="/lynxce" element={<LynxceIndex />} />
        <Route path="/lynxce/chat" element={<LynxceChatPage />} />
        <Route path="/lynxce/draw" element={<LynxceDrawPage />} />
        <Route path="/lynxce/mj" element={<LynxceMjPage />} />
        <Route path="/lynxce/video" element={<LynxceVideoPage />} />
        <Route path="/lynxce/music" element={<LynxceMusicPage />} />
        <Route path="/lynxce/effects" element={<LynxceEffectsPage />} />
        <Route path="/lynxce/study" element={<LynxceStudyPage />} />
        <Route path="/lynxce/apps" element={<LynxceAppsPage />} />
        <Route path="/lynxce/square" element={<LynxceSquarePage />} />
        <Route path="/lynxce/assets" element={<LynxceAssetsPage />} />
        <Route path="/lynxce/viral" element={<LynxceViralPage />} />
        <Route path="/lynxce/leads" element={<LynxceLeadsPage />} />
        <Route path="/lynxce/me" element={<LynxceMePage />} />
        <Route path="/lynxce/admin" element={<LynxceAdminPage />} />
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
      <Route path="/workflows/local" element={<RequireAuth><BasicLayout><Suspense fallback={<PageLoading />}><LocalWorkPathsPage /></Suspense></BasicLayout></RequireAuth>} />
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
      </Suspense>
    </ErrorBoundary>
  );
}
