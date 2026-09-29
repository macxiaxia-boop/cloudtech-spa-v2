/**
 * CloudTech WorkspaceSelector · v3 视觉母版 03 模块
 * 选择组织/工作空间（v3 新增 · 多租户隔离入口）· AuthContext 持久化
 */
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Plus, RefreshCw, Cloud, Building2, Briefcase, Users } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

interface Workspace {
  id: string;
  name: string;
  description: string;
  memberCount: number;
  role: '管理员' | '团队成员' | '数据观察';
  iconColor: string;
  icon: React.ComponentType<{ className?: string }>;
}

const workspaces: Workspace[] = [
  { id: 'nova-team',       name: 'Nova Team',  description: 'AI 业务全链路',     memberCount: 12, role: '管理员',   iconColor: 'text-brand-600 bg-brand-50',                 icon: Cloud },
  { id: 'operations',      name: '运营团队',   description: '多人协同 · 监控',   memberCount: 8,  role: '团队成员', iconColor: 'text-success-600 bg-success-50',           icon: Users },
  { id: 'rnd',             name: '研发团队',   description: '技术研发',          memberCount: 16, role: '团队成员', iconColor: 'text-warning-600 bg-warning-50',           icon: Briefcase },
  { id: 'client-projects', name: '客户项目组', description: '多人协同 · 监控',   memberCount: 4,  role: '数据观察', iconColor: 'text-accent-purple-600 bg-accent-purple-50', icon: Building2 },
];

export function WorkspaceSelectorPage() {
  const navigate = useNavigate();
  const { user, setCurrentWorkspace, logout } = useAuth();

  function handleSelect(ws: Workspace) {
    setCurrentWorkspace(ws);
    navigate('/dashboard');
  }

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--gradient-ice)' }}>
      <div className="w-full max-w-[var(--workspace-selector-w)] bg-[var(--surface-base)] rounded-xl shadow-xl border border-[var(--border-default)] p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
              <Cloud className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-semibold text-[var(--text-primary)] text-base">CloudTech</span>
              {user && <div className="text-xs text-[var(--text-tertiary)]">{user.email}</div>}
            </div>
          </div>
          <button onClick={handleLogout} className="text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)]">切换账号</button>
        </div>

        <h1 className="text-2xl font-bold mb-2">选择工作空间</h1>
        <p className="text-sm text-[var(--text-secondary)] mb-6">一个更高效的 AI 工作方式</p>

        <div className="flex flex-col gap-3 mb-6">
          {workspaces.map((ws) => (
            <button key={ws.id} onClick={() => handleSelect(ws)} className="flex items-center gap-4 p-4 rounded-lg border border-[var(--border-default)] hover:border-brand-500 hover:shadow-sm transition-all text-left group">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${ws.iconColor}`}>
                <ws.icon className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-[var(--text-primary)]">{ws.name}</span>
                  <span className="text-xs text-[var(--text-tertiary)]">{ws.memberCount} 人</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--surface-muted)] text-[var(--text-secondary)]">{ws.role}</span>
                </div>
                <p className="text-xs text-[var(--text-tertiary)] mt-0.5">{ws.description}</p>
              </div>
              <ArrowRight className="w-5 h-5 text-[var(--text-tertiary)] group-hover:text-brand-600 group-hover:translate-x-1 transition-all" />
            </button>
          ))}
        </div>

        <div className="flex items-center justify-between pt-4 border-t border-[var(--border-default)]">
          <button className="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-700 transition-colors">
            <Plus className="w-4 h-4" />
            创建新组织
          </button>
          <button onClick={handleLogout} className="flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
            <RefreshCw className="w-4 h-4" />
            切换账号
          </button>
        </div>
      </div>
    </div>
  );
}
