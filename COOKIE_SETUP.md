# Cookie 导入指南 — 解锁小红书/抖音真实数据采集

## 三步完成

### Step 1: 安装 Chrome 扩展

1. 打开 Chrome → 扩展商店搜索 **"EditThisCookie"**
2. 安装后右上角会出现 🍪 图标

### Step 2: 导出 Cookie

1. **打开小红书网页版** → https://www.xiaohongshu.com
2. 扫码登录你的小红书账号
3. 登录后点击右上角 🍪 → 点 **Export** (导出按钮)
4. 复制弹出的 JSON 文本
5. 粘贴到 `cookies_xiaohongshu.json` 文件

**抖音同理：**
1. 打开 https://www.douyin.com 并登录
2. 🍪 → Export → 复制 JSON
3. 粘贴到 `cookies_douyin.json` 文件

### Step 3: 放文件

将两个 JSON 文件放到这个目录：
```
D:\浏览器\CloudTech-v2.0.0\CloudTech-Portable\
├── cookies_xiaohongshu.json
└── cookies_douyin.json
```

完成后运行测试采集：
```bash
node scraper_browser.js --batch
```

---

## Cookie 文件格式示例

```json
[
  {
    "domain": ".xiaohongshu.com",
    "name": "web_session",
    "value": "xxxxxxxxxxxxx",
    "path": "/",
    "httpOnly": true,
    "secure": true
  },
  {
    "domain": ".xiaohongshu.com", 
    "name": "webId",
    "value": "xxxxxxxxxxxxx",
    "path": "/"
  }
]
```

---

## 注意事项

- Cookie 有效期通常 7-30 天，过期需重新导入
- 不要分享 Cookie 文件给任何人
- Cookie 文件已在 `.gitignore` 中排除
- 建议每两周刷新一次登录态
