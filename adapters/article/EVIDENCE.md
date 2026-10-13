# EVIDENCE.md — article adapters (WP-ARTICLE-REWRITE)

## 真实接口调用

| 调用项 | 状态 |
|--------|------|
| 真实网络爬虫 | ❌ 禁止，mock-only |
| 外部版权 API | ❌ 禁止，mock-only |
| 本地 ffmpeg | ❌ 不适用 (article adapters 不调 ffmpeg) |
| 网络 HTTP 请求 | 0 次 |

## Production Ready

**NO**

## License Checker 严格性策略

- 默认 `license = 'unknown'` (需 user 确认)
- 白名单匹配 `public_domain`: wikimedia.org / pixabay.com / pexels.com / unsplash.com
- 商业平台默认 `commercial_unknown`: 微信/bilibili/抖音/小红书/快手/youtube 等
- `cc-by` 暂不列入白名单，需 user 拍板

## 下一步 (L4 等待 user 拍板)

1. **接真实爬虫**: 需 user 拍板爬虫方案 (Playwright / HTTP + BeautifulSoup / Coze)
2. **接版权 API**: 需 user 拍板版权查询服务方 (Google Cloud Vision / 视觉中国 / 自建)
3. **接媒体 CDN**: 需 user 拍板媒体存储方案

## Mock 合同

所有 stub 返回值均含 `mock: True`，外部调用方应校验此字段。
