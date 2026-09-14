// Phase 46 D38-40 — 客户后台 Dashboard
// 数据源：v3_174_billing_quotas.py + v3_172_funnel_analytics.py + v3_173_opentelemetry.py
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { BarChart3, Users, TrendingUp, AlertTriangle, ArrowRight, Bot } from 'lucide-react';

interface UsageData {
  tenant_id: string;
  plan: string;
  plan_label: string;
  month: string;
  usage: {
    calls: number;
    tokens: number;
    by_category: Record<string, number>;
    by_industry_active: number;
    by_industry_deprecated: number;
  };
  quota: {
    calls: number;
    tokens: number;
    calls_remaining: number;
    tokens_remaining: number;
    calls_pct: number;
    tokens_pct: number;
  };
  phase45_warnings: {
    deprecated_industry_calls: number;
    hint: string;
  };
}

interface FunnelReview {
  industry: string;
  status: string;
  decision: string;
  reason: string;
  metrics?: {
    leads: number;
    demo: number;
    signed: number;
    estimated_ltv: number;
    roi_ratio: number;
  };
  phase45_status: string;
  migration_target?: string;
}

export function DashboardPage() {
  // 默认租户（demo 模式 · 生产从登录 token 拿 tenant_id）
  const tenantId = 'default';
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [reviews, setReviews] = useState<FunnelReview[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`/api/v2/billing/tenants/${tenantId}/usage`).then(r => r.json()),
      fetch('/api/v2/sales/funnel/review', { method: 'POST' }).then(r => r.json()),
    ]).then(([u, r]) => {
      setUsage(u);
      setReviews(r.reviews || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [tenantId]);

  if (loading) {
    return <div className="max-w-page mx-auto px-6 py-20 text-center">加载中…</div>;
  }
  if (!usage) {
    return <div className="max-w-page mx-auto px-6 py-20 text-center text-red-500">加载失败</div>;
  }

  return (
    <div className="py-12 bg-gray-50 min-h-screen">
      <div className="max-w-page mx-auto px-6">
        {/* Dashboard Preview Banner */}
        <div className="mb-6 rounded-xl overflow-hidden shadow-md bg-gradient-to-r from-blue-600 to-indigo-600 p-6 flex items-center gap-6 text-white">
          <img
            src="/images/dashboard-preview.jpeg"
            alt="Dashboard 预览"
            className="w-24 h-24 object-cover rounded-lg shadow-lg hidden md:block"
          />
          <div className="flex-1">
            <p className="text-xs uppercase tracking-wider opacity-90 mb-1">📊 你正在看的就是这个</p>
            <h2 className="text-xl font-bold mb-1">实时仪表盘 · 监控 / 漏斗 / 财务 / 告警</h2>
            <p className="text-sm opacity-90">MRR / ARR / CAC / LTV · 80 客户漏斗 P0-P3 · 13 告警规则 · 飞书实时推送</p>
          </div>
        </div>

        {/* 头部 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-1">客户后台</h1>
            <p className="text-gray-600">
              {usage.tenant_id} · {usage.plan_label} · {usage.month}
            </p>
          </div>
          <div className="flex gap-3">
            <Link to="/settings" className="px-4 py-2 border border-gray-300 rounded-md hover:border-brand-500 inline-flex items-center gap-2">
              设置 <ArrowRight className="w-4 h-4" />
            </Link>
            <Link to="/billing" className="px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2">
              升级套餐 <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>

        {/* 配额卡片 */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <QuotaCard
            title="API 调用"
            used={usage.quota.calls === 999_999 ? usage.usage.calls : usage.usage.calls}
            quota={usage.quota.calls === 999_999 ? Infinity : usage.quota.calls}
            pct={usage.quota.calls_pct}
            icon={<BarChart3 className="w-5 h-5" />}
          />
          <QuotaCard
            title="LLM Tokens"
            used={usage.usage.tokens}
            quota={usage.quota.tokens === 100_000_000 ? Infinity : usage.quota.tokens}
            pct={usage.quota.tokens_pct}
            icon={<Users className="w-5 h-5" />}
          />
        </div>

        {/* Phase 45 D4-7 警告 */}
        {usage.phase45_warnings.deprecated_industry_calls > 0 && (
          <div className="mb-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-yellow-800">
                检测到 {usage.phase45_warnings.deprecated_industry_calls} 次 deprecated 行业调用
              </p>
              <p className="text-sm text-yellow-700 mt-1">
                {usage.phase45_warnings.hint}
              </p>
            </div>
          </div>
        )}

        {/* 用量分类 */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            本月用量分类
          </h2>
          {Object.keys(usage.usage.by_category).length === 0 ? (
            <p className="text-gray-500 text-sm">本月暂无用量</p>
          ) : (
            <div className="grid md:grid-cols-3 gap-4">
              {Object.entries(usage.usage.by_category).map(([cat, n]) => (
                <div key={cat} className="p-4 bg-gray-50 rounded-md">
                  <p className="text-xs text-gray-500">{cat}</p>
                  <p className="text-2xl font-bold">{n}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 行业复盘 */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            行业自动复盘
          </h2>
          <div className="space-y-3">
            {reviews.map((r) => (
              <div
                key={r.industry}
                className={`p-4 rounded-md border ${
                  r.status === 'deprecated'
                    ? 'bg-gray-50 border-gray-300'
                    : r.decision === 'increase_investment'
                    ? 'bg-green-50 border-green-200'
                    : r.decision === 'pause_and_review'
                    ? 'bg-red-50 border-red-200'
                    : 'bg-white border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">
                      {r.industry === 'decoration' && '装企'}
                      {r.industry === 'medical' && '医美'}
                      {r.industry === 'education' && '教培'}
                      {r.industry === 'catering' && '餐饮'}
                      {r.industry === 'retail' && '零售'}
                      <span className="ml-2 text-xs text-gray-500">
                        ({r.phase45_status === 'active' ? 'active' : 'deprecated'})
                      </span>
                    </p>
                    <p className="text-sm text-gray-600 mt-1">{r.reason}</p>
                    {r.migration_target && (
                      <p className="text-xs text-brand-500 mt-1">
                        建议迁移到: {r.migration_target === 'decoration' ? '装企' : r.migration_target}
                      </p>
                    )}
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${
                    r.decision === 'increase_investment' ? 'bg-green-100 text-green-700' :
                    r.decision === 'pause_and_review' ? 'bg-red-100 text-red-700' :
                    r.decision === 'stop_investing' ? 'bg-gray-200 text-gray-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {r.decision}
                  </span>
                </div>
                {r.metrics && (
                  <div className="grid grid-cols-5 gap-2 mt-3 text-center text-xs">
                    <Metric label="留资" value={r.metrics.leads} />
                    <Metric label="演示" value={r.metrics.demo} />
                    <Metric label="签约" value={r.metrics.signed} />
                    <Metric label="LTV" value={r.metrics.estimated_ltv} />
                    <Metric label="ROI" value={r.metrics.roi_ratio} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function QuotaCard({ title, used, quota, pct, icon }: { title: string; used: number; quota: number; pct: number; icon: React.ReactNode }) {
  const unlimited = quota === Infinity;
  return (
    <div className="bg-white p-6 rounded-lg border border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-600 flex items-center gap-2">{icon} {title}</span>
        <span className="text-xs text-gray-500">{unlimited ? '不限' : `${pct.toFixed(1)}%`}</span>
      </div>
      <p className="text-3xl font-bold mb-1">{used.toLocaleString()}</p>
      <p className="text-xs text-gray-500">
        {unlimited ? '无限套餐' : `配额 ${quota.toLocaleString()}`}
      </p>
      {!unlimited && (
        <div className="mt-3 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full ${pct > 80 ? 'bg-red-500' : pct > 50 ? 'bg-yellow-500' : 'bg-brand-500'}`}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-white rounded p-2">
      <p className="text-gray-500">{label}</p>
      <p className="font-bold text-sm mt-0.5">{value}</p>
    </div>
  );
}
