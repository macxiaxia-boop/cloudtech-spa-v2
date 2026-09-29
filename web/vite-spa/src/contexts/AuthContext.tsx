/**
 * CloudTech AuthContext · 真实登录态（localStorage 持久化）
 *
 * 用法：
 *   const { user, currentWorkspace, login, logout, setCurrentWorkspace } = useAuth();
 *   await login(email, password); // 模拟：500ms 后返回 mock JWT
 *   logout(); // 清 localStorage + 跳转 /login
 *
 * 未来可平滑替换为真实 JWT 接入（仅需替换 mockApiCall 为 fetch）
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

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
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  register: (email: string, password: string, company: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
  setCurrentWorkspace: (ws: Workspace) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEYS = {
  user: 'ct.auth.user',
  workspace: 'ct.auth.workspace',
} as const;

function loadFromStorage<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function saveToStorage(key: string, value: unknown) {
  try {
    if (value === null || value === undefined) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch { /* quota exceeded 等异常忽略 */ }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(true);

  // 启动时从 localStorage 恢复
  useEffect(() => {
    const savedUser = loadFromStorage<User>(STORAGE_KEYS.user);
    const savedWorkspace = loadFromStorage<Workspace>(STORAGE_KEYS.workspace);
    if (savedUser) setUser(savedUser);
    if (savedWorkspace) setCurrentWorkspaceState(savedWorkspace);
    setLoading(false);
  }, []);

  const setCurrentWorkspace = (ws: Workspace) => {
    setCurrentWorkspaceState(ws);
    saveToStorage(STORAGE_KEYS.workspace, ws);
  };

  const login = async (email: string, password: string) => {
    if (!email || !password) return { ok: false, error: '邮箱和密码不能为空' };
    if (password.length < 6) return { ok: false, error: '密码至少 6 位' };

    // 模拟 API 调用（P1+ 替换为真实 fetch /api/v2/auth/login）
    await new Promise((resolve) => setTimeout(resolve, 400));

    const mockUser: User = {
      id: 'u_' + Date.now().toString(36),
      email,
      name: email.split('@')[0] || 'User',
      role: 'admin',
    };
    setUser(mockUser);
    saveToStorage(STORAGE_KEYS.user, mockUser);
    return { ok: true };
  };

  const register = async (email: string, password: string, company: string) => {
    if (!email || !password || !company) return { ok: false, error: '所有字段必填' };
    if (password.length < 6) return { ok: false, error: '密码至少 6 位' };

    await new Promise((resolve) => setTimeout(resolve, 500));

    const mockUser: User = {
      id: 'u_' + Date.now().toString(36),
      email,
      name: email.split('@')[0] || company,
      role: 'admin',
    };
    setUser(mockUser);
    saveToStorage(STORAGE_KEYS.user, mockUser);
    return { ok: true };
  };

  const logout = () => {
    setUser(null);
    setCurrentWorkspaceState(null);
    saveToStorage(STORAGE_KEYS.user, null);
    saveToStorage(STORAGE_KEYS.workspace, null);
  };

  return (
    <AuthContext.Provider value={{
      user,
      currentWorkspace,
      isAuthenticated: !!user,
      loading,
      login,
      register,
      logout,
      setCurrentWorkspace,
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
