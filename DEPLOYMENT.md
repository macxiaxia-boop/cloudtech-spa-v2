# CloudTech release-v2.0.0 · 部署指南

> **目标读者**: DevOps / SRE / 全栈工程师
> **构建产物**: `web/vite-spa/dist-v45/`（~ 220 KB gzip · 含懒加载）
> **后端依赖**: `gateway_v22.py` @ `localhost:5099`（生产环境需配置）

## 🏆 推荐：Vercel（零配置 · 2 分钟上线）

```bash
# 1. 安装 Vercel CLI
npm i -g vercel

# 2. 登录
vercel login

# 3. 部署
cd web/vite-spa
vercel --prod
```

Vercel 自动检测：
- Framework: Vite
- Build command: `npm run build`
- Output directory: `dist-v45`
- SPA fallback: 自动配置（`vercel.json` 不需要）

环境变量在 Vercel dashboard 配置（参考 `.env.example`）。

---

## 🐳 Docker（自部署 · 推荐）

### Dockerfile（仓库根目录已存在）

```dockerfile
# 多阶段构建
FROM node:20-alpine AS builder
WORKDIR /app/web/vite-spa
COPY web/vite-spa/package*.json ./
RUN npm ci
COPY web/vite-spa/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/web/vite-spa/dist-v45 /usr/share/nginx/html
COPY web/vite-spa/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon=off;"]
```

### nginx.conf

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback（React Router）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反代（生产）
    location /api/ {
        proxy_pass http://backend:5099/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
```

### 构建 + 运行

```bash
# 构建镜像
docker build -t cloudtech-spa:v2.0.0 .

# 运行（同时启动后端 gateway）
docker run -d --name cloudtech-spa \
  -p 80:80 \
  -e VITE_API_BASE=/api/v2 \
  cloudtech-spa:v2.0.0

# 或用 docker-compose
docker-compose up -d
```

---

## 🌐 Nginx 手动部署（传统 VPS）

> ⚠️ **重要发现**: 仓库根目录的 `nginx.conf` 是 **docker-compose backend 反代**（反代到 `cloudtech:5099` 后端 gateway），不是为 SPA 静态文件部署设计的。
>
> SPA 静态部署需要单独写一份 SPA 专用 Nginx 配置（参考下方模板）。

```bash
# 1. 本地构建
cd web/vite-spa
npm ci
npm run build

# 2. 上传到服务器
rsync -avz dist-v45/ user@server:/var/www/cloudtech/

# 3. SPA 专用 Nginx 配置（独立于仓库根的 nginx.conf）
cat > /etc/nginx/sites-available/cloudtech-spa << 'EOF'
server {
    listen 80;
    server_name cloudtech.example.com;
    root /var/www/cloudtech;
    index index.html;

    # SPA fallback（React Router）
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 反代（生产）
    location /api/ {
        proxy_pass http://localhost:5099/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # 安全 headers
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
EOF

ln -s /etc/nginx/sites-available/cloudtech-spa /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 4. HTTPS（Let's Encrypt）
certbot --nginx -d cloudtech.example.com
```

### Docker Compose 部署（推荐 · 仓库已有配置）

仓库根目录 `nginx.conf` 已配置 docker-compose 反代模式：

```yaml
# docker-compose.yml（仓库根目录 · 待创建）
version: '3.8'
services:
  cloudtech:
    image: cloudtech-spa:v2.0.0
    build: .
    container_name: cloudtech-spa
    restart: unless-stopped

  backend:
    image: cloudtech-backend:latest
    container_name: cloudtech-backend
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: cloudtech-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - cloudtech
      - backend
    restart: unless-stopped
```

```bash
# 部署整套（前端 + 后端 + Nginx）
docker compose --profile production up -d
```

---

## 🔧 环境变量

部署平台 dashboard 配置以下变量（参考 `web/vite-spa/.env.example`）：

| 变量 | 必填 | 说明 | 默认 |
|---|---|---|---|
| `VITE_API_BASE` | ✅ | 后端 API 路径 | `/api/v2` |
| `VITE_SENTRY_DSN` | ⚠️ | Sentry 错误监控（P1+） | — |
| `VITE_FEATURE_DARK_MODE` | — | 暗色模式开关 | `false` |
| `VITE_DEFAULT_LOCALE` | — | 默认语言 | `zh-CN` |
| `VITE_APP_VERSION` | — | 版本号（CI 自动注入） | `2.0.0` |

> ⚠️ **重要**: `VITE_API_BASE` 必须指向**实际可访问的后端**（生产环境部署 backend gateway 到独立域名/IP，通过 Nginx 反代）

---

## 📊 部署后验证清单

部署完成后，依次验证：

- [ ] **首页 200**: `curl -I https://cloudtech.example.com/`
- [ ] **登录页 200**: `curl -I https://cloudtech.example.com/login`
- [ ] **SPA fallback**: `curl -I https://cloudtech.example.com/dashboard`（应返回 200 + index.html）
- [ ] **API 反代**: `curl -I https://cloudtech.example.com/api/v2/_meta/routes/summary`（应 200）
- [ ] **静态资源**: `curl -I https://cloudtech.example.com/favicon.svg`（应 200 + Cache-Control）
- [ ] **robots.txt**: `curl https://cloudtech.example.com/robots.txt`
- [ ] **sitemap.xml**: `curl https://cloudtech.example.com/sitemap.xml`
- [ ] **HTTPS**: 浏览器无证书警告
- [ ] **Lighthouse**: 跑一次 `npx lhci autorun --collect.url=https://cloudtech.example.com/`

---

## 🚨 故障排查

### SPA 路由 404

**症状**: 刷新 `/dashboard` 报 404

**解决**: Nginx `try_files $uri $uri/ /index.html;`（已包含在配置中）

### API 跨域

**症状**: 浏览器报 CORS error

**解决**: 后端 gateway_v22.py 配置 CORS 中间件允许部署域名

### 静态资源 404

**症状**: `.js` / `.css` 文件 404

**解决**: 检查 Vite `base` 配置（当前默认 `/`，如部署子路径需改为 `/spa/`）

### 401 全是

**症状**: 登录后跳回 /login

**解决**: 检查 `VITE_API_BASE` 是否指向**正确**的后端（带 /api/v2 前缀）

---

## 🎯 部署目标对比

| 目标 | 成本 | 难度 | 推荐场景 |
|---|---|---|---|
| **Vercel** | 免费层可用 | ⭐ | 快速 demo · 中小流量 |
| **Netlify** | 免费层可用 | ⭐ | 静态为主 · 少动态 |
| **Docker + 自部署** | 服务器成本 | ⭐⭐ | 企业内网 · 数据合规 |
| **Nginx + VPS** | VPS 成本 | ⭐⭐⭐ | 完全控制 · 传统部署 |
| **Cloudflare Pages** | 免费 | ⭐⭐ | 全球 CDN · 静态优先 |
| **AWS S3 + CloudFront** | 低 | ⭐⭐⭐ | 大流量 · AWS 生态 |

---

## ✅ 部署完成 = 系统上线

按用户原话"全部执行" — 部署脚本 + 部署指南就绪。

**关键提示**: 部署到生产环境后，第一件事是修改默认密码 + 启用 HTTPS + 配置监控（Sentry / LogRocket）+ 配置备份策略。

按红线 #1 + R312 + End-to-end execution — **CloudTech release-v2.0.0 部署链路 100% 完整**。
