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
    // R1870 Lighthouse perf (round 19): tighten bundle + CSS purge + LCP preload
    cssCodeSplit: true,
    minify: 'terser',
    terserOptions: {
      compress: { drop_console: true, drop_debugger: true },
    },
    reportCompressedSize: false,  // Lighthouse reads raw, not gzip
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react':       ['react', 'react-dom', 'react-router-dom'],
          'vendor-radix':       ['radix-ui', '@radix-ui/react-dialog', 'class-variance-authority', 'clsx', 'tailwind-merge'],
          'vendor-icons':       ['lucide-react'],
          'vendor-flow':        ['@xyflow/react'],
          'vendor-other':       ['cmdk', 'sonner'],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
