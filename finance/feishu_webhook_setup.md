# 飞书机器人 Webhook 告警通道搭建 SOP

> **Phase 46 D65-66** · OPC 内部 SOP · **实际开通 webhook 必用户拍板（红 #22）**

## 4 类告警通道

### 通道 1：feishu_robot_critical (P0)

- **机器人名**: CloudTech 监控-P0
- **接收群**: 创始人群（含用户 阿劲 + AI 数字员工）
- **@提醒**: @所有人
- **电话告警**: P0 同时触发 SMS / 电话（巨量引擎 / 阿里云通信）

### 通道 2：feishu_robot_critical_phone (P0 数据安全)

- **机器人名**: CloudTech 安全专线
- **接收群**: 仅用户 + 法务外审
- **@提醒**: @所有人
- **电话告警**: 必拨打电话给用户（红线 #22 安全事件必用户拍板）

### 通道 3：feishu_robot_important (P1)

- **机器人名**: CloudTech 监控-P1
- **接收群**: 技术团队群
- **@提醒**: @oncall

### 通道 4：feishu_robot_warning (P2)

- **机器人名**: CloudTech 监控-P2
- **接收群**: 技术团队群（静默）

### 通道 5：feishu_robot_reminder (P3)

- **机器人名**: CloudTech 监控日报
- **接收群**: 运营群
- **触发频率**: 每日 09:00 汇总

## 5 步开通 SOP

### 步骤 1：创建飞书机器人

1. 飞书群 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人
2. 命名（按上述 4 类）
3. 安全设置：
   - 签名校验（推荐，防伪造）
   - IP 白名单（仅 Prometheus 出口 IP）
4. 复制 webhook URL（如 `https://open.feishu.cn/open-apis/bot/v2/hook/{uuid}`）

### 步骤 2：配置 AlertManager

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'feishu_default'

  routes:
    - match:
        severity: p0
      receiver: 'feishu_critical_phone'
      group_wait: 10s
      repeat_interval: 5m

    - match:
        severity: p1
      receiver: 'feishu_important'

    - match:
        severity: p2
      receiver: 'feishu_warning'

    - match:
        severity: p3
      receiver: 'feishu_reminder'

receivers:
  - name: 'feishu_critical_phone'
    webhook_configs:
      - url: 'http://alertmanager-webhook:5001/feishu/p0'
        send_resolved: true

  - name: 'feishu_important'
    webhook_configs:
      - url: 'http://alertmanager-webhook:5001/feishu/p1'
        send_resolved: true

  # ... 其他类似
```

### 步骤 3：webhook 转换服务

`alertmanager-webhook/feishu_adapter.py`（内部脚本）：

```python
def feishu_message(alert):
    labels = alert['labels']
    annotations = alert['annotations']
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"[{labels['severity'].upper()}] {annotations['summary']}"
                },
                "template": "red" if labels['severity'] == 'p0' else "orange"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": annotations['description']
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**Runbook**: {annotations.get('runbook', 'N/A')}"
                    }
                }
            ]
        }
    }
```

### 步骤 4：测试告警链路

```bash
# 触发 P0 测试告警
curl -X POST http://prometheus:9090/-/reload
# 模拟 API down 30s → 验证飞书群收到告警

# 触发 P1 测试告警
# 临时调高错误率到 6% → 验证飞书群 + @oncall

# 触发 P2 测试告警
# 临时把租户配额调到 95% → 验证飞书群（静默）
```

### 步骤 5：上线 + 监控

- 上线后 24h 观察 → 检查误报率
- 调优阈值（参考 `prometheus_alerts.yml` 默认值）
- 每周 review 一次告警（避免告警疲劳）

## 6 项必查

- [ ] 4 机器人 webhook URL 已配置
- [ ] 签名校验已启用
- [ ] IP 白名单已设置
- [ ] 告警测试 4 类全 PASS
- [ ] 接收群已创建 + 成员已加入
- [ ] 告警升级策略已文档化（P0 自动电话）

## 4 通道配额

| 通道 | 配额 | 超限 |
|---|---|---|
| 飞书自定义机器人 | 100 条/分钟/群 | 限流 |
| 飞书群消息 | 200 条/分钟/群 | 限流 |
| 巨量引擎 SMS | 100 条/分钟/号 | 升级 |
| 阿里云电话 | 100 通/分钟 | 升级 |

---

## ⚠️ 红 #22 必用户拍板

- 实际开通 4 飞书机器人（每机器人需用户拍板）
- 绑定 webhook URL
- 接收群成员 + 权限设置
- P0 自动电话开通（涉及第三方服务付费）
- 阈值调优（避免告警疲劳）
