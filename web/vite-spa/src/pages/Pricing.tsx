// Phase 45 D17-23: SaaS 定价页
// 3 档：免费 / 专业版 / 企业版
import { Link } from 'react-router-dom';
import { Check, ArrowRight } from 'lucide-react';

const PLANS = [
  {
    name: '免费版',
    price: '¥0',
    period: '/ 月',
    desc: '7 天体验，含 1 个 FE 员工',
    features: ['1 个 FE 数字员工', '100 次 / 月调用', '社区支持', '公开行业模板'],
    cta: '注册体验',
    href: '/login',
    highlight: false,
  },
  {
    name: '专业版',
    price: '¥499',
    period: '/ 月',
    desc: '推荐：装企 / 医美首选',
    features: ['3 个 FE + 5 个 BE 员工', '5000 次 / 月调用', '邮件 + 工单支持', '装企/医美 2 大行业管线', 'ROI 归因仪表盘'],
    cta: '开通专业版',
    href: '/login',
    highlight: true,
  },
  {
    name: '企业版',
    price: '¥2,499',
    period: '/ 月',
    desc: '含私有部署 + 定制开发',
    features: ['无限 FE/BE 员工', '无限调用', '专属客户成功', '私有部署 / VPC', '定制行业管线开发', 'SLA 99.95%'],
    cta: '联系销售',
    href: '/contact',
    highlight: false,
  },
];

export function PricingPage() {
  return (
    <div className="py-20">
      <div className="max-w-page mx-auto px-6">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">简单透明的定价</h1>
          <p className="text-gray-600 text-lg">按需选择 · 随时升级或退订</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`p-6 rounded-lg border ${
                plan.highlight
                  ? 'border-brand-500 shadow-lg ring-2 ring-brand-100 bg-white'
                  : 'border-gray-200 bg-white'
              }`}
            >
              <h3 className="text-lg font-bold mb-1">{plan.name}</h3>
              <p className="text-sm text-gray-500 mb-4">{plan.desc}</p>
              <div className="flex items-baseline mb-6">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-gray-500 ml-1">{plan.period}</span>
              </div>
              <ul className="space-y-2 mb-8 text-sm">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <Check className="w-4 h-4 text-brand-500 flex-shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                to={plan.href}
                className={`w-full inline-flex justify-center items-center gap-2 px-4 py-2 rounded-md ${
                  plan.highlight
                    ? 'bg-brand-500 text-white hover:bg-brand-600'
                    : 'border border-gray-300 hover:border-brand-500'
                }`}
              >
                {plan.cta} <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          ))}
        </div>
      </div>

      {/* 📎 配套文档引用 */}
      <section className="py-12 bg-gray-50 border-t border-gray-200 mt-12">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">📎 定价背后的财务模型</h2>
          <p className="text-gray-600 mb-6">3 套餐定价的 LTV / 续约率 / MRR 假设</p>
          <div className="grid md:grid-cols-3 gap-4">
            <a
              href="/docs/finance/financial_model.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition"
            >
              <p className="text-xs text-brand-600 mb-1">finance/</p>
              <p className="font-bold mb-1">financial_model.md</p>
              <p className="text-sm text-gray-600">3 套餐 LTV + MRR + 续约率假设</p>
            </a>
            <a
              href="/docs/finance/saas_selection.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition"
            >
              <p className="text-xs text-brand-600 mb-1">finance/</p>
              <p className="font-bold mb-1">saas_selection.md</p>
              <p className="text-sm text-gray-600">5 SaaS 选型（金蝶 / 飞书人事 / Grafana Cloud）</p>
            </a>
            <a
              href="/docs/finance/monitoring_dashboard.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow transition"
            >
              <p className="text-xs text-brand-600 mb-1">finance/</p>
              <p className="font-bold mb-1">monitoring_dashboard.md</p>
              <p className="text-sm text-gray-600">4 监控仪表盘 + MRR/P0/P1/P2 优先级</p>
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
