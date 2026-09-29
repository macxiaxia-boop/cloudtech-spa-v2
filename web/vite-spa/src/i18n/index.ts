/**
 * CloudTech i18n · 国际化 hook + context
 *
 * 用法：
 *   const { t, locale, setLocale } = useTranslation();
 *   t('login.welcome')          → "欢迎回来" 或 "Welcome Back"
 *   setLocale('en-US');         → 切换到英文
 *
 * 持久化：localStorage 'ct.locale'
 * 默认：浏览器语言 → 'zh-CN'
 */
import { createContext, createElement, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import zhCN from './zh-CN';
import enUS from './en-US';

export type Locale = 'zh-CN' | 'en-US';
export type Dict = typeof zhCN;

const DICTS: Record<Locale, Dict> = {
  'zh-CN': zhCN,
  'en-US': enUS,
};

const STORAGE_KEY = 'ct.locale';

function detectInitialLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'zh-CN' || saved === 'en-US') return saved;
  } catch { /* ignore */ }
  const browserLang = typeof navigator !== 'undefined' ? navigator.language : 'zh-CN';
  if (browserLang.startsWith('en')) return 'en-US';
  return 'zh-CN';
}

/** 路径取值：'login.welcome' → zhCN.login.welcome */
function getByPath(obj: any, path: string): string | undefined {
  return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : undefined), obj);
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectInitialLocale);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = (l: Locale) => {
    setLocaleState(l);
    try { localStorage.setItem(STORAGE_KEY, l); } catch { /* ignore */ }
  };

  const value = useMemo<I18nContextValue>(() => {
    const dict = DICTS[locale];
    return {
      locale,
      setLocale,
      t: (key: string): string => {
        const v = getByPath(dict, key);
        if (v !== undefined) return v;
        // 缺译回退到 zh-CN（保证中文始终可用）
        const fallback = getByPath(zhCN, key);
        if (fallback !== undefined) return fallback;
        return key; // 终极回退：返回原 key（开发可见）
      },
    };
  }, [locale]);

  return createElement(I18nContext.Provider, { value }, children);
}

export function useTranslation() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useTranslation must be used within I18nProvider');
  return ctx;
}

/** 语言切换组件 */
export function LocaleSwitcher({ className }: { className?: string }) {
  const { locale, setLocale } = useTranslation();
  return createElement(
    'select',
    {
      value: locale,
      onChange: (e: React.ChangeEvent<HTMLSelectElement>) => setLocale(e.target.value as Locale),
      className: className || 'h-8 px-2 text-xs rounded-md border border-[var(--border-default)] bg-[var(--surface-base)] text-[var(--text-secondary)] cursor-pointer focus:outline-none focus:border-brand-600',
      'aria-label': 'Language',
    },
    createElement('option', { value: 'zh-CN' }, '中文'),
    createElement('option', { value: 'en-US' }, 'English'),
  );
}
