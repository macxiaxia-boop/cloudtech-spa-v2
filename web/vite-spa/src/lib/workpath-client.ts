/**
 * CloudTech V4 — 前端 workpath client (TypeScript)
 * 接入 /v4/* FastAPI 端点
 * 红线 #60: 真实调用需 L4 user 拍板 + budget reserve
 */

export type ResolveRequest = {
  utterance: string;
  project_id?: string;
  input_refs: Array<{ role: string; value: string; mime?: string }>;
};

export type WorkPathSummary = {
  path_id: string;
  match_keyword: string | null;
  rank: number;
};

export type ResolveResponse = {
  matched_path_id: string | null;
  candidates: WorkPathSummary[];
  missing_roles: string[];
  reasoning: string;
};

export type CreateRunRequest = {
  path_id: string;
  revision: number;
  input_bindings: Record<string, unknown>;
  scope?: string;
  budget_cap_cents?: number;
  idempotency_key?: string;
  project_id?: string;
  conversation_id?: string;
};

export type ApproveRequest = {
  checkpoint_id: string;
  approved_budget_cents: number;
};

export type BindAliasRequest = {
  tenant_id: string;
  project_id?: string;
  conversation_id: string;
  alias: string;
  role: string;
  asset_id: string;
  version_id: string;
  message_id?: string;
};

export type NewVersionRequest = {
  tenant_id: string;
  project_id?: string;
  conversation_id: string;
  alias: string;
  new_asset_id: string;
  new_version_id: string;
  parent_version_id?: string;
  edit_spec?: Record<string, unknown>;
  source_refs?: string[];
  message_id?: string;
};

const DEFAULT_BASE = '/v4';

export class WorkPathClient {
  constructor(private baseUrl: string = DEFAULT_BASE, private tenantId: string = '') {}

  private requestIdentity(path: string): {
    url: string;
    authHeader: Record<string, string>;
  } {
    const token = sessionStorage.getItem('ct.auth.session');
    const tenant = this.tenantId || sessionStorage.getItem('ct.auth.tenant_id');
    const publicRequest = path === '/workpaths/resolve' || path === '/health';
    if (!publicRequest && (!token || !tenant)) {
      throw new Error('[WorkPathClient] 需要先登录已验证的企业账号');
    }
    const query = !publicRequest && tenant
      ? `${path.includes('?') ? '&' : '?'}tenant_id=${encodeURIComponent(tenant)}`
      : '';
    return {
      url: `${this.baseUrl}${path}${query}`,
      authHeader: token ? { Authorization: `Bearer ${token}` } : {},
    };
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const { url, authHeader } = this.requestIdentity(path);
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeader },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
    if (!response.ok) {
      const txt = await response.text();
      throw new Error(`[WorkPathClient] ${path} → ${response.status} ${txt}`);
    }
    return response.json() as Promise<T>;
  }

  private async get<T>(path: string): Promise<T> {
    const { url, authHeader } = this.requestIdentity(path);
    const response = await fetch(url, { headers: authHeader, cache: 'no-store' });
    if (!response.ok) {
      const txt = await response.text();
      throw new Error(`[WorkPathClient] ${path} → ${response.status} ${txt}`);
    }
    return response.json() as Promise<T>;
  }

  async resolve(req: ResolveRequest): Promise<ResolveResponse> {
    return this.post<ResolveResponse>('/workpaths/resolve', req);
  }

  async createRun(req: CreateRunRequest): Promise<{ run_id: string; status: string; idempotent_hit?: boolean }> {
    return this.post<{ run_id: string; status: string; idempotent_hit?: boolean }>('/workpaths/runs', req);
  }

  async getRun(runId: string): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(`/workpaths/runs/${runId}`);
  }

  async approveRun(runId: string, req: ApproveRequest): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(`/workpaths/runs/${runId}/approve`, req);
  }

  async resumeRun(runId: string, failedNodesOnly: boolean = true): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(`/workpaths/runs/${runId}/resume`, { failed_nodes_only: failedNodesOnly });
  }

  async exportRun(runId: string): Promise<Record<string, unknown>> {
    return this.get<Record<string, unknown>>(`/workpaths/runs/${runId}/export`);
  }

  async resolveAlias(conversationId: string, alias: string): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>('/assets/resolve-alias', { conversation_id: conversationId, alias });
  }

  async bindAlias(req: BindAliasRequest): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>('/assets/bind', req);
  }

  async newAssetVersion(assetId: string, req: NewVersionRequest): Promise<Record<string, unknown>> {
    return this.post<Record<string, unknown>>(`/assets/${assetId}/versions`, req);
  }

  async health(): Promise<{ ok: boolean; paths_registered: number; orchestrator_runs: number }> {
    return this.get<{ ok: boolean; paths_registered: number; orchestrator_runs: number }>('/health');
  }
}

// 默认 singleton
export const workPathClient = new WorkPathClient('/v4', '');
