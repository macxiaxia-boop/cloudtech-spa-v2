/**
 * CloudTech ThemeToggle · V23 视觉重做 (2026-09-30)
 * 浅色/深色 模式切换 · localStorage 持久化 · Sun/Moon icon
 *
 * 用法:
 *   import { ThemeToggle } from '@/components/ThemeToggle';
 *   <ThemeToggle />
 */
import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';

const STORAGE_KEY = 'ct.theme';

function getInitial(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* ignore */ }
  if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark';
  return 'light';
}

function applyTheme(theme: 'light' | 'dark') {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>(getInitial);

  useEffect(() => {
    applyTheme(theme);
    try { localStorage.setItem(STORAGE_KEY, theme); } catch { /* ignore */ }
  }, [theme]);

  function toggle() {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={theme === 'light' ? '切换深色模式' : '切换浅色模式'}
      title={theme === 'light' ? '切换深色模式' : '切换浅色模式'}
    >
      {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
    </Button>
  );
}