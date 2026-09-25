# 80 家客户漏斗监控配置

> **Phase 46 D67-68** · OPC 内部监控 · 客户触达进度可视化

## 漏斗 5 状态机

```
pending (80) → contacted → demo_scheduled → trial → signed
                       ↓             ↓           ↓
                    (流失)        (流失)       (流失)
```

## 数据模型

### client_outreach 表

```sql
CREATE TABLE client_outreach (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(32) NOT NULL,  -- e.g. 'D-CD-001'
    industry VARCHAR(16) NOT NULL,    -- 'decoration' / 'medical'
    city VARCHAR(32) NOT NULL,
    scale VARCHAR(16) NOT NULL,      -- 'small' / 'medium' / 'large'
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    priority VARCHAR(8) NOT NULL,    -- 'P0' / 'P1' / 'P2' / 'P3'
    contact_person VARCHAR(64),
    phone VARCHAR(32),
    email VARCHAR(128),
    last_contact_at TIMESTAMPTZ,
    next_action_at TIMESTAMPTZ,
    next_action VARCHAR(256),
    note TEXT,
    operator VARCHAR(64),            -- 'user_阿劲' / 'AI'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_client_outreach_status ON client_outreach(status);
CREATE INDEX idx_client_outreach_industry ON client_outreach(industry);
CREATE INDEX idx_client_outreach_priority ON client_outreach(priority);
```

### contact_log 表（每次触达记录）

```sql
CREATE TABLE contact_log (
    id BIGSERIAL PRIMARY KEY,
    client_id VARCHAR(32) NOT NULL,
    channel VARCHAR(16) NOT NULL,    -- 'phone' / 'wechat' / 'sms' / 'email'
    result VARCHAR(32) NOT NULL,     -- 'pending' / 'contacted' / ...
    note TEXT,
    operator VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contact_log_client ON contact_log(client_id, created_at DESC);
```

## 4 监控指标

### 指标 1: 总转化率 (Today)

```sql
SELECT
  COUNT(*) FILTER (WHERE status != 'pending')::float / COUNT(*) AS conversion_rate
FROM client_outreach;
```

**健康范围**: M1 应 ≥ 30%（D1 触达后）

### 指标 2: 漏斗分布 (实时)

```sql
SELECT status, COUNT(*) AS cnt
FROM client_outreach
GROUP BY status
ORDER BY cnt DESC;
```

**预期分布** (M1 末):
- pending: ~50% (40/80)
- contacted: ~30% (24/80)
- demo_scheduled: ~12% (10/80)
- trial: ~5% (4/80)
- signed: ~3% (2/80)

### 指标 3: P0 触达率 (P0 必 100%)

```sql
SELECT
  COUNT(*) FILTER (WHERE status != 'pending')::float / COUNT(*) AS p0_conversion
FROM client_outreach
WHERE priority = 'P0';
```

**P0 必 100% 触达**（用户亲自打电话），目标 ≥ 90%

### 指标 4: 行业转化对比

```sql
SELECT
  industry,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE status = 'signed') AS signed,
  COUNT(*) FILTER (WHERE status = 'trial') AS trial,
  COUNT(*) FILTER (WHERE status IN ('demo_scheduled', 'trial')) AS pipeline
FROM client_outreach
GROUP BY industry;
```

## 7 日触达 SOP（自动化）

```python
# Daily task: 9:00 / 14:00 / 18:00 跑
def daily_outreach_check():
    today = date.today()

    # 1. 找出今天需要跟进的所有 client
    clients_to_followup = query("""
        SELECT * FROM client_outreach
        WHERE next_action_at::date = %s
        AND status NOT IN ('signed')
    """, today)

    # 2. 按优先级分组
    p0 = [c for c in clients_to_followup if c.priority == 'P0']
    p1_p3 = [c for c in clients_to_followup if c.priority in ('P1', 'P2', 'P3')]

    # 3. P0 → 飞书 @用户（必用户亲自打）
    if p0:
        feishu_notify_user(
            f"📞 P0 客户 {len(p0)} 家今日必跟:\n" +
            "\n".join(f"- {c.client_id} {c.name} ({c.contact_person})" for c in p0)
        )

    # 4. P1-P3 → AI 数字员工自动外呼 (用户拍板后)
    # (红线 #22 实际触达必用户拍板)
    return clients_to_followup
```

## 7 项必查 (D67-68 落地后)

- [ ] client_outreach 表 80 条记录已灌入（50 装企 + 30 医美）
- [ ] priority 分级已分配（P0=8, P1=25, P2=47, P3=0）
- [ ] next_action_at 已填（按触达节奏表 D1/D3/D7/D14/D21）
- [ ] 漏斗监控 Grafana panel 已就绪（按 [grafana_dashboard_business.json]）
- [ ] 飞书机器人 webhook 已开通（参考 [feishu_webhook_setup.md]）
- [ ] P0 客户列表已推送飞书群（用户必亲自打）
- [ ] 每日 9:00 自动跑 daily_outreach_check

## 监控告警

### 告警 1: P0 触达率 < 80% (3 天)

```yaml
- alert: P0_Outreach_Stalled
  expr: |
    (SELECT COUNT(*) FROM client_outreach WHERE priority = 'P0' AND status != 'pending')::float
    / (SELECT COUNT(*) FROM client_outreach WHERE priority = 'P0')::float
    < 0.8
  for: 3d
  labels:
    severity: p1
  annotations:
    summary: "P0 客户触达率 < 80% (3 天)"
```

### 告警 2: 单客户连续 5 天无跟进

```yaml
- alert: ClientFollowUpStalled
  expr: |
    (NOW() - last_contact_at) > INTERVAL '5 days'
  labels:
    severity: p2
  annotations:
    summary: "客户 {{ $labels.client_id }} 5 天未跟进"
```

### 告警 3: 月度新签 < 2 家

```yaml
- alert: MonthlySigningsLow
  expr: |
    SELECT COUNT(*) FROM client_outreach
    WHERE status = 'signed'
    AND updated_at >= NOW() - INTERVAL '30 days'
    < 2
  labels:
    severity: p1
  annotations:
    summary: "月度签约 < 2 家"
```

---

## ⚠️ 红 #22 必用户拍板

- 实际开通数据库表 + 索引
- 灌入 80 条记录（必用户拍板数据准确性）
- 分配 priority 分级
- 飞书 webhook 开通
- daily_outreach_check 启用（cron 调度）
- P0 客户必用户亲自打
