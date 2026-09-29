/**
 * CloudTech AppShell · AppSidebar
 * 工作台左侧导航栏（v2 视觉母版实测 240px 宽）
 *
 * 8 大导航分组：
 * - 工作台: 工作台 / 智能体
 * - AI 能力: AI 对话 / 工作流 / 任务中心
 * - 资源: 知识库 / 文件管理
 * - 管理: 模型管理 / 团队与权限 / 系统设置
 * - 数据: 数据分析 / 通知中心
 * - 我的: 个人中心
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
    title: '管理',
    items: [
      { label: '模型管理', href: '/settings/models', icon: Settings2 },
      { label: '团队与权限', href: '/settings/team', icon: Users },
      { label: '系统设置', href: '/settings/system', icon: Sliders },
    ],
  },
  {
    title: '数据',
    items: [
      { label: '数据分析', href: '/analytics', icon: BarChart3 },
      { label: '通知中心', href: '/notifications', icon: Bell },
    ],
  },
];

export function AppSidebar() {
  return (
    <aside className="w-[var(--sidebar-width)] bg-[var(--surface-emphasis)] border-r border-[var(--border-default)] flex flex-col py-4 px-3 h-screen sticky top-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 mb-6">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
          <Cloud className="w-5 h-5 text-white" />
        </div>
        <span className="font-semibold text-[var(--text-primary)] text-base">CloudTech</span>
      </div>

      {/* Nav Sections */}
      <nav className="flex-1 flex flex-col gap-4 overflow-y-auto">
        {navSections.map((section, idx) => (
          <div key={idx} className="flex flex-col gap-1">
            {section.title && (
              <div className="px-3 py-1 text-xs font-medium text-[var(--text-tertiary)] uppercase tracking-wide">
                {section.title}
              </div>
            )}
            {section.items.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 h-9 px-3 rounded-md text-sm transition-colors',
                    isActive
                      ? 'bg-brand-50 text-brand-700 font-medium'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--surface-muted)] hover:text-[var(--text-primary)]'
                  )
                }
              >
                <item.icon className="w-5 h-5 shrink-0" />
                <span className="flex-1 truncate">{item.label}</span>
                {item.badge && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-700">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer: 个人中心 */}
      <div className="pt-3 border-t border-[var(--border-default)]">
        <NavLink
          to="/profile"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 h-9 px-3 rounded-md text-sm transition-colors',
              isActive
                ? 'bg-brand-50 text-brand-700 font-medium'
                : 'text-[var(--text-secondary)] hover:bg-[var(--surface-muted)] hover:text-[var(--text-primary)]'
            )
          }
        >
          <UserCircle className="w-5 h-5 shrink-0" />
          <span className="flex-1 truncate">个人中心</span>
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 h-9 px-3 rounded-md text-sm transition-colors mt-1',
              isActive
                ? 'bg-brand-50 text-brand-700 font-medium'
                : 'text-[var(--text-secondary)] hover:bg-[var(--surface-muted)] hover:text-[var(--text-primary)]'
            )
          }
        >
          <Sliders className="w-5 h-5 shrink-0" />
          <span className="flex-1 truncate">设置</span>
        </NavLink>
      </div>
    </aside>
  );
}
