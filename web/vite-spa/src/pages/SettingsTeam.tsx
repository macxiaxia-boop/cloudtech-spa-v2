/**
 * CloudTech Team · v3 视觉母版 13 模块
 * 团队与权限（成员卡形式）
 */
import { Plus, Mail, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslation } from '@/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface Member {
  id: string;
  name: string;
  email: string;
  role: '管理员' | '成员' | '访客';
  joinedAt: string;
  lastActive: string;
  status: 'online' | 'recent' | 'offline';
}

const members: Member[] = [
  { id: 't1', name: '张三', email: 'zhangsan@company.com', role: '管理员', joinedAt: '2024-01-15', lastActive: '5 分钟前', status: 'online' },
  { id: 't2', name: '李四', email: 'lisi@company.com',     role: '成员',   joinedAt: '2024-02-20', lastActive: '10 分钟前', status: 'online' },
  { id: 't3', name: '王五', email: 'wangwu@company.com',   role: '成员',   joinedAt: '2024-03-10', lastActive: '2 小时前',  status: 'recent' },
  { id: 't4', name: '赵六', email: 'zhaoliu@company.com',  role: '访客',   joinedAt: '2024-04-05', lastActive: '1 天前',   status: 'offline' },
  { id: 't5', name: '钱七', email: 'qianqi@company.com',   role: '成员',   joinedAt: '2024-05-12', lastActive: '3 小时前', status: 'recent' },
];

const roleColors = {
  管理员: 'bg-brand-50 text-brand-700 border-brand-200',
  成员:   'bg-info-bg text-brand-700 border-brand-100',
  访客:   'bg-muted text-muted-foreground border-border',
};

const statusColor = {
  online:  'bg-success-500',
  recent:  'bg-warning-500',
  offline: 'bg-neutral-300',
};

export function SettingsTeamPage() {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">团队与权限</h1>
          <p className="text-sm text-muted-foreground mt-1">成员管理 · 角色分配 · 权限控制</p>
        </div>
        <Button><Plus className="w-4 h-4" />{t('app.invite_member')}</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {members.map((m) => (
          <Card key={m.id} className="p-0 hover:shadow-sm transition-shadow">
            <CardContent className="p-5">
            <div className="flex items-start gap-3 mb-4">
              <div className="relative shrink-0">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white text-lg font-semibold">{m.name.slice(0, 1)}</div>
                <span className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-[var(--surface-base)] ${statusColor[m.status]}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-semibold truncate">{m.name}</span>
                </div>
                <div className="text-xs text-muted-foreground truncate flex items-center gap-1">
                  <Mail className="w-3 h-3 shrink-0" />
                  {m.email}
                </div>
              </div>
              <button className="p-1 hover:bg-muted rounded shrink-0">
                <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
              </button>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className={`px-2 py-0.5 rounded-full border font-medium ${roleColors[m.role]}`}>{m.role}</span>
              <span className="text-muted-foreground">{m.lastActive}</span>
            </div>
            <div className="mt-3 pt-3 border-t border-border text-xs text-muted-foreground">
              加入于 {m.joinedAt}
            </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 角色权限概览 */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h2 className="font-semibold mb-1">角色权限概览</h2>
        <p className="text-xs text-muted-foreground mb-4">三种预置角色 · 可在权限设置中自定义</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { role: '管理员', desc: '全部功能 + 团队管理 + 系统设置', count: members.filter((m) => m.role === '管理员').length, color: 'border-brand-300 bg-brand-50/30' },
            { role: '成员',   desc: '日常工作台全部功能（无管理）',     count: members.filter((m) => m.role === '成员').length,   color: 'border-brand-200 bg-info-bg/30' },
            { role: '访客',   desc: '只读访问 Dashboard 与公开内容',   count: members.filter((m) => m.role === '访客').length,   color: 'border-border bg-muted' },
          ].map((r) => (
            <div key={r.role} className={`p-4 rounded-lg border-2 ${r.color}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold">{r.role}</span>
                <span className="text-xs text-muted-foreground">{r.count} 人</span>
              </div>
              <p className="text-xs text-muted-foreground">{r.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
