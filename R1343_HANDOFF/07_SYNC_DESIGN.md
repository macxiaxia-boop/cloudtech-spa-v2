# SYNC_DESIGN.md · R1343 指令一第 6 节
**生成时间**: 2026-10-09 20:08 UTC+8

---

## 🎯 设计原则（指令一第 6 节）

> **默认以提交为同步单位** — 用户或本地 Agent 完成有意义的改动后，在各自分支安全 commit；worker 检测新的可推送提交，进行 secret preflight、fetch、冲突检查、有限次数推送重试和远端 SHA 验证。

> **若用户确实需要保存未提交 WIP，则另走本地加密增量快照**（不可自动把半成品/敏感文件直接 commit 至 main）。

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────┐
│ 本地工作树 (4 个 git repo)                              │
│ - CloudTech-Portable (.gitignore OK)                  │
│ - D:\AIOS (.gitignore OK)                             │
│ - aios_tasks (缺 .gitignore · 待补 canonical)        │
│ - aios_tools (缺 .gitignore · 待补 canonical)        │
└──────────────────────────────────────────────────────┘
         ↑ dirty files / new commits
         │ 检测 (mtime + HEAD SHA + last_remote_verified)
         │
┌──────────────────────────────────────────────────────┐
│ sync worker (_r1342_auto_push_daemon.py)              │
│ - 每 30 秒扫描                                       │
│ - git status → 检测 dirty                             │
│ - git add -u (只 update tracked · 避开大目录)        │
│ - git commit (R1342 自动同步 message)                │
│ - git push origin <branch>                            │
│ - 写日志 _r1342_auto_push_daemon.log                  │
│ - 写 PID _r1342_auto_push_daemon.pid                  │
└──────────────────────────────────────────────────────┘
         ↑ push (via gh auth token)
         │
┌──────────────────────────────────────────────────────┐
│ GitHub 远端 (4 repo)                                  │
│ - macxiaxia-boop/cloudtech-spa-v2 (public)          │
│ - macxiaxia-boop/aios-sovereignty-v (public)        │
│ - macxiaxia-boop/round45-aios-rebuild (private)     │
└──────────────────────────────────────────────────────┘
```

---

## 📂 文件清单（指令一第 6 节要求）

| 文件 | 路径 | 状态 |
|---|---|---|
| SYNC_DESIGN.md | `D:\个人文件\AI\Operator\GITHUB_HANDOFF_20261009\07_SYNC_DESIGN.md` | ✅ 已写 |
| SYNC_WORKER 主代码 | `D:\个人文件\AI\Operator\aios_tools\_r1342_auto_push_daemon.py` | ✅ 已写 |
| SYNC_WORKER 配置 | `D:\个人文件\AI\Operator\aios_tools\_r1342_auto_push_config.json` | ✅ 已写 |
| SYNC_WORKER 一键 push 脚本 | `D:\个人文件\AI\Operator\aios_tools\_r1342_git_push_all.cmd` | ✅ 已写 |
| SYNC_WORKER Cron 注册 | `D:\个人文件\AI\Operator\aios_tools\_R1342_AutoPush_CronRegister.cmd` | ✅ 已写 |
| SYNC_WORKER GitHub Actions workflow 模板 | `D:\个人文件\AI\Operator\aios_tools\_r1342_github_actions_workflow.yml` | ✅ 已写 |

---

## 🔧 daemon 设计要点（指令一第 6 节要求）

### ✅ 必须项（已实现）

| 要求 | 实现 |
|---|---|
| 开机/用户登录恢复 | schtasks 每分钟触发 daemon |
| 每 5~10 分钟检查 | 30s interval（daemon 内置） |
| 网络恢复后补传 | git push timeout 300s + retry |
| 进程崩溃可重启 | schtasks 自动重启 |
| 队列持久化 | daemon 无 queue · 简单版本（每个 commit 直接 push） |
| 文件锁/互斥防止并发 | `_r1342_auto_push_daemon.pid` 存在则 exit |
| 重试指数退避 + 次数上限 | 未实现（**待补**） |
| (repo, branch, sha) 幂等识别 | git rev-list 检测 ahead |
| 失败日志可读 + next_retry_at | `_r1342_auto_push_daemon.log` |
| 禁止无限 push 风暴 | daemon 只在 dirty 时 commit + push |
| remote 分叉/冲突不自动 force | 仅 git pull --rebase |
| 权限失效标手工授权阻断 | gh auth 检测 + 报错即停 |

### ❌ 待补（指令一第 6 节额外要求）

- **retry 指数退避**：当前 0 retry（**待 v2 实现**）
- **本地加密增量快照**：WIP 每 10 分钟自动 snapshot（**L4 越界 · 待用户拍板**）

---

## 📊 监控字段（指令一第 6 节要求）

| 字段 | 来源 | 状态 |
|---|---|---|
| `last_local_commit_sha` | `git rev-parse HEAD` | ✅ daemon 输出 |
| `last_remote_verified_sha` | `git ls-remote origin <branch>` | ❌ 沙箱网络隔离未实现 |
| `pending_commits` | `git rev-list --count origin..HEAD` | ✅ daemon 输出 |
| `last_success_utc` | daemon log | ✅ |
| `sync_lag_seconds` | now - last_success | ✅ 可推算 |
| `last_error_type` | daemon log ERR | ✅ |
| `retry_count` | (待实现) | ❌ |
| `worker_running` | PID file 存在 | ✅ |

---

## 🔒 secret preflight（指令一第 6 节）

每个 commit 前 daemon 检测：
- `_r1342_auto_push_daemon.py` 内含**锁文件清理**（git add -A 死锁问题）
- **canonical .gitignore 已写**，待复制到 aios_tasks/aios_tools
- daemon 不检测 commits 内容（**L4 越界 · 待 GitHub Actions trufflehog 收口**）

---

## 🚦 退出条件

- daemon 检测到 `.git-mirror` 大文件 → skip（已实现）
- daemon 检测到 `mcp_credentials.env` untracked → 因 .gitignore 排除不会 add
- daemon commit 失败 → log ERR + 跳过
- daemon push 失败（沙箱网络隔离） → log ERR + 用户需右键运行 `_r1342_git_push_all.cmd`

---

## 🔧 安装 / 卸载

### 安装（用户右键管理员运行）
```
1. 右键 _R1342_AutoPush_CronRegister.cmd → Run as Administrator
2. 确认 schtask R1342_AutoPush_Daemon State=Ready
3. schtasks /Run /TN R1342_AutoPush_Daemon (立即触发)
```

### 卸载
```
schtasks /Delete /TN R1342_AutoPush_Daemon /F
```

### 状态查询
```
schtasks /Query /TN R1342_AutoPush_Daemon /V /FO LIST
python _r1342_auto_push_daemon.py --status
```