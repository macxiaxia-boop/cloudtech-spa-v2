/**
 * CloudTech SystemSettings · V23 视觉重做 (2026-09-30)
 * 5 Tab：模型管理 / 团队管理 / 权限设置 / 使用统计 / 系统日志 + shadcn Card
 *
 * V23: bg-[var(--xxx)] 硬编码 → 标准 token (bg-card / text-muted-foreground / border-border)
 */
import { useState } from 'react';
import { Plus, Settings as SettingsIcon, Users, Shield, BarChart3, FileText, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslation } from '@/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

type Tab = 'models' | 'team' | 'permissions' | 'stats' | 'logs';

const tabs: { key: Tab; label: string; icon: any }[] = [
  { key: 'models',      label: '模型管理',   icon: SettingsIcon },
  { key: 'team',        label: '团队管理',   icon: Users },
  { key: 'permissions', label: '权限设置',   icon: Shield },
  { key: 'stats',       label: '使用统计',   icon: BarChart3 },
  { key: 'logs',        label: '系统日志',   icon: FileText },
];

interface Model {
  id: string;
  name: string;
  provider: string;
  type: '大模型' | '嵌入模型' | '简单模型' | '语音模型';
  enabled: boolean;
}

const models: Model[] = [
  { id: 'm1', name: 'GPT-4o',     provider: 'OpenAI',    type: '大模型',     enabled: true },
  { id: 'm2', name: 'Claude 3.5', provider: 'Anthropic', type: '大模型',     enabled: true },
  { id: 'm3', name: 'Gemini 1.5', provider: 'Google',    type: '大模型',     enabled: true },
  { id: 'm4', name: 'Llama-3',    provider: 'Meta',      type: '大模型',     enabled: false },
  { id: 'm5', name: 'DeepSeek',   provider: '深度求索',  type: '大模型',     enabled: true },
  { id: 'm6', name: '智谱 GLM-4', provider: '智谱AI',    type: '大模型',     enabled: true },
  { id: 'm7', name: 'BGE-Large',  provider: 'BAAI',      type: '嵌入模型',   enabled: true },
  { id: 'm8', name: 'Whisper',    provider: 'OpenAI',    type: '语音模型',   enabled: false },
];

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: '管理员' | '成员' | '访客';
  status: 'online' | '1h' | '3h';
}

const members: TeamMember[] = [
  { id: 't1', name: '张三', email: 'zhangsan@company.com', role: '管理员', status: 'online' },
  { id: 't2', name: '李四', email: 'lisi@company.com',     role: '成员',   status: 'online' },
  { id: 't3', name: '王五', email: 'wangwu@company.com',   role: '成员',   status: '1h' },
  { id: 't4', name: '赵六', email: 'zhaoliu@company.com',  role: '访客',   status: '3h' },
];

interface LogEntry {
  id: string;
  level: 'info' | 'warn' | 'error';
  actor: string;
  action: string;
  target: string;
  time: string;
}

const logs: LogEntry[] = [
  { id: 'l1', level: 'info',  actor: '系统',    action: '自动备份完成',           target: '数据卷 v22',         time: '今天 14:00' },
  { id: 'l2', level: 'warn',  actor: '张三',    action: '启用未配置 API Key',     target: 'Llama-3',           time: '今天 12:30' },
  { id: 'l3', level: 'error', actor: 'system',  action: '调用失败 (rate limit)', target: 'GPT-4o',             time: '今天 11:15' },
  { id: 'l4', level: 'info',  actor: '李四',    action: '登录',                   target: 'web',                time: '今天 09:30' },
  { id: 'l5', level: 'info',  actor: '王五',    action: '创建工作流',             target: '市场分析工作流',      time: '昨天 18:20' },
];

const levelMap: Record<LogEntry['level'], { label: string; cls: string }> = {
  info:  { label: 'INFO',  cls: 'bg-info-bg text-brand-700' },
  warn:  { label: 'WARN',  cls: 'bg-warning-bg text-warning-700' },
  error: { label: 'ERROR', cls: 'bg-destructive-bg text-destructive-700' },
};

