/**
 * CloudTech AppShell · AppBreadcrumb
 * 基于路由自动生成面包屑
 */
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

const routeLabels: Record<string, string> = {
  dashboard: '工作台',
  chat: 'AI 对话',
  employees: '智能体',
  workflows: '工作流',
  tasks: '任务中心',
  knowledge: '知识库',
  files: '文件管理',
  analytics: '数据分析',
  notifications: '通知中心',
  profile: '个人中心',
  settings: '设置',
  'new': '新建',
  pricing: '定价',
  clients: '客户',
  cases: '案例',
  funnel: '漏斗',
  monitoring: '监控',
  billing: '套餐',
  try: '试用',
  blog: '博客',
  faq: '帮助',
  'opc-story': 'OPC 故事',
  'content-sop': '内容 SOP',
  documents: '文档',
  industries: '行业',
  decoration: '装企',
  medical: '医美',
};

export function AppBreadcrumb() {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter(Boolean);

  if (pathnames.length === 0) return null;

  return (
    <nav className="flex items-center gap-1.5 text-sm text-[var(--text-secondary)] mb-4" aria-label="面包屑">
      <Link
        to="/dashboard"
        className="flex items-center gap-1 hover:text-[var(--text-primary)] transition-colors"
      >
        <Home className="w-4 h-4" />
      </Link>
      {pathnames.map((segment, idx) => {
        const href = '/' + pathnames.slice(0, idx + 1).join('/');
        const isLast = idx === pathnames.length - 1;
        const label = routeLabels[segment] || decodeURIComponent(segment);
        return (
          <span key={href} className="flex items-center gap-1.5">
            <ChevronRight className="w-3.5 h-3.5 text-[var(--text-tertiary)]" />
            {isLast ? (
              <span className="font-medium text-[var(--text-primary)]">{label}</span>
            ) : (
              <Link to={href} className="hover:text-[var(--text-primary)] transition-colors">
                {label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
