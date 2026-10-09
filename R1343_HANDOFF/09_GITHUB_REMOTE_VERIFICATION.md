# GITHUB_REMOTE_VERIFICATION.md · R1343 指令一第 5 节第一条链路
**生成时间**: 2026-10-09 20:08 UTC+8
**沙箱限制**: CC 沙箱无法连接 github.com:443 (Connection was reset) · 所有 ls-remote 必须沙箱外执行

---

## 📋 验证清单（指令一第 5 节）

| # | 仓库 | 本地 SHA | 远端 SHA 期望 | 验证命令 | 状态 |
|---|---|---|---|---|---|
| 1 | cloudtech-spa-v2 | `d0dcd392` | 待 ls-remote | `git ls-remote https://github.com/macxiaxia-boop/cloudtech-spa-v2.git master` | **BLOCKED** |
| 2 | aios-sovereignty-v | `4e5447f` | 待 ls-remote (远端可能 forced update) | `git ls-remote https://github.com/macxiaxia-boop/aios-sovereignty-v.git main` | **BLOCKED** |
| 3 | round45-aios-rebuild | `e5beb002` / `abc88f86` | 待 ls-remote (24 commits ahead + .git-mirror pack 部分 push) | `git ls-remote https://github.com/macxiaxia-boop/round45-aios-rebuild.git master` | **BLOCKED** |

---

## 🚨 已知风险（指令一第 9 节"假完成"）

- ❌ **CC 沙箱无法完成 ls-remote**（所有 push 之前命令都 timeout）
- ❌ **之前 R1342 push 未完整**（24 commits 部分 push + 部分被 .git-mirror pack 拒绝）
- ❌ **未做 LFS 对象存在性单独检验**（无 LFS 对象 · 0 个）

---

## 🧪 沙箱外验证 SOP（用户右键运行）

```bash
# 打开 Git Bash 或 PowerShell（沙箱外）

# 1. CloudTech
git ls-remote https://github.com/macxiaxia-boop/cloudtech-spa-v2.git master
# 期望: <SHA>\trefs/heads/master
# 比对: 本地 d0dcd392
# 若一致 → PASS
# 若不一致 → 远端被 force update · 需 git pull --rebase

# 2. AIOS Sovereignty
git ls-remote https://github.com/macxiaxia-boop/aios-sovereignty-v.git main
# 比对: 本地 4e5447f
# 若远端 SHA 不同 → 远端被 forced update · 用 git pull --no-rebase --allow-unrelated-histories

# 3. round45-aios-rebuild (private)
gh auth status
git ls-remote https://github.com/macxiaxia-boop/round45-aios-rebuild.git master
# 比对: 本地 e5beb002 (aios_tasks) 或 abc88f86 (aios_tools)
# ⚠️ 注意: 两个本地仓库 remote 都指向同一 GitHub repo · 推 24 + 1 commits
```

---

## 📂 文件存在性验证（mcp__github__get_file_contents 实证）

| 仓库 | 文件 | 验证状态 | 实证时间 |
|---|---|---|---|
| cloudtech-spa-v2 | `README.md` | ✅ PASS (mcp__github__get_file_contents 成功) | 2026-10-09 15:35 UTC+8 |
| cloudtech-spa-v2 | root dir listing | ❌ PENDING (沙箱内 mcp 工具未列 root) | - |
| aios-sovereignty-v | 任何文件 | ❌ PENDING (未读) | - |
| round45-aios-rebuild | README.md | ❌ **404 Not Found** (private + 无 token scope) | 2026-10-09 15:36 UTC+8 |

**结论**:
- ✅ **CloudTech** 仓库可读取
- ❌ **AIOS** 仓库未读取验证
- ❌ **round45-aios-rebuild** 仓库私有 · MCP 工具无 read scope

---

## 📊 SHA 验证表（本地 vs 远端）

