/**
 * CloudTech AppShell · AppSidebar (v3 移动端响应式)
 *
 * 响应式：
 * - ≥ 1024px (lg): 固定展开 240px
 * - 768-1023px (md): 固定展开 64px（仅图标）
 * - < 768px: 隐藏，外部 Sheet/Drawer 触发（用 <Sheet> 组件）
 */
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Bot, MessageSquare, Workflow, ListTodo,
  BookOpen, FileText, Settings2, Users, Sliders,
  BarChart3, Bell, UserCircle, Cloud,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavSection {
  title?: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    items: [
      { label: '工作台', href: '/dashboard', icon: LayoutDashboard },
      { label: '智能体', href: '/employees', icon: Bot, badge: '5' },
    ],
  },
  {
    title: 'AI 能力',
    items: [
      { label: 'AI 对话', href: '/chat', icon: MessageSquare },
      { label: '工作流', href: '/workflows', icon: Workflow },
      { label: '任务中心', href: '/tasks', icon: ListTodo },
    ],
  },
  {
    title: '资源',
    items: [
      { label: '知识库', href: '/knowledge', icon: BookOpen },
      { label: '文件管理', href: '/files', icon: FileText },
    ],
  },
  {
    title: '团队',
    items: [
      { label: '团队空间', href: '/workspace/select', icon: Users },
      { label: '团队与权限', href: '/settings/team', icon: Users },
    ],
  },
  {
    title: '管理',
    items: [
      { label: '模型管理', href: '/settings/models', icon: Settings2 },
      { label: '系统设置', href: '/settings/system', icon: Sliders },
      { label: '数据分析', href: '/analytics', icon: BarChart3 },
    ],
  },
];

interface AppSidebarProps {
  collapsed?: boolean;
  onNavigate?: () => void;
}

export function AppSidebar({ collapsed = false, onNavigate }: AppSidebarProps) {
  return (
    <aside className={cn(
      'bg-card border-r border-border flex flex-col h-screen sticky top-0 transition-all duration-300',
      collapsed ? 'w-16' : 'w-[var(--sidebar-width)]',
      // 移动端隐藏（lg 以上显示）
      'hidden lg:flex',
      'py-4 px-3'
    )}>
      {/* Logo */}
      <div className={cn('flex items-center mb-6', collapsed ? 'justify-center px-0' : 'gap-2 px-3')}>
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shrink-0">
          <Cloud className="w-5 h-5 text-white" />
        </div>
        {!collapsed && <span className="font-semibold text-foreground text-base">CloudTech</span>}
      </div>

      {/* Nav Sections */}
      <nav className="flex-1 flex flex-col gap-4 overflow-y-auto">
        {navSections.map((section, idx) => (
          <div key={idx} className="flex flex-col gap-1">
            {section.title && !collapsed && (
              <div className="px-3 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {section.title}
              </div>
            )}
            {section.items.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={onNavigate}
                title={collapsed ? item.label : undefined}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 h-9 px-3 rounded-md text-sm transition-colors',
                    collapsed && 'justify-center px-0',
                    isActive
                      ? 'bg-brand-50 text-brand-700 font-medium'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )
                }
              >
                <item.icon className="w-5 h-5 shrink-0" />
                {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                {!collapsed && item.badge && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-700">{item.badge}</span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="pt-3 border-t border-border">
        <NavLink to="/profile" onClick={onNavigate} title={collapsed ? '个人中心' : undefined}
          className={({ isActive }) =>
            cn('flex items-center gap-3 h-9 px-3 rounded-md text-sm transition-colors mt-1',
              collapsed && 'justify-center px-0',
              isActive ? 'bg-brand-50 text-brand-700 font-medium' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )
          }>
          <UserCircle className="w-5 h-5 shrink-0" />
          {!collapsed && <span className="flex-1 truncate">个人中心</span>}
        </NavLink>
        <NavLink to="/settings" onClick={onNavigate} title={collapsed ? '设置' : undefined}
          className={({ isActive }) =>
            cn('flex items-center gap-3 h-9 px-3 rounded-md text-sm transition-colors mt-1',
              collapsed && 'justify-center px-0',
              isActive ? 'bg-brand-50 text-brand-700 font-medium' : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )
          }>
          <Settings2 className="w-5 h-5 shrink-0" />
          {!collapsed && <span className="flex-1 truncate">设置</span>}
        </NavLink>
      </div>
    </aside>
  );
}

/* Mobile Drawer 包装（用于 < lg 屏幕） */
import { useEffect } from 'react';

export function MobileSidebarDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onEsc);
    return () => window.removeEventListener('keydown', onEsc);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div className="absolute inset-0 bg-[var(--surface-overlay)] animate-fade-in" onClick={onClose} />
      <div className="absolute left-0 top-0 bottom-0 w-[var(--sidebar-width)] bg-card shadow-xl animate-slide-up flex flex-col">
        <AppSidebar onNavigate={onClose} />
      </div>
    </div>
  );
}
