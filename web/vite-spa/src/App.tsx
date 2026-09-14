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
import { FEEmployeeMenu } from './components/FEEmployeeMenu';

// Phase 46 D53-60: 段 3 完整就绪（合同 + HR + 财务 + 营业执照）
// 路由:
//  /                                   — 营销首页
//  /pricing                            — 定价（公开）
//  /industries/decoration              — 装企行业落地页（SEO）
//  /industries/medical                 — 医美行业落地页（SEO + 合规）
//  /content-sop                        — 内容生产 SOP 工具
//  /clients                            — 80 家客户清单
//  /documents                          — 公司文档中心（D53-60 合同/HR/财务/营业执照）
//  /dashboard                          — 客户后台
//  /settings                           — 账号设置
//  /billing                            — 套餐切换
//  /employees                          — FE 3 员工菜单
export default function App() {
  return (
    <div className="min-h-screen bg-white">
      {/* 顶部导航 — Phase 46 D53-60 加 Documents 入口 */}
      <header className="border-b border-gray-200">
        <div className="max-w-page mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-brand-500">
            CloudTech · AI 数字员工
          </Link>
          <nav className="flex items-center gap-6 text-sm">
            <Link to="/" className="hover:text-brand-500">首页</Link>
            <Link to="/industries/decoration" className="hover:text-brand-500">装企</Link>
            <Link to="/industries/medical" className="hover:text-brand-500">医美</Link>
            <Link to="/content-sop" className="hover:text-brand-500">SOP</Link>
            <Link to="/clients" className="hover:text-brand-500">客户</Link>
            <Link to="/documents" className="hover:text-brand-500">文档</Link>
            <Link to="/pricing" className="hover:text-brand-500">定价</Link>
            <Link to="/dashboard" className="hover:text-brand-500">后台</Link>
            <Link to="/billing" className="hover:text-brand-500">套餐</Link>
            <FEEmployeeMenu />
            <Link to="/settings" className="hover:text-brand-500">设置</Link>
            <Link to="/login" className="px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600">
              登录
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<MarketingPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/industries/decoration" element={<IndustryDecorationPage />} />
          <Route path="/industries/medical" element={<IndustryMedicalPage />} />
          <Route path="/content-sop" element={<ContentSOPPage />} />
          <Route path="/clients" element={<ClientListPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/billing" element={<BillingPage />} />
          <Route path="/employees" element={<FEEmployeeMenu />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      <footer className="border-t border-gray-200 mt-20 py-8 text-center text-sm text-gray-500">
        CloudTech SaaS · Phase 46 OPC · 1 人 + AI 的整家公司
      </footer>
    </div>
  );
}

function NotFound() {
  return (
    <div className="max-w-page mx-auto px-6 py-20 text-center">
      <h1 className="text-3xl font-bold mb-4">404</h1>
      <Link to="/" className="text-brand-500 hover:underline">返回首页</Link>
    </div>
  );
}
