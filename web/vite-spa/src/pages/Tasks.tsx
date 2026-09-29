/**
 * CloudTech Tasks · v3 视觉母版 09 模块
 * Tab + Table + 进度条 + 状态徽章 + i18n
 */
import { useState } from 'react';
import { MoreHorizontal, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslation } from '@/i18n';

type TaskStatus = 'running' | 'completed' | 'failed' | 'pending';
type FilterTab = 'all' | 'running' | 'completed' | 'failed';

interface Task {
  id: string;
  name: string;
  owner: string;
  progress: number;
  status: TaskStatus;
  startAt: string;
}

const statusMap: Record<TaskStatus, { label: string; cls: string }> = {
  running:   { label: '进行中', cls: 'bg-info-bg text-brand-700' },
  completed: { label: '已完成', cls: 'bg-success-bg text-success-700' },
  failed:    { label: '失败',   cls: 'bg-destructive-bg text-destructive-700' },
  pending:   { label: '等待中', cls: 'bg-warning-bg text-warning-700' },
};

const tasks: Task[] = [
  { id: '1', name: '生成市场分析报告', owner: '李四', progress: 80, status: 'running', startAt: '今天 10:30' },
  { id: '2', name: '处理用户反馈数据', owner: '李四', progress: 45, status: 'running', startAt: '今天 20:00' },
  { id: '3', name: '竞品调研分析',   owner: '王五', progress: 0,  status: 'pending', startAt: '明天 10:00' },
  { id: '4', name: '制作演示文稿',   owner: '张三', progress: 100, status: 'completed', startAt: '3 月 10 日' },
  { id: '5', name: '数据清洗任务',   owner: '李四', progress: 100, status: 'completed', startAt: '3 月 10 日' },
  { id: '6', name: '用户调研问卷',   owner: '张三', progress: 0,  status: 'pending', startAt: '3 月 12 日' },
  { id: '7', name: '产品需求文档',   owner: '王五', progress: 0,  status: 'pending', startAt: '3 月 12 日' },
];

const tabs: { key: FilterTab; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'running', label: '进行中' },
  { key: 'completed', label: '已完成' },
  { key: 'failed', label: '失败' },
];

export function TasksPage() {
  const [tab, setTab] = useState<FilterTab>('all');
  const { t } = useTranslation();
  const filtered = tab === 'all' ? tasks : tasks.filter((t) => t.status === tab);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('nav.tasks')}</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">任务管理 · 执行进度 · 日志追踪 · 异常处理</p>
        </div>
        <Button><Plus className="w-4 h-4" />{t('app.create_task')}</Button>
      </div>

      <div className="bg-[var(--surface-base)] rounded-lg border border-[var(--border-default)]">
        <div className="border-b border-[var(--border-default)] px-4">
          <nav className="flex gap-6">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                  tab === t.key
                    ? 'border-brand-600 text-brand-600'
                    : 'border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>

        <table className="w-full">
          <thead>
            <tr className="bg-[var(--surface-subtle)] border-b border-[var(--border-default)]">
              <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-10">
                <input type="checkbox" className="rounded" />
              </th>
              <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5">任务名称</th>
              <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-32">进度</th>
              <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-32">负责人</th>
              <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-28">状态</th>
              <th className="text-left text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-32">起止时间</th>
              <th className="text-right text-xs font-medium text-[var(--text-secondary)] px-4 py-2.5 w-12">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((task) => {
              const sm = statusMap[task.status];
              return (
                <tr key={task.id} className="border-b border-[var(--border-default)] hover:bg-[var(--surface-subtle)]">
                  <td className="px-4 py-2.5"><input type="checkbox" className="rounded" /></td>
                  <td className="px-4 py-2.5 text-sm font-medium text-[var(--text-primary)]">{task.name}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-[var(--neutral-200)] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            task.status === 'failed' ? 'bg-destructive-500' : 'bg-brand-600'
                          }`}
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-[var(--text-secondary)] w-9 text-right">{task.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-[var(--text-secondary)]">{task.owner}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sm.cls}`}>{sm.label}</span>
                  </td>
                  <td className="px-4 py-2.5 text-sm text-[var(--text-tertiary)]">{task.startAt}</td>
                  <td className="px-4 py-2.5 text-right">
                    <button className="p-1 hover:bg-[var(--surface-muted)] rounded">
                      <MoreHorizontal className="w-4 h-4 text-[var(--text-tertiary)]" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
