/**
 * CloudTech Login · v3 视觉母版 02 模块
 * 居中卡片 + 全屏冰山渐变背景
 *
 * v3 实测布局：CloudTech Logo + 欢迎回来 + 邮箱/手机/密码 + 记住我 + 登录 + 第三方 + 立即注册
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Cloud, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export function LoginPage() {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    // 模拟登录：mock 实现（真实接入 AuthContext 后替换）
    setTimeout(() => {
      navigate('/workspace/select');
    }, 500);
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ background: 'var(--gradient-ice)' }}
    >
      <div className="w-full max-w-md bg-[var(--surface-base)] rounded-xl shadow-xl border border-[var(--border-default)] p-8">
        {/* Logo */}
        <div className="flex items-center gap-2 mb-6">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
            <Cloud className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-[var(--text-primary)] text-base">CloudTech</span>
        </div>

        {/* 标题 */}
        <h1 className="text-2xl font-bold mb-1.5">欢迎回来</h1>
        <p className="text-sm text-[var(--text-secondary)] mb-6">登录你的 CloudTech 账户</p>

        {/* 登录方式 Tab */}
        <div className="flex border-b border-[var(--border-default)] mb-6">
          <button className="flex-1 pb-3 text-sm font-medium text-brand-600 border-b-2 border-brand-600">
            邮箱登录
          </button>
          <button className="flex-1 pb-3 text-sm font-medium text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors">
            SSO 登录
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-5">
          <div className="space-y-1.5">
            <Label htmlFor="account">邮箱 / 手机号</Label>
            <Input
              id="account"
              type="text"
              placeholder="name@company.com"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">密码</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
                aria-label={showPassword ? '隐藏密码' : '显示密码'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="rounded border-[var(--border-default)] text-brand-600 focus:ring-brand-500/20"
              />
              <span className="text-[var(--text-secondary)]">记住我</span>
            </label>
            <Link to="/forgot-password" className="text-brand-600 hover:text-brand-700">
              忘记密码？
            </Link>
          </div>

          <Button type="submit" size="lg" disabled={loading} className="w-full mt-1">
            {loading ? '登录中…' : '登录'}
          </Button>
        </form>

        {/* 第三方 SSO */}
        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[var(--border-default)]" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-[var(--surface-base)] px-3 text-[var(--text-tertiary)]">其他登录方式</span>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-6">
          {['Google', 'GitHub', 'Microsoft', '微信'].map((p) => (
            <button
              key={p}
              type="button"
              className="h-10 rounded-md border border-[var(--border-default)] hover:bg-[var(--surface-muted)] transition-colors text-xs font-medium text-[var(--text-secondary)]"
            >
              {p}
            </button>
          ))}
        </div>

        {/* 立即注册 */}
        <p className="text-center text-sm text-[var(--text-secondary)]">
          没有账户？
          <Link to="/register" className="text-brand-600 hover:text-brand-700 font-medium ml-1">
            立即注册
          </Link>
        </p>
      </div>
    </div>
  );
}
