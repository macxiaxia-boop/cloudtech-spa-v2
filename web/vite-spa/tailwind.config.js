/**
 * CloudTech Tailwind Config (完整版)
 * 来源：CLOUDTECH_DESIGN_SYSTEM.md（v2 视觉母版）
 *
 * 变更（vs v1）：
 * - brand 色系从 #0066FF 升级到 #2563EB 系（Tailwind blue）
 * - 补全 neutral/success/warning/destructive/accent 完整色阶
 * - 补全 radius / shadow / fontFamily / maxWidth 系统
 * - 启用 darkMode: 'class'（v1 无）
 * - 启用 tailwindcss-animate 插件
 */

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        /* Brand */
        brand: {
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
          DEFAULT: '#2563EB',
        },
        /* Neutral (slate) */
        neutral: {
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
        },
        /* Semantic */
        success: {
          50: '#ECFDF5',
          100: '#D1FAE5',
          500: '#10B981',
          600: '#059669',
          700: '#047857',
          DEFAULT: '#10B981',
        },
        warning: {
          50: '#FFFBEB',
          100: '#FEF3C7',
          500: '#F59E0B',
          600: '#D97706',
          700: '#B45309',
          DEFAULT: '#F59E0B',
        },
        destructive: {
          50: '#FEF2F2',
          100: '#FEE2E2',
          500: '#EF4444',
          600: '#DC2626',
          700: '#B91C1C',
          DEFAULT: '#EF4444',
        },
        /* Accent */
        'accent-purple': {
          50: '#F5F3FF',
          500: '#8B5CF6',
          600: '#7C3AED',
        },
        'accent-orange': {
          50: '#FFF7ED',
          500: '#F97316',
          600: '#EA580C',
        },
        /* Surfaces & semantic helpers (V23: rgb(var()) wrapper 支持 opacity /50 等) */
        border: 'rgb(var(--border-rgb, 226 232 240) / <alpha-value>)',
        input: 'rgb(var(--border-rgb, 226 232 240) / <alpha-value>)',
        ring: 'rgb(var(--ring-rgb, 37 99 235) / <alpha-value>)',
        background: 'rgb(var(--surface-base-rgb, 255 255 255) / <alpha-value>)',
        foreground: 'rgb(var(--text-primary-rgb, 15 23 42) / <alpha-value>)',
        primary: {
          DEFAULT: 'rgb(var(--brand-600-rgb, 37 99 235) / <alpha-value>)',
          foreground: 'rgb(var(--neutral-0-rgb, 255 255 255) / <alpha-value>)',
        },
        secondary: {
          DEFAULT: 'rgb(var(--neutral-100-rgb, 241 245 249) / <alpha-value>)',
          foreground: 'rgb(var(--neutral-900-rgb, 15 23 42) / <alpha-value>)',
        },
        muted: {
          DEFAULT: 'rgb(var(--neutral-100-rgb, 241 245 249) / <alpha-value>)',
          foreground: 'rgb(var(--neutral-500-rgb, 100 116 139) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'rgb(var(--neutral-100-rgb, 241 245 249) / <alpha-value>)',
          foreground: 'rgb(var(--neutral-900-rgb, 15 23 42) / <alpha-value>)',
        },
        popover: {
          DEFAULT: 'rgb(var(--surface-base-rgb, 255 255 255) / <alpha-value>)',
          foreground: 'rgb(var(--text-primary-rgb, 15 23 42) / <alpha-value>)',
        },
        card: {
          DEFAULT: 'rgb(var(--surface-base-rgb, 255 255 255) / <alpha-value>)',
          foreground: 'rgb(var(--text-primary-rgb, 15 23 42) / <alpha-value>)',
        },
      },
      borderRadius: {
        none: '0',
        sm: '0.375rem',
        DEFAULT: '0.5rem',
        md: '0.75rem',
        lg: '1rem',
        xl: '1.25rem',
        '2xl': '1.5rem',
        full: '9999px',
      },
      boxShadow: {
        xs: '0 1px 2px rgba(15, 23, 42, 0.04)',
        sm: '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
        DEFAULT: '0 2px 4px rgba(15, 23, 42, 0.06), 0 4px 8px rgba(15, 23, 42, 0.04)',
        md: '0 4px 8px rgba(15, 23, 42, 0.08), 0 2px 4px rgba(15, 23, 42, 0.04)',
        lg: '0 8px 16px rgba(15, 23, 42, 0.10), 0 4px 8px rgba(15, 23, 42, 0.06)',
        xl: '0 16px 32px rgba(15, 23, 42, 0.12), 0 8px 16px rgba(15, 23, 42, 0.08)',
        glow: '0 0 0 4px rgba(37, 99, 235, 0.12)',
        none: 'none',
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      maxWidth: {
        page: '1200px',
        'page-wide': '1280px',
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      transitionDuration: {
        fast: '150ms',
        normal: '250ms',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { transform: 'translateY(8px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.2s ease-out',
        'slide-up': 'slide-up 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
