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

  async listPaths(): Promise<{
    total_paths: number;
    workpaths: Array<{
      id: string; title: string; goal: string; domain: string; revision: number;
      inputs: Array<{ role: string; min: number; max: number }>;
      steps: Array<{ id: string; operation: string }>;
    }>;
  }> {
    return this.get('/operations');
  }

  async getLocalOutputByRun(runId: string): Promise<{
    item: {
      run_id: string; node_id: string; path_id: string;
      artifact_kind: string; source_sha256: string; output_sha256: string;
      created_at: string;
    };
    source: 'verified_local_outbox_catalog';
    raw_customer_content_in_response: false;
    production_ready: false;
  }> {
    return this.get(`/workpaths/local-outputs/${encodeURIComponent(runId)}`);
  }

  async listLocalOutputs(): Promise<{
    items: Array<{
      run_id: string; node_id: string; path_id: string;
      artifact_kind: string; source_sha256: string;
      output_sha256: string; created_at: string;
    }>;
    returned: number;
    source: string;
    raw_customer_content_in_response: false;
    production_ready: false;
  }> {
    return this.get('/workpaths/local-outputs');
  }

  async listRuns(): Promise<{
    items: Array<{
      run_id: string; path_id: string; tenant_id: string;
      status: string; created_at: string;
    }>;
    storage: string; worker_connected: boolean; production_ready: boolean;
  }> {
    return this.get('/workpaths/runs');
  }

  async enqueueLocalRun(runId: string): Promise<{
    run_id: string; state: string; queued_only: boolean;
    worker_invoked: boolean; storage: string; idempotent_hit: boolean;
  }> {
    return this.post(`/workpaths/runs/${encodeURIComponent(runId)}/enqueue-local`, {});
  }

  async getLocalQueueStatus(runId: string): Promise<{
    run_id: string; state: 'QUEUED' | 'LEASED' | 'DONE' | 'FAILED';
    attempts: number; max_attempts: number; error_code: string | null;
    worker_connected: boolean;
  }> {
    return this.get(`/workpaths/runs/${encodeURIComponent(runId)}/local-queue`);
  }

  async executeLocalRun(runId: string): Promise<{
    run_id: string;
    status: string;
    idempotent_hit?: boolean;
    worker_type?: string;
    provider_called?: boolean;
    cost_cents?: number;
    storage?: string;
    nodes: Array<{
      node_id: string;
      status: string;
      output_ref?: {
        title: string; text: string; images: unknown[]; videos: unknown[];
        content_sha256: string; mock: boolean;
      };
    }>;
  }> {
    return this.post(`/workpaths/runs/${encodeURIComponent(runId)}/execute-local`, {});
  }

  async reconcileLocalRun(runId: string): Promise<{
    run_id: string; status: string; reconciled: boolean;
    provider_recalled?: boolean; new_charge_cents?: number;
  }> {
    return this.post(`/workpaths/runs/${encodeURIComponent(runId)}/reconcile-local`, {});
  }

  async extractSuppliedHTML(html: string, sourceUrl: string): Promise<{
    title: string; text: string; images: unknown[]; videos: unknown[];
    content_sha256: string; mock: boolean; saved: boolean;
  }> {
    return this.post('/article/extract-html', { html, source_url: sourceUrl });
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
