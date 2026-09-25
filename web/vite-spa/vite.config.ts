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
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
