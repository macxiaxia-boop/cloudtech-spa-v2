// 共享组件 · 空状态（带插画占位 + 主 CTA）
import { ReactNode } from 'react';
import { Sparkles } from 'lucide-react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  desc: string;
  cta?: ReactNode;
  illustration?: 'rocket' | 'chart' | 'team' | 'doc' | 'chat' | 'money';
}

const ILLUSTRATIONS: Record<string, string> = {
  rocket: '🚀',
  chart: '📊',
  team: '👥',
  doc: '📄',
  chat: '💬',
  money: '💰',
};

export function EmptyState({ icon, title, desc, cta, illustration = 'rocket' }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="text-6xl mb-4">{icon || ILLUSTRATIONS[illustration]}</div>
      <h3 className="text-xl font-bold text-gray-900 mb-2">{title}</h3>
      <p className="text-gray-500 mb-6 max-w-md">{desc}</p>
      {cta && <div>{cta}</div>}
      <p className="text-xs text-gray-400 mt-6 inline-flex items-center gap-1">
        <Sparkles className="w-3 h-3" /> OPC 模式：AI 自动跑出首批数据
      </p>
    </div>
  );
}
