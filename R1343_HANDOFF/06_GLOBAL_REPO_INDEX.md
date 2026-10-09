# GLOBAL_REPO_INDEX.md · R1343 指令一第 7 节
**生成时间**: 2026-10-09 20:08 UTC+8

---

## 🌐 CloudTech SaaS

| 字段 | 值 |
|---|---|
| **GitHub URL** | https://github.com/macxiaxia-boop/cloudtech-spa-v2 |
| **Owner/Repo** | macxiaxia-boop / cloudtech-spa-v2 |
| **Default Branch** | master |
| **HEAD SHA (local)** | `d0dcd392` |
| **HEAD SHA (remote, if verified)** | (待 ls-remote 验证 · 沙箱网络隔离) |
| **本地绝对路径** | `D:\CloudTech-Portable` |
| **Owner** | user |
| **可见性** | public |
| **依赖关系** | 无（独立产品） |
| **最新 push 状态** | **PARTIAL** · 24 commits ahead + 沙箱网络隔离 push 失败 |

**项目描述**: CloudTech SaaS release-v2.0.0 - 企业级 AI 工作空间 SPA · 23 工具 · 6 引擎 · 1 键出内容
**README 摘要**: 端口 5099 (管理后台) / 8501 (AI 仪表盘) / 8502 (装企控制台) · 内容生产 + 数据分析 + 多租户 + API 管理 + 微信支付

**云端 AI 接手文件建议**:
- `web/vite-spa/src/` (核心 SPA 代码)
- `D:\CloudTech-Portable\run_prod.py` (启动入口)
- `D:\CloudTech-Portable\model_aggregator.py` (模型聚合)
- `D:\CloudTech-Portable\workflows/` (工作流引擎)

---

## 🤖 AIOS Sovereignty-V (V5 认知治理 + V5.2 跨任务学习)

| 字段 | 值 |
|---|---|
| **GitHub URL** | https://github.com/macxiaxia-boop/aios-sovereignty-v |
| **Owner/Repo** | macxiaxia-boop / aios-sovereignty-v |
| **Default Branch** | main |
| **HEAD SHA (local)** | `4e5447f` |
| **HEAD SHA (remote, if verified)** | (远端被 forced update · 待 pull --allow-unrelated-histories) |
| **本地绝对路径** | `D:\AIOS` |
| **Owner** | user |
| **可见性** | public |
| **依赖关系** | 依赖 cloudtech-spa-v2 + aios_tasks + aios_tools |
| **最新 push 状态** | **PARTIAL** · 2 commits ahead + 远端冲突 |

**项目描述**: AIOS Sovereignty-V · ModelPolicy reconciler + 4 adapters (Codex/CC/OpenClaw/Hermes) enforcing MiniMax canonical LLM

**云端 AI 接手文件建议**:
- `D:\AIOS\_agent-hub\AGENTS.md` (中央 SSOT)
- `D:\AIOS\_agent-hub\policy\reconciler\reconciler.py` (策略引擎)
- `D:\AIOS\_agent-hub\policy\regression-tests\regression_tests.py` (回归测试)
- `D:\AIOS\kernel\` (AIOS 内核)

---

## 🔄 AIOS Round 45 Rebuild (aios_tasks + aios_tools)

| 字段 | 值 |
|---|---|
| **GitHub URL** | https://github.com/macxiaxia-boop/round45-aios-rebuild |
| **Owner/Repo** | macxiaxia-boop / round45-aios-rebuild |
| **Default Branch** | master |
| **HEAD SHA (aios_tasks local)** | `e5beb002` |
| **HEAD SHA (aios_tools local)** | `abc88f86` |
| **本地路径 (aios_tasks)** | `D:\个人文件\AI\Operator\aios_tasks` |
| **本地路径 (aios_tools)** | `D:\个人文件\AI\Operator\aios_tools` |
| **Owner** | user |
| **可见性** | **private** |
| **依赖关系** | 依赖 aios-sovereignty-v + cloudtech-spa-v2 |
| **最新 push 状态** | **PARTIAL** · 24 commits ahead + 缺 .gitignore + .git-mirror 巨型 pack |

**项目描述**: AIOS Round 45 rebuild · aios_tasks (130 files) + aios_tools (1121 files) · ModelPolicy + 4 adapters

**云端 AI 接手文件建议**:
- `aios_tasks/_aios_intent_compiler.py` (意图编译器)
- `aios_tasks/_aios_v51_learning_gate.py` (学习门 5 类)
- `aios_tasks/_aios_v51_continuity_memory.py` (12 字段记忆)
- `aios_tasks/_aios_problem_resolution_engine.py` (8 阶段解决引擎)
- `aios_tools/_aios_*.py` (工具集 50+ 文件)
- `aios_tools/_r13xx_*.py` (R1331-R1343 系列工作产物)

---

## 📊 项目依赖矩阵

```
cloudtech-spa-v2 (产品 · public)
        ↑
        │ depends on
aios-sovereignty-v (中央 SSOT · public)
        ↑
        │ depends on
round45-aios-rebuild (R45 实战 · private)
   ├── aios_tasks (任务执行)
   └── aios_tools (工具)
```

---

## 🚧 工单入口 + 监控

| 入口 | URL |
|---|---|
| GitHub Issues | https://github.com/macxiaxia-boop/cloudtech-spa-v2/issues |
| AIOS Dashboard | `D:\个人文件\AI\Operator\aios_data\memory-bank\index.html` (本地) |
| Push 监控 | schtask `R1342_AutoPush_Daemon` (需用户右键运行) |
| 沙箱外 push | 右键管理员 `_r1342_git_push_all.cmd` |

---

## ✅ 接手清单（ChatGPT Work / OpenAI Codex Cloud）

1. 读 `D:\个人文件\AI\Operator\GITHUB_HANDOFF_20261009\05_REPOSITORY_HANDOFF.json`
2. clone 4 仓库（README 真实路径）
3. 查 `git ls-remote` 验证远端 SHA
4. 跑 `bash _r1342_git_push_all.cmd`（Windows）或等 schtasks 自动 push
5. 加 GitHub Actions secrets-scan workflow
6. 轮换 6 项凭证（B06）
7. 复制 `_canonical.gitignore` 到 aios_tasks + aios_tools

---

**NEXT_HANDOFF_ALLOWED**: **NO**（PARTIAL · 待 B01-B06 全部解决才能 PASS）