import { Routes, Route, Link } from 'react-router-dom';
import { MarketingPage } from './pages/Marketing';
import { PricingPage } from './pages/Pricing';
import { FEEmployeeMenu } from './components/FEEmployeeMenu';

// Phase 45 D4-7 + D17-23: SaaS 官网 + 数字员工 FE 3 菜单收敛
// 路由:
//  /              — 营销首页
//  /pricing       — 定价
//  /employees     — FE 3 员工菜单 (content_writer/customer_service/market_researcher)
export default function App() {
  return (
    <div className="min-h-screen bg-white">
      {/* 顶部导航 — Phase 45 D17-23 收敛：3 主菜单 + FE 员工下拉 */}
      <header className="border-b border-gray-200">
        <div className="max-w-page mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold text-brand-500">
            CloudTech · AI 数字员工
          </Link>
          <nav className="flex items-center gap-6 text-sm">
            <Link to="/" className="hover:text-brand-500">首页</Link>
            <Link to="/pricing" className="hover:text-brand-500">定价</Link>
            <FEEmployeeMenu />
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
          <Route path="/employees" element={<FEEmployeeMenu />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>

      <footer className="border-t border-gray-200 mt-20 py-8 text-center text-sm text-gray-500">
        CloudTech SaaS · Phase 45 D17-23 · 让 AI 成为 8 位数字员工
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
