// 试用页 · 7 天免费试用
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Check, ArrowRight, Sparkles, Clock, Shield, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const STEPS = [
  {
    n: 1,
    title: '提交企业账户信息',
    desc: '企业名称、邮箱和密码由服务端验证。',
    time: '30 秒',
  },
  {
    n: 2,
    title: '服务端核验租户身份',
    desc: '注册响应必须通过签名会话和所属企业核验。',
    time: '1 分钟',
  },
  {
    n: 3,
    title: '查看已接通的业务工作流',
    desc: '仅允许访问已真实实现并已授权的业务功能。',
    time: '30 分钟',
  },
  {
    n: 4,
    title: '按真实权益使用',
    desc: '试用时长和套餐以服务端明确授权为准，不提供模拟权益。',
    time: '7 天',
  },
];

export function TryNowPage() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    tenant_name: '',
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setError('');
    setLoading(true);
    try {
      // Signed backend register + /api/saas/v1/me verification happen inside
      // AuthContext.register(). Never manufacture browser admin identities.
      const result = await register(
        form.email.trim(), form.password, form.tenant_name.trim(),
      );
      if (!result.ok) {
        setError(result.error || '服务端没有确认注册，不能进入工作空间。');
        return;
      }
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : '服务端未确认注册，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <section className="py-16 bg-gradient-to-br from-orange-50 via-white to-pink-50 dark:from-neutral-900 dark:via-neutral-800 dark:to-neutral-900">
        <div className="max-w-page mx-auto px-6 text-center">
          <span className="inline-flex items-center gap-2 px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-sm mb-4">
            <Sparkles className="w-3 h-3" /> 企业账户注册 · 服务端真实验证
          </span>
          <h1 className="text-4xl md:text-5xl font-bold mb-4">
            把企业需求接入
            <br />
            <span className="text-brand-500">真实工作空间</span>
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            面向企业的 AI 工作空间。未实现、未验证或未经授权的功能不会模拟开通。
          </p>
        </div>
      </section>

      {/* 4 步骤 */}
      <section className="py-12 bg-card">
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
                <p className="text-sm text-muted-foreground">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 表单 */}
      <section className="py-12 bg-muted">
        <div className="max-w-2xl mx-auto px-6">
          <div className="bg-card rounded-2xl shadow-xl border border-gray-200 p-8">
            {submitted ? (
              <div className="text-center py-8">
                <div className="text-6xl mb-4">🎉</div>
                <h2 className="text-2xl font-bold mb-2">企业账户验证成功</h2>
                <p className="text-muted-foreground mb-6">
                  <strong>{form.tenant_name}</strong>（{form.email}）已通过服务端身份及租户核验；试用期限和套餐以后端授权为准。
                </p>
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 text-left">
                  <p className="text-sm font-medium text-green-900 mb-2">下一步：</p>
                  <ol className="text-sm text-green-800 space-y-1">
                    <li>1. 打开已经验证的企业工作空间</li>
                    <li>2. 查看实际可用的工作流</li>
                    <li>3. 仅执行已授权的功能</li>
                  </ol>
                </div>
                <Link
                  to="/dashboard"
                  className="px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 inline-flex items-center gap-2"
                >
                  进入后台 <ArrowRight className="w-4 h-4" />
                </Link>
              </div>
            ) : (
              <>
                <h2 className="text-2xl font-bold mb-2">填写信息，验证企业账户</h2>
                <p className="text-sm text-gray-500 mb-6 flex items-center gap-1">
                  <Shield className="w-3 h-3" /> 信息提交给真实身份服务；后端不可用时不会生成模拟账号
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-3 text-sm text-red-700">
                      {error}
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium mb-1">公司/团队名称 *</label>
                    <input
                      required
                      placeholder="例如：深圳市云数科技有限公司"
                      value={form.tenant_name}
                      onChange={(e) => setForm({ ...form, tenant_name: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">邮箱 *</label>
                    <input
                      required
                      type="email"
                      placeholder="zhangsan@company.com"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">密码 *</label>
                    <input
                      required
                      type="password"
                      placeholder="不少于 6 位"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:border-brand-500 focus:outline-none"
                    />
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3 text-sm">
                    <p className="font-medium text-yellow-900 mb-1">试用说明：</p>
                    <ul className="text-yellow-800 space-y-0.5 text-xs">
                      <li>✓ 账户权限由真实服务端授权控制</li>
                      <li>✓ 未配置的模型及外部服务不会自动开通</li>
                      <li>✓ 注册不会自动付款，也不会生成模拟登录令牌</li>
                    </ul>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full px-6 py-3 bg-brand-500 text-white rounded-md hover:bg-brand-600 font-medium text-lg flex items-center justify-center gap-2 disabled:opacity-60"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" /> 开通中...
                      </>
                    ) : (
                      '服务端验证并创建企业账户'
                    )}
                  </button>

                  <p className="text-xs text-gray-500 text-center">
                    开通即代表同意 <Link to="/terms" className="text-brand-500">服务条款</Link> +{' '}
                    <Link to="/privacy" className="text-brand-500">隐私政策</Link>
                  </p>
                </form>
              </>
            )}
          </div>

          <p className="mt-8 text-sm text-muted-foreground">
            企业注册不等于已获试用或生产权限。付费模型、自动发布、套餐额度均需独立服务端授权。
          </p>
        </div>
      </section>
    </>
  );
}
