import { useState } from "react";
import { workPathClient } from "../lib/workpath-client";

/**
 * V4 WorkPaths Demo Page
 * 接入 6 旗舰 workpath: 用户输入 utterance → resolve → create run → bind asset
 * 真实跑通需 FastAPI 在 :8000 启动
 */
export default function V4WorkPathsDemo() {
  const [utterance, setUtterance] = useState("研究博主");
  const [resolved, setResolved] = useState<any>(null);
  const [runId, setRunId] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const onResolve = async () => {
    setError("");
    setBusy(true);
    try {
      const r = await workPathClient.resolve({
        utterance,
        input_refs: [
          { role: "homepage_url", value: "https://example.com/u1" },
          { role: "target_industry", value: "decoration" },
        ],
      });
      setResolved(r);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  };

  const onCreateRun = async () => {
    if (!resolved?.matched_path_id) return;
    setError("");
    setBusy(true);
    try {
      const r = await workPathClient.createRun({
        path_id: resolved.matched_path_id,
        revision: 1,
        input_bindings: {
          homepage_url: "https://example.com/u1",
          target_industry: "decoration",
        },
        idempotency_key: `demo-${Date.now()}`,
        conversation_id: "demo-conv-001",
      });
      setRunId(r.run_id);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">CloudTech V4 — WorkPaths Demo</h1>
      <p className="text-sm text-gray-500 mb-6">
        接入 <code>api/v4/__init__.py</code> FastAPI 端点。
        真实跑通需 <code>uvicorn api.v4:app --port 8000</code> 启动。
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">用户输入 utterance</label>
          <input
            className="w-full border rounded px-3 py-2"
            value={utterance}
            onChange={(e) => setUtterance(e.target.value)}
            placeholder="例: 研究博主 / 装修效果图 / 提取视频"
          />
        </div>

        <div className="flex gap-2">
          <button
            className="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50"
            disabled={busy}
            onClick={onResolve}
          >
            1. Resolve
          </button>
          <button
            className="bg-green-500 text-white px-4 py-2 rounded disabled:opacity-50"
            disabled={busy || !resolved?.matched_path_id}
            onClick={onCreateRun}
          >
            2. Create Run
          </button>
        </div>

        {error && (
          <div className="text-red-500 text-sm">⚠️ {error}</div>
        )}

        {resolved && (
          <div className="border rounded p-4 bg-gray-50">
            <div className="font-semibold mb-2">Resolve 响应</div>
            <pre className="text-xs overflow-x-auto">{JSON.stringify(resolved, null, 2)}</pre>
          </div>
        )}

        {runId && (
          <div className="border rounded p-4 bg-green-50">
            <div className="font-semibold mb-2">Run 已创建</div>
            <div>run_id: <code className="bg-white px-1 rounded">{runId}</code></div>
          </div>
        )}

        <div className="text-xs text-gray-400 mt-8">
          <div>6 旗舰路径: WP-BLOGGER-RESEARCH / WP-VIDEO-TRANSCRIBE / WP-ARTICLE-REWRITE / WP-RENOVATION-FULL / WP-GROWTH-VIDEO / WP-PRODUCT-MARKETING</div>
          <div>228 mock 测试 PASSED · Production Ready = 0 (红线 #60)</div>
        </div>
      </div>
    </div>
  );
}
