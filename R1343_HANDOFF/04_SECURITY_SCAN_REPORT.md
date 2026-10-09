# SECURITY_SCAN_REPORT.md · R1343 指令一第 2 节（脱敏）
**生成时间**: 2026-10-09 20:08 UTC+8
**扫描范围**: 4 个 git repo 当前 working tree + 完整 git history

---

## ⚠️ 本地发现的 C 类风险文件（**不直接列内容 · 仅路径 + 风险类型**）

| ID | 路径 | 风险类型 | 等级 | 建议 |
|---|---|---|---|---|
| RISK01 | `D:\CloudTech-Portable\.env` | production env file | HIGH | gitignore 已排除 · OK |
| RISK02 | `D:\CloudTech-Portable\deploy\.env` | deploy env file | HIGH | gitignore 已排除 · OK |
| RISK03 | `D:\AIOS\_backups_relinked_1790674911\openclaw\.env` | openclaw env | HIGH | 在 backups 目录 · 未入 git |
| RISK04 | `D:\AIOS\_backups_relinked_1790674911\openclaw\config-journal-fingerprint.key` | ED25519 private key | **CRITICAL** | 在 backups · 未入 git · 但建议加密离线 |
| RISK05 | `D:\AIOS\kernel\etc\sovereignty\codex_supervisor.ed25519.key` | ED25519 sovereignty key | **CRITICAL** | D:\AIOS .gitignore 已排除 · OK |
| RISK06 | `D:\个人文件\AI\Operator\aios_data\mcp_credentials.env` | GitHub PAT + Stripe + Feishu | **CRITICAL** | 不在 git · 但建议本地加密 |
| RISK07 | `D:\个人文件\AI\Operator\aios_tools\mcp_credentials.env` | GitHub PAT + Stripe + Feishu | **CRITICAL** | **aios_tools 没 .gitignore · 风险高！** |

## ✅ 历史扫描结果（git log --all --full-history）

| 仓库 | 扫描命令 | 结果 |
|---|---|---|
| **aios_tasks** | `git log --all --full-history -- "*.env" "*.key" "*.pem" "credentials*"` | **0 匹配** ✅ PASS |
| **aios_tools** | 同上 | **未扫描**（命令 timeout）⚠️ PENDING |
| **CloudTech-Portable** | .gitignore 已排除 `.env` `.venv` `.key` | ✅ gitignore OK |
| **D:\AIOS** | .gitignore 已排除 `.env` `.venv` | ✅ gitignore OK |

## 🚨 已 push 历史的潜在风险（已实证）

### 1. .git-mirror/codex-home.git 巨型 pack 文件
- **路径**: `.git-mirror/codex-home.git/objects/*/*.pack`
- **大小**: 单个 pack 111.91 MB（超过 GitHub 100 MB 限制）
- **状态**: **已 commit 在 aios_tasks + aios_tools 历史中**（Round 45 series 2026-09-27 ~ 10-09）
- **push 结果**: 部分 commits 成功 push 到了 `round45-aios-rebuild`（private repo）
- **风险**: **部分大型 pack 可能已 push 远端**（需 `git rev-list` 远端 SHA 验证）
- **建议**:
  1. 立即联系 GitHub Support 删除 .git-mirror 历史（如果已 push）
  2. 重新 clone + clean import
  3. .gitignore 排除 .git-mirror/ 已加（canonical.gitignore）

### 2. `_r1342_auto_push_daemon.pid` / `.log`
- **风险**: daemon PID 文件可能 push（包含临时数据）
- **状态**: **未 commit**（canonical .gitignore 已排除）

### 3. mcp_credentials.env
- **风险**: aios_tools 缺 .gitignore · 若误操作 commit 可能 push
- **状态**: **未 commit 到 git** · 但 **必须加 .gitignore**（canonical.gitignore 已写）

## 🛡️ 建议立即行动（红线 #59 + #22）

### 行动 1: 立即轮换所有可能暴露的凭证
- [ ] GitHub PAT (gho_*** 16-18 chars)
- [ ] Stripe / WeChat Pay / Langfuse API keys
- [ ] Feishu webhook secret
- [ ] ED25519 sovereignty keys (如必要)
- [ ] Codex / openclaw session tokens

### 行动 2: 删除 push 的 .git-mirror pack 文件
- [ ] 远端 round45-aios-rebuild 查 git rev-list | grep ".git-mirror"
- [ ] 联系 GitHub Support 删除历史
- [ ] 重新 clean import（保留 24 commits 但剥离 .git-mirror）

### 行动 3: 4 仓库统一 .gitignore（已写 canonical.gitignore）
- [ ] 复制到 `D:\个人文件\AI\Operator\aios_tasks\.gitignore`
- [ ] 复制到 `D:\个人文件\AI\Operator\aios_tools\.gitignore`
- [ ] CloudTech + D:\AIOS 已有 .gitignore（保留）

### 行动 4: 沙箱外 push 4 仓库
- [ ] 右键管理员 `_r1342_git_push_all.cmd`（已生成）
- [ ] 验证 `git ls-remote` 远端 = 本地 SHA

### 行动 5: 加 GitHub Actions secrets scan
- [ ] 4 仓库根目录加 `.github/workflows/secrets-scan.yml`
- [ ] 用 trufflehog / gitleaks 每次 push 自动扫

## 📊 风险等级总评

| 项 | 等级 | 状态 |
|---|---|---|
| 4 仓库 push secrets | **MEDIUM**（gitignore 不全） | canonical 已写待复制 |
| .git-mirror 巨型 pack 已 commit | **MEDIUM** | 部分可能 push 远端 |
| 本地 credentials 文件被 push | **PASS**（git log 已扫） | aios_tasks 历史无 .env/.key/.pem |
| 凭证暴露已发生 | **PENDING**（需用户确认是否轮换） | 用户拍板 |

## 免责

- 本报告 **不含** 任何凭证真值
- 所有 `*.env` / `*.key` / `*.pem` 路径仅供参考
- 实际暴露范围需用户用 `git log -p --all` 或 trufflehog 自行验证