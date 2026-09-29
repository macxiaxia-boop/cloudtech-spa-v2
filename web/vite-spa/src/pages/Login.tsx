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
  const [remember, setRemember] = useState(true);
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
      navigate('/workspace/select');
    } else {
      setError(result.error || t('common.error'));
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6" style={{ background: 'var(--gradient-ice)' }}>
      <div className="w-full max-w-md bg-[var(--surface-base)] rounded-xl shadow-xl border border-[var(--border-default)] p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
              <Cloud className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-[var(--text-primary)] text-base">CloudTech</span>
          </div>
          <LocaleSwitcher />
        </div>

        <h1 className="text-2xl font-bold mb-1.5">{t('login.welcome')}</h1>
        <p className="text-sm text-[var(--text-secondary)] mb-6">{t('login.subtitle')}</p>

        <div className="flex border-b border-[var(--border-default)] mb-6">
          <button type="button" className="flex-1 pb-3 text-sm font-medium text-brand-600 border-b-2 border-brand-600">{t('login.email_tab')}</button>
          <button type="button" className="flex-1 pb-3 text-sm font-medium text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors">{t('login.sso_tab')}</button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-destructive-bg border border-destructive-100 rounded-lg flex items-start gap-2 text-sm text-destructive-700">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-5">
          <div className="space-y-1.5">
            <Label htmlFor="account">{t('login.email_placeholder')}</Label>
            <Input id="account" type="text" placeholder={t('login.email_placeholder')} value={account} onChange={(e) => setAccount(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">{t('login.password_placeholder')}</Label>
            <div className="relative">
              <Input id="password" type={showPassword ? 'text' : 'password'} placeholder={t('login.password_placeholder')} value={password} onChange={(e) => setPassword(e.target.value)} required className="pr-10" />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]" aria-label={showPassword ? 'hide' : 'show'}>
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="rounded border-[var(--border-default)] text-brand-600 focus:ring-brand-500/20" />
              <span className="text-[var(--text-secondary)]">{t('login.remember')}</span>
            </label>
            <Link to="/forgot-password" className="text-brand-600 hover:text-brand-700">{t('login.forgot')}</Link>
          </div>

          <Button type="submit" size="lg" disabled={loading} className="w-full mt-1">
            {loading ? t('login.submitting') : t('login.submit')}
          </Button>
        </form>

        <div className="relative my-5">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-[var(--border-default)]" /></div>
          <div className="relative flex justify-center text-xs"><span className="bg-[var(--surface-base)] px-3 text-[var(--text-tertiary)]">{t('login.sso_divider')}</span></div>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-6">
          {[t('login.sso_google'), t('login.sso_github'), t('login.sso_microsoft'), t('login.sso_wechat')].map((p) => (
            <button key={p} type="button" className="h-10 rounded-md border border-[var(--border-default)] hover:bg-[var(--surface-muted)] transition-colors text-xs font-medium text-[var(--text-secondary)]">{p}</button>
          ))}
        </div>

        <p className="text-center text-sm text-[var(--text-secondary)]">
          {t('login.no_account')}
          <Link to="/register" className="text-brand-600 hover:text-brand-700 font-medium ml-1">{t('login.register_link')}</Link>
        </p>
      </div>
    </div>
  );
}
