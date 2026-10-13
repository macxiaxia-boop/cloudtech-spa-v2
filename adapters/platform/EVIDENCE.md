# adapters/platform — Mock-Only 实证报告

## 真实 API 调用次数

| 指标 | 值 |
|------|----|
| 真实 HTTP 请求次数 | 0 |
| 真实 OAuth / token 使用次数 | 0 |
| 真实接口成功率 | 0% (mock only) |

---

## 凭证现状（TikHub MCP 已注册但未接入）

TikHub 5 端 MCP 已注册于 `~/.claude.json`（douyin / xiaohongshu / bilibili / kuaishou / wechat_mp）。
adapter 目前 **完全没有调用** 这些 MCP，全部返回 hardcoded mock 数据。

| 平台 | MCP 已注册 | adapter 已接入 |
|------|-----------|--------------|
| 抖音 | ✅ | ❌ |
| 小红书 | ✅ | ❌ |
| B站 | ✅ | ❌ |
| 快手 | ✅ | ❌ |
| 微信公众号 | ✅ | ❌ |
| 视频号 | ✅ | ❌ |
| 微博 | ❌ | — |

---

## Production Ready

**NO**

当前 adapter 为纯 mock stub：
- 所有 `retrieved_policy = "mock"`
- 所有 `rights_status = "unknown_need_user_confirm"`
- 所有 `view_count = "mock-not-real"`
- `rate_limit_remaining` 全部硬编码为 100 / 0，无真实限速逻辑

---

## 下一步路线图

1. **立即**：将 TikHub MCP 接入 `HomepageParser.call_remote(url)`
   - 用 `TikHubMCPClient` 替代 hardcoded mock 数据
   - 保留 `retrieved_policy = "tikhub_api"` 标注
2. **短期**：接入 `PermissionGate` → 真实白名单/黑名单查询
3. **中期**：接入 `PublicMetadataExtractor` → 真实播放量/时长字段
4. **合规**：所有 `rights_status` 必须由用户确认后覆盖，永不自动设为 "clear"

---

## 不确定项

- TikHub MCP 的 `fetch_user_homepage` 接口签名尚未验证；
  adapter 层预留了 `call_remote()` 槽位，待接入时填充。
- 微博尚未注册 MCP 凭证，无法评估该平台的接入成本。
