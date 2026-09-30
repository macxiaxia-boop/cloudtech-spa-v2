/**
 * CloudTech Analytics · v3 视觉母版 12 模块
 * 数据分析中心：KPI 卡 + 折线 + 饼图 + 条形 + i18n
 */
import { useState } from 'react';
import { Users, TrendingUp, Activity, Layers, Download, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslation } from '@/i18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

type TimeRange = '7d' | '30d' | '90d' | '1y';

const ranges: { key: TimeRange; label: string }[] = [
  { key: '7d', label: '7 天' },
  { key: '30d', label: '30 天' },
  { key: '90d', label: '90 天' },
  { key: '1y', label: '1 年' },
];

const taskDistribution = [
  { label: '跟进中', value: 35, color: '#2563EB' },
  { label: '待执行', value: 20, color: '#F59E0B' },
  { label: '已完成', value: 25, color: '#10B981' },
  { label: '已签约', value: 12, color: '#8B5CF6' },
  { label: '已废弃', value: 8,  color: '#EF4444' },
];

const industryData = [
  { name: '数据中台', leads: 35, signed: 28 },
  { name: '内容营销', leads: 25, signed: 18 },
  { name: '市场运营', leads: 20, signed: 12 },
  { name: '代码优化', leads: 12, signed: 8 },
  { name: '数据可视化', leads: 8, signed: 4 },
];

const userGrowthData = [40, 65, 50, 80, 70, 90, 85, 60, 75, 95, 70, 88, 100];

export function AnalyticsPage() {
  const [range, setRange] = useState<TimeRange>('30d');
  const { t } = useTranslation();
  const total = taskDistribution.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">{t('nav.analytics')}</h1>
          <p className="text-sm text-muted-foreground mt-1">用户增长 · 任务分布 · 行业转化 · 每日活跃</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex border border-border rounded-md overflow-hidden">
            {ranges.map((r) => (
              <button key={r.key} onClick={() => setRange(r.key)}
                className={`px-3 py-1.5 text-xs transition-colors ${
                  range === r.key ? 'bg-brand-50 text-brand-700 font-medium' : 'text-muted-foreground hover:bg-muted'
                }`}>{r.label}</button>
            ))}
          </div>
          <Button variant="outline" size="sm"><Calendar className="w-3.5 h-3.5" />自定义</Button>
          <Button variant="outline" size="sm"><Download className="w-3.5 h-3.5" />导出</Button>
        </div>
      </div>

      {/* 4 KPI 卡 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: '总用户数',     value: '32,480', change: '+32%', positive: true, icon: Users, color: 'text-brand-600 bg-brand-50' },
          { label: '活跃用户',     value: '12,640', change: '+18%', positive: true, icon: Activity, color: 'text-success-600 bg-success-50' },
          { label: '任务完成率',   value: '68%',    change: '+6%',  positive: true, icon: TrendingUp, color: 'text-accent-purple-600 bg-accent-purple-50' },
          { label: '总调用次数',   value: '856',    change: '+24%', positive: true, icon: Layers, color: 'text-warning-600 bg-warning-50' },
        ].map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="bg-card rounded-xl border border-border p-5">
              <div className="flex items-center justify-between mb-3">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${kpi.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className={`text-xs font-medium ${kpi.positive ? 'text-success-600' : 'text-destructive-600'}`}>{kpi.change}</span>
              </div>
              <div className="text-2xl font-bold text-foreground">{kpi.value}</div>
              <div className="text-xs text-muted-foreground mt-1">{kpi.label}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 用户增长 折线图 */}
        <div className="bg-card rounded-xl border border-border p-5">
          <h2 className="font-semibold mb-1">用户增长趋势</h2>
          <p className="text-xs text-muted-foreground mb-4">最近 30 天新增用户数</p>
          <LineChart data={userGrowthData} />
          <div className="flex justify-between text-[10px] text-muted-foreground mt-3">
            <span>3/1</span><span>3/8</span><span>3/15</span><span>3/22</span><span>3/30</span>
          </div>
        </div>

        {/* 任务类型分布 饼图 */}
        <div className="bg-card rounded-xl border border-border p-5">
          <h2 className="font-semibold mb-1">任务类型分布</h2>
          <p className="text-xs text-muted-foreground mb-4">按当前活跃任务分类</p>
          <div className="flex items-center gap-6">
            <PieChart data={taskDistribution} total={total} />
            <div className="flex-1 grid grid-cols-1 gap-2">
              {taskDistribution.map((d) => (
                <div key={d.label} className="flex items-center gap-2 text-sm">
                  <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: d.color }} />
                  <span className="text-muted-foreground">{d.label}</span>
                  <span className="ml-auto font-medium">{d.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 行业转化 条形图 */}
      <div className="bg-card rounded-xl border border-border p-5">
        <h2 className="font-semibold mb-1">行业转化分布</h2>
        <p className="text-xs text-muted-foreground mb-4">各行业的线索与签约数对比</p>
        <div className="space-y-3">
          {industryData.map((ind) => {
            const max = Math.max(...industryData.map((d) => d.leads));
            return (
              <div key={ind.name}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="font-medium">{ind.name}</span>
                  <span className="text-xs text-muted-foreground">{ind.signed}/{ind.leads}</span>
                </div>
                <div className="flex gap-1 h-6">
                  <div className="bg-brand-500 rounded" style={{ width: `${(ind.leads / max) * 100}%` }} />
                  <div className="bg-success-500 rounded" style={{ width: `${(ind.signed / max) * 100}%` }} />
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 mt-4 pt-3 border-t border-border text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5"><span className="w-3 h-3 bg-brand-500 rounded" />线索数</div>
          <div className="flex items-center gap-1.5"><span className="w-3 h-3 bg-success-500 rounded" />签约数</div>
        </div>
      </div>
    </div>
  );
}

function LineChart({ data }: { data: number[] }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const w = 320;
  const h = 120;
  const range = max - min || 1;
  const step = w / (data.length - 1);
  const points = data.map((v, i) => `${i * step},${h - ((v - min) / range) * h}`).join(' ');
  const areaPoints = `0,${h} ${points} ${w},${h}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-32">
      <defs>
        <linearGradient id="line-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563EB" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#2563EB" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill="url(#line-grad)" />
      <polyline points={points} fill="none" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {data.map((v, i) => (
        <circle key={i} cx={i * step} cy={h - ((v - min) / range) * h} r="3" fill="#2563EB" />
      ))}
    </svg>
  );
}

function PieChart({ data, total }: { data: { label: string; value: number; color: string }[]; total: number }) {
  const radius = 60;
  const cx = 75;
  const cy = 75;
  let cum = 0;
  return (
    <svg viewBox="0 0 150 150" className="w-36 h-36 shrink-0">
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
          <path key={i}
            d={`M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`}
            fill={d.color}
          />
        );
      })}
      <circle cx={cx} cy={cy} r="30" fill="white" />
      <text x={cx} y={cy - 4} textAnchor="middle" className="text-xs font-semibold" fill="#0F172A">总任务</text>
      <text x={cx} y={cy + 12} textAnchor="middle" className="text-lg font-bold" fill="#0F172A">{total}</text>
    </svg>
  );
}
