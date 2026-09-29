/**
 * CloudTech AppShell · AppHeader
 * 工作台顶栏（v2 视觉母版实测 56px 高）
 *
 * 组成：搜索框 + 通知 + 企业版徽章 + 用户菜单
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Bell, ChevronDown, User, Settings, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function AppHeader() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="h-[var(--header-height)] bg-[var(--surface-base)] border-b border-[var(--border-default)] flex items-center px-6 gap-4 sticky top-0 z-10">
      {/* 搜索框 */}
      <div className="flex-1 max-w-2xl relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)] pointer-events-none" />
        <input
          type="search"
          placeholder="搜索知识、文档、智能体、任务…"
          className="w-full h-9 pl-10 pr-4 rounded-md border border-[var(--border-default)] bg-[var(--surface-subtle)] text-sm placeholder:text-[var(--text-tertiary)] focus:outline-none focus:border-brand-600 focus:bg-[var(--surface-base)] focus:ring-3 focus:ring-brand-500/20 transition-colors"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:inline-flex items-center gap-0.5 text-[10px] font-mono text-[var(--text-tertiary)] bg-[var(--surface-muted)] px-1.5 py-0.5 rounded border border-[var(--border-default)]">
          ⌘K
        </kbd>
      </div>

      {/* 通知 */}
      <Link
        to="/notifications"
        className="relative p-2 rounded-md hover:bg-[var(--surface-muted)] transition-colors"
        aria-label="通知"
      >
        <Bell className="w-5 h-5 text-[var(--text-secondary)]" />
        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive-500 rounded-full" />
      </Link>

      {/* 企业版徽章 */}
      <span className="hidden md:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-brand-50 text-brand-700 border border-brand-200">
        企业版
      </span>

      {/* 用户菜单 */}
      <div className="relative">
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="flex items-center gap-2 p-1 rounded-md hover:bg-[var(--surface-muted)] transition-colors"
          aria-label="用户菜单"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white text-xs font-semibold">
            NS
          </div>
          <ChevronDown className="w-4 h-4 text-[var(--text-secondary)] hidden sm:block" />
        </button>
        {menuOpen && (
          <>
            <div
              className="fixed inset-0 z-20"
              onClick={() => setMenuOpen(false)}
              aria-hidden="true"
            />
            <div className="absolute right-0 top-12 w-56 bg-[var(--surface-base)] rounded-md border border-[var(--border-default)] shadow-lg z-30 py-1 animate-slide-up">
              <div className="px-3 py-2 border-b border-[var(--border-default)]">
                <div className="font-medium text-sm">Nova Team</div>
                <div className="text-xs text-[var(--text-tertiary)] truncate">nova@company.com</div>
              </div>
              <Link
                to="/profile"
                className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--surface-muted)] transition-colors"
                onClick={() => setMenuOpen(false)}
              >
                <User className="w-4 h-4" />
                个人中心
              </Link>
              <Link
                to="/settings"
                className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--surface-muted)] transition-colors"
                onClick={() => setMenuOpen(false)}
              >
                <Settings className="w-4 h-4" />
                账号设置
              </Link>
              <div className="border-t border-[var(--border-default)] my-1" />
              <button className="flex items-center gap-2 px-3 py-2 text-sm text-destructive-600 hover:bg-destructive-50 transition-colors w-full">
                <LogOut className="w-4 h-4" />
                退出登录
              </button>
            </div>
          </>
        )}
      </div>
    </header>
  );
}
