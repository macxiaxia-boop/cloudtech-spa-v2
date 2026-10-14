/** CloudTech SaaS identity — signed backend session, no fake browser admins. */
import { createContext, useContext, useEffect, useState, type ReactNode, useCallback } from 'react';
import { checkBackendHealth, setUnauthorizedHandler } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: 'admin' | 'member' | 'guest';
}

export interface Workspace {
  id: string;
  name: string;
  description: string;
  memberCount: number;
  role: '管理员' | '团队成员' | '数据观察';
}

interface AuthState {
  user: User | null;
  currentWorkspace: Workspace | null;
  isAuthenticated: boolean;
  loading: boolean;
  backendOnline: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  register: (email: string, password: string, company: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
  setCurrentWorkspace: (ws: Workspace) => void;
  refreshBackend: () => Promise<void>;
}

type VerifiedSession = {
  verified: true;
  user_id: string;
  email: string;
  tenant_id: string;
  workspace_name: string;
  role: string;
};

type AuthToken = { token: string; tenant_id: string };

const AuthContext = createContext<AuthContextValue | null>(null);
const TOKEN_KEY = 'ct.auth.session';
const TENANT_KEY = 'ct.auth.tenant_id';

function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TENANT_KEY);
  // Old browser-local fake identities must never grant access.
  localStorage.removeItem('ct.auth.user');
  localStorage.removeItem('ct.auth.workspace');
}

async function verifySession(token: string): Promise<VerifiedSession> {
  const response = await fetch('/api/saas/v1/me', {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('会话无效、已过期或所属企业无访问权限');
  const data: VerifiedSession = await response.json();
  if (!data.verified || !data.user_id || !data.tenant_id || !data.email) {
    throw new Error('认证服务未返回可验证的用户和租户信息');
  }
  return data;
}

async function submitCredentials(endpoint: 'login' | 'register', body: object): Promise<AuthToken> {
  const response = await fetch(`/api/saas/v1/${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error('邮箱或密码错误');
    if (response.status === 409) throw new Error('该邮箱已经注册');
    if (response.status === 503) throw new Error('认证服务尚未完成安全配置');
    throw new Error(`认证服务请求失败（HTTP ${response.status}）`);
  }
  const payload = await response.json();
  if (payload.status !== 'ok' || typeof payload.token !== 'string' ||
      typeof payload.tenant_id !== 'string') {
    throw new Error('服务器没有返回有效登录凭证');
  }
  return { token: payload.token, tenant_id: payload.tenant_id };
}

function profileFromVerified(data: VerifiedSession): { user: User; workspace: Workspace } {
  return {
    user: {
      id: data.user_id, email: data.email,
      name: data.email.split('@')[0] || '成员', role: 'member',
    },
    workspace: {
      id: data.tenant_id, name: data.workspace_name || '我的企业',
      description: '已验证的企业工作空间', memberCount: 1,
      role: '团队成员',
    },
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);

  const acceptVerified = useCallback((data: VerifiedSession) => {
    const profile = profileFromVerified(data);
    setUser(profile.user);
    setCurrentWorkspaceState(profile.workspace);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    setCurrentWorkspaceState(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    let active = true;
    (async () => {
      // Public pages must not auto-probe a backend that is not mounted in
      // static preview. This keeps the unknown/offline state fail-closed.
      // Signed session verification, login/register and explicit refresh
      // still surface real upstream failures instead of returning mock data.
      let verified = false;
      try {
        const token = sessionStorage.getItem(TOKEN_KEY);
        if (token) {
          const data = await verifySession(token);
          verified = true;
          if (active) {
            sessionStorage.setItem(TENANT_KEY, data.tenant_id);
            acceptVerified(data);
          }
        } else {
          clearSession();
        }
      } catch {
        if (active) logout();
      } finally {
        if (active) setLoading(false);
      }
      if (active && verified) {
        const online = await checkBackendHealth().catch(() => false);
        if (active) setBackendOnline(online);
      } else if (active) {
        setBackendOnline(false);
      }
    })();
    return () => { active = false; };
  }, [acceptVerified, logout]);

  const refreshBackend = useCallback(async () => {
    const online = await checkBackendHealth().catch(() => false);
    setBackendOnline(online);
  }, []);

  const setCurrentWorkspace = useCallback((ws: Workspace) => {
    // A client-side workspace choice must not override a server-verified tenant.
    const signedTenant = sessionStorage.getItem(TENANT_KEY);
    if (!signedTenant || signedTenant !== ws.id) return;
    setCurrentWorkspaceState(ws);
  }, []);

  const authenticate = useCallback(async (
    endpoint: 'login' | 'register', body: object,
  ): Promise<{ ok: boolean; error?: string }> => {
    try {
      const session = await submitCredentials(endpoint, body);
      const verified = await verifySession(session.token);
      if (session.tenant_id !== verified.tenant_id) {
        throw new Error('登录响应与验证后的租户不一致');
      }
      sessionStorage.setItem(TOKEN_KEY, session.token);
      sessionStorage.setItem(TENANT_KEY, verified.tenant_id);
      acceptVerified(verified);
      return { ok: true };
    } catch (error) {
      logout();
      return { ok: false, error: error instanceof Error ? error.message : '认证失败' };
    }
  }, [acceptVerified, logout]);

  const login = useCallback(async (email: string, password: string) => {
    if (!email || !password) return { ok: false, error: '邮箱和密码不能为空' };
    return authenticate('login', { email, password });
  }, [authenticate]);

  const register = useCallback(async (email: string, password: string, company: string) => {
    if (!email || !password || !company) return { ok: false, error: '所有字段必填' };
    return authenticate('register', { email, password, tenant_name: company });
  }, [authenticate]);

  return (
    <AuthContext.Provider value={{
      user, currentWorkspace, isAuthenticated: !!user,
      loading, backendOnline, login, register, logout,
      setCurrentWorkspace, refreshBackend,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
