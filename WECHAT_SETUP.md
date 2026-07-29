# 微信支付商户号接入指南

## 前置条件

1. 已注册微信支付商户号 (https://pay.weixin.qq.com)
2. 已通过商户认证
3. 已绑定公众号/小程序 (JSAPI支付) 或开通 Native 支付

## 获取凭证

登录微信支付商户平台 → 账户中心 → API安全：

| 凭证 | 位置 | 环境变量 |
|------|------|----------|
| AppID | 产品中心 → AppID | `WECHAT_APP_ID` |
| 商户号 | 账户中心 → 商户信息 | `WECHAT_MCH_ID` |
| APIv2密钥 | API安全 → 设置API密钥 | `WECHAT_API_KEY` |
| APIv3密钥 | API安全 → 设置APIv3密钥 | `WECHAT_API_V3_KEY` |
| 证书序列号 | API安全 → 申请API证书 | `WECHAT_SERIAL_NO` |
| 私钥文件 | API安全 → 下载证书 | `WECHAT_PRIVATE_KEY_PATH` |

## 配置

```bash
# .env 文件
WECHAT_APP_ID=wx1234567890abcdef
WECHAT_MCH_ID=1234567890
WECHAT_API_KEY=your-v2-key-32chars
WECHAT_NOTIFY_URL=https://your-domain.com/api/payment/wechat/notify
```

## 测试

```bash
# 创建支付订单
curl -X POST http://localhost:5099/api/payment/create-order \
  -H "Content-Type: application/json" \
  -d '{"plan_id":"starter","user_id":"test-user"}'

# 返回: {"success":true, "code_url":"weixin://...", "order_id":"..."}
```

## 上线检查清单

- [ ] 商户号已完成认证
- [ ] API 密钥已配置
- [ ] 支付回调 URL 可公网访问
- [ ] HTTPS 证书有效
- [ ] 已设置 1 分钱测试交易
- [ ] 正式环境切换到真实 API (删除 mock 模式)
