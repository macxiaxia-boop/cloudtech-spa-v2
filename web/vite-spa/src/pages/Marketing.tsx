// Phase 45-47: SaaS 官网首页 · 5 AI 员工矩阵 + 客户证言 + 真插画 + i18n
import { Link } from 'react-router-dom';
import { Sparkles, Bot, Briefcase, Heart, ArrowRight, Hammer, Stethoscope, CheckCircle2, Quote, Building2 } from 'lucide-react';
import { CUSTOMER_LOGOS, TESTIMONIALS, TRUST_STATS } from '../data/customers';
import { useTranslation } from '@/i18n';

const FE_EMPLOYEES = [
  { id: 'content_writer', name: '内容创作', desc: 'AI 写公众号 / 小红书 / 抖音脚本', icon: '✍️' },
  { id: 'customer_service', name: '智能客服', desc: '7×24 自动应答 + 工单分流', icon: '💬' },
  { id: 'market_researcher', name: '市场调研', desc: '竞品监控 + 行业趋势报告', icon: '🔍' },
];

const INDUSTRIES = [
  { id: 'decoration', name: '装企全案获客', desc: '线索 → 画像 → 报价 → 直播 → 复盘（5 步闭环）', icon: Hammer, priority: 'primary' },
  { id: 'medical', name: '医美合规获客', desc: '线索 → 种草 → 术前 QA → 案例 → 复盘（5 步闭环）', icon: Stethoscope, priority: 'fallback' },
];

