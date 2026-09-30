/**
 * CloudTech Notifications · V23 视觉重做 (2026-09-30)
 * 通知中心：3 Tab (系统/任务/协作) + shadcn Card + Badge + i18n
 *
 * V23: bg-[var(--xxx)] 硬编码 → 标准 token (bg-card / text-muted-foreground / border-border)
 */
import { useState } from 'react';
import { Bell, Trash2, Check, X, AlertCircle, Settings as SettingsIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardAction } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useTranslation } from '@/i18n';

type Tab = 'all' | 'system' | 'task' | 'collab';

interface Notification {
  id: string;
  type: 'system' | 'task' | 'collab';
  icon: string;
  title: string;
  desc: string;
  time: string;
  unread: boolean;
}

const notifications: Notification[] = [
  { id: 'n1', type: 'task',   icon: '✓', title: '任务《市场分析报告》已完成',  desc: '由 AI 助手生成 · 耗时 12 分钟',         time: '10 分钟前',  unread: true  },
  { id: 'n2', type: 'system', icon: '⚙', title: '系统升级到 v22.5',            desc: '新增 12 个功能 + 8 个修复',             time: '30 分钟前',  unread: true  },
  { id: 'n3', type: 'collab', icon: '👤', title: '李四邀请你加入团队',           desc: '研发团队 · 邀请待确认',                 time: '1 小时前',   unread: true  },
  { id: 'n4', type: 'task',   icon: '⚡', title: '工作流《内容生产 SOP》运行成功', desc: '5 个节点全部完成',                       time: '2 小时前',   unread: false },
  { id: 'n5', type: 'system', icon: '🔒', title: '检测到新设备登录',               desc: 'iPhone 15 Pro · 上海',                  time: '3 小时前',   unread: false },
  { id: 'n6', type: 'collab', icon: '📝', title: '王五评论了你的工作流',           desc: '"这个节点配置可以再优化一下"',           time: '昨天 18:30', unread: false },
  { id: 'n7', type: 'task',   icon: '⚠️', title: '任务《数据清洗》运行失败',     desc: '节点 3 报错：超时 · 可重试',             time: '昨天 16:00', unread: false },
];

const tabs: { key: Tab; label: string; count: number }[] = [
  { key: 'all',    label: '全部',     count: notifications.length },
  { key: 'system', label: '系统通知', count: notifications.filter((n) => n.type === 'system').length },
  { key: 'task',   label: '任务通知', count: notifications.filter((n) => n.type === 'task').length },
  { key: 'collab', label: '协作通知', count: notifications.filter((n) => n.type === 'collab').length },
];

const typeBadge: Record<Notification['type'], { color: string; label: string }> = {
  system: { color: 'bg-info-bg text-brand-700',     label: '系统' },
  task:   { color: 'bg-success-bg text-success-700', label: '任务' },
  collab: { color: 'bg-accent-purple-50 text-accent-purple-700', label: '协作' },
};

export function NotificationsPage() {
  const [tab, setTab] = useState<Tab>('all');
  const { t } = useTranslation();
  const filtered = tab === 'all' ? notifications : notifications.filter((n) => n.type === tab);
  const unreadCount = notifications.filter((n) => n.unread).length;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bell className="w-6 h-6 text-brand-600" />
            {t('nav.notifications')}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">系统通知 · 任务通知 · 协作通知</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Check className="w-3.5 h-3.5" />全部已读</Button>
          <Button variant="outline" size="sm"><SettingsIcon className="w-3.5 h-3.5" />通知设置</Button>
        </div>
      </div>

      {unreadCount > 0 && (
        <div className="bg-brand-50 border border-brand-200 rounded-lg px-4 py-2.5 text-sm text-brand-700 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-brand-500 animate-pulse" />
          您有 <strong>{unreadCount}</strong> 条未读通知
        </div>
      )}

      <Card className="p-0">
        <nav className="flex border-b border-border px-2 overflow-x-auto">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
                tab === t.key ? 'border-brand-600 text-brand-600' : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}>
              {t.label}
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${tab === t.key ? 'bg-brand-100 text-brand-700' : 'bg-muted text-muted-foreground'}`}>{t.count}</span>
            </button>
          ))}
        </nav>

        <div className="divide-y divide-border">
          {filtered.map((n) => {
            const tb = typeBadge[n.type];
            return (
              <div key={n.id} className={`flex items-start gap-3 p-4 hover:bg-accent transition-colors cursor-pointer ${n.unread ? 'bg-brand-50/30' : ''}`}>
                <div className="text-2xl shrink-0">{n.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    {n.unread && <span className="w-2 h-2 rounded-full bg-brand-500 shrink-0" />}
                    <span className="font-medium text-sm text-foreground">{n.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${tb.color}`}>{tb.label}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">{n.desc}</div>
                </div>
                <div className="text-xs text-muted-foreground shrink-0">{n.time}</div>
                <button className="p-1 hover:bg-accent rounded shrink-0" aria-label="删除"><Trash2 className="w-3.5 h-3.5 text-muted-foreground" /></button>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
