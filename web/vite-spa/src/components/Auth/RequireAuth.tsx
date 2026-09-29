/**
 * CloudTech RequireAuth · 路由保护 wrapper
 *
 * 未登录 → 重定向 /login
 * 已登录但无 workspace → 重定向 /workspace/select
 * 已登录 + 有 workspace → 渲染 children
 */
import { Navigate, useLocation } from 'react-router-dom';
import { type ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';

interface RequireAuthProps {
  children: ReactNode;
  /** 是否跳过 workspace 检查（用于不需要 workspace 的页面，如 /dashboard）*/
  skipWorkspace?: boolean;
}

export function RequireAuth({ children, skipWorkspace = false }: RequireAuthProps) {
  const { user, currentWorkspace, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[var(--surface-subtle)]">
        <div className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
          <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          加载中…
        </div>
      </div>
    );
  }

  // 未登录 → /login
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  // 已登录但无 workspace 且需要 → /workspace/select
  if (!skipWorkspace && !currentWorkspace) {
    return <Navigate to="/workspace/select" replace />;
  }

  return <>{children}</>;
}
