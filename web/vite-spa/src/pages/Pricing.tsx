// Phase 45-47: 定价页 · 3 套餐 + 客户 logo + 退款保证 + 比较表
import { Link } from 'react-router-dom';
import { Check, ArrowRight, Shield, Building2, Clock } from 'lucide-react';
import { CUSTOMER_LOGOS, TESTIMONIALS } from '../data/customers';

const PLANS = [
  {
    name: '轻装版',
    price: '¥299',
    period: '/ 月',
    desc: '适合 1-2 人小团队 / 个人老板',
    features: [
      '5 AI 数字员工全功能',
      '1,000 次 / 月 LLM 调用',
      '邮件 + 工单支持',
      '装企/医美 2 大行业模板',
      '3 个 SPA 页面 + 5 份公司文档',
    ],
    cta: '7 天免费试用',
    href: '/try',
    highlight: false,
  },
  {
    name: '标准版',
    price: '¥999',
    period: '/ 月',
    desc: '推荐：装企 / 医美 / 中小团队首选',
    features: [
      '5 AI 数字员工 + 1500+ skill 模板',
      '10,000 次 / 月 LLM 调用',
      '1v1 微信群 + 7×24 响应',
      '装企/医美 完整 5 步管线',
      '11 个 SPA 页面无限访问',
      '80 家客户清单 + 外呼',
      '监控告警 + 飞书推送',
      '16 份公司文档 + 14 财务科目',
    ],
    cta: '开通标准版',
    href: '/try',
    highlight: true,
  },
  {
    name: '旗舰版',
    price: '¥3,999',
    period: '/ 月',
    desc: '含定制开发 + 专属客服',
    features: [
      '5 AI 数字员工 + 自定义 skill',
      '无限 LLM 调用',
      '专属客户成功经理',
      '私有部署 / VPC',
      '定制行业管线开发（5 人天/月）',
      'SLA 99.95% + 季度回顾',
      'API 开放 + Webhook',
      'OPC 模式白皮书 + 案例库',
    ],
    cta: '联系销售',
    href: '/contact',
    highlight: false,
  },
];

const COMPARISON = [
  { feature: '5 AI 数字员工', light: '✓', standard: '✓', flagship: '✓' },
  { feature: 'skill 模板数', light: '150+', standard: '1500+', flagship: '无限' },
  { feature: 'LLM 调用', light: '1,000/月', standard: '10,000/月', flagship: '无限' },
  { feature: '客户清单', light: '10 家', standard: '80 家', flagship: '无限' },
  { feature: '监控告警', light: '基础', standard: '完整 + 飞书', flagship: '完整 + 定制' },
  { feature: '公司文档', light: '5 份', standard: '16 份', flagship: '16 份 + 自定义' },
  { feature: '1v1 支持', light: '邮件', standard: '微信群 24h', flagship: '专属经理' },
  { feature: 'API', light: '×', standard: 'RESTful', flagship: 'RESTful + Webhook' },
  { feature: '私有部署', light: '×', standard: '×', flagship: 'VPC / 独立部署' },
];

