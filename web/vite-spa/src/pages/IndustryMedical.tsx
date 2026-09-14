// Phase 46 D41-44 — 医美行业落地页（合规获客闭环）
import { Link } from 'react-router-dom';
import { Stethoscope, ArrowRight, Shield, Sparkles, AlertCircle, CheckCircle2 } from 'lucide-react';

const STEPS = [
  { key: 'lead_profile', label: '客户画像', desc: '年龄段 + 需求 + 预算 + 风险偏好', emoji: '👤' },
  { key: 'content', label: '种草内容', desc: '公众号 / 小红书 / 抖音合规种草', emoji: '🌱' },
  { key: 'pre_op_qa', label: '术前合规问答', desc: 'AI 答术前/术后/资质/价格 4 类问题', emoji: '⚖️' },
  { key: 'case', label: '案例展示', desc: '合规案例展示（含脱敏授权书）', emoji: '🖼️' },
  { key: 'review', label: 'AI 复盘', desc: '合规 ROI 归因 + 监管红线告警', emoji: '🤖' },
];

const COMPLIANCE = [
  '严禁承诺疗效',
  '严禁使用绝对化用语（"最佳/最好"）',
  '严禁对比其他机构贬损',
  '案例展示需脱敏 + 客户授权书',
  '价格透明 · 不诱导贷款',
  '术前/术后知情同意书必须留痕',
];

const METRICS = [
  { label: '合规拦截', value: '100%', vs: 'AI 自动拦截违规话术', color: 'text-green-600' },
  { label: '术前 QA 准确率', value: '95%+', vs: '人工 60-70%', color: 'text-green-600' },
  { label: '案例脱敏', value: '100%', vs: 'AI 自动人脸模糊', color: 'text-brand-500' },
  { label: '复盘频率', value: '实时', vs: '人工 1 周', color: 'text-brand-500' },
];

export function IndustryMedicalPage() {
  return (
    <>
      {/* HERO */}
      <section className="relative py-20 bg-gradient-to-br from-pink-50 via-white to-rose-50">
        <div className="max-w-page mx-auto px-6">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-pink-100 text-pink-700 rounded-full text-sm mb-4">
              <Stethoscope className="w-3 h-3" /> 医美行业 · Phase 45 D4-7 兜底
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 leading-[1.1]">
              医美合规获客闭环
              <br />
              <span className="text-pink-500">让 AI 数字员工替你守住 6 条监管红线</span>
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              从线索 → 客户画像 → 种草内容 → 术前合规 QA → 案例展示 → AI 复盘，
              AI 自动拦截违规话术 + 案例脱敏。
            </p>
            <div className="flex gap-4">
              <Link
                to="/login"
                className="px-6 py-3 bg-pink-500 text-white rounded-md hover:bg-pink-600 inline-flex items-center gap-2"
              >
                7 天免费试用 <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/pricing"
                className="px-6 py-3 border border-gray-300 rounded-md hover:border-pink-500"
              >
                查看定价
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 合规红线 */}
      <section className="py-12 bg-red-50 border-y border-red-200">
        <div className="max-w-page mx-auto px-6">
          <div className="flex items-start gap-4">
            <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-1" />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-red-800 mb-2">医美 6 条监管红线（AI 必拦截）</h2>
              <p className="text-sm text-red-700 mb-4">
                国家市场监管总局《医疗广告管理办法》+《医疗美容服务管理办法》明令禁止的 6 类违规话术
              </p>
              <div className="grid md:grid-cols-3 gap-3">
                {COMPLIANCE.map((c) => (
                  <div key={c} className="flex items-start gap-2 p-3 bg-white rounded border border-red-200">
                    <Shield className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                    <span className="text-sm">{c}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5 步闭环 */}
      <section className="py-20 bg-white">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">5 步合规获客闭环</h2>
            <p className="text-gray-600">每步 AI 自动合规检查</p>
          </div>
          <div className="grid md:grid-cols-5 gap-4">
            {STEPS.map((s, i) => (
              <div key={s.key} className="relative p-6 bg-gray-50 rounded-lg border border-gray-200 hover:border-pink-500 hover:shadow-md transition">
                <div className="text-4xl mb-3">{s.emoji}</div>
                <p className="text-xs text-gray-500 mb-1">第 {i + 1} 步</p>
                <h3 className="text-base font-bold mb-2">{s.label}</h3>
                <p className="text-sm text-gray-600">{s.desc}</p>
                {i < STEPS.length - 1 && (
                  <ArrowRight className="hidden md:block absolute top-1/2 -right-2 w-4 h-4 text-pink-500 -translate-y-1/2" />
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
            <h2 className="text-3xl font-bold mb-3">合规 + 效率双指标</h2>
            <p className="text-gray-600">医美客户实测</p>
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

      {/* 📎 配套文档引用 */}
      <section className="py-12 bg-gray-50 border-t border-gray-200">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-4">📎 配套文档</h2>
          <p className="text-gray-600 mb-6">医美行业合规脚本 + 6 红线守护 + 客户清单</p>
          <div className="grid md:grid-cols-2 gap-4">
            <a
              href="/docs/marketing/scripts/outreach_medical.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-pink-500 hover:shadow transition"
            >
              <p className="text-xs text-pink-600 mb-1">marketing/scripts/</p>
              <p className="font-bold mb-1">outreach_medical.md</p>
              <p className="text-sm text-gray-600">医美 30 家合规外呼脚本 + 6 红线守护</p>
            </a>
            <a
              href="/docs/legal/medical_compliance_redlines.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-pink-500 hover:shadow transition"
            >
              <p className="text-xs text-pink-600 mb-1">legal/</p>
              <p className="font-bold mb-1">medical_compliance_redlines.md</p>
              <p className="text-sm text-gray-600">6 医美合规红线 + AI 拦截逻辑 + 法规依据</p>
            </a>
            <a
              href="/docs/marketing/scripts/p0_8_clients.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-pink-500 hover:shadow transition"
            >
              <p className="text-xs text-pink-600 mb-1">marketing/scripts/</p>
              <p className="font-bold mb-1">p0_8_clients.md</p>
              <p className="text-sm text-gray-600">P0 8 家精选清单（含 3 家北京医美）</p>
            </a>
            <a
              href="/docs/finance/financial_model.md"
              className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-pink-500 hover:shadow transition"
            >
              <p className="text-xs text-pink-600 mb-1">finance/</p>
              <p className="font-bold mb-1">financial_model.md</p>
              <p className="text-sm text-gray-600">医美客户单价模型 + 单店 ARPU</p>
            </a>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-pink-500 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Sparkles className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">合规底线 + 获客效率，AI 全包</h2>
          <p className="text-lg opacity-90 mb-8">7 天免费试用 · 无需信用卡 · 合规检查全自动化</p>
          <Link
            to="/login"
            className="px-8 py-3 bg-white text-pink-500 rounded-md hover:bg-gray-100 inline-flex items-center gap-2 font-medium"
          >
            立即开始 <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>
    </>
  );
}
