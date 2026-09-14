// Phase 46 D41-44 — 装企行业落地页（SEO + 获客闭环展示）
import { Link } from 'react-router-dom';
import { Hammer, ArrowRight, CheckCircle2, TrendingUp, Users, Sparkles } from 'lucide-react';

const STEPS = [
  { key: 'lead_profile', label: '客户画像', desc: 'AI 自动提取客户需求 + 户型 + 预算区间', emoji: '👤' },
  { key: 'quote', label: '报价拆解', desc: '按户型 + 风格 + 面积自动拆解报价清单', emoji: '💰' },
  { key: 'content', label: '获客内容', desc: '朋友圈 / 小红书 / 抖音 3 大平台内容矩阵', emoji: '📱' },
  { key: 'live_script', label: '工地直播', desc: 'AI 工地直播话术 + 户型讲解话术', emoji: '🎥' },
  { key: 'review', label: 'AI 复盘', desc: '每条线索 ROI 归因 + 下一步行动清单', emoji: '🤖' },
];

const METRICS = [
  { label: '单条线索成本', value: '< ¥30', vs: '行业平均 ¥150', color: 'text-green-600' },
  { label: '签约转化率', value: '8-15%', vs: '行业平均 2-4%', color: 'text-green-600' },
  { label: '单工长获客', value: '20-40 / 月', vs: '传统 5-10 / 月', color: 'text-green-600' },
  { label: 'AI 复盘频率', value: '实时', vs: '人工复盘 1 周', color: 'text-brand-500' },
];

const CASES = [
  {
    company: '成都华宁装饰',
    city: '成都',
    stage: '已签约 12 个月',
    quote: '装企全案获客闭环帮我们月签单从 8 单涨到 32 单，单工长月获客从 5 个到 28 个。',
    person: '王总 · 总经理',
  },
  {
    company: '杭州良工装饰',
    city: '杭州',
    stage: '已签约 6 个月',
    quote: 'AI 工地直播话术是杀手锏，单场直播到店转化 30%+，传统话术只有 8%。',
    person: '李工 · 直播运营',
  },
  {
    company: '苏州尚层装饰',
    city: '苏州',
    stage: '已签约 3 个月',
    quote: '获客内容矩阵（朋友圈 + 小红书 + 抖音）让我们单月品牌曝光从 5w 到 50w。',
    person: '陈总监 · 市场',
  },
];

