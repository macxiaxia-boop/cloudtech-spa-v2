/**
 * CloudTech Register · v3 视觉母版 02 模块
 * 复用 Login 居中卡片样式 + 注册字段 + i18n
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Cloud, Eye, EyeOff, Check } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useTranslation, LocaleSwitcher } from '@/i18n';

export function RegisterPage() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    company: '',
    email: '',
    password: '',
    confirm: '',
    agreed: false,
    code: '',
  });

  const passwordStrength = (() => {
    const p = form.password;
    if (!p) return 0;
    let score = 0;
    if (p.length >= 8) score++;
    if (/[A-Z]/.test(p)) score++;
    if (/[0-9]/.test(p)) score++;
    if (/[^a-zA-Z0-9]/.test(p)) score++;
    return score;
  })();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.agreed) return;
    if (form.password !== form.confirm) return;
    setLoading(true);
    setTimeout(() => navigate('/workspace/select'), 500);
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--gradient-ice)' }}>
      <div className="w-full max-w-md bg-card rounded-xl shadow-xl border border-border p-8">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
            <Cloud className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-foreground text-base">CloudTech</span>
        </div>

        <h1 className="text-2xl font-bold mb-1.5">创建账户</h1>
        <p className="text-sm text-muted-foreground mb-6">开始你的 AI 工作空间之旅</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-5">
          <div className="space-y-1.5">
            <Label htmlFor="company">公司名称</Label>
            <Input id="company" placeholder="我的公司" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">工作邮箱</Label>
            <Input id="email" type="email" placeholder="name@company.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="code">验证码</Label>
            <div className="flex gap-2">
              <Input id="code" placeholder="6 位验证码" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required className="flex-1" />
              <Button type="button" variant="outline" size="default">发送验证码</Button>
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">密码</Label>
            <div className="relative">
              <Input id="password" type={showPassword ? 'text' : 'password'} placeholder="至少 8 位，含大小写数字符号" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required className="pr-10" />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {form.password && (
              <div className="flex gap-1 mt-1">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className={`flex-1 h-1 rounded-full ${i <= passwordStrength ? (passwordStrength <= 1 ? 'bg-destructive-500' : passwordStrength <= 2 ? 'bg-warning-500' : 'bg-success-500') : 'bg-[var(--neutral-200)]'}`} />
                ))}
              </div>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm">确认密码</Label>
            <Input id="confirm" type="password" placeholder="再次输入密码" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} required />
            {form.confirm && form.password !== form.confirm && (
              <p className="text-xs text-destructive-600">两次输入的密码不一致</p>
            )}
            {form.confirm && form.password === form.confirm && (
              <p className="text-xs text-success-600 flex items-center gap-1"><Check className="w-3 h-3" />密码一致</p>
            )}
          </div>
          <label className="flex items-start gap-2 cursor-pointer text-sm">
            <input type="checkbox" checked={form.agreed} onChange={(e) => setForm({ ...form, agreed: e.target.checked })} className="mt-0.5 rounded border-border text-brand-600 focus:ring-brand-500/20" />
            <span className="text-muted-foreground">
              我已阅读并同意 <a href="#" className="text-brand-600 hover:underline">服务条款</a> 和 <a href="#" className="text-brand-600 hover:underline">隐私政策</a>
            </span>
          </label>
          <Button type="submit" size="lg" disabled={loading || !form.agreed || form.password !== form.confirm} className="w-full mt-1">
            {loading ? '注册中…' : '创建账户'}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          已有账户？
          <Link to="/login" className="text-brand-600 hover:text-brand-700 font-medium ml-1">立即登录</Link>
        </p>
      </div>
    </div>
  );
}
