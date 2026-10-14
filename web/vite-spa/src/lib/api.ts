/** CloudTech same-origin API. Refuses external-token leakage and aborts timeouts. */
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
  // Browser-supplied user IDs and role headers are not authentication.
  const token = sessionStorage.getItem('ct.auth.session');
  const tenantId = sessionStorage.getItem('ct.auth.tenant_id');
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (tenantId) headers['X-Tenant-Id'] = tenantId;
  return headers;

}

/** API session credentials must never leave the internal API path. */
function internalApiPath(path: string): string {
  if (!path || path.trim() !== path || path.includes('\\') ||
      /[\u0000-\u001f\u007f]/.test(path) ||
      /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(path)) {
    throw new ApiError(0, 'External or invalid API URL blocked', null, String(path));
  }
  const suffix = path.replace(/^\/+/, '');
  const pathname = suffix.split(/[?#]/, 1)[0];
  if (!pathname || pathname.split('/').some((part) => {
    let decoded: string;
    try { decoded = decodeURIComponent(part); } catch { return true; }
    return decoded === '.' || decoded === '..';
  })) {
    throw new ApiError(0, 'Invalid API path', null, path);
  }
  return API_BASE + '/' + suffix;
}

/** Abort the actual fetch on timeout, not just a Promise waiting for it. */
async function requestWithTimeout(url: string, init: RequestInit, ms: number): Promise<Response> {
  if (!Number.isFinite(ms) || ms <= 0 || ms > 120_000) {
    throw new ApiError(0, 'Invalid API timeout', null, url);
  }
  const aborter = new AbortController();
  const caller = init.signal;
  const onAbort = () => aborter.abort();
  if (caller?.aborted) aborter.abort();
  else caller?.addEventListener('abort', onAbort, { once: true });
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    aborter.abort();
  }, ms);
  try {
    return await fetch(url, {
      ...init,
      redirect: 'error',
      signal: aborter.signal,
    });
  } catch (error) {
    if (timedOut) throw new ApiError(0, 'Timeout', null, url);
    throw error;
  } finally {
    clearTimeout(timer);
    caller?.removeEventListener('abort', onAbort);
  }
}

/** 核心 fetch 方法 */
export async function apiFetch<T = unknown>(path: string, options: ApiOptions = {}): Promise<T> {
  const { timeout = TIMEOUT_MS, skipUnauthorized, headers, ...rest } = options;

  const url = internalApiPath(path);
  const response = await requestWithTimeout(url, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(headers as Record<string, string> | undefined),
    },
  }, timeout);

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
