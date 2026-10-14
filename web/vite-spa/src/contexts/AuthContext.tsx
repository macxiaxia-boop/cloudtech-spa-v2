/** CloudTech PR1: fail-closed frontend shell pending signed server auth integration.
 * A backend health endpoint is never proof that a password was authenticated.
 * PR2 contains the separately reviewed tenant-scoped signed session flow.
 */
import { createContext, useContext, useEffect, useState, type ReactNode, useCallback } from 'react';
import { checkBackendHealth } from '@/lib/api';

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

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEYS = {
  user: 'ct.auth.user',
  workspace: 'ct.auth.workspace',
} as const;

function saveToStorage(key: string, value: unknown) {
  try {
    if (value === null || value === undefined) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch { /* ignore quota */ }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);

  // Clear all historical client-created identities: localStorage cannot
  // prove a signed server session or tenant membership. No API probe is
  // performed for unauthenticated public/preview pages.
  useEffect(() => {
    saveToStorage(STORAGE_KEYS.user, null);
    saveToStorage(STORAGE_KEYS.workspace, null);
    setUser(null);
    setCurrentWorkspaceState(null);
    setBackendOnline(false);
    setLoading(false);
  }, []);

  // 注册 401 处理器（避免循环依赖）
  useEffect(() => {
    // 动态 require 防止循环
    import('@/lib/api').then(({ setUnauthorizedHandler }) => {
      setUnauthorizedHandler(() => {
        setUser(null);
        setCurrentWorkspaceState(null);
        saveToStorage(STORAGE_KEYS.user, null);
        saveToStorage(STORAGE_KEYS.workspace, null);
        // 注意：导航到 /login 由 RequireAuth 处理
      });
    });
  }, []);

  const refreshBackend = useCallback(async () => {
    const ok = await checkBackendHealth();
    setBackendOnline(ok);
  }, []);

  const setCurrentWorkspace = useCallback((ws: Workspace) => {
    setCurrentWorkspaceState(ws);
    saveToStorage(STORAGE_KEYS.workspace, ws);
  }, []);

  // No credential verification endpoint is implemented on this P5 branch.
  // Never mint an admin role from an email pattern or silently sign in offline.
  const login = useCallback(async (_email: string, _password: string) => ({
    ok: false,
    error: '企业登录尚未接通受信任的服务端身份验证，不能使用模拟管理员身份。',
  }), []);

  const register = useCallback(async (_email: string, _password: string, _company: string) => ({
    ok: false,
    error: '企业注册尚未接通受信任的服务端账号创建接口，请联系平台管理员。',
  }), []);

  const logout = useCallback(() => {
    setUser(null);
    setCurrentWorkspaceState(null);
    saveToStorage(STORAGE_KEYS.user, null);
    saveToStorage(STORAGE_KEYS.workspace, null);
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      currentWorkspace,
      isAuthenticated: !!user,
      loading,
      backendOnline,
      login,
      register,
      logout,
      setCurrentWorkspace,
      refreshBackend,
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
