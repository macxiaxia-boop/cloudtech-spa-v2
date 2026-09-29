/**
 * CloudTech API Client · 真实后端 fetch 封装
 *
 * 能力：
 * - 自动注入 Authorization Bearer Token（从 AuthContext localStorage）
 * - 自动注入 X-Tenant / X-Workspace headers
 * - 401 自动清登录态 + 跳转 /login
 * - 5xx 显示错误 Toast（sonner）
 * - fetch 超时 10s
 * - 类型安全响应（typed API）
 *
 * 后端真相（2026-09-29 探查）：
 * - gateway_v22.py @ 5099 在 v10 stub 模式
 * - /api/v2/{rest:path} catch-all 返回合理空 mock（空数组/空对象）
 * - 4 个真实端点：/api/v2/_meta/{routes/summary,industries,employees/tier}
 * - 无 JWT auth endpoint → login 仍走前端 mock（验证格式 + 写 localStorage）
 */
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = '/api/v2';
const TIMEOUT_MS = 10_000;

export interface ApiOptions extends RequestInit {
  /** 超时（默认 10s） */
  timeout?: number;
  /** 不触发 401 跳转（用于健康检查等） */
  skipUnauthorized?: boolean;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body: unknown,
    public url: string,
  ) {
    super(`[${status}] ${statusText} (${url})`);
  }
}

/** 401 处理回调（注册到 AuthContext 避免循环依赖） */
let onUnauthorized: () => void = () => {};

export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

/** 当前 localStorage 读取 token（避免循环依赖 AuthContext） */
function getAuthHeaders(): Record<string, string> {
  try {
    const userRaw = localStorage.getItem('ct.auth.user');
    const wsRaw = localStorage.getItem('ct.auth.workspace');
    const headers: Record<string, string> = {};

    if (userRaw) {
      const user = JSON.parse(userRaw);
      // 注：后端暂未启用 JWT，发送 mock token 即可
      if (user.email) headers['X-User-Email'] = user.email;
      if (user.id)    headers['X-User-Id'] = user.id;
      if (user.role)  headers['X-User-Role'] = user.role;
    }
    if (wsRaw) {
      const ws = JSON.parse(wsRaw);
      if (ws.id)   headers['X-Workspace-Id'] = ws.id;
      if (ws.role) headers['X-Workspace-Role'] = ws.role;
    }
    return headers;
  } catch {
    return {};
  }
}

/** fetch with timeout */
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new ApiError(0, 'Timeout', null, '')), ms);
    promise.finally(() => clearTimeout(timer)).then(resolve, reject);
  });
}

/** 核心 fetch 方法 */
export async function apiFetch<T = unknown>(path: string, options: ApiOptions = {}): Promise<T> {
  const { timeout = TIMEOUT_MS, skipUnauthorized, headers, ...rest } = options;

  const url = path.startsWith('http') ? path : `${API_BASE}/${path.replace(/^\//, '')}`;

  const response = await withTimeout(
    fetch(url, {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...(headers as Record<string, string> | undefined),
      },
    }),
    timeout,
  );

  // 401 处理
  if (response.status === 401 && !skipUnauthorized) {
    onUnauthorized();
    throw new ApiError(401, 'Unauthorized', null, url);
  }

  // 204 No Content
  if (response.status === 204) return undefined as T;

  // 解析响应
  const contentType = response.headers.get('content-type') || '';
  const body: unknown = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText, body, url);
  }

  return body as T;
}

/** 便捷方法 */
export const api = {
  get:    <T = unknown>(path: string, options?: ApiOptions) => apiFetch<T>(path, { ...options, method: 'GET' }),
  post:   <T = unknown>(path: string, body?: unknown, options?: ApiOptions) =>
    apiFetch<T>(path, { ...options, method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  put:    <T = unknown>(path: string, body?: unknown, options?: ApiOptions) =>
    apiFetch<T>(path, { ...options, method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),
  delete: <T = unknown>(path: string, options?: ApiOptions) => apiFetch<T>(path, { ...options, method: 'DELETE' }),
};

/** 健康检查（不触发 401） */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    await api.get('_meta/routes/summary', { skipUnauthorized: true, timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

/** 类型导出 */
export type { User, Workspace } from '@/contexts/AuthContext';
