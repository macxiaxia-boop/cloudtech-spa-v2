/**
 * CloudTech Login · v3 视觉母版 02 模块
 * 居中卡片 + 全屏冰山渐变背景 + AuthContext + i18n
 */
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Cloud, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/contexts/AuthContext';
import { useTranslation, LocaleSwitcher } from '@/i18n';

export function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { t } = useTranslation();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const result = await login(account, password);
    setLoading(false);
    if (result.ok) {
      navigate('/dashboard');
    } else {
      setError(result.error || t('common.error'));
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-6 bg-gradient-to-br from-orange-50 via-white to-pink-50 dark:from-neutral-900 dark:via-neutral-800 dark:to-neutral-900">
      <div className="w-full max-w-md bg-card rounded-xl shadow-xl border border-border p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
              <Cloud className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-foreground text-base">CloudTech</span>
          </div>
          <LocaleSwitcher />
        </div>

        <h1 className="text-2xl font-bold mb-1.5">{t('login.welcome')}</h1>
        <p className="text-sm text-muted-foreground mb-6">{t('login.subtitle')}</p>

        <p className="text-sm text-muted-foreground mb-6 border-b border-border pb-3">
          当前仅支持已接通的企业邮箱密码登录；第三方单点登录尚未上线。
        </p>

        {error && (
          <div className="mb-4 p-3 bg-destructive-bg border border-destructive-100 rounded-lg flex items-start gap-2 text-sm text-destructive-700">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-5">
          <div className="space-y-1.5">
            <Label htmlFor="account">{t('login.email_placeholder')}</Label>
            <Input id="account" type="email" autoComplete="username" placeholder={t('login.email_placeholder')} value={account} onChange={(e) => setAccount(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">{t('login.password_placeholder')}</Label>
            <div className="relative">
              <Input id="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder={t('login.password_placeholder')} value={password} onChange={(e) => setPassword(e.target.value)} required className="pr-10" />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-muted-foreground" aria-label={showPassword ? '隐藏密码' : '显示密码'}>
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <p className="text-xs text-muted-foreground">
            尚未启用自助密码重置；如需找回账号，请通过已核实的组织管理员处理。
          </p>

          <Button type="submit" size="lg" disabled={loading} className="w-full mt-1">
            {loading ? t('login.submitting') : t('login.submit')}
          </Button>
        </form>


        <p className="text-center text-sm text-muted-foreground">
          {t('login.no_account')}
          <Link to="/register" className="text-brand-600 hover:text-brand-700 font-medium ml-1">{t('login.register_link')}</Link>
        </p>
      </div>
    </main>
  );
}