export function SettingsSystemPage() {
  const [tab, setTab] = useState<Tab>('models');
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">{t('nav.settings')}</h1>
        <p className="text-sm text-muted-foreground mt-1">模型 · 团队 · 权限 · 统计 · 日志</p>
      </div>

      {/* 5 Tab 横向 */}
      <div className="bg-card rounded-lg border border-border">
        <nav className="flex border-b border-border px-2 overflow-x-auto">
          {tabs.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  tab === t.key ? 'border-brand-600 text-brand-600' : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}>
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            );
          })}
        </nav>

        {/* 模型管理 Tab */}
        {tab === 'models' && (
          <div className="p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold">已配置模型</h2>
                <p className="text-xs text-muted-foreground mt-0.5">{models.filter((m) => m.enabled).length} / {models.length} 已启用</p>
              </div>
              <Button size="sm"><Plus className="w-4 h-4" />添加模型</Button>
            </div>
            <table className="w-full">
              <thead>
                <tr className="bg-muted border-b border-border">
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-2.5">模型</th>
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-2.5 w-32">类型</th>
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-2.5 w-40">服务商</th>
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-2.5 w-24">状态</th>
                  <th className="text-right text-xs font-medium text-muted-foreground px-4 py-2.5 w-24">操作</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.id} className="border-b border-border hover:bg-muted">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white text-xs font-semibold">{m.name.slice(0, 1)}</div>
                        <span className="text-sm font-medium">{m.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{m.type}</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{m.provider}</td>
                    <td className="px-4 py-2.5">
                      <button className={`relative w-9 h-5 rounded-full transition-colors ${m.enabled ? 'bg-brand-600' : 'bg-[var(--neutral-300)]'}`}>
                        <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-card transition-transform ${m.enabled ? 'translate-x-4' : ''}`} />
                      </button>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button className="text-xs text-brand-600 hover:underline mr-2">设置</button>
                      <button className="p-1 hover:bg-muted rounded"><MoreHorizontal className="w-4 h-4 text-muted-foreground" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 团队管理 Tab */}
        {tab === 'team' && (
          <div className="p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-semibold">成员管理</h2>
                <p className="text-xs text-muted-foreground mt-0.5">{members.length} 名成员 · {members.filter((m) => m.role === '管理员').length} 名管理员</p>
              </div>
              <Button size="sm"><Plus className="w-4 h-4" />邀请成员</Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {members.map((m) => (
                <div key={m.id} className="flex items-center gap-3 p-4 rounded-lg border border-border hover:shadow-sm transition-shadow">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white font-semibold shrink-0">{m.name.slice(0, 1)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{m.name}</span>
                      <span className={`w-2 h-2 rounded-full shrink-0 ${m.status === 'online' ? 'bg-success-500' : m.status === '1h' ? 'bg-warning-500' : 'bg-neutral-300'}`} />
                    </div>
                    <div className="text-xs text-muted-foreground truncate">{m.email}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 font-medium">{m.role}</span>
                    <button className="text-xs text-muted-foreground hover:text-foreground">编辑</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 权限设置 Tab */}
        {tab === 'permissions' && (
          <div className="p-5">
            <h2 className="font-semibold mb-1">角色权限矩阵</h2>
            <p className="text-xs text-muted-foreground mb-4">配置每个角色可访问的功能模块</p>
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted border-b border-border">
                  <th className="text-left text-xs font-medium text-muted-foreground px-4 py-2.5">模块</th>
                  <th className="text-center text-xs font-medium text-muted-foreground px-4 py-2.5 w-24">管理员</th>
                  <th className="text-center text-xs font-medium text-muted-foreground px-4 py-2.5 w-24">成员</th>
                  <th className="text-center text-xs font-medium text-muted-foreground px-4 py-2.5 w-24">访客</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { module: 'Dashboard', perms: [true, true, true] },
                  { module: 'AI 对话',   perms: [true, true, true] },
                  { module: '智能体',     perms: [true, true, false] },
                  { module: '工作流',     perms: [true, true, false] },
                  { module: '任务中心',   perms: [true, true, false] },
                  { module: '知识库',     perms: [true, true, false] },
                  { module: '文件管理',   perms: [true, true, false] },
                  { module: '团队管理',   perms: [true, false, false] },
                  { module: '系统设置',   perms: [true, false, false] },
                ].map((row) => (
                  <tr key={row.module} className="border-b border-border">
                    <td className="px-4 py-2.5 font-medium">{row.module}</td>
                    {row.perms.map((p, i) => (
                      <td key={i} className="px-4 py-2.5 text-center">
                        {p ? (
                          <span className="inline-flex w-5 h-5 rounded-full bg-success-100 text-success-700 items-center justify-center text-xs">✓</span>
                        ) : (
                          <span className="inline-flex w-5 h-5 rounded-full bg-muted text-muted-foreground items-center justify-center text-xs">—</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 使用统计 Tab */}
        {tab === 'stats' && (
          <div className="p-5">
            <h2 className="font-semibold mb-4">API 调用统计</h2>
            <div className="grid grid-cols-3 gap-4 mb-4">
              {[
                { label: '今日调用', value: '1,247', trend: '+12%' },
                { label: '总 Token 消耗', value: '892K', trend: '+8%' },
                { label: '本月费用', value: '¥328', trend: '+15%' },
              ].map((s) => (
                <div key={s.label} className="p-4 bg-muted rounded-lg">
                  <div className="text-xs text-muted-foreground">{s.label}</div>
                  <div className="text-2xl font-bold mt-1">{s.value}</div>
                  <div className="text-xs text-success-600 mt-1">{s.trend}</div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-info-bg border border-brand-200 rounded-lg text-sm text-brand-700">
              详细统计请访问 <a href="/monitoring" className="font-medium underline">监控中心</a>
            </div>
          </div>
        )}

        {/* 系统日志 Tab */}
        {tab === 'logs' && (
          <div className="p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">系统日志</h2>
              <select className="h-8 rounded border border-border bg-card px-2 text-xs">
                <option>全部级别</option>
                <option>INFO</option>
                <option>WARN</option>
                <option>ERROR</option>
              </select>
            </div>
            <div className="space-y-1">
              {logs.map((log) => {
                const lm = levelMap[log.level];
                return (
                  <div key={log.id} className="flex items-center gap-3 px-3 py-2 rounded hover:bg-muted text-sm">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold shrink-0 ${lm.cls}`}>{lm.label}</span>
                    <span className="text-muted-foreground shrink-0 w-16">{log.actor}</span>
                    <span className="text-foreground flex-1 truncate">
                      <span className="text-muted-foreground">{log.action}</span> · <span className="font-medium">{log.target}</span>
                    </span>
                    <span className="text-xs text-muted-foreground shrink-0">{log.time}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
