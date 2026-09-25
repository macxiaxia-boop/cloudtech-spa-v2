// Onboarding 触发器 · 首次访问自动弹 5 步引导
import { useEffect, useState } from 'react';
import { Onboarding } from './Onboarding';

const STORAGE_KEY = 'cloudtech_onboarding_done';

export function OnboardingTrigger() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    // 首次访问检测
    if (typeof window === 'undefined') return;
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      // 延迟 1.5 秒弹，让首页先加载
      const t = setTimeout(() => setShow(true), 1500);
      return () => clearTimeout(t);
    }
  }, []);

  const handleClose = () => {
    setShow(false);
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, 'true');
    }
  };

  if (!show) return null;
  return <Onboarding onComplete={handleClose} />;
}
