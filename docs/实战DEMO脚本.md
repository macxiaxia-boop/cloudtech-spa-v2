# Cloud 实战 Demo 脚本

> 版本：v1.0 ｜ 2026-09-11
> 适用场景：面向装企/医美客户演示, 销售可独立操作
> 网关地址：`http://127.0.0.1:5099`（部署到客户内网时改为局域网 IP）
> 鉴权（演示租户）：`X-Tenant-Id: demo`，`X-Tenant-Token: demo-token-xyz`

---

## 一、5 分钟极速演示路径

### Step 1：开场（30 秒）
"哥你好，今天给你看个真东西。不是 PPT，是实时跑一遍。装企客户从线索进入到报价单出来，30 秒内完成，全程 AI 真实调用（DeepSeek），不是模板。"

### Step 2：装企全链 DAG（90 秒）
打开终端（建议 PowerShell），复制粘贴：

```bash
curl -X POST http://127.0.0.1:5099/api/v2/runtime/pipeline/decoration/run \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: demo" -H "X-Tenant-Token: demo-token-xyz" \
  -d '{"lead":{"name":"王老板","location":"厦门·湖里","property_type":"三室两厅 120m²","decoration_style":"现代极简","budget_total":350000,"room_count":3,"pain_points":["工期拖延","增项多"],"site_progress":"水电完工"}, "tenant_id":"demo"}'
```

预期：30 秒内返回 `trace_id` + 5 个步骤（lead_profile / quote / content / live_script / review），全部 `engine: llm`，**DeepSeek 真实生成**。

**销售话术**："你看到这 5 步，每步都是针对你这条线索的 AI 实时生成，不是模板。每步产物都有 ID 路径，可以二次调用。这就是 1 个'数字营销总监'。"

### Step 3：归因成本（30 秒）
```bash
curl "http://127.0.0.1:5099/api/v2/runtime/usage/me" -H "X-Tenant-Id: demo" -H "X-Tenant-Token: demo-token-xyz"
```
预期：返回近 30 天 token 用量、调用次数、平均延迟。
**话术**："DeepSeek 实测一次管线 4000 tokens，按 deepseek-chat 价格约 0.02 元。这条线索从画像到复盘花 2 分钱，比你雇一个助理一天 200 块便宜 1 万倍。"

### Step 4：竞品雷达（45 秒）
```bash
curl "http://127.0.0.1:5099/api/v2/runtime/competitive/search?q=数字员工&limit=5"
```
预期：1989 篇竞品语料，466ms 返回 Top 5，含真实拆解内容。
**话术**："这 1989 篇是我们过去 8 个月扒的 40+ 竞品 UI 拆解，市场上没有人卖这个数据。你每天花 5 分钟看雷达，就知道同行在做什么。"

### Step 5：营销垂直连接器（30 秒）
```bash
curl http://127.0.0.1:5099/api/v2/runtime/connectors/status
```
预期：6 个连接器配置状态——企微/飞书/钉钉/抖音/微信小程序/即梦，**即梦已经配好凭证**可以立刻出视频。

---

## 二、行业对比话术（针对不同客户）

### A. 装企客户（30-50 人规模，年收 5000 万+）
**痛点**：销售跟进不及时、客户流失率高、工地直播没人做
**演示主线**：装企 DAG + 即梦视频（`POST /api/v2/runtime/connectors/jimeng/video/generate`）+ 飞书多维表格写入（线索同步给销售）
**报价锚点**：5 万/年（10 个销售，每个销售每天省 2 小时）

### B. 医美机构（10-30 人，年收 2000 万+）
**痛点**：复购转化低、术前合规风险、内容产出慢
**演示主线**：医美 DAG + 飞书复购提醒 + 短视频脚本生成
**报价锚点**：3 万/年

### C. 教培/餐饮/零售（通用模板）
**演示主线**：竞品雷达 + 多专家咨询（`/runtime/experts/`）+ 内容生成
**报价锚点**：2-3 万/年

---

## 三、技术护城河（应对"为什么不用 ChatGPT"）

1. **行业纵深**：200 真实可执行技能 + 60 行业补丁（装企 46 个，医美 12 个），不是通用助手
2. **真实归因**：每次 AI 调用 token 落库，能算出每个数字员工的 ROI——向老板收费的依据
3. **多租户**：X-Tenant-Token 鉴权 + 限流，部署到客户内网数据不外流
4. **可验收**：装企全链 5 步每步有产物 ID，不是"AI 帮你想文案"而是"AI 帮你做出报价单"
5. **竞品雷达独占**：1989 篇竞品 UI 拆解是稀缺数据，市场上没人卖
6. **私有化部署**：Docker 化（路径已环境变量化），不上公网