export function IndustryDecorationPage() {
  return (
    <>
      {/* HERO */}
      <section className="relative py-20 bg-gradient-to-br from-brand-50 via-white to-yellow-50 overflow-hidden">
        <div className="max-w-page mx-auto px-6 grid md:grid-cols-2 gap-8 items-center">
          <div>
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm mb-4">
              <Hammer className="w-3 h-3" /> 装企行业 · Phase 45 D4-7 重点
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-[1.1]">
              装企全案获客闭环
              <br />
              <span className="text-brand-500">让 AI 数字员工替你跑 5 个环节</span>
            </h1>
            <p className="text-lg text-gray-600 mb-6">
              从线索 → 客户画像 → 报价拆解 → 获客内容 → 工地直播 → AI 复盘，
              每步有产物可查，每条线索 ROI 归因落库。
            </p>
            <div className="flex flex-wrap gap-4 mb-6">
              <Link
                to="/try"
                className="px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2 font-medium"
              >
                7 天免费试用 <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/cases"
                className="px-6 py-3 border border-gray-300 rounded-md hover:border-brand-500 inline-flex items-center gap-2"
              >
                看 5 装企案例 →
              </Link>
            </div>
            <div className="grid grid-cols-3 gap-3 pt-6 border-t border-gray-200">
              <div>
                <p className="text-2xl font-bold text-brand-500">50 家</p>
                <p className="text-xs text-gray-500">签约装企</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-brand-500">12%</p>
                <p className="text-xs text-gray-500">平均签约率</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-brand-500">¥28</p>
                <p className="text-xs text-gray-500">单条线索成本</p>
              </div>
            </div>
          </div>
          <div>
            <img
              src="/images/decoration-hero.jpeg"
              alt="装企获客闭环"
              className="rounded-2xl shadow-2xl w-full"
            />
          </div>
        </div>
      </section>

      {/* 50 装企合作 logo 网格 */}
      <section className="py-12 bg-white border-b border-gray-200">
        <div className="max-w-page mx-auto px-6">
          <p className="text-center text-xs uppercase font-bold text-gray-500 mb-6 tracking-wider">
            50 装企信赖（5 标杆展示）
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { name: '华宁装饰', city: '成都', scale: '200 工长', color: 'bg-orange-100 text-orange-700' },
              { name: '良工装饰', city: '杭州', scale: '150 工长', color: 'bg-amber-100 text-amber-700' },
              { name: '尚层装饰', city: '苏州', scale: '50 工长', color: 'bg-yellow-100 text-yellow-700' },
              { name: '业之峰', city: '北京', scale: '500 工长', color: 'bg-red-100 text-red-700' },
              { name: '聚通装饰', city: '上海', scale: '300 工长', color: 'bg-pink-100 text-pink-700' },
            ].map((c) => (
              <div key={c.name} className={`px-3 py-3 ${c.color} rounded-lg text-center`}>
                <p className="font-bold text-sm">{c.name}</p>
                <p className="text-xs opacity-75">{c.city} · {c.scale}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5 步闭环 */}
      <section className="py-20 bg-white">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">5 步闭环，每步都有 AI 数字员工接管</h2>
            <p className="text-gray-600">一键调用，无需写 prompt</p>
          </div>
          <div className="grid md:grid-cols-5 gap-4">
            {STEPS.map((s, i) => (
              <div key={s.key} className="relative p-6 bg-gray-50 rounded-lg border border-gray-200 hover:border-brand-500 hover:shadow-md transition">
                <div className="text-4xl mb-3">{s.emoji}</div>
                <p className="text-xs text-gray-500 mb-1">第 {i + 1} 步</p>
                <h3 className="text-base font-bold mb-2">{s.label}</h3>
                <p className="text-sm text-gray-600">{s.desc}</p>
                {i < STEPS.length - 1 && (
                  <ArrowRight className="hidden md:block absolute top-1/2 -right-2 w-4 h-4 text-brand-500 -translate-y-1/2" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4 大指标 */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">数据说话</h2>
            <p className="text-gray-600">装企客户实测</p>
          </div>
          <div className="grid md:grid-cols-4 gap-6">
            {METRICS.map((m) => (
              <div key={m.label} className="bg-white p-6 rounded-lg border border-gray-200 text-center">
                <p className="text-sm text-gray-500 mb-2">{m.label}</p>
                <p className={`text-4xl font-bold mb-1 ${m.color}`}>{m.value}</p>
                <p className="text-xs text-gray-400">{m.vs}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 客户案例 */}
      <section className="py-20 bg-white">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">客户实证</h2>
            <p className="text-gray-600">3 个城市的装企老板怎么说</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {CASES.map((c) => (
              <div key={c.company} className="p-6 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-bold">{c.company}</p>
                    <p className="text-xs text-gray-500">{c.city} · {c.person}</p>
                  </div>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">{c.stage}</span>
                </div>
                <p className="text-sm text-gray-700 italic">"{c.quote}"</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 📎 配套文档引用 */}
      <section className="py-12 bg-gray-50 border-t border-gray-200">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">📎 配套文档</h2>
          <p className="text-gray-600 mb-6">装企行业落地页的 SOP + 客户脚本 + 行业模板</p>
          <div className="grid md:grid-cols-2 gap-4">
            <a
              href="/docs/marketing/scripts/outreach_decoration.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">marketing/scripts/</p>
              <p className="font-bold mb-1">outreach_decoration.md</p>
              <p className="text-sm text-gray-600">装企 50 家外呼脚本 + 转化漏斗 + 4 步法</p>
            </a>
            <a
              href="/docs/marketing/scripts/p0_8_clients.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">marketing/scripts/</p>
              <p className="font-bold mb-1">p0_8_clients.md</p>
              <p className="text-sm text-gray-600">P0 8 家精选清单（含 3 家北京装企）</p>
            </a>
            <a
              href="/docs/finance/financial_model.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">finance/</p>
              <p className="font-bold mb-1">financial_model.md</p>
              <p className="text-sm text-gray-600">装企客户单价模型 + LTV + 续约率假设</p>
            </a>
            <a
              href="/docs/clients"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-emerald-500 hover:shadow transition"
            >
              <p className="text-xs text-emerald-600 mb-1">→ SPA</p>
              <p className="font-bold mb-1">/clients 80 家清单</p>
              <p className="text-sm text-gray-600">装企 50 家 + 医美 30 家全量清单</p>
            </a>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-brand-500 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Sparkles className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">30 分钟跑通你的首条装企管线</h2>
          <p className="text-lg opacity-90 mb-8">7 天免费试用 · 无需信用卡 · 装企老板亲自上手</p>
          <Link
            to="/login"
            className="px-8 py-3 bg-white text-brand-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            立即开始 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
