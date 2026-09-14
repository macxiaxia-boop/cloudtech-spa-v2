// Phase 45 D17-23: SaaS 官网首页
// 收敛菜单：FE 3 员工 (content_writer / customer_service / market_researcher)
// 行业聚焦：装企 + 医美
import { Link } from 'react-router-dom';
import { Sparkles, Bot, Briefcase, Heart, ArrowRight, Hammer, Stethoscope } from 'lucide-react';

const FE_EMPLOYEES = [
  { id: 'content_writer', name: '内容创作', desc: 'AI 写公众号 / 小红书 / 抖音脚本', icon: '✍️' },
  { id: 'customer_service', name: '智能客服', desc: '7×24 自动应答 + 工单分流', icon: '💬' },
  { id: 'market_researcher', name: '市场调研', desc: '竞品监控 + 行业趋势报告', icon: '🔍' },
];

const INDUSTRIES = [
  { id: 'decoration', name: '装企全案获客', desc: '线索 → 画像 → 报价 → 直播', icon: Hammer, priority: 'primary' },
  { id: 'medical', name: '医美合规获客', desc: '线索 → 种草 → 术前 QA → 案例', icon: Stethoscope, priority: 'fallback' },
];

export function MarketingPage() {
  return (
    <>
      {/* HERO */}
      <section className="relative pt-12 pb-20 md:pt-20 md:pb-32 bg-gradient-to-br from-brand-50 to-white">
        <div className="max-w-page mx-auto px-6 lg:px-10">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-brand-100 text-brand-700 rounded-full text-sm mb-5">
              <Sparkles className="w-3 h-3" /> Phase 45 · 让 AI 成为数字员工
            </span>
            <h1 className="text-4xl md:text-5xl font-bold mb-6 leading-[1.1]">
              让 AI 成为 <span className="text-brand-500 italic">3 位前台员工</span> + 5 位后端员工，
              <br />
              像一支完整的团队一样工作。
            </h1>
            <p className="text-lg text-gray-600 mb-8">
              装企全案获客闭环 + 医美合规获客闭环，2 大行业管线，3+5 数字员工矩阵，
              把营销从"想法"变成"可追溯的产物"。
            </p>
            <div className="flex gap-4">
              <Link
                to="/pricing"
                className="px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2"
              >
                查看定价 <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/employees"
                className="px-6 py-3 border border-gray-300 rounded-md hover:border-brand-500 inline-flex items-center gap-2"
              >
                体验 FE 员工
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* FE 3 员工菜单收敛展示 */}
      <section className="py-20 bg-white">
        <div className="max-w-page mx-auto px-6">
          <div className="text-center mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 bg-brand-50 text-brand-700 rounded-full text-sm mb-3">
              <Bot className="w-3 h-3" /> 前台员工（3）
            </span>
            <h2 className="text-3xl font-bold mb-3">直接面向用户的 3 位数字员工</h2>
            <p className="text-gray-600">用户在前台能直接对话、调用、收产物的员工</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {FE_EMPLOYEES.map((emp) => (
              <div key={emp.id} className="p-6 border border-gray-200 rounded-lg hover:border-brand-500 hover:shadow-md transition">
                <div className="text-4xl mb-3">{emp.icon}</div>
                <h3 className="text-lg font-bold mb-2">{emp.name}</h3>
                <p className="text-gray-600 text-sm">{emp.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 行业聚焦 */}
      <section className="py-20 bg-gray-50">
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
                <div key={ind.id} className="p-6 bg-white border border-gray-200 rounded-lg hover:shadow-md transition">
                  <div className="flex items-center gap-3 mb-3">
                    <Icon className="w-6 h-6 text-brand-500" />
                    <h3 className="text-lg font-bold">{ind.name}</h3>
                    <span className={`text-xs px-2 py-1 rounded ${
                      ind.priority === 'primary' ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {ind.priority === 'primary' ? '重点' : '兜底'}
                    </span>
                  </div>
                  <p className="text-gray-600 text-sm">{ind.desc}</p>
                </div>
              );
            })}
          </div>
          <p className="text-center text-xs text-gray-400 mt-6">
            注：教培/餐饮/零售行业已 P3-BA 撤回（2026-09-11），永久 deprecated
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-brand-500 text-white">
        <div className="max-w-page mx-auto px-6 text-center">
          <Heart className="w-12 h-12 mx-auto mb-4" />
          <h2 className="text-3xl font-bold mb-4">开始你的数字员工之旅</h2>
          <p className="text-lg opacity-90 mb-8">7 天免费试用 · 无需信用卡 · 30 分钟跑通首条管线</p>
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
