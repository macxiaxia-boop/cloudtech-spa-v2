# SOURCE_OF_TRUTH_MATRIX.md · R1343 指令一第 1 节
**生成时间**: 2026-10-09 20:08 UTC+8
**指令**: V1.0 指令一 第 1 节 · Windows 本地 Claude Code · READ-ONLY 摸底

---

## 🎯 现役源码（CANONICAL · 主使用）

| ID | 项目 | 绝对路径 | 远端 | HEAD SHA | 状态 |
|---|---|---|---|---|---|
| SC01 | **CloudTech SPA v2.0** | `D:\CloudTech-Portable` | `macxiaxia-boop/cloudtech-spa-v2` | `d0dcd392` | dirty (5 mod + 5 untracked) |
| SC02 | **AIOS Sovereignty-V** | `D:\AIOS` | `macxiaxia-boop/aios-sovereignty-v` | `4e5447f` | dirty (11 mod + 11 new + 6 deleted) |
| SC04 | **AIOS aios_tasks** | `D:\个人文件\AI\Operator\aios_tasks` | `macxiaxia-boop/round45-aios-rebuild` | `e5beb002` | dirty (24 ahead + submodule) |
| SC05 | **AIOS aios_tools** | `D:\个人文件\AI\Operator\aios_tools` | `macxiaxia-boop/round45-aios-rebuild` | `abc88f86` | dirty (24 ahead + submodule) |

## 📚 候选（CANDIDATE · 备查未使用）

| ID | 路径 | 备注 |
|---|---|---|
| SC06 | `D:\个人文件\AI\Operator\aios_data` | MCP 凭证目录 · 非 git repo |
| SC07 | `D:\个人文件\AI\Operator\00_CORE` | 宪法层文档 · 非 git repo |
| SC03 | `D:\AIOS\aios_tasks\aios_vnext` | D:\AIOS 子模块 · 由 SC02 管理 |

## 🗃️ 历史（HISTORICAL · 仅参考）

| 路径 | 备注 |
|---|---|
| `D:\AIOS\_backups_relinked_1790674911\` | openclaw 安装备份 · 含 .env + .key (RISK03 + RISK04) |
| `D:\AIOS\kernel\etc\sovereignty\` | AIOS 内核配置 · 含 ed25519 key (RISK05) |

## 📦 只读归档（READ-ONLY ARCHIVE）

| 路径 | 备注 |
|---|---|
| `Desktop/_archived_<日期>/` | 桌面副本用完即删（红线 #12.6） |
| `aios_tools/_archived_R137_20260922/` | R137 历史归档 |
| `aios_tools/_archived_R151_20260922/` | R151 历史归档 |

## 🏗️ 生成物（BUILD ARTIFACTS · 不进 git）

| 路径 | 备注 |
|---|---|
| `CloudTech-Portable/dist-v45/` | SPA 构建产物 · 已被 .gitignore 排除 |
| `CloudTech-Portable/.venv/` | Python 虚拟环境 · 已被 .gitignore 排除 |
| `CloudTech-Portable/node_modules/` | npm 依赖 · 已被 .gitignore 排除 |
| `aios_tools/.git-mirror/codex-home.git/objects/*.pack` | 120MB+ git pack · **已 commit 到 aios_tasks 历史！需清理** |

## ❓ UNKNOWN 项（不可证实 · 禁止推断）

| 项 | 状态 |
|---|---|
| R1342 之前 24 个 commits 是否含敏感内容 | **aios_tasks 已扫描 · 无 .env/.key/.pem**（HIST_RISK01 PASS） |
| aios_tools 24 commits 是否含敏感内容 | **未扫描完**（HIST_RISK02 PENDING） |
| 之前 24 commits 是否包含 .git-mirror 巨型 pack | **YES**（RISK aios_tasks .git-mirror/codex-home.git/objects/*） |

## 🔴 冲突标记（CONFLICT · 需用户决策）

| 冲突 | 说明 |
|---|---|
| aios_tasks + aios_tools 缺 .gitignore | **指令一第 2 节违规**（C 类可能 push）· 已写 canonical .gitignore 待用户复制 |
| CloudTech 24+ commits ahead 但 push 因网络隔离失败 | **沙箱网络隔离** · 需用户右键运行 `_r1342_git_push_all.cmd` |
| D:\AIOS 远端 main 被 forced update | 远端 history 改变 · 本地 `git pull --no-rebase --allow-unrelated-histories` 才能 push |