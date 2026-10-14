/** CloudTech Workspace selection — show only the verified SaaS tenant. */
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Building2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';

export function WorkspaceSelectorPage() {
  const navigate = useNavigate();
  const { user, currentWorkspace, setCurrentWorkspace, logout } = useAuth();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6"
         style={{ background: 'var(--gradient-ice)' }}>
      <div className="w-full max-w-lg bg-card rounded-xl shadow-xl border border-border p-8">
        <h1 className="text-2xl font-bold mb-2">企业工作空间</h1>
        <p className="text-sm text-muted-foreground mb-6">
          仅显示后端已核验身份、租户归属的工作空间；不会加载演示组织。
        </p>
        {user && currentWorkspace ? (
          <button
            type="button"
            onClick={() => {
              setCurrentWorkspace(currentWorkspace);
              navigate('/dashboard');
            }}
            className="w-full flex items-center gap-4 border border-border rounded-lg
                       p-4 hover:border-brand-500 text-left"
          >
            <Building2 className="w-8 h-8 text-brand-600 shrink-0" />
            <span className="flex-1 min-w-0">
              <strong className="block truncate">{currentWorkspace.name}</strong>
              <span className="text-sm text-muted-foreground block truncate">
                企业 ID：{currentWorkspace.id}
              </span>
              <span className="text-xs text-muted-foreground block mt-1">{user.email}</span>
            </span>
            <ArrowRight className="w-5 h-5 text-muted-foreground" />
          </button>
        ) : (
          <p role="alert" className="text-sm text-destructive-600">
            未获取到经过服务器验证的企业身份，请重新登录。
          </p>
        )}
        <div className="mt-6 flex justify-end">
          <Button type="button" variant="outline" onClick={handleLogout}>切换账号</Button>
        </div>
      </div>
    </div>
  );
}
