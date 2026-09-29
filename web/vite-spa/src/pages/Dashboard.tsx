/**
 * CloudTech Dashboard · v3 视觉母版 04 模块
 *
 * v3 实测布局：
 * - 顶部欢迎语 + 时间
 * - 4 个 KPI 卡（今日总工时 / 本周总工时 / 累计完成任务 / 平均成功率）
 * - "AI 今日简报" 浮动卡（右下角）
 * - "最近项目" + "最近动态" 双栏
 * - "团队任务分布" 饼图
 *
 * i18n: zh-CN + en-US via useTranslation
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Users, TrendingUp, AlertTriangle, ArrowRight, Bot, Sparkles, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { timeAgo } from '@/lib/utils';
import { useTranslation } from '@/i18n';

interface UsageData {
  calls: number;
  tokens: number;
  by_category: Record<string, number>;
}

interface FunnelReview {
  industry: string;
  status: string;
  decision: string;
  reason: string;
  metrics?: { leads: number; demo: number; signed: number; estimated_ltv: number; roi_ratio: number };
}

interface Project { id: string; name: string; progress: number; status: string; owner: string; updatedAt: string; }
interface Activity { id: string; actor: string; action: string; target: string; time: string; }

const projects: Project[] = [
  { id: 'p1', name: '市场分析报告集', progress: 80, status: '进行中', owner: 'NS', updatedAt: '今天 10:30' },
  { id: 'p2', name: '产品卖点分析', progress: 100, status: '已生成', owner: 'YS', updatedAt: '今天 19:20' },
  { id: 'p3', name: '用户调研问卷', progress: 60, status: '已生成', owner: 'NS', updatedAt: '今天 9:08' },
  { id: 'p4', name: '周报生成助手', progress: 30, status: '运行中', owner: 'WZ', updatedAt: '3月10日' },
];

const activities: Activity[] = [
  { id: 'a1', actor: 'NS', action: '生成了', target: '《市场分析报告》', time: '10:30' },
  { id: 'a2', actor: 'AI 生成', action: '《市场分析报告》', target: '已完成', time: '09:20' },
  { id: 'a3', actor: 'NS', action: '《用户调研问卷》', target: '已生成', time: '09:20' },
  { id: 'a4', actor: '王五', action: '《竞调报告》', target: '已生成', time: '昨天 16:20' },
];

const taskDistribution = [
  { label: '跟进中', value: 35, color: 'bg-brand-500' },
  { label: '待执行', value: 20, color: 'bg-warning-500' },
  { label: '已完成', value: 25, color: 'bg-success-500' },
  { label: '已签约', value: 12, color: 'bg-accent-purple-500' },
  { label: '已废弃', value: 8,  color: 'bg-destructive-500' },
];

export function DashboardPage() {
  const [showBriefing, setShowBriefing] = useState(true);
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      {/* 欢迎区 */}
      <div className="bg-[var(--surface-base)] rounded-xl border border-[var(--border-default)] p-6 flex items-start justify-between gap-4">
        <div className="flex-1">
          <h1 className="text-2xl font-bold mb-1.5">{t('dashboard.greeting')}</h1>
          <p className="text-sm text-[var(--text-secondary)]">{t('dashboard.greeting_subtitle')}</p>
        </div>
        <div className="hidden md:flex items-center gap-1 text-sm text-[var(--text-secondary)]">
          <button className="p-1 hover:bg-[var(--surface-muted)] rounded"><ChevronLeft className="w-4 h-4" /></button>
          <span className="font-medium">3月10日 周一</span>
          <button className="p-1 hover:bg-[var(--surface-muted)] rounded"><ChevronRight className="w-4 h-4" /></button>
        </div>
      </div>

      {/* KPI + 运行概览 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { labelKey: 'dashboard.today_running', sub: '进行中的任务', icon: TrendingUp, color: 'text-brand-600 bg-brand-50' },
            { labelKey: 'dashboard.agents_online', sub: '待命智能体',  icon: Bot,        color: 'text-accent-purple-600 bg-accent-purple-50' },
            { labelKey: 'dashboard.today_done',    sub: '已完成任务',  icon: BarChart3,   color: 'text-success-600 bg-success-50' },
            { labelKey: 'dashboard.pending',      sub: '待处理任务',  icon: AlertTriangle, color: 'text-warning-600 bg-warning-50' },
          ].map((kpi) => {
            const Icon = kpi.icon;
            return (
              <div key={kpi.labelKey} className="bg-[var(--surface-base)] rounded-xl border border-[var(--border-default)] p-5 hover:shadow-sm transition-shadow">
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${kpi.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
                <div className="text-3xl font-bold text-[var(--text-primary)]">{kpi.value}</div>
                <div className="text-xs text-[var(--text-secondary)] mt-1">{t(kpi.labelKey)}</div>
                <div className="text-[10px] text-[var(--text-tertiary)] mt-0.5">{kpi.sub}</div>
              </div>
            );
          })}
        </div>

        {/* 运行概览 柱状图 */}
        <div className="bg-[var(--surface-base)] rounded-xl border border-[var(--border-default)] p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-semibold">{t('dashboard.running_overview')}</div>
              <div className="text-xs text-[var(--text-tertiary)]">{t('app.view_detail')}</div>
            </div>
            <Link to="/monitoring" className="text-xs text-brand-600 hover:underline">{t('app.view_detail')} →</Link>
          </div>
          <div className="flex items-end justify-between gap-1 h-32">
            {[40, 65, 50, 80, 70, 90, 85, 60, 75, 95, 70, 88].map((h, i) => (
              <div key={i} className="flex-1 bg-brand-500 rounded-t" style={{ height: `${h}%` }} />
            ))}
          </div>
          <div className="flex justify-between text-[10px] text-[var(--text-tertiary)] mt-2">
            <span>3/1</span><span>3/3</span><span>3/5</span><span>3/7</span><span>3/9</span><span>3/11</span>
          </div>
        </div>
      </div>

      {/* 最近项目 + 最近动态 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[var(--surface-base)] rounded-xl border border-[var(--border-default)] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">{t('dashboard.recent_projects')}</h2>
            <Link to="/tasks" className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">{t('app.view_all')} →</Link>
          </div>
          <div className="space-y-2">
            {projects.map((p) => (
              <div key={p.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[var(--surface-subtle)] transition-colors">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-100 to-accent-purple-100 flex items-center justify-center text-xs font-semibold text-brand-700 shrink-0">{p.owner}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{p.name}</div>
                  <div className="text-xs text-[var(--text-tertiary)] mt-0.5">{p.updatedAt}</div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${
                  p.status === '已生成' ? 'bg-success-bg text-success-700' :
                  p.status === '进行中' ? 'bg-info-bg text-brand-700' :
                  'bg-warning-bg text-warning-700'
                }`}>{p.status}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[var(--surface-base)] rounded-xl border border-[var(--border-default)] p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">{t('dashboard.recent_activity')}</h2>
            <Link to="/notifications" className="text-xs text-[var(--text-tertiary)] hover:text-[var(--text-primary)]">{t('app.view_all')} →</Link>
          </div>
          <div className="space-y-3">
            {activities.map((a) => (
              <div key={a.id} className="flex items-start gap-3 text-sm">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white text-xs font-medium shrink-0">{a.actor.slice(0, 1)}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-[var(--text-primary)] truncate">
                    <span className="font-medium">{a.actor}</span>{' '}
                    <span className="text-[var(--text-secondary)]">{a.action}</span>{' '}
                    <span className="font-medium text-brand-700">{a.target}</span>
                  </div>
                  <div className="text-xs text-[var(--text-tertiary)] mt-0.5">{a.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 团队任务分布 饼图 */}
      <div className="bg-[var(--surface-base)] rounded-xl border border-[var(--border-default)] p-5">
        <h2 className="font-semibold mb-4">{t('dashboard.task_distribution')}</h2>
        <div className="flex items-center gap-8">
          <PieChart data={taskDistribution} />
          <div className="flex-1 grid grid-cols-2 md:grid-cols-3 gap-3">
            {taskDistribution.map((s) => (
              <div key={s.label} className="flex items-center gap-2 text-sm">
                <span className={`w-3 h-3 rounded-sm ${s.color}`} />
                <span className="text-[var(--text-secondary)]">{s.label}</span>
                <span className="ml-auto font-medium">{s.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AI 今日简报 浮动卡（右下） */}
      {showBriefing && (
        <div className="fixed bottom-6 right-6 w-80 bg-[var(--surface-base)] rounded-xl shadow-xl border border-[var(--border-default)] p-4 z-30 animate-slide-up">
          <button onClick={() => setShowBriefing(false)} className="absolute top-2 right-2 text-[var(--text-tertiary)] hover:text-[var(--text-primary)] text-lg leading-none">×</button>
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-accent-purple-500" />
            <span className="text-sm font-semibold">{t('dashboard.ai_briefing')}</span>
          </div>
          <p className="text-sm text-[var(--text-secondary)] mb-3">{t('dashboard.ai_briefing_text')}</p>
          <Button size="sm" className="w-full">{t('dashboard.ai_briefing_action')}<ArrowRight className="w-3.5 h-3.5" /></Button>
        </div>
      )}
    </div>
  );
}

function PieChart({ data }: { data: { label: string; value: number; color: string }[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  let cum = 0;
  const radius = 50;
  const cx = 60;
  const cy = 60;
  return (
    <svg viewBox="0 0 120 120" className="w-32 h-32 shrink-0">
      {data.map((d, i) => {
        const startAngle = (cum / total) * 2 * Math.PI - Math.PI / 2;
        cum += d.value;
        const endAngle = (cum / total) * 2 * Math.PI - Math.PI / 2;
        const x1 = cx + radius * Math.cos(startAngle);
        const y1 = cy + radius * Math.sin(startAngle);
        const x2 = cx + radius * Math.cos(endAngle);
        const y2 = cy + radius * Math.sin(endAngle);
        const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
        const color = d.color.replace('bg-', '').replace('-500', '');
        const colorMap: Record<string, string> = {
          brand: '#2563EB', success: '#10B981', warning: '#F59E0B',
          'accent-purple': '#8B5CF6', destructive: '#EF4444',
        };
        return (
          <path key={i}
            d={`M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`}
            fill={colorMap[color] || '#94A3B8'}
          />
        );
      })}
    </svg>
  );
}
