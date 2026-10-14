/** CloudTech Workflows: live V4 contracts and tenant-scoped run records. */
import { useEffect, useState } from 'react';
import { Workflow, RefreshCw, FileText, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { workPathClient } from '@/lib/workpath-client';
import { useTranslation } from '@/i18n';
import { SubtitleExportTool } from '@/components/workflows/SubtitleExportTool';

type PathDefinition = {
  id: string; title: string; goal: string; domain: string; revision: number;
  inputs: Array<{ role: string; min: number; max: number }>;
  steps: Array<{ id: string; operation: string }>;
};

type RunRecord = {
  run_id: string; path_id: string; tenant_id: string;
  status: string; created_at: string;
};

type ArticlePreview = {
  title: string; text: string; images: unknown[]; videos: unknown[];
  content_sha256: string; mock: boolean; saved: boolean;
};

export function WorkflowsPage() {
  const { t } = useTranslation();
  const [paths, setPaths] = useState<PathDefinition[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [workerConnected, setWorkerConnected] = useState(false);
  const [runStorage, setRunStorage] = useState('UNKNOWN');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [html, setHtml] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [article, setArticle] = useState<ArticlePreview | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState('');
  const [lastRunId, setLastRunId] = useState('');
  const [lastRunStorage, setLastRunStorage] = useState('');
  const [queuedRunId, setQueuedRunId] = useState('');
  const [queueState, setQueueState] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const [definitions, currentRuns] = await Promise.all([
        workPathClient.listPaths(), workPathClient.listRuns(),
      ]);
      setPaths(definitions.workpaths);
      setRuns(currentRuns.items);
      setWorkerConnected(currentRuns.worker_connected);
      setRunStorage(currentRuns.storage);
    } catch (err) {
      setPaths([]);
      setRuns([]);
      setError(err instanceof Error ? err.message : 'V4 服务不可用');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function extractHTML() {
    setExtracting(true);
    setExtractError('');
    setArticle(null);
    setLastRunId('');
    setLastRunStorage('');
    try {
      if (new TextEncoder().encode(html).length > 1_800_000) {
        throw new Error('HTML 不得超过 1.8MB');
      }
      const created = await workPathClient.createRun({
        path_id: 'WP-LOCAL-ARTICLE-EXTRACT',
        revision: 1,
        input_bindings: { html, source_url: sourceUrl },
      });
      setLastRunId(created.run_id);
      const executed = await workPathClient.executeLocalRun(created.run_id);
      if (executed.status !== 'COMPLETED' || executed.nodes.length !== 1) {
        throw new Error('任务没有可靠的单节点完成证据');
      }
      const output = executed.nodes[0].output_ref;
      if (!output || output.mock !== false || !output.content_sha256) {
        throw new Error('输出内容缺少来源哈希或不是实际提取结果');
      }
      setArticle({ ...output, saved: executed.storage === 'SQLITE_LOCAL_DURABLE' });
      setLastRunStorage(executed.storage || 'UNKNOWN');
      await refresh();
    } catch (err) {
      setExtractError(err instanceof Error ? err.message : '任务执行失败');
    } finally {
      setExtracting(false);
    }
  }

  async function enqueueHTML() {
    setExtracting(true);
    setExtractError('');
    setArticle(null);
    try {
      if (new TextEncoder().encode(html).length > 1_800_000) {
        throw new Error('HTML 不得超过 1.8MB');
      }
      const created = await workPathClient.createRun({
        path_id: 'WP-LOCAL-ARTICLE-EXTRACT',
        revision: 1,
        input_bindings: { html, source_url: sourceUrl },
      });
      const queued = await workPathClient.enqueueLocalRun(created.run_id);
      setLastRunId(created.run_id);
      setLastRunStorage(queued.storage);
      setQueuedRunId(created.run_id);
      setQueueState(queued.state);
      await refresh();
    } catch (err) {
      setExtractError(err instanceof Error ? err.message : '任务入队失败');
    } finally {
      setExtracting(false);
    }
  }

  useEffect(() => {
    if (!queuedRunId) return;
    let alive = true;
    const check = async () => {
      try {
        const state = await workPathClient.getLocalQueueStatus(queuedRunId);
        if (!alive) return;
        setQueueState(state.state);
        if (state.state === 'DONE') {
          const record = await workPathClient.getRun(queuedRunId);
          if (!alive) return;
          const nodes = record.nodes as Array<{
            status: string;
            output_ref?: ArticlePreview;
          }> | undefined;
          const extracted = nodes?.length === 1 ? nodes[0].output_ref : undefined;
          if (record.status !== 'COMPLETED' ||
              nodes?.[0]?.status !== 'COMPLETED' ||
              extracted?.mock !== false || !extracted?.content_sha256) {
            throw new Error('Worker 已结束但结果缺少可验证的持久化凭证');
          }
          setArticle({ ...extracted, saved: lastRunStorage === 'SQLITE_LOCAL_DURABLE' });
          setQueuedRunId('');
          await refresh();
        } else if (state.state === 'FAILED') {
          setExtractError(`Worker 失败：${state.error_code || '未知错误'}，请查看本地操作日志`);
          setQueuedRunId('');
          await refresh();
        }
      } catch (err) {
        if (alive) {
          setExtractError(err instanceof Error ? err.message : '无法查询队列状态');
          setQueuedRunId('');
        }
      }
    };
    void check();
    const timer = window.setInterval(() => void check(), 3000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [queuedRunId]);

  const selected = paths.find((path) => path.id === selectedPath);
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold">{t('nav.workflows')}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            来自 CloudTech V4 的真实路径定义、实际创建的任务和明确的功能阻断
          </p>
        </div>
        <Button type="button" variant="outline" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw className="w-4 h-4" /> 刷新真实状态
        </Button>
      </div>

      <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm space-y-1">
        <p className="font-medium">运行底座：{workerConnected ? 'Worker 已连接' : 'Worker 尚未连接'}</p>
        <p className="text-muted-foreground">
          任务存储：{runStorage}。未接入持久化和执行器之前，创建记录不等于完成 AI 业务。
        </p>
      </div>

      {error && (
        <p role="alert" className="border border-destructive-200 rounded-lg p-3 text-sm text-destructive-700">
          <AlertTriangle className="inline w-4 h-4 mr-2" />{error}
        </p>
      )}
      {loading && <p role="status" className="text-sm text-muted-foreground">正在读取实际工作流…</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {paths.map((path) => (
          <Card key={path.id} className="p-0">
            <CardContent className="p-5 space-y-3">
              <div className="flex justify-between items-start gap-3">
                <Workflow className="w-7 h-7 text-brand-600 shrink-0" />
                <span className="text-xs rounded bg-muted px-2 py-1">契约 v{path.revision}</span>
              </div>
              <h2 className="font-semibold">{path.title}</h2>
              <p className="text-sm text-muted-foreground">{path.goal}</p>
              <p className="text-xs text-muted-foreground">
                {path.inputs.length} 个输入角色 · {path.steps.length} 个节点 ·
                本租户已创建 {runs.filter((r) => r.path_id === path.id).length} 条任务记录
              </p>
              <Button type="button" variant="outline" size="sm"
                      onClick={() => setSelectedPath(selectedPath === path.id ? null : path.id)}>
                {selectedPath === path.id ? '收起契约' : '查看真实节点与输入'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {selected && (
        <Card>
          <CardContent className="p-5 space-y-3">
            <h2 className="font-semibold">{selected.title} — 源码契约</h2>
            <p className="text-sm">输入：
              {selected.inputs.map((x) => `${x.role} [${x.min}-${x.max}]`).join('，') || '无'}
            </p>
            <ol className="list-decimal pl-5 text-sm text-muted-foreground space-y-1">
              {selected.steps.map((step) => (
                <li key={step.id}>{step.id}：{step.operation}</li>
              ))}
            </ol>
            <p className="text-xs text-muted-foreground">契约存在不代表执行器已经运行以上节点。</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-5 space-y-3">
          <h2 className="font-semibold">当前租户任务记录</h2>
          {runs.length ? (
            <ul className="space-y-2 text-sm">
              {runs.map((run) => (
                <li key={run.run_id} className="border-b border-border pb-2">
                  <strong>{run.path_id}</strong> · {run.status}
                  <span className="block text-xs text-muted-foreground">
                    {run.run_id} · {run.created_at}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              未读取到实际任务记录；不会生成演示运行次数或伪造最近执行时间。
            </p>
          )}
        </CardContent>
      </Card>

      <SubtitleExportTool />

      <Card>
        <CardContent className="p-5 space-y-3">
          <h2 className="font-semibold flex gap-2 items-center">
            <FileText className="w-5 h-5" /> 用户 HTML 素材提取
          </h2>
          <p className="text-sm text-muted-foreground">
            将你有权处理的 HTML 提交给 CloudTech 任务引擎：记录任务、执行本地解析、
            保存原文及媒体引用、可从任务记录重新读取。不抓取外部网页、不调用模型。
            输入会存放在当前租户的任务存储中；不要粘贴未授权或含密钥的内容。
          </p>
          <label htmlFor="ct-article-source" className="text-sm font-medium">原文来源 URL（可选）</label>
          <input id="ct-article-source" value={sourceUrl}
                 onChange={(e) => setSourceUrl(e.target.value)}
                 className="w-full border border-border rounded p-2 text-sm"
                 placeholder="https://example.com/article" />
          <label htmlFor="ct-article-html" className="text-sm font-medium">HTML 内容</label>
          <textarea id="ct-article-html" value={html}
                    onChange={(e) => setHtml(e.target.value)}
                    rows={6} className="w-full border border-border rounded p-3 text-sm"
                    placeholder="<article>...</article>" />
          <div className="flex flex-wrap gap-2">
            <Button type="button"
                    disabled={extracting || !!queuedRunId || !html.trim() ||
                              runStorage !== 'SQLITE_LOCAL_DURABLE'}
                    onClick={() => void enqueueHTML()}>
              {queuedRunId ? 'Worker 任务处理中…' : '提交独立 Worker 队列'}
            </Button>
            <Button type="button" variant="outline"
                    disabled={extracting || !!queuedRunId || !html.trim()}
                    onClick={() => void extractHTML()}>
              {extracting ? '正在执行任务…' : '在 API 内同步执行（测试）'}
            </Button>
          </div>
          {runStorage !== 'SQLITE_LOCAL_DURABLE' && (
            <p role="status" className="text-xs text-muted-foreground">
              独立 Worker 队列需要服务端单机事务存储；当前仅允许测试同步执行。
            </p>
          )}
          {queuedRunId && (
            <p role="status" className="text-sm text-muted-foreground">
              已进入真实队列：{queueState || '读取中'}。
              {workerConnected ? '正在等待已检测到的 Worker。' :
                '尚未检测到常驻 Worker，任务会保留在队列中。'}
            </p>
          )}
          {extractError && <p role="alert" className="text-sm text-destructive-600">{extractError}</p>}
          {lastRunId && (
            <p className="text-xs text-muted-foreground break-all">
              任务：{lastRunId} · 存储：{lastRunStorage || '未确认'}
            </p>
          )}
          {article && (
            <section className="border border-border rounded p-4 text-sm space-y-2">
              <h3 className="font-semibold">{article.title || '无标题'}</h3>
              <p className="text-muted-foreground whitespace-pre-wrap">{article.text.slice(0, 2000)}</p>
              <p>图片引用：{article.images.length} · 视频引用：{article.videos.length}</p>
              <p className="text-xs text-muted-foreground break-all">
                来源摘要：{article.content_sha256} ·
                任务结果：{article.saved ? '已写入单机事务数据库' : '仅临时保存，尚无持久化保证'}
                · 尚未建立独立素材资产版本
              </p>
            </section>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
