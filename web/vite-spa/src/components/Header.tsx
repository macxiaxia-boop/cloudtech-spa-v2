// 顶部导航 · 4 大区下拉（产品/行业/资源/我的）
import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronDown, Sparkles } from 'lucide-react';

interface NavItem {
  label: string;
  to: string;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: '产品',
    items: [
      { label: '首页', to: '/' },
      { label: '定价', to: '/pricing' },
      { label: '5 AI 员工', to: '/employees', badge: 'HOT' },
      { label: '监控中心', to: '/monitoring', badge: 'NEW' },
      { label: '漏斗转化', to: '/funnel', badge: 'NEW' },
      { label: '7 天试用', to: '/try', badge: 'FREE' },
    ],
  },
  {
    title: '行业',
    items: [
      { label: '装企获客', to: '/industries/decoration' },
      { label: '医美合规', to: '/industries/medical' },
      { label: '内容 SOP', to: '/content-sop' },
    ],
  },
  {
    title: '资源',
    items: [
      { label: '案例库', to: '/cases' },
      { label: '博客', to: '/blog' },
      { label: 'FAQ 帮助', to: '/faq' },
      { label: 'OPC 故事', to: '/opc-story' },
    ],
  },
  {
    title: '我的',
    items: [
      { label: '客户后台', to: '/dashboard' },
      { label: '80 家清单', to: '/clients' },
      { label: '文档中心', to: '/documents' },
      { label: '套餐切换', to: '/billing' },
      { label: '账号设置', to: '/settings' },
    ],
  },
];

export function Header() {
  const [openSection, setOpenSection] = useState<string | null>(null);
  const location = useLocation();

  return (
    <header className="border-b border-border bg-card sticky top-0 z-40 shadow-sm">
      <div className="max-w-page mx-auto px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 text-xl font-bold text-brand-500">
          <Sparkles className="w-5 h-5" />
          Cloud
        </Link>

        {/* 4 大区导航 */}
        <nav className="hidden md:flex items-center gap-1">
          {NAV_SECTIONS.map((section) => (
            <div
              key={section.title}
              className="relative"
              onMouseEnter={() => setOpenSection(section.title)}
              onMouseLeave={() => setOpenSection(null)}
            >
              <button
                className={`px-3 py-2 rounded-md text-sm font-medium hover:bg-gray-50 flex items-center gap-1 ${
                  openSection === section.title ? 'bg-gray-50' : ''
                }`}
              >
                {section.title}
                <ChevronDown className="w-3 h-3 text-gray-400" />
              </button>
              {openSection === section.title && (
                <div className="absolute top-full left-0 mt-0 w-56 bg-card border border-border rounded-md shadow-lg py-2">
                  {section.items.map((item) => (
                    <Link
                      key={item.to}
                      to={item.to}
                      className={`flex items-center justify-between px-4 py-2 text-sm hover:bg-gray-50 ${
                        location.pathname === item.to ? 'bg-brand-50 text-brand-600 font-medium' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      <span>{item.label}</span>
                      {item.badge && (
                        <span
                          className={`px-1.5 py-0.5 text-[10px] rounded font-bold ${
                            item.badge === 'HOT'
                              ? 'bg-red-100 text-red-600'
                              : item.badge === 'NEW'
                              ? 'bg-green-100 text-green-600'
                              : 'bg-blue-100 text-blue-600'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* 右侧 CTA */}
        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="hidden md:block text-sm text-muted-foreground hover:text-brand-500"
          >
            登录
          </Link>
          <Link
            to="/try"
            className="px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 text-sm font-medium"
          >
            🚀 7 天试用
          </Link>
        </div>
      </div>
    </header>
  );
}
