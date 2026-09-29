/**
 * CloudTech Design System Tokens (TS mirror)
 * 来源：CLOUDTECH_DESIGN_SYSTEM.md（基于 v2 视觉母版 SHA256 5d6f1e40...）
 *
 * 用途：在 TS 代码中引用颜色/间距等 token（与 globals.css 同步）
 */

export const brand = {
  50: '#EFF6FF',
  100: '#DBEAFE',
  200: '#BFDBFE',
  300: '#93C5FD',
  400: '#60A5FA',
  500: '#3B82F6',
  600: '#2563EB',
  700: '#1D4ED8',
  800: '#1E40AF',
  900: '#1E3A8A',
  950: '#172554',
} as const;

export const neutral = {
  0: '#FFFFFF',
  50: '#F8FAFC',
  100: '#F1F5F9',
  200: '#E2E8F0',
  300: '#CBD5E1',
  400: '#94A3B8',
  500: '#64748B',
  600: '#475569',
  700: '#334155',
  800: '#1E293B',
  900: '#0F172A',
  950: '#020617',
} as const;

export const success = {
  50: '#ECFDF5',
  100: '#D1FAE5',
  500: '#10B981',
  600: '#059669',
  700: '#047857',
  bg: 'rgba(16, 185, 129, 0.08)',
} as const;

export const warning = {
  50: '#FFFBEB',
  100: '#FEF3C7',
  500: '#F59E0B',
  600: '#D97706',
  700: '#B45309',
  bg: 'rgba(245, 158, 11, 0.08)',
} as const;

export const destructive = {
  50: '#FEF2F2',
  100: '#FEE2E2',
  500: '#EF4444',
  600: '#DC2626',
  700: '#B91C1C',
  bg: 'rgba(239, 68, 68, 0.08)',
} as const;

export const accent = {
  purple: { 500: '#8B5CF6', 600: '#7C3AED' },
  orange: { 500: '#F97316', 600: '#EA580C' },
} as const;

export const radius = {
  none: '0',
  sm: '0.375rem',
  DEFAULT: '0.5rem',
  md: '0.75rem',
  lg: '1rem',
  xl: '1.25rem',
  '2xl': '1.5rem',
  full: '9999px',
} as const;

export const shadow = {
  xs: '0 1px 2px rgba(15, 23, 42, 0.04)',
  sm: '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
  DEFAULT: '0 2px 4px rgba(15, 23, 42, 0.06), 0 4px 8px rgba(15, 23, 42, 0.04)',
  md: '0 4px 8px rgba(15, 23, 42, 0.08), 0 2px 4px rgba(15, 23, 42, 0.04)',
  lg: '0 8px 16px rgba(15, 23, 42, 0.10), 0 4px 8px rgba(15, 23, 42, 0.06)',
  xl: '0 16px 32px rgba(15, 23, 42, 0.12), 0 8px 16px rgba(15, 23, 42, 0.08)',
  glow: '0 0 0 4px rgba(37, 99, 235, 0.12)',
} as const;

export const sidebar = {
  width: '240px',
  widthCollapsed: '64px',
} as const;

export const header = {
  height: '56px',
} as const;

export const layout = {
  maxWidth: '1280px',
} as const;