export function MarketingPage() {
  const { t } = useTranslation();
  return (
    <>
      {/* HERO */}
      <section className="relative pt-12 pb-20 md:pt-20 md:pb-32 bg-gradient-to-br from-brand-50 via-white to-purple-50 overflow-hidden">
        <div className="max-w-page mx-auto px-6 lg:px-10 grid md:grid-cols-2 gap-8 items-center">
          <div>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-brand-100 text-brand-700 rounded-full text-sm mb-5">
              <Sparkles className="w-3 h-3" /> Phase 47 · 1 人 + 5 AI 员工的整家公司
            </span>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6 leading-[1.1]">
              让 AI 成为 <span className="text-brand-500 italic">5 位数字员工</span>，
              <br />
              像一支完整团队跑。
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              装企全案获客闭环 + 医美合规获客闭环，2 大行业管线，5 AI 员工矩阵，
              把营销从"想法"变成"可追溯的产物"。
            </p>
            <div className="flex flex-wrap gap-4 mb-8">
              <Link
                to="/try"
                className="px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2 font-medium"
              >
                7 天免费试用 <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/employees"
                className="px-6 py-3 border border-gray-300 rounded-md hover:border-brand-500 inline-flex items-center gap-2"
              >
                看 5 AI 员工
              </Link>
              <Link
                to="/cases"
                className="px-6 py-3 text-brand-500 hover:bg-brand-50 rounded-md inline-flex items-center gap-2"
              >
                看 10 客户案例 →
              </Link>
            </div>
            {/* 关键数字 · Phase 48.D85 4 关键（80 家 / 1.25% / ¥999 / ¥3.99） */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-6 border-t border-gray-200">
              <div>
                <p className="text-2xl font-bold text-brand-500">80</p>
                <p className="text-xs text-gray-500">P0 客户清单</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-500">1.25%</p>
                <p className="text-xs text-gray-500">漏斗转化率</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-500">¥999</p>
                <p className="text-xs text-gray-500">标准版 / 月</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-brand-500">3.99</p>
                <p className="text-xs text-gray-500">LTV/CAC（健康）</p>
              </div>
            </div>
          </div>
          {/* Hero 插画 */}
          <div className="relative">
            <img
              src="/images/ai-team.jpeg"
              alt="5 AI 数字员工团队"
              className="rounded-2xl shadow-2xl w-full"
            />
            <div className="absolute -bottom-4 -left-4 bg-white p-3 rounded-lg shadow-lg border border-gray-200">
              <div className="flex items-center gap-2 text-sm">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                <span className="font-medium">5 AI 员工在线</span>
              </div>
            </div>
            <div className="absolute -top-4 -right-4 bg-white p-3 rounded-lg shadow-lg border border-gray-200">
              <div className="text-xs">
                <p className="font-bold text-purple-600">Hermes · 治理</p>
                <p className="text-gray-500">49 红线全绿</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trusted By 客户 logo */}
      <section className="py-12 bg-white border-y border-gray-200">
        <div className="max-w-page mx-auto px-6">
          <p className="text-center text-xs uppercase font-bold text-gray-500 mb-6 tracking-wider">
            <Building2 className="w-4 h-4 inline mr-1" /> 80+ P0 客户信赖 · 装企 + 医美 + 通用 SaaS
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {CUSTOMER_LOGOS.slice(0, 10).map((c) => (
              <div
                key={c.name}
                className={`px-4 py-3 ${c.color} rounded-lg text-center hover:shadow-md transition cursor-pointer`}
                title={`${c.name} · ${c.city} · ${c.scale}`}
              >
                <p className="font-bold text-sm">{c.shortName}</p>
                <p className="text-xs opacity-75">{c.city}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FE 3 + BE 5 员工 */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-brand-50 text-brand-700 rounded-full text-sm mb-3">
              <Bot className="w-3 h-3" /> 5 AI 数字员工 · 前台 3 + 后端 5
            </span>
            <h2 className="text-3xl font-bold mb-3">不只 3 个 FE 员工，5 个后端 AI 也在跑</h2>
            <p className="text-gray-600">Hermes（治理）+ Lyra（内容）+ Athena（架构）+ Apollo（数据）+ Artemis（运营）</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            {FE_EMPLOYEES.map((emp) => (
              <div key={emp.id} className="p-6 bg-white border border-gray-200 rounded-lg hover:border-brand-500 hover:shadow-md transition">
                <div className="text-4xl mb-3">{emp.icon}</div>
                <h3 className="text-lg font-bold mb-2">{emp.name}</h3>
                <p className="text-gray-600 text-sm">{emp.desc}</p>
                <p className="text-xs text-brand-500 mt-3">← 前台（用户直接对话）</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { name: 'Hermes', desc: '治理', icon: '🛡️', color: 'bg-purple-100 text-purple-700' },
              { name: 'Lyra', desc: '内容', icon: '🧠', color: 'bg-pink-100 text-pink-700' },
              { name: 'Athena', desc: '架构', icon: '⚙️', color: 'bg-blue-100 text-blue-700' },
              { name: 'Apollo', desc: '数据', icon: '📊', color: 'bg-green-100 text-green-700' },
              { name: 'Artemis', desc: '运营', icon: '📣', color: 'bg-orange-100 text-orange-700' },
            ].map((e) => (
              <div key={e.name} className={`p-4 ${e.color} rounded-lg text-center`}>
                <p className="text-2xl mb-1">{e.icon}</p>
                <p className="font-bold text-sm">{e.name}</p>
                <p className="text-xs opacity-75">{e.desc}</p>
              </div>
            ))}
          </div>
          <div className="text-center mt-6">
            <Link to="/employees" className="text-brand-500 hover:underline text-sm">
              看完整 5 AI 员工工时表 →
            </Link>
          </div>
        </div>
      </section>

      {/* 行业聚焦 */}
      <section className="py-20 bg-white">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-brand-50 text-brand-700 rounded-full text-sm mb-3">
              <Briefcase className="w-3 h-3" /> 行业聚焦（2 active · 3 deprecated）
            </span>
            <h2 className="text-3xl font-bold mb-3">2 大行业管线，闭环交付</h2>
            <p className="text-gray-600">每条线索进入 CRM 后，每步都有产物可查</p>
          </div>
          <div className="grid md:grid-cols-2 gap-6 max-w-3xl mx-auto">
            {INDUSTRIES.map((ind) => {
              const Icon = ind.icon;
              return (
                <Link
                  key={ind.id}
                  to={`/industries/${ind.id}`}
                  className="p-6 bg-white border border-gray-200 rounded-lg hover:shadow-md transition block"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <Icon className="w-6 h-6 text-brand-500" />
                    <h3 className="text-lg font-bold">{ind.name}</h3>
                    <span className={`text-xs px-2 py-1 rounded ${
                      ind.priority === 'primary' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {ind.priority === 'primary' ? '重点' : '兜底'}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm mb-3">{ind.desc}</p>
                  <p className="text-brand-500 text-sm">看案例 →</p>
                </Link>
              );
            })}
          </div>
          <p className="text-center text-xs text-gray-400 mt-6">
            注：教培/餐饮/零售行业已 P3-BA 撤回（2026-09-11），永久 deprecated
          </p>
        </div>
      </section>

      {/* Dashboard preview */}
      <section className="py-20 bg-gradient-to-br from-blue-50 to-white">
        <div className="max-w-page mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <span className="inline-block px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm mb-3">
                📊 你的真实仪表盘
              </span>
              <h2 className="text-3xl font-bold mb-4">监控 / 漏斗 / 财务 / 告警<br />一眼看完</h2>
              <ul className="space-y-3">
                {[
                  'MRR 月度经常性收入 + ARR + CAC + LTV',
                  '80 家客户漏斗（P0/P1/P2/P3）',
                  'Grafana 5 技术面板 + 7 业务面板',
                  '13 告警规则 P0-P3 + 飞书实时推送',
                  '208 测试 PASS 数据守护',
                ].map((f) => (
                  <li key={f} className="flex items-start gap-2 text-gray-700">
                    <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                to="/monitoring"
                className="mt-6 inline-flex items-center gap-2 text-brand-500 hover:underline font-medium"
              >
                看监控 demo <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
            <div>
              <img
                src="/images/dashboard-preview.jpeg"
                alt="Cloud 仪表盘预览"
                className="rounded-2xl shadow-2xl w-full"
              />
            </div>
          </div>
        </div>
      </section>

      {/* 客户证言 */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm mb-3">
              <Quote className="w-3 h-3" /> 真实客户证言 · 6 个脱敏案例
            </span>
            <h2 className="text-3xl font-bold mb-3">老板们怎么说</h2>
            <p className="text-gray-600">不编故事 · 每条都有客户名 + 数据可验证</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {TESTIMONIALS.map((t, i) => (
              <div key={i} className="p-6 bg-white rounded-xl border border-gray-200 hover:shadow-lg transition">
                <Quote className="w-6 h-6 text-brand-300 mb-3" />
                <p className="text-sm text-gray-700 mb-4 leading-relaxed">"{t.quote}"</p>
                <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-100">
                  <div>
                    <p className="font-bold text-sm">{t.author}</p>
                    <p className="text-xs text-gray-500">{t.role}</p>
                  </div>
                </div>
                <div className="flex gap-3 text-xs">
                  {Object.entries(t.metrics).map(([k, v]) => (
                    <div key={k} className="flex-1">
                      <p className="text-lg font-bold text-brand-500">{v}</p>
                      <p className="text-gray-500">{k}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <Link
              to="/cases"
              className="px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2"
            >
              看全部 10 案例 <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* OPC 故事引流 */}
      <section className="py-20 bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        <div className="max-w-page mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <img
                src="/images/opc-hero.jpeg"
                alt="OPC 1 人 + AI 创业"
                className="rounded-2xl shadow-2xl w-full"
              />
            </div>
            <div>
              <span className="inline-block px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm mb-3">
                👤 心之所向便是光的今天 · Day 30
              </span>
              <h2 className="text-3xl font-bold mb-4">Cloud 自己就是 OPC 跑出来的</h2>
              <p className="text-gray-600 mb-6">
                创始人心之所向便是光 1 人 + 5 AI 数字员工 · 30 天跑出 80 家客户清单 + 16 份公司文档 +
                11 个 SPA 页面 + 208 测试 PASS。OPC 不是营销词，是实证。
              </p>
              <ul className="space-y-2 mb-6 text-sm">
                {TRUST_STATS.map((s) => (
                  <li key={s.label} className="flex items-center justify-between border-b border-gray-200 pb-2">
                    <span className="text-gray-600">{s.label}</span>
                    <span className="font-bold text-brand-500">{s.value}</span>
                  </li>
                ))}
              </ul>
              <Link
                to="/opc-story"
                className="px-6 py-3 bg-indigo-500 text-white rounded-md hover:bg-indigo-600 inline-flex items-center gap-2"
              >
                看心之所向便是光的 OPC 故事 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-brand-500 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Heart className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">7 天免费试用 · 不需要信用卡</h2>
          <p className="text-lg opacity-90 mb-8">30 分钟跑通你公司的第一条管线 · 1v1 微信群 24h 响应</p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/try"
              className="px-8 py-3 bg-white text-brand-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
            >
              立即试用 <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/contact"
              className="px-8 py-3 border border-white text-white rounded-md hover:bg-white/10"
            >
              约 1v1 demo
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
