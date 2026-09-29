/**
 * CloudTech AppShell · BasicLayout (v3 移动端响应式)
 *
 * 布局：
 * ┌────────────┬──────────────────────────────┐
 * │ Sidebar    │ Header (56px)                │
 * │ (240px)    │──────────────────────────────│
 * │ (lg+ 固定) │ Breadcrumb                    │
 * │ (md 折叠)  │                              │
 * │ (< md 隐藏) │ Main Content (flex-1)        │
 * │           │                              │
 * └────────────┴──────────────────────────────┘
 */
import { useState, useEffect } from 'react';
import { Menu } from 'lucide-react';
import { AppSidebar, MobileSidebarDrawer } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { AppBreadcrumb } from './AppBreadcrumb';
import { CommandPalette } from './CommandPalette';
import { Button } from '@/components/ui/button';

interface BasicLayoutProps {
  children: React.ReactNode;
  showBreadcrumb?: boolean;
}

export function BasicLayout({ children, showBreadcrumb = true }: BasicLayoutProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // 路由切换时关闭 mobile drawer
  useEffect(() => { setMobileNavOpen(false); }, []);

  return (
    <div className="min-h-screen bg-[var(--surface-subtle)] flex">
      {/* 桌面端 Sidebar (lg+) */}
      <div className="hidden lg:block">
        <AppSidebar />
      </div>

      {/* 移动端 Drawer (< lg) */}
      <MobileSidebarDrawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header 含移动端 menu 按钮 */}
        <div className="h-[var(--header-height)] bg-[var(--surface-base)] border-b border-[var(--border-default)] flex items-center px-4 lg:px-6 gap-4 sticky top-0 z-10">
          {/* 移动端 Hamburger (< lg) */}
          <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileNavOpen(true)} aria-label="打开导航">
            <Menu className="w-5 h-5" />
          </Button>
          <div className="flex-1 max-w-2xl relative">
            <AppHeaderCompact />
          </div>
        </div>
        <main className="flex-1 px-4 lg:px-6 py-4 overflow-x-auto">
          {showBreadcrumb && <AppBreadcrumb />}
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}

/* 移动端紧凑 Header（搜索 + 通知 + 用户） */
function AppHeaderCompact() {
  return (
    <div className="flex items-center gap-3">
      <div className="hidden md:block flex-1 relative">
        <input type="search" placeholder="搜索…" className="w-full h-9 px-4 rounded-md border border-[var(--border-default)] bg-[var(--surface-subtle)] text-sm placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-brand-600 focus:bg-[var(--surface-base)] transition-colors" />
      </div>
      <div className="ml-auto flex items-center gap-2">
        <span className="hidden md:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-brand-50 text-brand-700 border border-brand-200">企业版</span>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white text-xs font-semibold">NS</div>
      </div>
    </div>
  );
}
