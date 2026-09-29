/**
 * CloudTech Profile · v3 视觉母版 15 模块
 * 个人中心：6 Tab（个人资料/账号安全/API 管理/使用统计/通知与消息/隐私设置）
 */
import { useState } from 'react';
import { Camera, User, Shield, Key, BarChart3, Bell, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

type Tab = 'profile' | 'security' | 'api' | 'stats' | 'notifications' | 'privacy';

const tabs: { key: Tab; label: string; icon: any }[] = [
  { key: 'profile',       label: '个人资料', icon: User },
  { key: 'security',      label: '账号安全', icon: Shield },
  { key: 'api',           label: 'API 管理', icon: Key },
  { key: 'stats',         label: '使用统计', icon: BarChart3 },
  { key: 'notifications', label: '通知与消息', icon: Bell },
  { key: 'privacy',       label: '隐私设置', icon: Lock },
];

export function ProfilePage() {
  const [tab, setTab] = useState<Tab>('profile');

  return (
    <div className="space-y-4">
      {/* 顶部用户卡 */}
      <div className="bg-gradient-to-br from-brand-50 to-accent-purple-50 rounded-xl border border-brand-200 p-6 flex items-center gap-5">
        <div className="relative">
          <div className="w-20 h-20 rounded-full bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white text-2xl font-bold">ZS</div>
          <button className="absolute bottom-0 right-0 w-7 h-7 rounded-full bg-[var(--surface-base)] border border-[var(--border-default)] flex items-center justify-center hover:bg-brand-50 transition-colors shadow-sm">
            <Camera className="w-3.5 h-3.5 text-[var(--text-secondary)]" />
          </button>
        </div>
        <div className="flex-1">
          <h1 className="text-xl font-bold">张三</h1>
          <div className="text-sm text-[var(--text-secondary)]">zhangsan@company.com</div>
          <div className="flex items-center gap-3 mt-2 text-xs text-[var(--text-tertiary)]">
            <span>ID: 188****6666</span>
            <span>·</span>
            <span>产品研发部</span>
            <span>·</span>
            <span className="px-2 py-0.5 rounded-full bg-brand-100 text-brand-700">管理员</span>
          </div>
        </div>
        <Button variant="outline">更换头像</Button>
      </div>

      {/* 6 Tab */}
      <div className="bg-[var(--surface-base)] rounded-lg border border-[var(--border-default)] flex">
        <nav className="w-56 border-r border-[var(--border-default)] p-3 space-y-1">
          {tabs.map((t) => {
            const Icon = t.icon;
            return (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                  tab === t.key ? 'bg-brand-50 text-brand-700 font-medium' : 'text-[var(--text-secondary)] hover:bg-[var(--surface-muted)]'
                }`}>
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            );
          })}
        </nav>

        <div className="flex-1 p-6">
          {tab === 'profile' && (
            <div className="space-y-5 max-w-2xl">
              <h2 className="font-semibold mb-3">个人资料</h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5"><Label>姓名</Label><Input defaultValue="张三" /></div>
                <div className="space-y-1.5"><Label>邮箱</Label><Input defaultValue="zhangsan@company.com" /></div>
                <div className="space-y-1.5"><Label>手机</Label><Input defaultValue="+86 138 0000 0000" /></div>
                <div className="space-y-1.5"><Label>部门</Label><Input defaultValue="产品研发部" /></div>
              </div>
              <Button>保存修改</Button>
            </div>
          )}

          {tab === 'security' && (
            <div className="space-y-4 max-w-2xl">
              <h2 className="font-semibold mb-3">账号安全</h2>
              <SettingRow label="登录密码" desc="上次修改：90 天前" action="修改" />
              <SettingRow label="两步验证" desc="已启用 · 使用 Google Authenticator" action="管理" status="已启用" statusCls="success" />
              <SettingRow label="登录设备" desc="3 台设备 · 当前 MacBook Pro" action="查看" />
              <SettingRow label="备用邮箱" desc="未设置" action="添加" />
            </div>
          )}

          {tab === 'api' && (
            <div className="space-y-4 max-w-2xl">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold">API Keys</h2>
                <Button size="sm">+ 创建新 Key</Button>
              </div>
              <div className="space-y-2">
                {[
                  { name: 'Production Key', prefix: 'sk-prod-****abc123', created: '2026-01-15', lastUsed: '2 小时前' },
                  { name: 'Dev Key',         prefix: 'sk-dev-****xyz789',  created: '2026-02-20', lastUsed: '10 分钟前' },
                  { name: 'Test Key',        prefix: 'sk-test-****qwe456', created: '2026-03-10', lastUsed: '3 天前' },
                ].map((k) => (
                  <div key={k.name} className="flex items-center gap-3 p-3 rounded-md border border-[var(--border-default)]">
                    <Key className="w-4 h-4 text-[var(--text-tertiary)]" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium">{k.name}</div>
                      <div className="text-xs text-[var(--text-tertiary)] font-mono">{k.prefix}</div>
                    </div>
                    <div className="text-xs text-[var(--text-tertiary)]">最后使用 {k.lastUsed}</div>
                    <button className="text-xs text-destructive-600 hover:underline">撤销</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === 'stats' && (
            <div className="space-y-4">
              <h2 className="font-semibold mb-3">使用统计（本月）</h2>
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: 'API 调用次数', value: '4,821', trend: '+18%' },
                  { label: 'Token 消耗',   value: '1.2M',  trend: '+22%' },
                  { label: '本月费用',     value: '¥85.20', trend: '+15%' },
                ].map((s) => (
                  <div key={s.label} className="p-4 bg-[var(--surface-subtle)] rounded-lg">
                    <div className="text-xs text-[var(--text-tertiary)]">{s.label}</div>
                    <div className="text-2xl font-bold mt-1">{s.value}</div>
                    <div className="text-xs text-success-600 mt-1">{s.trend}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === 'notifications' && (
            <div className="space-y-4 max-w-2xl">
              <h2 className="font-semibold mb-3">通知与消息</h2>
              {[
                { label: '邮件通知', desc: '任务完成 · 系统更新 · 周报' },
                { label: '站内消息', desc: '工作流执行结果 · 协作邀请' },
                { label: '短信通知', desc: '仅紧急告警' },
                { label: '桌面通知', desc: '浏览器原生通知' },
              ].map((n) => (
                <SettingRow key={n.label} label={n.label} desc={n.desc} action="配置" status="已启用" statusCls="success" />
              ))}
            </div>
          )}

          {tab === 'privacy' && (
            <div className="space-y-4 max-w-2xl">
              <h2 className="font-semibold mb-3">隐私设置</h2>
              <SettingRow label="数据收集" desc="用于改进产品体验" action="关闭" />
              <SettingRow label="个性化推荐" desc="基于使用历史的智能推荐" action="关闭" />
              <SettingRow label="第三方共享" desc="不与第三方共享您的数据" action="关闭" status="已禁用" statusCls="muted" />
              <SettingRow label="导出我的数据" desc="下载所有个人数据副本" action="导出" />
              <SettingRow label="删除账户" desc="永久删除账户及所有数据" action="删除" danger />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SettingRow({ label, desc, action, status, statusCls, danger }: { label: string; desc: string; action: string; status?: string; statusCls?: 'success' | 'muted'; danger?: boolean }) {
  const statusClasses = {
    success: 'bg-success-bg text-success-700',
    muted:   'bg-[var(--surface-muted)] text-[var(--text-secondary)]',
  };
  return (
    <div className="flex items-center gap-4 p-4 rounded-lg border border-[var(--border-default)]">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium">{label}</span>
          {status && <span className={`text-xs px-2 py-0.5 rounded-full ${statusClasses[statusCls || 'success']}`}>{status}</span>}
        </div>
        <div className="text-xs text-[var(--text-tertiary)] mt-0.5">{desc}</div>
      </div>
      <Button variant="outline" size="sm" className={danger ? 'text-destructive-600 border-destructive-200 hover:bg-destructive-bg' : ''}>{action}</Button>
    </div>
  );
}