---

## 四、常见客户异议应答

**Q1：会不会把客户隐私数据上传到公网？**
A：不会。LLM 调用走 DeepSeek API，但调用上下文可以替换为本地模型（MiniMax/GLM/Kimi 自托管）。敏感数据可以通过环境变量切到内网 LLM 网关。

**Q2：AI 生成的报价客户看到不专业怎么办？**
A：AI 是初稿生成，人工审核环节保留（DAG 末尾 review 步就是给老板看的）。也可以接人工 gate（v3_67_chatops 有相关端点）。

**Q3：怎么保证不出错？**
A：模板回退机制——LLM 失败时返回结构化模板，服务永不 500。`stub:true` 头标识让你看清哪些是真数据。

**Q4：跟Cloud/WorkBuddy 区别？**
A：灵策是泛行业 G1-G6 营销管线，我们专注装企/医美做深；WorkBuddy 是通用助手，我们有 1989 篇独占竞品数据 + 营销垂直连接器（企微/抖音/即梦）。

---

## 五、关键端点速查

| 场景 | 端点 | 用途 |
|---|---|---|
| 健康 | `GET /health` | 网关状态 |
| 行业闭环 | `POST /api/v2/runtime/pipeline/{decoration\|medical}/run` | 装企/医美全链 |
| 专家对话 | `POST /api/v2/runtime/experts/{id}/chat` | 225 个数字员工 |
| 技能执行 | `POST /api/v2/runtime/skills/{cat}/{skill}/run` | 200 个真实技能 |
| ROI | `GET /api/v2/runtime/roi/summary` | token 成本汇总 |
| 用量 | `GET /api/v2/runtime/usage/me` | 当前租户 30 天 |
| 竞品检索 | `GET /api/v2/runtime/competitive/search?q=` | 1989 篇检索 |
| 竞品监控 | `GET /api/v2/runtime/competitive/monitor?days=14` | 周级增量趋势 |
| 连接器状态 | `GET /api/v2/runtime/connectors/status` | 6 个连接器 |
| 即梦视频 | `POST /api/v2/runtime/connectors/jimeng/video/generate` | 文生视频（已配） |
| 技能候选 | `GET /api/v2/runtime/skills/candidates` | 高频调用→新技能建议 |
| 计划 actual | `GET /api/v2/plan/{id}/actual` | 4 周复盘数据 |

---

## 六、演示失败回退

如果 LLM 调用失败（DeepSeek 限流/网络抖动），所有端点会自动回退到模板模式（`engine: template`），不会白屏。可以用 `?CLOUDTECH_SKILLS_TEMPLATE_ONLY=1` 环境变量强制演示模式（不消耗 token）。

```bash
CLOUDTECH_SKILLS_TEMPLATE_ONLY=1 ./.venv/Scripts/python.exe gateway_v22.py
```

---

## 七、销售线索流转（实际成交场景）

```
客户微信聊天
  → 数字员工 "客户成功" (expert_chat) 初步跟进
  → 客户表达意向, 拉群给老板
  → 老板发起装企 DAG (装企 skill_pipeline run)
  → 5 步产出, 截图发客户群
  → 客户付定金
  → 数字员工 "工地直播" 持续输出工地内容
  → ROI 仪表板老板每周看: 这个月 AI 帮你省了多少钱 / 产出多少线索
  → 续费
```

---

## 八、下一步建议

签约后立即启动：
1. **W1**：现场 1 天陪跑，演示脚本从厦门→漳州→福州 3 个样板客户
2. **W2-4**：连真实企微/飞书，让数字员工对接进客户工作流
3. **月 2**：开第二个行业 SaaS（教培/餐饮二选一），复用同样的"行业纵深+营销垂直+多租户"路径

签单前给老板的承诺（书面）：
- 30 天可验收 demo：装企/医美 1 条完整线索从进入到报价单
- 90 天跑通 ROI 仪表：客户用 AI 后每月省多少钱/增多少线索
- 180 天接入客户私域：企微/飞书/抖音真实连接

---

> 这份文档独立可读。销售拿去谈客户前先练 2 遍，把 curl 命令复制粘贴熟手即可。
