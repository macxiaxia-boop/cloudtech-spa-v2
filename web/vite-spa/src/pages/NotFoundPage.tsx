/**
 * CloudTech NotFoundPage · 404 页面
 */
import { Link } from 'react-router-dom';
import { Home, Search, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-muted">
      <div className="max-w-lg text-center">
        {/* 大字 404 */}
        <div className="text-9xl font-bold bg-gradient-to-br from-brand-500 via-accent-purple-500 to-accent-orange-500 bg-clip-text text-transparent mb-4 leading-none select-none">
          404
        </div>

        <h1 className="text-2xl md:text-3xl font-bold mb-3">页面找不到</h1>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
          抱歉，您访问的页面不存在或已被移除。<br />
          请检查 URL 是否正确，或从下方选择一个方向继续。
        </p>

        {/* 建议操作 */}
        <div className="flex items-center justify-center gap-3 mb-8 flex-wrap">
          <Button onClick={() => window.history.back()}>
            <ArrowLeft className="w-4 h-4" />
            返回上一页
          </Button>
          <Link to="/dashboard">
            <Button variant="outline">
              <Home className="w-4 h-4" />
              前往工作台
            </Button>
          </Link>
        </div>

        {/* 推荐路由 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-2xl mx-auto">
          {[
            { label: 'AI 对话',   href: '/chat',       icon: '💬' },
            { label: '智能体',    href: '/employees',  icon: '🤖' },
            { label: '工作流',    href: '/workflows',  icon: '⚡' },
            { label: '任务中心',  href: '/tasks',      icon: '✓' },
            { label: '知识库',    href: '/knowledge',  icon: '📚' },
            { label: '数据分析',  href: '/analytics',  icon: '📊' },
            { label: '系统设置',  href: '/settings',   icon: '⚙️' },
            { label: '个人中心',  href: '/profile',    icon: '👤' },
          ].map((s) => (
            <Link
              key={s.href}
              to={s.href}
              className="flex flex-col items-center gap-1 p-3 rounded-lg border border-border hover:border-brand-500 hover:shadow-sm transition-all bg-card"
            >
              <span className="text-2xl">{s.icon}</span>
              <span className="text-xs text-muted-foreground">{s.label}</span>
            </Link>
          ))}
        </div>

        {/* 帮助链接 */}
        <div className="mt-8 text-xs text-muted-foreground">
          需要帮助？
          <Link to="/faq" className="text-brand-600 hover:underline mx-1">访问帮助中心</Link>
          或
          <Link to="/" className="text-brand-600 hover:underline mx-1">联系客服</Link>
        </div>
      </div>
    </div>
  );
}
