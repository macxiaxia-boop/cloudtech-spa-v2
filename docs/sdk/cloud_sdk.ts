/**
 * Cloud TypeScript / JavaScript SDK
 * ===================================
 * Phase 48.D87 · TS/JS 客户端 SDK（Cloud API 封装）
 * 基于 OpenAPI 3.0 规范 · 15 个端点全覆盖
 * 红线 #22：实际使用需用户拍板（API key 申请 + 调用额度）
 *
 * 安装：
 *   npm install node-fetch
 *   或
 *   pnpm add node-fetch
 *
 * 使用示例：
 *   import { CloudClient } from './cloud_sdk';
 *
 *   const client = new CloudClient({
 *     baseUrl: 'https://api.cloud.example.com',
 *   });
 *
 *   // 登录
 *   const auth = await client.login('user@example.com', 'password123');
 *   client.setToken(auth.access_token);
 *
 *   // 生成内容
 *   const result = await client.generateContent({
 *     topic: 'OPC 模式适合什么规模的公司',
 *     style_id: 'hermes_governance',
 *     form_id: 'wechat_article',
 *   });
 *   console.log(result.content);
 */

// ============ 类型定义 ============

export interface User {
  id: string;
  email: string;
  role: 'user' | 'admin';
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}

export interface Style {
  id: string;
  name: string;
  description: string;
  emoji: string;
}

export interface GenerateRequest {
  topic: string;
  style_id: string;
  form_id: string;
  max_tokens?: number;
  temperature?: number;
}

export interface GenerateResponse {
  content: string;
  tokens_used: number;
  style_id: string;
  form_id: string;
  redline_violations: string[];
}

export interface TopicDiscoveryRequest {
  industry: 'decoration' | 'medical' | 'saas' | 'retail' | 'education';
  keywords: string[];
  max_results?: number;
}

export interface RepurposeExtractRequest {
  content: string;
  extract_types?: Array<'title' | 'hook' | 'data' | 'case' | 'quote'>;
}

export interface RepurposeRewriteRequest {
  content: string;
  target_form: 'wechat' | 'xiaohongshu' | 'douyin' | 'moments' | 'linkedin';
  max_length?: number;
}

export interface IMChatRequest {
  user_id: string;
  message: string;
  context?: Array<Record<string, unknown>>;
}

export interface ClientConfig {
  baseUrl?: string;
  accessToken?: string;
  timeout?: number;
  maxRetries?: number;
}

// ============ 异常 ============

export class CloudError extends Error {
  readonly code: number;
  readonly request_id: string;

  constructor(message: string, code: number = 0, request_id: string = '') {
    super(message);
    this.name = 'CloudError';
    this.code = code;
    this.request_id = request_id;
  }
}

export class CloudAuthError extends CloudError {
  constructor(message: string, request_id: string = '') {
    super(message, 401, request_id);
    this.name = 'CloudAuthError';
  }
}

export class CloudForbiddenError extends CloudError {
  constructor(message: string, request_id: string = '') {
    super(message, 403, request_id);
    this.name = 'CloudForbiddenError';
  }
}

export class CloudQuotaError extends CloudError {
  constructor(message: string, request_id: string = '') {
    super(message, 402, request_id);
    this.name = 'CloudQuotaError';
  }
}

export class CloudNotFoundError extends CloudError {
  constructor(message: string, request_id: string = '') {
    super(message, 404, request_id);
    this.name = 'CloudNotFoundError';
  }
}

// ============ 客户端 ============

export class CloudClient {
  private baseUrl: string;
  private accessToken?: string;
  private timeout: number;
  private maxRetries: number;

  constructor(config: ClientConfig = {}) {
    this.baseUrl = (config.baseUrl ?? 'https://api.cloud.example.com').replace(/\/$/, '');
    this.accessToken = config.accessToken;
    this.timeout = config.timeout ?? 30000;
    this.maxRetries = config.maxRetries ?? 3;
  }

  setToken(accessToken: string): void {
    this.accessToken = accessToken;
  }

