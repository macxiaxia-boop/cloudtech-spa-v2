import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// CloudTech SaaS Vite 配置 — Phase 45 D17-23
// 注：web/dist/ 是历史 build，源码已 untracked 在 web/src/pages/Marketing.tsx
// 本配置支持从 web/vite-spa/ 起一个新 SPA（与 dist 并行）
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5098,  // 与 gateway 5099 错开
    proxy: {
      '/api/v2': 'http://localhost:5099',  // 代理到 FastAPI gateway
    },
  },
  build: {
    outDir: 'dist-v45',
    sourcemap: true,
    target: 'es2020',
    // R362 Lighthouse perf 优化 · 把大 vendor 拆出 main chunk (治本 perf 64)
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react':       ['react', 'react-dom', 'react-router-dom'],
          'vendor-radix':       ['radix-ui', '@radix-ui/react-dialog', 'class-variance-authority', 'clsx', 'tailwind-merge'],
          'vendor-icons':       ['lucide-react'],
          'vendor-motion':      ['framer-motion'],
          'vendor-flow':        ['@xyflow/react'],
          'vendor-forms':       ['react-hook-form', '@hookform/resolvers', 'zod'],
          'vendor-other':       ['cmdk', 'sonner'],
        },
      },
    },
    chunkSizeWarningLimit: 800,  // 治本 main chunk > 500KB warning
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
