// Phase 46 D38-40 — 客户计费/升级页
import { useEffect, useState } from 'react';
import { Check, ArrowRight, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';

interface Plan {
  label: string;
  monthly_calls: number;
  monthly_tokens: number;
  fe_employees: number;
  be_employees: number;
  industries: string[];
  price_yuan: number;
}

interface PlansResponse {
  plans: Record<string, Plan>;
}

export function BillingPage() {
  const [plans, setPlans] = useState<Record<string, Plan> | null>(null);
  const [currentPlan, setCurrentPlan] = useState('pro');

  useEffect(() => {
    Promise.all([
      fetch('/api/v2/billing/plans').then(r => r.json()),
      fetch('/api/v2/billing/tenants/default/usage').then(r => r.json()),
    ]).then(([p, u]) => {
      setPlans(p.plans);
      setCurrentPlan(u.plan);
    });
  }, []);

  if (!plans) {
    return <div className="max-w-page mx-auto px-6 py-20 text-center">加载中…</div>;
  }

  return (
    <div className="py-12 bg-gray-50 min-h-screen">
      <div className="max-w-page mx-auto px-6">
        <h1 className="text-3xl font-bold mb-2">套餐与计费</h1>
        <p className="text-gray-600 mb-8">
          当前套餐: <span className="font-medium">{plans[currentPlan]?.label}</span> ·{' '}
          <Link to="/dashboard" className="text-brand-500 hover:underline">返回后台</Link>
        </p>

        {/* 红 #22 守门提示 */}
        <div className="mb-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium text-yellow-800">OPC 模式 Demo</p>
            <p className="text-yellow-700 mt-1">
              实际支付/发票/合同功能需用户拍板后接入金税系统（红 #22）。当前仅切换套餐标识。
            </p>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {Object.entries(plans).map(([pid, plan]) => {
            const isCurrent = pid === currentPlan;
            return (
              <div
                key={pid}
                className={`p-6 bg-white rounded-lg border-2 ${
                  isCurrent ? 'border-brand-500 shadow-lg' : 'border-gray-200'
                }`}
              >
                {isCurrent && (
                  <span className="inline-block px-2 py-0.5 bg-brand-100 text-brand-700 text-xs rounded mb-2">
                    当前
                  </span>
                )}
                <h3 className="text-xl font-bold mb-1">{plan.label}</h3>
                <div className="flex items-baseline mb-4">
                  <span className="text-4xl font-bold">¥{plan.price_yuan}</span>
                  <span className="text-gray-500 ml-1">/ 月</span>
                </div>
                <ul className="space-y-2 text-sm mb-6">
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-brand-500 flex-shrink-0 mt-0.5" />
                    <span>{plan.monthly_calls.toLocaleString()} 次 / 月调用</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-brand-500 flex-shrink-0 mt-0.5" />
                    <span>{(plan.monthly_tokens / 1_000_000).toFixed(1)}M LLM tokens / 月</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-brand-500 flex-shrink-0 mt-0.5" />
                    <span>{plan.fe_employees} FE 员工 + {plan.be_employees} BE 员工</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-brand-500 flex-shrink-0 mt-0.5" />
                    <span>
                      行业: {plan.industries.map(i =>
                        i === 'decoration' ? '装企' : i === 'medical' ? '医美' : i
                      ).join(' / ')}
                    </span>
                  </li>
                </ul>
                <button
                  disabled={isCurrent}
                  onClick={() => {
                    if (confirm(`确认切换到 ${plan.label}?`)) {
                      fetch(`/api/v2/billing/tenants/default/upgrade?plan_id=${pid}`, {
                        method: 'POST',
                      }).then(() => window.location.reload());
                    }
                  }}
                  className={`w-full inline-flex justify-center items-center gap-2 px-4 py-2 rounded-md ${
                    isCurrent
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-brand-500 text-white hover:bg-brand-600'
                  }`}
                >
                  {isCurrent ? '当前套餐' : <>切换 <ArrowRight className="w-4 h-4" /></>}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