  private async request<T = any>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
    path: string,
    options: {
      json?: Record<string, unknown>;
      params?: Record<string, string | number>;
      authRequired?: boolean;
    } = {},
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (options.params) {
      for (const [k, v] of Object.entries(options.params)) {
        url.searchParams.set(k, String(v));
      }
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (options.authRequired) {
      if (!this.accessToken) {
        throw new CloudAuthError('需要先登录或设置 accessToken');
      }
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    let lastError: Error | null = null;
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        const resp = await fetch(url.toString(), {
          method,
          headers,
          body: options.json ? JSON.stringify(options.json) : undefined,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        const requestId = resp.headers.get('X-Request-ID') ?? '';
        if (resp.status === 401) throw new CloudAuthError(await resp.text(), requestId);
        if (resp.status === 402) throw new CloudQuotaError(await resp.text(), requestId);
        if (resp.status === 403) throw new CloudForbiddenError(await resp.text(), requestId);
        if (resp.status === 404) throw new CloudNotFoundError(await resp.text(), requestId);
        if (!resp.ok) throw new CloudError(`HTTP ${resp.status}`, resp.status, requestId);

        return await resp.json() as T;
      } catch (e: any) {
        lastError = e;
        if (e instanceof CloudError) throw e;  // 业务异常不重试
        if (attempt < this.maxRetries - 1) {
          await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)));  // 指数退避
          continue;
        }
        throw new CloudError(`网络错误: ${e.message}`);
      }
    }
    throw new CloudError(`重试 ${this.maxRetries} 次后失败: ${lastError?.message}`);
  }

  // ===== Auth =====
  async login(email: string, password: string): Promise<LoginResponse> {
    const data = await this.request<LoginResponse>('POST', '/api/v2/auth/login', {
      json: { email, password },
    });
    this.setToken(data.access_token);
    return data;
  }

  // ===== System =====
  async health(): Promise<{ status: string; version: string; uptime_seconds: number; dependencies: Record<string, string> }> {
    return this.request('GET', '/api/v2/health');
  }

  async metrics(): Promise<string> {
    return this.request<string>('GET', '/api/v2/metrics');
  }

  // ===== Content Creation =====
  async listStyles(): Promise<Style[]> {
    return this.request<Style[]>('GET', '/api/v2/create/styles');
  }

  async listForms(): Promise<Array<Record<string, unknown>>> {
    return this.request('GET', '/api/v2/create/forms');
  }

  async generateContent(req: GenerateRequest): Promise<GenerateResponse> {
    return this.request<GenerateResponse>('POST', '/api/v2/create/generate', {
      json: {
        topic: req.topic,
        style_id: req.style_id,
        form_id: req.form_id,
        max_tokens: req.max_tokens ?? 4000,
        temperature: req.temperature ?? 0.7,
      },
    });
  }

  async topicDiscovery(req: TopicDiscoveryRequest): Promise<Array<Record<string, unknown>>> {
    return this.request('POST', '/api/v2/create/topic-discovery', {
      json: {
        industry: req.industry,
        keywords: req.keywords,
        max_results: req.max_results ?? 20,
      },
    });
  }

  // ===== Repurpose =====
  async repurposeExtract(req: RepurposeExtractRequest): Promise<Record<string, unknown>> {
    return this.request('POST', '/api/v2/repurpose/extract', {
      json: {
        content: req.content,
        extract_types: req.extract_types ?? ['title', 'hook', 'data', 'case', 'quote'],
      },
    });
  }

  async repurposeRewrite(req: RepurposeRewriteRequest): Promise<Record<string, unknown>> {
    const payload: Record<string, unknown> = {
      content: req.content,
      target_form: req.target_form,
    };
    if (req.max_length !== undefined) payload.max_length = req.max_length;
    return this.request('POST', '/api/v2/repurpose/rewrite', { json: payload });
  }

  // ===== Admin =====
  async adminDashboard(): Promise<Record<string, unknown>> {
    return this.request('GET', '/api/v2/admin/dashboard', { authRequired: true });
  }

  async adminUsers(search: string = '', page: number = 1, limit: number = 20): Promise<Record<string, unknown>> {
    return this.request('GET', '/api/v2/admin/users', {
      params: { search, page, limit },
      authRequired: true,
    });
  }

  // ===== IM =====
  async imChat(req: IMChatRequest): Promise<Record<string, unknown>> {
    return this.request('POST', '/api/v2/im/chat', {
      json: { user_id: req.user_id, message: req.message, context: req.context ?? [] },
    });
  }

  async imWecomSend(user_id: string, message: string): Promise<Record<string, unknown>> {
    return this.request('POST', '/api/v2/im/wecom/send', {
      json: { user_id, message },
    });
  }
}

// ============ 便捷函数 ============

let _defaultClient: CloudClient | null = null;

export function getDefaultClient(): CloudClient {
  if (!_defaultClient) {
    _defaultClient = new CloudClient();
  }
  return _defaultClient;
}

export async function quickGenerate(
  topic: string,
  style_id: string = 'hermes_governance',
  form_id: string = 'wechat_article',
): Promise<string> {
  const client = getDefaultClient();
  const result = await client.generateContent({ topic, style_id, form_id });
  return result.content;
}

export default CloudClient;
