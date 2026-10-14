/** Timestamped transcript -> actual persisted subtitle export via existing V4 worker. */
import { useEffect, useState } from 'react';
import { FileText, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { workPathClient } from '@/lib/workpath-client';

type SubtitleResult = {
  srt: string; vtt: string; source_sha256: string;
  segment_count: number; duration_ms: number;
  mock: false; asr_performed: false; model_called: false;
};
type ReceiptNode = { status?: string; operation?: string; output_ref?: SubtitleResult };

function exportTextFile(content: string, extension: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `cloudtech-subtitles.${extension}`;
  link.click();
  URL.revokeObjectURL(url);
}

export function SubtitleExportTool() {
  const [segmentsJson, setSegmentsJson] = useState('');
  const [runId, setRunId] = useState('');
  const [queueState, setQueueState] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<SubtitleResult | null>(null);

  async function submit() {
    setError('');
    setResult(null);
    setBusy(true);
    try {
      if (new TextEncoder().encode(segmentsJson).length > 700_000) {
        throw new Error('字幕数据过大；请限制在 700KB 以内');
      }
      let parsed: unknown;
      try {
        parsed = JSON.parse(segmentsJson);
      } catch {
        throw new Error('请输入合法的 JSON 数组');
      }
      if (!Array.isArray(parsed) || parsed.length < 1 || parsed.length > 2000) {
        throw new Error('必须提交 1 至 2000 条含时间戳的片段');
      }
      const created = await workPathClient.createRun({
        path_id: 'WP-LOCAL-SUBTITLE-EXPORT',
        revision: 1,
        input_bindings: { segments: parsed },
      });
      setRunId(created.run_id);
      const queued = await workPathClient.enqueueLocalRun(created.run_id);
      setQueueState(queued.state);
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!runId || result) return;
    let alive = true;
    let fetching = false;
    const check = async () => {
      if (fetching) return;
      fetching = true;
      try {
        const queue = await workPathClient.getLocalQueueStatus(runId);
        if (!alive) return;
        setQueueState(queue.state);
        if (queue.state === 'FAILED') {
          setError(`字幕 Worker 失败：${queue.error_code || '请检查运行日志'}`);
          return;
        }
        if (queue.state !== 'DONE') return;
        const run = await workPathClient.getRun(runId);
        if (!alive) return;
        const nodes = run.nodes as ReceiptNode[] | undefined;
        const output = nodes?.[0]?.output_ref;
        if (run.status !== 'COMPLETED' || nodes?.length !== 1 ||
            nodes[0].operation !== 'subtitle.format_supplied' ||
            nodes[0].status !== 'COMPLETED' ||
            output?.mock !== false || output?.asr_performed !== false ||
            output?.model_called !== false ||
            typeof output.srt !== 'string' ||
            typeof output.vtt !== 'string' ||
            !output.source_sha256) {
          throw new Error('字幕输出缺少可验证的真实节点完成凭证');
        }
        setResult(output);
      } catch (err) {
        if (alive) setError(err instanceof Error ? err.message : '读取字幕失败');
      } finally {
        fetching = false;
      }
    };
    void check();
    const interval = window.setInterval(() => void check(), 3000);
    return () => {
      alive = false;
      window.clearInterval(interval);
    };
  }, [runId, result]);

  return (
    <Card>
      <CardContent className="p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2">
          <FileText className="w-5 h-5" />
          真实转写片段转 SRT / VTT 字幕
        </h2>
        <p className="text-sm text-muted-foreground">
          输入你已获得使用授权的时间戳与文本。CloudTech 不会自行听取音频、
          猜测转写内容，也不会调用付费模型。结果由本地 Worker 生成并写入任务记录。
        </p>
        <label htmlFor="ct-subtitle-segments" className="text-sm font-medium">
          片段 JSON（时间单位：毫秒）
        </label>
        <textarea
          id="ct-subtitle-segments"
          value={segmentsJson}
          onChange={(event) => setSegmentsJson(event.target.value)}
          rows={5}
          className="w-full rounded border border-border p-3 text-sm font-mono"
          placeholder={'[{"start_ms":0,"end_ms":1500,"text":"实际字幕第一句"}]'}
        />
        <Button
          type="button"
          onClick={() => void submit()}
          disabled={busy || !segmentsJson.trim() || !!(runId && !result && queueState !== 'FAILED')}
        >
          {busy ? '提交中…' : '提交独立 Worker 并生成字幕'}
        </Button>
        {runId && (
          <p role="status" className="text-sm text-muted-foreground break-all">
            任务：{runId} · 真实队列状态：{queueState || '查询中'}
          </p>
        )}
        {error && <p role="alert" className="text-sm text-destructive-600">{error}</p>}
        {result && (
          <div className="space-y-3 border border-border rounded p-4">
            <p className="text-sm">
              已生成 {result.segment_count} 条字幕，时长 {result.duration_ms} 毫秒。
              <span className="block text-xs text-muted-foreground break-all">
                来源哈希：{result.source_sha256}
              </span>
            </p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={() => exportTextFile(result.srt, 'srt')}>
                <Download className="w-4 h-4" /> 下载 SRT
              </Button>
              <Button type="button" variant="outline"
                      onClick={() => exportTextFile(result.vtt, 'vtt')}>
                <Download className="w-4 h-4" /> 下载 VTT
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
