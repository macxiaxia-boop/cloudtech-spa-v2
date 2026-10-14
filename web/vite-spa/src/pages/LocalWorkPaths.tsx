/** Actual CloudTech workpath UI — user-supplied content, no paid provider.
 *
 * Create -> durable enqueue -> independent local worker -> exact-run outbox
 * ACK -> authenticated source result. Never equate QUEUED or COMPLETED with
 * independently verified delivery.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { workPathClient } from '@/lib/workpath-client';

type Mode = 'article' | 'subtitle';
type NodeReceipt = { node_id?: string; operation?: string; output_ref?: Record<string, unknown> };
type Run = { run_id: string; status: string; path_id: string; nodes: NodeReceipt[] };
type VerifiedOutput = {
  item: { run_id: string; artifact_kind: string; source_sha256: string; output_sha256: string };
  source: string;
  raw_customer_content_in_response: boolean;
  production_ready: boolean;
};

function downloadText(content: string, fileName: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    link.click();
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

function parseSegments(input: string): Array<{ start_ms: number; end_ms: number; text: string }> {
  let value: unknown;
  try { value = JSON.parse(input); } catch { throw new Error('字幕必须是合法的 JSON 数组'); }
  if (!Array.isArray(value) || value.length < 1 || value.length > 2000) {
    throw new Error('字幕必须是 1–2000 条有时间码的数组');
  }
  let lastEnd = 0;
  const segments: Array<{ start_ms: number; end_ms: number; text: string }> = [];
  for (const item of value) {
    if (!item || typeof item !== 'object') throw new Error('每条字幕必须是对象');
    const row = item as Record<string, unknown>;
    if (typeof row.start_ms !== 'number' || !Number.isInteger(row.start_ms) ||
        typeof row.end_ms !== 'number' || !Number.isInteger(row.end_ms) ||
        row.start_ms < lastEnd || row.end_ms <= row.start_ms ||
        row.end_ms > 86_400_000 || typeof row.text !== 'string' || !row.text.trim()) {
      throw new Error('字幕时间必须递增、不重叠，且每条含有效文本');
    }
    segments.push({ start_ms: row.start_ms, end_ms: row.end_ms, text: row.text.trim() });
    lastEnd = row.end_ms;
  }
  return segments;
}

export function LocalWorkPathsPage() {
  const [mode, setMode] = useState<Mode>('article');
  const [html, setHtml] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [segmentsJson, setSegmentsJson] = useState('');
  const [runId, setRunId] = useState('');
  const [run, setRun] = useState<Run | null>(null);
  const [queue, setQueue] = useState<string>('');
  const [verified, setVerified] = useState<VerifiedOutput | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [polling, setPolling] = useState(false);
  const idem = useRef<string | null>(null);
  const polls = useRef(0);

  const refresh = useCallback(async (id: string) => {
    const record = await workPathClient.getRun(id) as unknown as Run;
    setRun(record);
    if (record.status === 'FAILED' || record.status === 'PARTIAL' ||
        record.status === 'CANCELED' || record.status === 'BLOCKED_PERMISSION') {
      setPolling(false);
      setError('后台任务未完成，需查看运行状态和日志；没有生成已核验产物。');
      return;
    }
    // Even after the worker has committed COMPLETED, the independent output
    // projector may not yet have verified the receipts and ACKed the event.
    if (record.status === 'COMPLETED') {
      try {
        const result = await workPathClient.getLocalOutputByRun(id);
        if (result.item?.run_id !== id ||
            result.source !== 'verified_local_outbox_catalog' ||
            result.raw_customer_content_in_response !== false ||
            !result.item.output_sha256) {
          throw new Error('产物回执未通过来源及完整性验证');
        }
        setVerified(result);
        setPolling(false);
        setError('');
      } catch (exc) {
        if (exc instanceof Error && /→ 404 /.test(exc.message)) return;
        throw exc;
      }
    } else {
      const state = await workPathClient.getLocalQueueStatus(id);
      setQueue(state.state + (state.worker_connected ? ' · Worker 已连接' : ' · Worker 未连接'));
    }
  }, []);

  useEffect(() => {
    if (!runId || !polling || verified) return;
    let active = true;
    const poll = async () => {
      if (!active) return;
      if (++polls.current > 45) {
        if (active) setPolling(false);
        if (active) setError('等待核验超时。任务仍保留在 SQLite 中，可以手动刷新，不会重复创建或重新收费。');
        return;
      }
      try { await refresh(runId); }
      catch (exc) { if (active) setError(exc instanceof Error ? exc.message : '状态查询失败'); }
    };
    void poll();
    const interval = setInterval(() => { void poll(); }, 2000);
    return () => { active = false; clearInterval(interval); };
  }, [runId, polling, verified, refresh]);

  const submit = async () => {
    if (busy) return;
    setError('');
    setBusy(true);
    try {
      const input_bindings: Record<string, unknown> = mode === 'article'
        ? { html, source_url: sourceUrl.trim() }
        : { segments: parseSegments(segmentsJson) };
      if (mode === 'article' && (!html.trim() ||
          new TextEncoder().encode(html).length > 1_800_000 ||
          sourceUrl.length > 2048)) {
        throw new Error('请输入不超过 1.8MB 的已获授权 HTML，来源 URL 最多 2048 字符');
      }
      // Reuse the same idempotency key if the API write times out after the
      // server commits. Reset only for a deliberate new input/new run.
      if (!idem.current) idem.current = crypto.randomUUID();
      const created = await workPathClient.createRun({
        path_id: mode === 'article' ? 'WP-LOCAL-ARTICLE-ANALYZE' : 'WP-LOCAL-SUBTITLE-EXPORT',
        revision: 1,
        scope: 'tenant',
        budget_cap_cents: 0,
        input_bindings,
        idempotency_key: idem.current,
      });
      setRunId(created.run_id);
      setVerified(null);
      const enqueued = await workPathClient.enqueueLocalRun(created.run_id);
      setQueue(enqueued.state + ' · 已提交持久队列，不代表已执行');
      polls.current = 0;
      setPolling(true);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : '提交失败，未确认持久化');
    } finally { setBusy(false); }
  };

  const output = run?.nodes?.at(-1)?.output_ref ?? null;
  const extraction = run?.nodes?.[0]?.output_ref ?? null;
  const canDownload = !!verified && !!output;

  const changeMode = (next: Mode) => {
    setMode(next);
    setRunId('');
    setRun(null);
    setVerified(null);
    setPolling(false);
    setError('');
    idem.current = null;
  };

  return (
    <section className="mx-auto max-w-5xl space-y-6" aria-label="本地真实工作流">
      <div>
        <h1 className="text-2xl font-semibold">本地内容工作流</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          当前只支持用户已提供的 HTML 分析和已有字幕格式化，不执行网页抓取、
          AI 改写、语音识别、付费模型调用或自动发布。需要独立本地 Worker 在线。
        </p>
      </div>
      <div className="rounded-lg border bg-card p-5 space-y-4">
        <div className="flex gap-2">
          <button type="button" onClick={() => changeMode('article')}
            aria-pressed={mode === 'article'}
            className={mode === 'article' ? 'rounded bg-brand-700 px-4 py-2 text-white' : 'rounded border px-4 py-2'}>
            文章正文与结构分析
          </button>
          <button type="button" onClick={() => changeMode('subtitle')}
            aria-pressed={mode === 'subtitle'}
            className={mode === 'subtitle' ? 'rounded bg-brand-700 px-4 py-2 text-white' : 'rounded border px-4 py-2'}>
            已有字幕转 SRT / VTT
          </button>
        </div>
        {mode === 'article' ? (
          <>
            <label className="block text-sm font-medium" htmlFor="article-source">文章来源网址（可选，只作为溯源，不会联网抓取）</label>
            <input id="article-source" type="url" value={sourceUrl}
              onChange={(e) => { setSourceUrl(e.target.value); idem.current = null; }}
              placeholder="https://example.org/your-article"
              className="w-full rounded border bg-background p-3" />
            <label className="block text-sm font-medium" htmlFor="article-html">粘贴已获授权的 HTML 原文</label>
            <textarea id="article-html" value={html}
              onChange={(e) => { setHtml(e.target.value); idem.current = null; }}
              rows={10} placeholder="<article><h1>...</h1><p>...</p></article>"
              className="w-full rounded border bg-background p-3 font-mono text-sm" />
          </>
        ) : (
          <>
            <label className="block text-sm font-medium" htmlFor="segments-json">已有字幕段落（JSON；时间单位毫秒）</label>
            <textarea id="segments-json" value={segmentsJson}
              onChange={(e) => { setSegmentsJson(e.target.value); idem.current = null; }}
              rows={10} placeholder={'[{"start_ms":0,"end_ms":2500,"text":"实际已转写的字幕"}]'}
              className="w-full rounded border bg-background p-3 font-mono text-sm" />
            <p className="text-xs text-muted-foreground">这不是 ASR。请先提供实际转写的文字和时间码。</p>
          </>
        )}
        <button type="button" onClick={() => void submit()} disabled={busy || polling}
          className="rounded bg-brand-700 px-5 py-3 text-white disabled:opacity-50">
          {busy ? '提交中…' : '创建并入队零付费本地任务'}
        </button>
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      </div>
      {runId && (
        <div className="rounded-lg border bg-card p-5 space-y-3">
          <h2 className="text-lg font-semibold">真实执行记录</h2>
          <p className="font-mono text-xs break-all">Run ID: {runId}</p>
          <p className="text-sm">运行状态：{run?.status || '已提交'}；队列：{queue || '查询中'}</p>
          <p className="text-sm">
            独立成果验真：{verified ? '已 ACK，并确认租户归属与输出哈希' : '未完成 / 等待 Outbox 独立验真'}
          </p>
          <button type="button" onClick={() => { polls.current = 0; setPolling(true); void refresh(runId).catch((e) => setError(String(e))); }}
            className="rounded border px-3 py-2" disabled={polling}>刷新真实状态</button>
          {canDownload && (
            <div className="space-y-3 border-t pt-3">
              <p className="text-xs font-mono break-all">来源 SHA-256：{verified.item.source_sha256}</p>
              <p className="text-xs font-mono break-all">输出 SHA-256：{verified.item.output_sha256}</p>
              {mode === 'article' ? (
                <>
                  <h3 className="font-medium">正文与配图（仅展示当前租户自己的结果）</h3>
                  <p className="whitespace-pre-wrap text-sm">{String(extraction?.text ?? '')}</p>
                  <button type="button" className="rounded border px-3 py-2"
                    onClick={() => downloadText(
                      JSON.stringify({ extraction, analysis: output, run_id: runId }, null, 2),
                      runId + '-article-analysis.json', 'application/json;charset=utf-8',
                    )}>下载带来源的 JSON 成果</button>
                </>
              ) : (
                <div className="flex flex-wrap gap-3">
                  <button type="button" className="rounded border px-3 py-2"
                    onClick={() => downloadText(String(output?.srt ?? ''), runId + '.srt', 'text/plain;charset=utf-8')}>
                    下载实际 SRT
                  </button>
                  <button type="button" className="rounded border px-3 py-2"
                    onClick={() => downloadText(String(output?.vtt ?? ''), runId + '.vtt', 'text/vtt;charset=utf-8')}>
                    下载实际 VTT
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
