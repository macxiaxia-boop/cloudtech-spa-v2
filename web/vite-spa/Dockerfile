# CloudTech SPA Frontend · Multi-stage Docker Build
# 产物: dist-v45/ (~240 KB gzip) → nginx:alpine

# ===== Stage 1: Build =====
FROM node:20-alpine AS builder

WORKDIR /app

# 单独 copy package.json 利用 layer cache
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund

# copy 源码 + 构建
COPY . ./
RUN npm run build

# ===== Stage 2: Production nginx =====
FROM nginx:1.27-alpine

# CloudTech 品牌标识
LABEL app="cloudtech-spa" version="2.0.0" maintainer="CloudTech Team"

# 删除默认 nginx 配置
RUN rm /etc/nginx/conf.d/default.conf

# SPA 专用 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist-v45 /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

EXPOSE 80

# 前台运行 nginx
CMD ["nginx", "-g", "daemon=off;"]
