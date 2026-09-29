/**
 * CloudTech Workflows · v3 视觉母版 08 模块 · 列表页
 * 工作流列表 · 卡片网格 · 状态徽章
 */
import { Link } from 'react-router-dom';
import { Plus, Workflow, MoreHorizontal, Play, Edit2, Trash2, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'published' | 'draft' | 'paused';
  nodeCount: number;
  updatedAt: string;
  lastRun?: string;
  runs: number;
}

const workflows: Workflow[] = [
  { id: 'w1', name: '市场分析工作流', description: '数据采集 → AI 分析 → 报告生成 → 邮件发送', status: 'published', nodeCount: 5, updatedAt: '今天 14:20', lastRun: '2 小时前', runs: 47 },
  { id: 'w2', name: '客户报告助手',     description: '用户反馈 → 情感分析 → 报告草稿 → 钉钉通知', status: 'published', nodeCount: 6, updatedAt: '昨天 18:30', lastRun: '昨天 16:20', runs: 23 },
  { id: 'w3', name: '内容生产 SOP',     description: '选题 → 大纲 → AI 撰写 → 校对 → 发布',       status: 'draft',     nodeCount: 4, updatedAt: '3 月 10 日', runs: 0 },
  { id: 'w4', name: '竞品监控日报',     description: '定时抓取 → 数据清洗 → AI 摘要 → 飞书推送', status: 'published', nodeCount: 7, updatedAt: '3 月 9 日',  lastRun: '今天 09:00', runs: 124 },
  { id: 'w5', name: '用户调研分析',     description: '问卷收集 → 数据处理 → 聚类分析 → 可视化',   status: 'paused',    nodeCount: 5, updatedAt: '3 月 5 日',  runs: 8 },
  { id: 'w6', name: '合同审查',         description: '上传 → OCR → 关键条款提取 → 法务审核',     status: 'draft',     nodeCount: 4, updatedAt: '2 月 28 日', runs: 0 },
];

const statusMap: Record<Workflow['status'], { label: string; cls: string }> = {
  published: { label: '已发布', cls: 'bg-success-bg text-success-700' },
  draft:     { label: '草稿',   cls: 'bg-[var(--surface-muted)] text-[var(--text-secondary)]' },
  paused:    { label: '已暂停', cls: 'bg-warning-bg text-warning-700' },
};

export function WorkflowsPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">工作流</h1>
          <p className="text-sm text-[var(--text-secondary)] mt-1">可视化拖拽 · 条件分支 · 多智能体协同 · 调试运行</p>
        </div>
        <Link to="/workflows/new">
          <Button><Plus className="w-4 h-4" />新建工作流</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workflows.map((w) => {
          const sm = statusMap[w.status];
          return (
            <div key={w.id} className="bg-[var(--surface-base)] rounded-xl border border-[var(--border-default)] p-5 hover:shadow-md hover:border-brand-300 transition-all group">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-brand-500 to-accent-purple-500 flex items-center justify-center shrink-0">
                  <Workflow className="w-5 h-5 text-white" />
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sm.cls}`}>{sm.label}</span>
              </div>
              <Link to={`/workflows/${w.id}`} className="block">
                <h3 className="font-semibold text-base mb-1 group-hover:text-brand-600 transition-colors">{w.name}</h3>
                <p className="text-xs text-[var(--text-secondary)] mb-3 line-clamp-2 min-h-[2.5em]">{w.description}</p>
              </Link>
              <div className="flex items-center gap-4 text-xs text-[var(--text-tertiary)] mb-3 pb-3 border-b border-[var(--border-default)]">
                <span>{w.nodeCount} 节点</span>
                <span>·</span>
                <span>{w.runs} 次运行</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1 text-xs text-[var(--text-tertiary)]">
                  <Clock className="w-3 h-3" />
                  {w.lastRun || '尚未运行'}
                </div>
                <div className="flex items-center gap-1">
                  <Link to={`/workflows/${w.id}`} className="p-1.5 hover:bg-[var(--surface-muted)] rounded" aria-label="编辑"><Edit2 className="w-3.5 h-3.5 text-[var(--text-tertiary)]" /></Link>
                  <button className="p-1.5 hover:bg-[var(--surface-muted)] rounded" aria-label="运行"><Play className="w-3.5 h-3.5 text-[var(--text-tertiary)]" /></button>
                  <button className="p-1.5 hover:bg-destructive-bg rounded" aria-label="删除"><Trash2 className="w-3.5 h-3.5 text-[var(--text-tertiary)] hover:text-destructive-600" /></button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
