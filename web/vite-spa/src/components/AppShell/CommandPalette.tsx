/**
 * CloudTech AppShell · CommandPalette
 * Cmd+K 全局命令面板（基于 cmdk）
 *
 * P0 阶段：占位实现（仅 UI 壳，未接入真实搜索/命令）
 */
import { useEffect, useState } from 'react';
import { Command } from 'cmdk';
import { useNavigate } from 'react-router-dom';
import { Search, LayoutDashboard, Bot, MessageSquare, Workflow, ListTodo, BookOpen } from 'lucide-react';

interface CommandItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  group: string;
}

const commands: CommandItem[] = [
  { label: '工作台', href: '/dashboard', icon: LayoutDashboard, group: '导航' },
  { label: 'AI 对话', href: '/chat', icon: MessageSquare, group: '导航' },
  { label: '智能体中心', href: '/employees', icon: Bot, group: '导航' },
  { label: '工作流', href: '/workflows', icon: Workflow, group: '导航' },
  { label: '任务中心', href: '/tasks', icon: ListTodo, group: '导航' },
  { label: '知识库', href: '/knowledge', icon: BookOpen, group: '导航' },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === 'Escape') {
        setOpen(false);
      }
    };
    window.addEventListener('keydown', down);
    return () => window.removeEventListener('keydown', down);
  }, []);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-[var(--surface-overlay)] flex items-start justify-center pt-[20vh] animate-fade-in"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl bg-[var(--surface-base)] rounded-lg shadow-xl border border-[var(--border-default)] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Command label="命令面板" className="flex flex-col">
          <div className="flex items-center gap-2 px-4 border-b border-[var(--border-default)]">
            <Search className="w-4 h-4 text-[var(--text-tertiary)]" />
            <Command.Input
              placeholder="输入命令或搜索…"
              className="flex-1 h-12 bg-transparent border-0 outline-none text-sm placeholder:text-[var(--text-tertiary)]"
            />
            <kbd className="text-[10px] font-mono text-[var(--text-tertiary)] bg-[var(--surface-muted)] px-1.5 py-0.5 rounded border border-[var(--border-default)]">
              ESC
            </kbd>
          </div>
          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-[var(--text-tertiary)]">
              未找到结果
            </Command.Empty>
            {['导航'].map((group) => (
              <Command.Group key={group} heading={group} className="text-xs text-[var(--text-tertiary)] px-2 py-1.5 font-medium">
                {commands
                  .filter((c) => c.group === group)
                  .map((item) => (
                    <Command.Item
                      key={item.href}
                      value={item.label}
                      onSelect={() => {
                        navigate(item.href);
                        setOpen(false);
                      }}
                      className="flex items-center gap-3 px-3 py-2 rounded-md text-sm cursor-pointer aria-selected:bg-brand-50 aria-selected:text-brand-700"
                    >
                      <item.icon className="w-4 h-4" />
                      <span>{item.label}</span>
                    </Command.Item>
                  ))}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
