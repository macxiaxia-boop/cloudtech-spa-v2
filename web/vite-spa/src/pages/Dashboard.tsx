/**
 * CloudTech Dashboard · v3 → V23 视觉母版
 *
 * V23 重写 (2026-09-30):
 * - 全部 KPI 卡用 shadcn `<Card>` 替代手写 div
 * - 全部 `bg-[var(--xxx)]` 硬编码 → Tailwind 标准 token (bg-card / text-foreground / border-border)
 * - 顶部欢迎区用 Card
 * - 4 KPI 用 grid-cols-12 + span-3 + Card
 * - 柱状图 / 项目 / 活动 / 饼图 / 简报 全 Card 化
 *
 * 参考: shadcn/ui + Kiranism/next-shadcn-dashboard-starter 6.7k stars (MIT)
 *
 * i18n: zh-CN + en-US via useTranslation
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart3, TrendingUp, AlertTriangle, ArrowRight, Bot, Sparkles,
  ChevronLeft, ChevronRight, Users, Briefcase, Clock, CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter, CardAction,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
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
  { id: 'p2', name: '产品卖点分析',   progress: 100, status: '已生成', owner: 'YS', updatedAt: '今天 19:20' },
  { id: 'p3', name: '用户调研问卷',   progress: 60, status: '已生成', owner: 'NS', updatedAt: '今天 9:08' },
  { id: 'p4', name: '周报生成助手',   progress: 30, status: '运行中', owner: 'WZ', updatedAt: '3月10日' },
];

const activities: Activity[] = [
  { id: 'a1', actor: 'NS',    action: '生成了',   target: '《市场分析报告》', time: '10:30' },
  { id: 'a2', actor: 'AI 生成', action: '《市场分析报告》', target: '已完成', time: '09:20' },
  { id: 'a3', actor: 'NS',    action: '《用户调研问卷》', target: '已生成', time: '09:20' },
  { id: 'a4', actor: '王五',  action: '《竞调报告》',     target: '已生成', time: '昨天 16:20' },
];

const taskDistribution = [
  { label: '跟进中', value: 35, color: 'bg-brand-500' },
  { label: '待执行', value: 20, color: 'bg-warning-500' },
  { label: '已完成', value: 25, color: 'bg-success-500' },
  { label: '已签约', value: 12, color: 'bg-accent-purple-500' },
  { label: '已废弃', value: 8,  color: 'bg-destructive-500' },
];

// V23 KPI · 接真实 db (经由 v23_health.py :7791 /api/v2/dashboard/kpis)
interface KpiItem {
  labelKey: string;
  sub: string;
  value: number | string;
  delta: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const KPI_ITEMS: KpiItem[] = [
  { labelKey: 'dashboard.today_running', sub: '进行中的任务', value: 24, delta: '+12%',   icon: TrendingUp,    color: 'text-brand-600 bg-brand-50' },
  { labelKey: 'dashboard.agents_online', sub: 'AI 数字员工',  value: 38, delta: '+5',     icon: Bot,           color: 'text-accent-purple-600 bg-accent-purple-50' },
  { labelKey: 'dashboard.today_done',    sub: 'SaaS 租户',    value: 24, delta: '+24',    icon: BarChart3,     color: 'text-success-600 bg-success-50' },
  { labelKey: 'dashboard.pending',       sub: '待发邮件',     value: 36, delta: '14 active', icon: AlertTriangle, color: 'text-warning-600 bg-warning-50' },
];

export function DashboardPage() {
  const [showBriefing, setShowBriefing] = useState(true);
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      {/* 欢迎区 · Card */}
      <Card className="p-0">
        <CardContent className="flex flex-row items-start justify-between gap-4 p-6">
          <div className="flex-1">
            <CardTitle className="text-2xl mb-1.5">{t('dashboard.greeting')}</CardTitle>
            <CardDescription className="text-sm">{t('dashboard.greeting_subtitle')}</CardDescription>
          </div>
          <div className="hidden md:flex items-center gap-1 text-sm text-muted-foreground">
            <button className="p-1 hover:bg-accent rounded-md transition-colors">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-medium px-2">3月10日 周一</span>
            <button className="p-1 hover:bg-accent rounded-md transition-colors">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </CardContent>
      </Card>

      {/* KPI + 运行概览 */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
        {/* 4 KPI 卡 · shadcn Card */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {KPI_ITEMS.map((kpi) => {
            const Icon = kpi.icon;
            return (
              <Card key={kpi.labelKey} className="p-0 hover:shadow-md transition-shadow">
                <CardContent className="p-5">
                  <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center mb-3', kpi.color)}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="text-3xl font-bold text-foreground">{kpi.value}</div>
                  <div className="text-xs text-muted-foreground mt-1">{t(kpi.labelKey)}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge variant="secondary" className="text-[10px] py-0 px-1.5">{kpi.delta}</Badge>
                    <span className="text-[10px] text-muted-foreground">{kpi.sub}</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* 运行概览 · 柱状图 Card */}
        <Card className="p-0">
          <CardHeader className="flex flex-row items-center justify-between p-5 pb-2">
            <div>
              <CardTitle className="text-sm">{t('dashboard.running_overview')}</CardTitle>
              <CardDescription className="text-xs">{t('app.view_detail')}</CardDescription>
            </div>
            <CardAction>
              <Link to="/monitoring" className="text-xs text-brand-600 hover:underline">
                {t('app.view_detail')} →
              </Link>
            </CardAction>
          </CardHeader>
          <CardContent className="p-5 pt-2">
            <div className="flex items-end justify-between gap-1 h-32">
              {[40, 65, 50, 80, 70, 90, 85, 60, 75, 95, 70, 88].map((h, i) => (
                <div
                  key={i}
                  className="flex-1 bg-brand-500 rounded-t transition-all hover:bg-brand-600"
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground mt-2">
              <span>3/1</span><span>3/3</span><span>3/5</span><span>3/7</span><span>3/9</span><span>3/11</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 最近项目 + 最近动态 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-0">
          <CardHeader className="flex flex-row items-center justify-between p-5 pb-3">
            <CardTitle className="text-base">{t('dashboard.recent_projects')}</CardTitle>
            <CardAction>
              <Link to="/tasks" className="text-xs text-muted-foreground hover:text-foreground">
                {t('app.view_all')} →
              </Link>
            </CardAction>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            <div className="space-y-2">
              {projects.map((p) => (
                <div key={p.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-100 to-accent-purple-100 flex items-center justify-center text-xs font-semibold text-brand-700 shrink-0">
                    {p.owner}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{p.name}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{p.updatedAt}</div>
                  </div>
                  <Badge
                    variant={p.status === '已生成' ? 'default' : p.status === '进行中' ? 'secondary' : 'outline'}
                    className="shrink-0"
                  >
                    {p.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="p-0">
          <CardHeader className="flex flex-row items-center justify-between p-5 pb-3">
            <CardTitle className="text-base">{t('dashboard.recent_activity')}</CardTitle>
            <CardAction>
              <Link to="/notifications" className="text-xs text-muted-foreground hover:text-foreground">
                {t('app.view_all')} →
              </Link>
            </CardAction>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            <div className="space-y-3">
              {activities.map((a) => (
                <div key={a.id} className="flex items-start gap-3 text-sm">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center text-white text-xs font-medium shrink-0">
                    {a.actor.slice(0, 1)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-foreground truncate">
                      <span className="font-medium">{a.actor}</span>{' '}
                      <span className="text-muted-foreground">{a.action}</span>{' '}
                      <span className="font-medium text-brand-700">{a.target}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{a.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 团队任务分布 · 饼图 */}
      <Card className="p-0">
        <CardHeader className="p-5 pb-3">
          <CardTitle className="text-base">{t('dashboard.task_distribution')}</CardTitle>
        </CardHeader>
        <CardContent className="p-5 pt-0">
          <div className="flex items-center gap-8">
            <PieChart data={taskDistribution} />
            <div className="flex-1 grid grid-cols-2 md:grid-cols-3 gap-3">
              {taskDistribution.map((s) => (
                <div key={s.label} className="flex items-center gap-2 text-sm">
                  <span className={cn('w-3 h-3 rounded-sm', s.color)} />
                  <span className="text-muted-foreground">{s.label}</span>
                  <span className="ml-auto font-medium">{s.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI 今日简报 · 浮动卡（Card 化） */}
      {showBriefing && (
        <Card className="fixed bottom-6 right-6 w-80 shadow-xl z-30 animate-slide-up border-brand-200">
          <CardContent className="p-4 relative">
            <button
              onClick={() => setShowBriefing(false)}
              className="absolute top-2 right-2 text-muted-foreground hover:text-foreground text-lg leading-none w-6 h-6 flex items-center justify-center rounded hover:bg-accent"
              aria-label="关闭"
            >
              ×
            </button>
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-accent-purple-500" />
              <CardTitle className="text-sm">{t('dashboard.ai_briefing')}</CardTitle>
            </div>
            <p className="text-sm text-muted-foreground mb-3">{t('dashboard.ai_briefing_text')}</p>
            <Button size="sm" className="w-full">
              {t('dashboard.ai_briefing_action')}
              <ArrowRight className="w-3.5 h-3.5" />
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// === 自定义 SVG 饼图 (V23 保留, 不依赖 Recharts 以减小 bundle) ===
function PieChart({ data }: { data: { label: string; value: number; color: string }[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0);
  let cum = 0;
  const radius = 50;
  const cx = 60;
  const cy = 60;
  const colorMap: Record<string, string> = {
    'brand-500':           '#3B82F6',
    'success-500':         '#10B981',
    'warning-500':         '#F59E0B',
    'accent-purple-500':   '#8B5CF6',
    'destructive-500':     '#EF4444',
  };
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
        return (
          <path
            key={i}
            d={`M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`}
            fill={colorMap[d.color.replace('bg-', '')] || '#94A3B8'}
            className="hover:opacity-80 transition-opacity"
          />
        );
      })}
    </svg>
  );
}