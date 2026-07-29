# CloudTech v2.1 — AI 数字营销中台

> 23工具 · 6引擎 · 1键出内容。AI写得出，检测过得去，发布不用改。

---

## 快速开始

### 本地运行

```bash
pip install -r requirements.txt
python run_prod.py
# 打开 http://localhost:5099
```

### Docker 部署

```bash
docker-compose up -d
# 打开 http://localhost:5099
```

### 生产部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实值

# 2. 启动 (PostgreSQL + HTTPS)
docker-compose --profile production up -d
```

---

## 服务端口

| 端口 | 服务 | 地址 |
|------|------|------|
| 5099 | 管理后台 | http://localhost:5099/admin |
| 8501 | AI 仪表盘 | http://localhost:8501 |
| 8502 | 装企控制台 | http://localhost:8502 |

---

## 功能模块

### 内容生产
- **AI 文案生成**: 小红书/公众号/知乎多平台
- **内容改写**: 一键去 AI 腔，降重优化
- **视频脚本**: 短视频口播脚本自动生成
- **批量生产**: 批量选题→批量生成→批量发布

### 数据分析
- **数据看板**: 可视化仪表盘
- **趋势分析**: 自动检测数据趋势
- **竞品分析**: 对标账号深度拆解

### 平台管理
- **多租户**: 企业级租户隔离
- **API 管理**: Key 管理 + 限流 + 用量追踪
- **许可管理**: 机器指纹 + RSA 签名验证
- **支付**: 微信支付接入

### 运营后台
- **MRR 仪表盘**: 月度收入实时追踪
- **用户管理**: 租户列表/状态/用量
- **错误监控**: 聚合追踪 + Sentry 集成

---

## API 文档

### 认证

```
POST /api/auth/register  注册 {"email","password","name","company","plan"}
POST /api/auth/login     登录 {"email","password"}
```

### 支付

```
POST /api/payment/create-order  创建订单 {"plan_id","user_id"}
```

### 运营

```
GET /api/admin/ops      运营数据 (MRR/用户/用量)
GET /api/admin/errors   错误统计
```

### 系统

```
GET /health             健康检查
GET /api/system/status  系统状态
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CLOUDTECH_PORT` | 服务端口 | 5099 |
| `DB_TYPE` | sqlite 或 postgresql | sqlite |
| `PG_DSN` | PostgreSQL 连接串 | — |
| `JWT_SECRET` | JWT 密钥 | 自动生成 |
| `SMTP_HOST` | 邮件服务器 | — |
| `WECHAT_APP_ID` | 微信 AppID | — |
| `SENTRY_DSN` | Sentry 错误追踪 | — |

---

## 测试

```bash
pytest tests/ -v
```

---

## 技术栈

- **后端**: Python / Flask / Waitress
- **数据**: SQLite / PostgreSQL
- **AI 仪表盘**: Streamlit
- **支付**: 微信支付 V2/V3
- **认证**: JWT + PBKDF2
- **部署**: Docker / Nginx

---

CloudTech v2.1.0 | Built with AI