export function PricingPage() {
  return (
    <div className="py-20">
      <div className="max-w-page mx-auto px-6">
        {/* HERO */}
        <div className="text-center mb-12">
          <span className="inline-block px-3 py-1 bg-brand-100 text-brand-700 rounded-full text-sm mb-4">
            💰 简单透明的定价
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            3 套餐 · 按需选 · 随时升
          </h1>
          <p className="text-gray-600 text-lg mb-6">
            7 天免费试用 · 无需信用卡 · 30 分钟跑通首条管线
          </p>
          <div className="flex items-center justify-center gap-6 text-sm">
            <div className="flex items-center gap-1 text-green-600">
              <Shield className="w-4 h-4" /> 30 天无理由退款
            </div>
            <div className="flex items-center gap-1 text-green-600">
              <Check className="w-4 h-4" /> 1v1 微信群服务
            </div>
            <div className="flex items-center gap-1 text-green-600">
              <Clock className="w-4 h-4" /> 24h 内回复
            </div>
          </div>
        </div>

        {/* 3 套餐卡片 */}
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-16">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`relative p-6 rounded-xl border-2 ${
                plan.highlight
                  ? 'border-brand-500 bg-gradient-to-br from-brand-50 to-white shadow-xl'
                  : 'border-gray-200 bg-white'
              }`}
            >
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-brand-500 text-white text-xs rounded-full font-bold">
                  ⭐ 推荐
                </span>
              )}
              <h3 className="text-xl font-bold mb-2">{plan.name}</h3>
              <p className="text-sm text-gray-500 mb-4">{plan.desc}</p>
              <div className="flex items-baseline mb-4">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-gray-500 ml-1">{plan.period}</span>
              </div>
              <ul className="space-y-2 mb-6">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                to={plan.href}
                className={`block text-center px-4 py-2 rounded-md font-medium ${
                  plan.highlight
                    ? 'bg-brand-500 text-white hover:bg-brand-600'
                    : 'border border-gray-300 hover:border-brand-500'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* 比较表 */}
        <div className="max-w-5xl mx-auto mb-16">
          <h2 className="text-2xl font-bold mb-6 text-center">3 套餐详细对比</h2>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">功能</th>
                  <th className="px-4 py-3 text-center font-medium">轻装版</th>
                  <th className="px-4 py-3 text-center font-medium bg-brand-50">标准版 ⭐</th>
                  <th className="px-4 py-3 text-center font-medium">旗舰版</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {COMPARISON.map((row) => (
                  <tr key={row.feature}>
                    <td className="px-4 py-3 text-gray-700">{row.feature}</td>
                    <td className="px-4 py-3 text-center">{row.light}</td>
                    <td className="px-4 py-3 text-center bg-brand-50 font-medium">{row.standard}</td>
                    <td className="px-4 py-3 text-center">{row.flagship}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Trusted by */}
        <div className="max-w-5xl mx-auto mb-16">
          <p className="text-center text-xs uppercase font-bold text-gray-500 mb-6 tracking-wider">
            <Building2 className="w-4 h-4 inline mr-1" /> 210+ 客户信赖 · 部分代表
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {CUSTOMER_LOGOS.slice(0, 10).map((c) => (
              <div
                key={c.name}
                className={`px-3 py-3 ${c.color} rounded-lg text-center`}
                title={`${c.name} · ${c.city} · ${c.scale}`}
              >
                <p className="font-bold text-sm">{c.shortName}</p>
                <p className="text-xs opacity-75">{c.city}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 客户证言 */}
        <div className="max-w-5xl mx-auto mb-16">
          <h2 className="text-2xl font-bold mb-6 text-center">老板证言</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {TESTIMONIALS.slice(0, 3).map((t, i) => (
              <div key={i} className="p-5 bg-white rounded-lg border border-gray-200">
                <p className="text-sm text-gray-700 mb-3 italic">"{t.quote}"</p>
                <p className="text-xs text-gray-500">— {t.author} · {t.role}</p>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ mini */}
        <div className="max-w-3xl mx-auto mb-16">
          <h2 className="text-2xl font-bold mb-6 text-center">常见问题</h2>
          <div className="space-y-3">
            {[
              { q: '7 天试用是真的免费吗？', a: '真的。无需信用卡。7 天内你可以用全部功能，到期后自动转为免费版（功能受限）。' },
              { q: '可以升级或降档吗？', a: '随时可以。升级立即生效，差价按天补。降档下个计费周期生效。数据完整保留。' },
              { q: '支持哪些支付方式？', a: '微信支付、支付宝、企业网银（公对公转账）。年付可签合同 + 开增票。' },
              { q: '年付有折扣吗？', a: '有。年付 8 折，相当于 2 个月免费。标准版年付 ¥9,590（省 ¥2,398）。' },
            ].map((f) => (
              <div key={f.q} className="p-4 bg-white rounded-lg border border-gray-200">
                <p className="font-medium mb-1">{f.q}</p>
                <p className="text-sm text-gray-600">{f.a}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center py-12 bg-gradient-to-br from-brand-50 to-white rounded-2xl">
          <h3 className="text-2xl font-bold mb-4">7 天免费试用 · 不需要信用卡</h3>
          <Link
            to="/try"
            className="px-8 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2 font-medium"
          >
            立即试用 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
