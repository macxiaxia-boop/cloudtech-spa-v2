# CloudTech V4 技能资产私有迁移规范（非“已完成”声明）

## 当前阻断
公开 GitHub 仓库不包含 Windows 本地的 `D:\CloudTech-Portable\data\skill_orchestrator`。
GitHub Actions Linux 环境不能访问 Windows D 盘。因此 V4 的 3 个真实技能盘点测试失败必须保留，直到真实技能文件可在受控环境读到。

## Codex Windows 一次性执行流程
1. 检查本地绝对路径是否存在，优先用环境变量 `CLOUDTECH_SKILL_ROOT` 指向实际位置；不要创建一个有空文件的目录冒充真实来源。
2. 从现有 CloudTech 主仓运行：
   ```powershell
   $env:CLOUDTECH_SKILL_ROOT = 'D:\CloudTech-Portable\data\skill_orchestrator'
   python scripts/cloudtech_skill_inventory.py --minimum 100 --output 'D:\CloudTech-Portable\evidence\skill_inventory.json'
   ```
3. 将输出中的实际技能文件数、真实失败原因、SHA-256 清单数量和 OperationRegistry 加载结果写回项目工程状态；不得将设计中的“200”当作实测。
4. 在 Windows 本地运行 `pytest tests/test_v4_registry_real_load.py -v`，保留日志。
5. 使用**私有存储/受控挂载**将技能资产提供给实际 Worker。未经确认严禁将 SKILL.md 原文、密钥、个人知识、客户信息或导出压缩包提交至公开仓库。
6. 对每个技能做独立登记：名称、所属行业、输入/输出 JSON Schema、工具依赖、模型依赖、访问权限、成本、错误类别、幂等、安全级别、测试夹具和业务链路对应。目录数量不等于可运行功能数量。
7. 如目录缺失，标记 `BLOCKED_LOCAL_ASSET`；不得生成占位 SKILL.md 或降低通过门槛来刷绿 CI。

## 验收分层
- **INDEXED**：通过清点和文件哈希，能追溯实际来源。
- **LOADABLE**：OperationRegistry 能在隔离进程加载技能，数量、类型与审计清单一致。
- **EXECUTABLE**：技能依赖实际工具可用，能运行且输出非模拟结果；出错行为可验证。
- **INTEGRATED**：工作流引擎可引用其 op_id，并实现输入绑定、权限和结果归档。
- **VALIDATED**：在同租户/跨租户、重复请求、异常、付费边界上均有真实证据。
- **PRODUCTION READY**：部署、备份、计费审计、告警和权限都有可追溯验收。

不得将 `INDEXED` 冒充 `EXECUTABLE` 或 `PRODUCTION READY`。

## 版本与仓库红线
保留唯一 CloudTech 主仓 `macxiaxia-boop/cloudtech-spa-v2`；未来新增技能沿用版本管理，不以每次升级新建仓库。公共 GitHub 只存放允许公开的代码、测试夹具和不含敏感信息的契约，不保存私有运行凭证。
