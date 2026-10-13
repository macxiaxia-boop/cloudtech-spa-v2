# adapters.media — EVIDENCE (Mock-Only Stub)

## 真实 API 调用: 0
所有 provider (Jimeng/Yihook/Kling/DoubaoSeedream) 均为 mock stub，
使用 PIL.Image.new 生成 1×1 white PNG，base64 编码，不写文件，不发 HTTP。

## 真实 Provider Endpoint: 未访问
- jimeng (即梦)       — JIMENG_API_BASE / JIMENG_API_KEY 占位，未读取
- yihook              — YIHOOK_API_BASE / YIHOOK_API_KEY 占位，未读取
- kling (可灵)        — KLING_API_BASE / KLING_API_KEY 占位，未读取
- doubao_seedream     — DOUBAO_SEEDREAM_API_BASE / DOUBAO_SEEDREAM_API_KEY 占位，未读取

## Production Ready: NO
本模块为 mock-only stub，用于:
- 门禁逻辑验证
- 幂等/预算集成验证
- 后续 user 拍 provider 策略后，写真实 HTTP client 替换 stub

## 真实环境
mcp_credentials.env 中有 jimeng/Yihook/kling/dashscope key，
本次完全不访问。

## 下一步
1. User 拍板 provider 策略 (选哪家先用 / 降级方案)
2. 实现真实 HTTP client (requests / aiohttp)
3. 接入 budgets (真实计费)
4. 端到端集成测试 (含网络层 mock)