| 仓库 | 本地 HEAD | 远端 HEAD | 一致？ | 备注 |
|---|---|---|---|---|
| cloudtech-spa-v2 | d0dcd392 | ? | BLOCKED | 待用户执行 ls-remote |
| aios-sovereignty-v | 4e5447f | 05bead3 → 82f8782 (forced update) | NO | 已确认远端被 force update |
| round45-aios-rebuild (aios_tasks) | e5beb002 | ? | BLOCKED | 待 ls-remote |
| round45-aios-rebuild (aios_tools) | abc88f86 | ? | BLOCKED | 待 ls-remote |

**唯一确认的失败**:
- ❌ **aios-sovereignty-v 远端被 force update**（`fatal: refusing to merge unrelated histories`）

---

## 🛡️ 沙箱内可做 vs 沙箱外必做

### 沙箱内可做（已做）
- ✅ `mcp__github__get_file_contents` 读 README.md
- ✅ `mcp__github__search_repositories` 搜仓库
- ✅ `mcp__github__list_commits` 列最近 commits

### 沙箱外必做（用户）
- ⚠️ `git ls-remote` 验证远端 SHA（github.com:443 沙箱拒绝）
- ⚠️ `git pull` 处理 aios-sovereignty-v forced update
- ⚠️ `gh auth status` 验证 macxiaxia-boop token
- ⚠️ 跑 `_r1342_git_push_all.cmd` 一键 push
- ⚠️ 复制 `_canonical.gitignore` 到 aios_tasks + aios_tools

---

## 🚫 当前阻塞

| ID | 描述 | 影响 |
|---|---|---|
| **B01** | 沙箱网络隔离 github.com:443 | 无法验证远端 SHA · 无法 ls-remote |
| **B07** | 远端 main 已被 force update (aios-sovereignty-v) | 本地 pull 需 --allow-unrelated-histories |
| **B08** | round45-aios-rebuild 部分 commits push + .git-mirror 巨型 pack 拒绝 | 需 ls-remote 验证实际 push 状态 |

---

## 📊 PASS 条件

```
当且仅当以下全部满足时，Remote check = PASS：
✅ CloudTech: 远端 HEAD == 本地 d0dcd392
✅ AIOS Sovereignty: 远端 HEAD == 本地 4e5447f (pull 后)
✅ round45-aios-rebuild: 远端 HEAD == 本地 e5beb002 / abc88f86
✅ 无 .git-mirror 巨型 pack 残留（git rev-list 验证）
✅ 4 仓库 main/master 分支保护开启（PR-only · 阻止 force push）
```

当前: **3/5 BLOCKED + 1/5 PASS + 1/5 NO**

---

## 📝 验证日志（沙箱内已跑）

```
2026-10-09 15:30 mcp__github__search_repositories "cloudtech" → 718 results (top: CloudTechDevOps/CloudTechDevOps)
2026-10-09 15:32 mcp__github__search_repositories "user:macxiaxia-boop" → 3 results (cloudtech-spa-v2, aios-sovereignty-v, openclaw)
2026-10-09 15:33 mcp__github__get_file_contents macxiaxia-boop/cloudtech-spa-v2 README.md → ✅ PASS (CloudTech v2.1 AI 数字营销中台)
2026-10-09 15:36 mcp__github__get_file_contents macxiaxia-boop/round45-aios-rebuild README.md → ❌ 404 (private)
2026-10-09 15:40 mcp__github__list_commits macxiaxia-boop/cloudtech-spa-v2 perPage=5 → ✅ top: Add lighthouserc (48a7c2e7, 2026-09-29)
2026-10-09 16:00+ git push attempts (沙箱内) → ❌ Connection reset (所有)
2026-10-09 16:05 gh auth status (沙箱内) → ✅ Logged in to github.com account macxiaxia-boop (keyring)
```

---

## 结论

**REMOTE_CHECK**: **FAIL** (3/5 BLOCKED + 1/5 FAIL) · 需沙箱外 ls-remote 全部跑通才能转 PASS

**详细路径**: 见 [08_RESTORE_RUNBOOK.md](08_RESTORE_RUNBOOK.md) 第 1-3 步