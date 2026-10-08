# ADR-PRODUCT-001: 旧 CloudTech 命名冲突 ADR

**Date**: 2026-10-08T16:30:00+08:00
**Author**: Codex (supervisor)
**Status**: ACTIVE
**Authority**: V2 Master Command §2 + CloudTech Product Spec §1

## Context

历史母文件 `CLOUDTECH_MASTER_ARCHITECTURE_AND_BUILD_COMMAND_v1.0.md` 将 CloudTech 定义为 **AIOS 下方的执行/路由/控制底座**。

用户最新 V2 商业定位将 CloudTech 定义为 **直接向企业售卖、负责业务交付和计费的 SaaS 产品**（外部品牌：灵策智算）。

这是真实命名和职责冲突，不能通过默默覆盖旧文件解决。

## Decision

**新定义（V2 优先）**：

- `AIOS Core` 负责: Goal/Task/Plan/Durable Orchestration/Evidence/Eval/Memory/Skill Evolution/Worker
- `CloudTech Product` 负责: Tenant/Identity/Seat/Digital Employee/Workflow Studio/Business Data/Knowledge/CRM/Content/Usage/Billing/Customer UI/Service Delivery
- 旧 CloudTech 工程运行代码（v22/v23 系列）**只读识别 + 分类**，真正属于运行底座的资产经复核可复用/封装到 AIOS Core 或 Shared Runtime
- 原始仓库命名不得在未核实调用依赖前直接重命名
- 若两套代码都存在，建立清晰别名、仓库表和映射；不要擅自合库

## Status（事实）

- 旧文件 `references/CLOUDTECH_MASTER_ARCHITECTURE_AND_BUILD_COMMAND_v1.0.md` 保留为 **历史参考**
- 用户确认**唯一云端仓库** = `cloudtech-spa-v2` (`github.com/macxiaxia-boop/cloudtech-spa-v2`)
- 用户新定义商业定位 **SaaS Product** 优先于旧架构底座
- 现有 150+ Python 文件不直接分类，需逐个 audit 后才能决定复用/封装/迁移

## 受影响仓库与处理

| 仓库/路径 | 当前身份 | 决定 | 证据 |
|---|---|---|---|
| `D:\CloudTech-Portable` | Enterprise SaaS Product (V2) | **保留 + audit 优先此路径** | git remote `cloudtech-spa-v2` + 用户明确指定 |
| `D:\CloudTech-Portable\_HANDOFF_V2_UNZIPPED\references\CLOUDTECH_MASTER_ARCHITECTURE_v1.0.md` | Historical v1 design | **保留为参考, 不覆盖** | 用户 V2 优先, 旧文件归档 |
| `D:\AIOS\kernel` (AIOS Core) | AIOS Core runtime | **保留, 不与 CloudTech 混** | Phase A+B+C+D+E Done |
| `D:\AIOS` | Personal AIOS | **保留, 治理历史** | 自有治理 |

## 实施约束

1. 不得在未获用户单独批准时删除旧 CloudTech 文件
3. 不得擅自合并 `cloudtech-spa-v2` 与 `AIOS` 仓库
4. 旧文件中的功能迁移必须经过独立验收 + 真实证据

## Future

后续 ADR 需求：
- ADR-PRODUCT-002 (待): Tenant/Identity 模型 Provider Adapter 选型
- ADR-PRODUCT-003 (待): Digital Employee 自治等级评估
- ADR-PRODUCT-004 (待): Workflow Studio 与 AIOS Workflow Engine 边界

## Sign-off

Pending user approval for explicit Code-to-Product reclassification.
