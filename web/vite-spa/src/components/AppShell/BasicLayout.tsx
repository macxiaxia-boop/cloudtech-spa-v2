/**
 * CloudTech AppShell · BasicLayout
 * 工作台主框架（v2 视觉母版实测：左 Sidebar + 顶 Header + 主内容区）
 *
 * 布局：
 * ┌────────────┬──────────────────────────────┐
 * │ Sidebar    │ Header (56px)                │
 * │ (240px)    │──────────────────────────────│
 * │            │ Breadcrumb                    │
 * │            │                              │
 * │            │ Main Content (flex-1)        │
 * │            │                              │
 * └────────────┴──────────────────────────────┘
 */
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { AppBreadcrumb } from './AppBreadcrumb';
import { CommandPalette } from './CommandPalette';

interface BasicLayoutProps {
  children: React.ReactNode;
  showBreadcrumb?: boolean;
}

export function BasicLayout({ children, showBreadcrumb = true }: BasicLayoutProps) {
  return (
    <div className="min-h-screen bg-[var(--surface-subtle)] flex">
      <AppSidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <AppHeader />
        <main className="flex-1 px-6 py-4 overflow-x-auto">
          {showBreadcrumb && <AppBreadcrumb />}
          {children}
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
