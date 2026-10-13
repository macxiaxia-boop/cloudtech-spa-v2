// Vite proxy for V4 backend (FastAPI on :8000)
// 接入 vite-spa 主构建时: 把此配置 import 到 vite.config.ts 的 defineConfig merge
import type { Config } from "vite";

export const v4ProxyConfig: Partial<Config> = {
  server: {
    port: 5098,
    proxy: {
      "/v4": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
};
