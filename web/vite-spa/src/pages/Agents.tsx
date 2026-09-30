/**
 * CloudTech Agents · v3 视觉母版 06 模块
 * 智能体中心：4 Tab（全部/我的/团队/官方模板）+ 6 智能体卡片网格 + i18n
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, MoreHorizontal, Bot, TrendingUp, FileText, Heart, BarChart3, Headphones, FileSearch } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTranslation } from '@/i18n';

type Tab = 'all' | 'mine' | 'team' | 'official';

const tabs: { key: Tab; label: string; count: number }[] = [
  { key: 'all',      label: '全部',       count: 6 },
  { key: 'mine',     label: '我的智能体', count: 2 },
  { key: 'team',     label: '团队智能体', count: 3 },
  { key: 'official', label: '官方模板',   count: 1 },
];

const agents = [
  { id: 'a1', name: '市场分析师',    description: '数据分析 · 市场研究 · 行业洞察', icon: TrendingUp,  bg: 'bg-gradient-to-br from-brand-500 to-brand-700',       tags: ['数据分析', '市场研究'], uses: '1.2k 使用', owner: 'Nova Team', status: 'team' },
  { id: 'a2', name: '内容创作助手',  description: '内容创作 · 排版 · 校对',             icon: FileText,     bg: 'bg-gradient-to-br from-accent-orange-500 to-accent-orange-600', tags: ['文案', '排版'], uses: '856 使用', owner: 'Nova Team', status: 'team' },
  { id: 'a3', name: '客户成功助手',  description: '客户沟通 · 排版 · 反馈',             icon: Heart,        bg: 'bg-gradient-to-br from-destructive-500 to-destructive-600', tags: ['客服', '客户关系'], uses: '643 使用', owner: 'Nova Team', status: 'team' },
  { id: 'a4', name: '数据分析专家',  description: '数据探索 · 规格配置 · 文档',         icon: BarChart3,    bg: 'bg-gradient-to-br from-accent-purple-500 to-accent-purple-600', tags: ['数据', '分析'], uses: '1.3k 使用', owner: 'Nova Team', status: 'team' },
  { id: 'a5', name: '客户报告助手',  description: '数据报告 · 智能文档 · 处理',         icon: Headphones,   bg: 'bg-gradient-to-br from-success-500 to-success-600', tags: ['报告', '客户'], uses: '980 使用', owner: '我', status: 'mine' },
  { id: 'a6', name: '文档处理助手',  description: '文档整理 · 文件处理 · 翻译',         icon: FileSearch,   bg: 'bg-gradient-to-br from-warning-500 to-warning-600', tags: ['文档', '翻译'], uses: '664 使用', owner: '我', status: 'mine' },
];

export function AgentsPage() {
  const [tab, setTab] = useState<Tab>('all');
  const { t } = useTranslation();
  const filtered = tab === 'all' ? agents : agents.filter((a) => a.status === tab || (tab === 'official' && a.status === 'team'));

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">{t('nav.agents')}</h1>
          <p className="text-sm text-muted-foreground mt-1">智能体市场 · 创建配置 · 技能扩展 · 版本管理</p>
        </div>
        <Link to="/employees/new">
          <Button><Plus className="w-4 h-4" />{t('app.create_agent')}</Button>
        </Link>
      </div>

      <div className="bg-card rounded-lg border border-border">
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

        <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((a) => {
            const Icon = a.icon;
            return (
              <div key={a.id} className="group bg-card rounded-xl border border-border p-5 hover:shadow-md hover:border-brand-300 transition-all">
                <div className="flex items-start justify-between mb-3">
                  <div className={`w-12 h-12 rounded-xl ${a.bg} flex items-center justify-center shadow-sm`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <button className="p-1 opacity-0 group-hover:opacity-100 hover:bg-muted rounded transition-opacity">
                    <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
                  </button>
                </div>
                <h3 className="font-semibold mb-1 group-hover:text-brand-600 transition-colors">{a.name}</h3>
                <p className="text-xs text-muted-foreground mb-3 line-clamp-2 min-h-[2.5em]">{a.description}</p>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {a.tags.map((t) => (
                    <span key={t} className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground">{t}</span>
                  ))}
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <div className="text-xs text-muted-foreground">
                    <Bot className="w-3 h-3 inline mr-0.5" />
                    {a.owner}
                  </div>
                  <span className="text-xs text-muted-foreground">{a.uses}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
