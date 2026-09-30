// 试用页 · 7 天免费试用
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ArrowRight, Sparkles, Clock, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const STEPS = [
  {
    n: 1,
    title: '填写信息（30 秒）',
    desc: '公司名 + 手机号 + 邮箱。无需信用卡。',
    time: '30 秒',
  },
  {
    n: 2,
    title: '5 AI 员工就绪（自动）',
    desc: 'Hermes/Lyra/Athena/Apollo/Artemis 自动初始化，无需配置。',
    time: '1 分钟',
  },
  {
    n: 3,
    title: '跑你的第一条管线（30 分钟）',
    desc: '选模板（装企/医美/通用），AI 自动跑出第一条获客 / 内容 / 财务管线。',
    time: '30 分钟',
  },
  {
    n: 4,
    title: '看真实数据 + 试用 7 天',
    desc: '监控 / 漏斗 / 财务 / 客户清单全开。任意功能免费用 7 天。',
    time: '7 天',
  },
];

export function TryNowPage() {
  const [form, setForm] = useState({
    company: '',
    name: '',
    phone: '',
    email: '',
    industry: 'decoration',
    scale: 'small',
  });
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // 实际提交到后端 (mock)
    setSubmitted(true);
  };

  return (
    <>
      <section className="py-16 bg-gradient-to-br from-orange-50 via-white to-pink-50">
        <div className="max-w-page mx-auto px-6 text-center">
          <span className="inline-flex items-center gap-2 px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm mb-4">
            <Sparkles className="w-3 h-3" /> 7 天免费试用 · 无需信用卡
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            30 分钟跑通你公司的
            <br />
            <span className="text-brand-500">第一条管线</span>
          </h1>
          <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
            不懂技术也能用。装企老板 / 医美老板 / 中小企业主 — 自己填表，5 AI 员工自动跑。
          </p>
        </div>
      </section>

      {/* 4 步骤 */}
      <section className="py-12 bg-white">
        <div className="max-w-page mx-auto px-6">
          <h2 className="text-2xl font-bold mb-8 text-center">4 步跑通</h2>
          <div className="grid md:grid-cols-4 gap-4">
            {STEPS.map((s) => (
              <div key={s.n} className="p-5 bg-gradient-to-br from-gray-50 to-white rounded-lg border border-gray-200">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-8 h-8 bg-brand-500 text-white rounded-full flex items-center justify-center font-bold">
                    {s.n}
                  </div>
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {s.time}
                  </span>
                </div>
                <h3 className="font-bold mb-2">{s.title}</h3>
                <p className="text-sm text-gray-600">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 表单 */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-2xl mx-auto px-6">
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-8">
            {submitted ? (
              <div className="text-center py-8">
                <div className="text-6xl mb-4">🎉</div>
                <h2 className="text-2xl font-bold mb-2">试用开通成功！</h2>
                <p className="text-gray-600 mb-6">
                  我们已向 <strong>{form.email}</strong> 发送开通邮件 + 登录链接。
                </p>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left">
                  <p className="text-sm font-medium text-blue-900 mb-2">下一步：</p>
                  <ol className="text-sm text-blue-800 space-y-1">
                    <li>1. 登录邮箱，点击激活链接</li>
                    <li>2. 进入 /onboarding 走 5 步引导</li>
                    <li>3. 让 5 AI 员工跑你的第一条管线</li>
                  </ol>
                </div>
                <Link
                  to="/dashboard"
                  className="px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2"
                >
                  先看后台 <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            ) : (
              <>
                <h2 className="text-2xl font-bold mb-2">填写信息，立即开通</h2>
                <p className="text-sm text-gray-500 mb-6 flex items-center gap-1">
                  <Shield className="w-3 h-3" /> 信息加密 · 仅用于开通账号
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">公司名 *</label>
                      <input
                        required
                        value={form.company}
                        onChange={(e) => setForm({ ...form, company: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">你的名字 *</label>
                      <input
                        required
                        value={form.name}
                        onChange={(e) => setForm({ ...form, name: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">手机号 *</label>
                      <input
                        required
                        type="tel"
                        value={form.phone}
                        onChange={(e) => setForm({ ...form, phone: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">邮箱 *</label>
                      <input
                        required
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">行业</label>
                      <select
                        value={form.industry}
                        onChange={(e) => setForm({ ...form, industry: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                      >
                        <option value="decoration">装企</option>
                        <option value="medical">医美</option>
                        <option value="general">通用</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">规模</label>
                      <select
                        value={form.scale}
                        onChange={(e) => setForm({ ...form, scale: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                      >
                        <option value="small">1-5 人</option>
                        <option value="medium">6-20 人</option>
                        <option value="large">21+ 人</option>
                      </select>
                    </div>
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 text-sm">
                    <p className="font-medium text-yellow-900 mb-1">📞 试用期内你会收到：</p>
                    <ul className="text-yellow-800 space-y-0.5 text-xs">
                      <li>✓ 1v1 微信群（5 人服务群 · 24h 内回复）</li>
                      <li>✓ 7 天后 1v1 续费回访（不强制）</li>
                      <li>✓ 月度 OPC 案例分享会邀请</li>
                    </ul>
                  </div>

                  <button
                    type="submit"
                    className="w-full px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 font-medium text-lg"
                  >
                    🚀 立即开通 7 天试用
                  </button>

                  <p className="text-xs text-gray-500 text-center">
                    开通即代表同意 <Link to="/terms" className="text-brand-500">服务条款</Link> +{' '}
                    <Link to="/privacy" className="text-brand-500">隐私政策</Link>
                  </p>
                </form>
              </>
            )}
          </div>

          {/* 试用包含什么 */}
          <div className="mt-8 grid md:grid-cols-2 gap-4">
            {[
              '5 AI 数字员工全功能',
              '11 个 SPA 页面无限访问',
              '80 家客户清单 + 外呼',
              '16 份公司文档下载',
              '监控仪表盘 + 告警',
              '7 天 1v1 微信群',
            ].map((f) => (
              <div key={f} className="flex items-center gap-2 text-sm">
                <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                <span>{f}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
