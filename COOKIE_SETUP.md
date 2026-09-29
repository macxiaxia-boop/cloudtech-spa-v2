# Cookie 配置指南 · R321

> **用户原话**: "cookie 后面配"
> **目标**: 把 5 平台 cookie 文件从占位换成真值, 工作流自动从 `mock_fallback` 切到 `real`

## 5 平台 cookie 文件

| 平台 | 文件 | 状态 | 备注 |
|------|------|------|------|
| 抖音 | `D:\CloudTech-Portable\cookies_douyin.json` | 🔴 过期 (2025-07) | 需重新扫码 |
| 小红书 | `D:\CloudTech-Portable\cookies_xiaohongshu.json` | 🔴 过期 (2025-07) | 需重新扫码 |
| 视频号 | `D:\CloudTech-Portable\cookies_shipinhao.json` | 🟡 占位 | 模板已生成 |
| 公众号 | `D:\CloudTech-Portable\cookies_wechat_mp.json` | 🟡 占位 | 模板已生成 |
| B站 | `D:\CloudTech-Portable\cookies_bilibili.json` | 🟡 占位 | 模板已生成 |

## 重新登录方法

### 方法 1: Playwright 脚本 (推荐)

```python
# 双击运行 `D:\CloudTech-Portable\login_<平台>.py` (已存在 douyin / xhs)
# 浏览器打开 → 手动扫码 → 检测登录成功 → 自动保存 cookie 到对应文件
```

### 方法 2: 手动提取

1. Chrome 打开目标平台 + 扫码登录
2. F12 → Application → Cookies → 复制所有 cookies
3. 按 `[{name, value, domain, path, expires, httpOnly, secure, sameSite}, ...]` 格式粘贴到 `cookies_<平台>.json`

## 登录验证

```bash
curl http://127.0.0.1:5099/api/v3/v3_193_multi_workflow/douyin/workflow/run \
  -H "Content-Type: application/json" -d '{"industry":"decoration"}'
```

返回 `"publish": {"mode": "real", ...}` 即生效。

## 安全提醒

- cookie = 账号凭证, **不可提交到 git**
- 当前 `.gitignore` 应已包含 `cookies_*.json` (若未, 加一行)
- cookie 过期时间: 抖音/小红书 ~30 天, 视频号/公众号 ~2 小时 (微信风控), B站 ~7 天

## L2 自治完成的 prep work

- 5 个 cookie 文件**模板已就位**
- `v3_193_multi_workflow` 自动检测 cookie 内容 (REPLACE 视为占位 → mock)
- 一旦 cookie 真实, **无需改代码**, 重启 V22 gateway 即生效

## L4 待办 (用户授权)

- 真实登录 5 平台
- 按方法 1/2 替换 cookie 值
- 验证 publish 模式从 mock 切到 real