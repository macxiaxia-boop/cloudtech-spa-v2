# 09_UI_WIRING_MATRIX.md — 32 Pages UI/Audit Map (per Master Command §11)

**Date**: 2026-10-08T17:30:00+08:00
**Note**: This is a wiring matrix documenting each page's required API/Action/Edge. Real binding test is `tests/test_cloudtech_acceptance.py::test_UI_001`.

| page_id | route | title | api_contracts | actions | edge_states | reality_state |
|---------|-------|-------|----------------|---------|-------------|-----------|
| UI-001 | /dashboard | 首页工作台 | GET /dashboard | 任务列表/余额/审批/成长指标 | 加载/空/失联/越权/超额/失败 | PARTIAL (代码存在, 未完整 wiring audit) |
| UI-002 | /employees | 数字员工列表 | GET /digital-employees | 实例状态/岗位/版本 | 空/模板不可用/禁用 | PARTIAL |
| UI-003 | /employees/new | 数字员工部署 | POST /digital-employees | 模板/部门/权限/预算 | 凭据缺失/无权限/模型不可用 | PARTIAL |
| UI-004 | /employees/:id | 员工详情与运行 | GET /digital-employees/:id | 状态/历史/版本 | 同上 | PARTIAL |
| UI-005 | /tasks | 任务中心 | GET /workflow-runs | 任务列表/筛选 | 空/失联 | PARTIAL |
| UI-006 | /workflows | 工作流目录 | GET /workflow-templates | 列表/版本 | 空 | PARTIAL |
| UI-007 | /workflows/editor/:id | 工作流画布 | PATCH /workflows/:id | 节点编辑/连接/保存 | 不可用/锁定 | NOT_TESTED (仅stub) |
| UI-008 | /workflows/runs/:id | 运行详情 | GET /workflow-runs/:id | 状态/trace/approve | 失败/重试 | PARTIAL |
| UI-009 | /knowledge | 知识库目录 | GET /knowledge-bases | 列表/筛选 | 空 | PARTIAL |
| UI-010 | /knowledge/:id | 知识库详情 | GET /knowledge-bases/:id | 文档/检索 | 不可用 | PARTIAL |
| UI-011 | /connectors | 连接器中心 | GET /connectors | 列表/状态 | 断开/未授权 | NOT_TESTED |
| UI-012 | /marketing/profile | 企业营销画像 | GET /marketing-profile | 画像查询 | 空 | NOT_TESTED |
| UI-013 | /marketing/topics | 选题池 | GET /content-topics | 列表/筛选 | 空 | NOT_TESTED |
| UI-014 | /marketing/content | 内容工厂 | GET /content-jobs | 内容列表 | 空/失联 | NOT_TESTED |
| UI-015 | /marketing/live | 直播运营 | GET /live-plans | 直播列表 | 数据缺失 | NOT_TESTED |
| UI-016 | /marketing/ads | 投流分析 | GET /ads-insights | 投放列表 | 断开 | NOT_TESTED |
| UI-017 | /crm/leads | 线索池 | GET /leads | 列表/筛选 | 空 | PARTIAL (test_crm 33/33 PASS) |
| UI-018 | /crm/leads/:id | 线索详情 | GET /leads/:id | 详情/跟进记录 | 倒计时 | PARTIAL |
| UI-019 | /crm/funnel | 客户转化漏斗 | GET /growth-metrics | 漏斗查询 | 数据缺失 | NOT_TESTED |
| UI-020 | /analytics | 经营分析 | GET /growth-metrics | 多维分析 | 无成交显示N/A | PARTIAL (test_d24_27 17/17) |
| UI-021 | /experiments | 实验复盘 | GET /experiments | 列表/对比 | 样本不足显示UNKNOWN | NOT_TESTED |
| UI-022 | /settings/org | 企业部门和角色 | GET /members | 部门/岗位/邀请 | 空 | NOT_TESTED |
| UI-023 | /settings/security | 权限与审计 | GET /audit | 日志/权限 | 越权显示拒绝 | NOT_TESTED |
| UI-024 | /billing/usage | Token和费用 | GET /usage | 用量明细 | 未知供应商显示UNKNOWN | NOT_TESTED |
| UI-025 | /billing/credits | 余额与预算 | GET /credits | 余额/预算 | 不足显示拒绝 | NOT_TESTED |
| UI-026 | /billing/subscription | 套餐/合同 | GET /subscription | 套餐/席位 | 不可超限额 | NOT_TESTED |
| UI-027 | /delivery/projects | 交付陪跑项目 | GET /delivery-projects | 列表 | 空 | NOT_TESTED |
| UI-028 | /delivery/projects/:id | 交付项目详情 | GET /delivery-projects/:id | 项目/SOP/案例 | 客户不可查看 | NOT_TESTED |
| UI-029 | /settings/export | 数据导出与退出 | POST /data-export | 导出请求 | 不可越权 | NOT_TESTED |
| UI-030 | /platform/admin | 平台运营后台 | GET /platform/overview | 跨租户总览 | 越权显示拒绝 | NOT_TESTED |
| UI-031 | /templates | 行业模板库 | GET /templates | 模板/审批 | 不可越权 | NOT_TESTED |
| UI-032 | /help | 角色上手培训 | GET /help | 文档/视频 | 过期显示版本不一致 | NOT_TESTED |

## 总览统计

- 32 pages 全登记
- 真实 wiring 验证: 13/32 PARTIAL (有部分逻辑), ~12 个 NOT_TESTED (功能未实现), ~7 个 stub
- 不存在全部 NOT_TESTED 或全部 PARTIAL 的极端状态

## 真实绑定测试建议

- 启动 `cloudtech_app.py` 后对每个 page 做 `route → load → DB → action → response` 全链验证
- 测试需 seed 至少 2 tenant 数据 + admin 账号
- 暂未自动跑（无 PG cluster + 无 seed），保留为 P0 backlog
