# BLOCKERS.md · R1343 指令一第 11 节
**生成时间**: 2026-10-09 20:08 UTC+8
**诚实状态**: 当前 **CLAUDE_GITHUB_HANDOFF: PARTIAL**（指令一第 10 节必须诚实汇报）

---

## 🚧 关键 Blockers（按优先级排序）

| ID | 标题 | 严重度 | 阻塞范围 | 解决方案 |
|---|---|---|---|---|
| **B01** | **沙箱网络隔离**（CC 沙箱无法连 github.com:443） | **CRITICAL** | 所有 4 仓库的 push + ls-remote | 用户右键 `_r1342_git_push_all.cmd` 在沙箱外执行 |
| **B02** | **D:\AIOS 远端 main 被 forced update** | HIGH | D:\AIOS push | `git pull --no-rebase --allow-unrelated-histories origin main` 后 push |
| **B03** | **aios_tasks/aios_tools 缺 .gitignore** | HIGH | C 类敏感文件 (.env/.key/.pem) 可能误 push | 复制 `_canonical.gitignore` 到 2 个目录 |
| **B04** | **.git-mirror 巨型 pack 在历史**（Round 45 series） | MEDIUM | round45-aios-rebuild push 部分拒绝 | rebase 剥离 .git-mirror + 加 .gitignore |
| **B05** | **Round 45 部分 commits 可能已 push 含 .git-mirror** | MEDIUM | 远端仓库可能有巨型 pack | `git ls-remote` 验证 + 联系 GitHub Support 删除 |
| **B06** | **凭证轮换建议**（GitHub PAT + Stripe + Feishu + ED25519） | MEDIUM | 即使没明确暴露建议轮换 | 用户在 GitHub Settings + Stripe Dashboard + Feishu 后台手动轮换 |
| **B07** | **加密备份第二条链路未做**（L4 越界） | MEDIUM | 灾难恢复 | 待用户拍板 GPG key + 加密目标路径 |
| **B08** | **round45-aios-rebuild private · MCP 无 read scope** | LOW | 远端验证 | 待用户授权 + 提供 read scope token |
| **B09** | **daemon --once 仍 timeout** | LOW | 自我测试 | 需更细粒度增量 add + 后台跑 |
| **B10** | **4 仓库 main/master 分支保护未开启** | MEDIUM | 防止 force push | 用户在 GitHub Settings 开启 Require PR + block force push |
| **B11** | **GitHub Actions workflow 未部署到 4 仓库** | LOW | CI/lint | 复制 `_r1342_github_actions_workflow.yml` 到 4 个仓库 |

---

## 🛠 立即可执行（沙箱外 · 用户操作）

### 优先级 1（必须做）

```bash
# 1. 复制 .gitignore 到 aios_tasks + aios_tools
cp "D:\个人文件\AI\Operator\GITHUB_HANDOFF_20261009\_canonical.gitignore" \
   "D:\个人文件\AI\Operator\aios_tasks\.gitignore"

cp "D:\个人文件\AI\Operator\GITHUB_HANDOFF_20261009\_canonical.gitignore" \
   "D:\个人文件\AI\Operator\aios_tools\.gitignore"

# 2. 右键管理员运行一键 push 脚本
右键 "D:\个人文件\AI\Operator\aios_tools\_r1342_git_push_all.cmd" → Run as Administrator

# 3. 验证 4 仓库远端 SHA（沙箱外）
git ls-remote https://github.com/macxiaxia-boop/cloudtech-spa-v2.git master
git ls-remote https://github.com/macxiaxia-boop/aios-sovereignty-v.git main
git ls-remote https://github.com/macxiaxia-boop/round45-aios-rebuild.git master

# 4. 处理 D:\AIOS 远端 forced update
cd D:\AIOS
git pull --no-rebase --allow-unrelated-histories origin main
git push origin main
```

### 优先级 2（应该做）

```bash
# 5. 注册 daemon 自动 push
右键 "D:\个人文件\AI\Operator\aios_tools\_R1342_AutoPush_CronRegister.cmd" → Run as Administrator
schtasks /Query /TN R1342_AutoPush_Daemon /V /FO LIST

# 6. 4 仓库开启 main 分支保护（GitHub 网页）
# - Settings → Branches → Branch protection rules → Add rule
# - Branch name pattern: main (or master)
# - ✅ Require pull request reviews before merging
# - ✅ Require status checks to pass before merging
# - ✅ Do not allow forcing the branch
# - ✅ Do not allow deletions

# 7. 部署 GitHub Actions workflow
# 复制 D:\个人文件\AI\Operator\aios_tools\_r1342_github_actions_workflow.yml
# 到 4 仓库的 .github/workflows/sync.yml
```

### 优先级 3（建议做）

```bash
# 8. 轮换所有可能暴露的凭证（红线 #22 + #59 + #87 + 指令一第 2 节）
# - GitHub Settings → Developer settings → Personal access tokens → 轮换
# - Stripe Dashboard → API keys → 轮换
# - Feishu 后台 → 机器人 webhook → 轮换
# - AIOS sovereignty key (ED25519) → 重新生成 + 备份

# 9. 处理 .git-mirror 巨型 pack 风险
# 联系 GitHub Support: https://support.github.com/contact
# 提供 repo 名 + 历史 commit SHA 列表 + 申请删除大文件
# 或本地 rebase + force push（但红线 #59 不可逆 · 需 user 拍板）

# 10. 加密备份第二条链路（L4 越界 · 待 user 拍板）
# 决策: GPG key 路径 + 加密目标路径 + 保留周期
```

---

## 📊 阻塞进度（截止 2026-10-09 20:08）

```
B01 (沙箱网络隔离):       [==========] 100% 待沙箱外执行
B02 (远端 forced update): [========  ] 80%  pull 命令已写
B03 (缺 .gitignore):      [==========] 100% canonical 已写待复制
B04 (.git-mirror pack):   [====    ] 40%  .gitignore 已加 · rebase 待做
B05 (部分 push 含 pack):  [===     ] 30%  待 ls-remote 验证
B06 (凭证轮换):           [        ] 0%   用户手动
B07 (加密备份第二条链):   [        ] 0%   L4 待拍板
B08 (private MCP read):   [        ] 0%   需新 token scope
B09 (daemon --once):      [====    ] 40%  lock+add -u 修了
B10 (分支保护):            [        ] 0%   用户 GitHub 网页
B11 (Actions workflow):   [====    ] 40%  模板已写待部署
```

---

## 🎯 NEXT_HANDOFF_ALLOWED 判定

**当前**: **NO** (PARTIAL)

**变 YES 的条件**（按指令一第 10 节）：
- [ ] B01 解决（4 仓库成功 push + ls-remote SHA 一致）
- [ ] B03 解决（canonical .gitignore 已复制）
- [ ] B05 解决（远端无 .git-mirror 大文件残留）
- [ ] B06 完成（凭证轮换）
- [ ] B10 完成（4 仓库分支保护开启）
- [ ] Restore test PASS（4 仓库 clone + checkout + hash 一致）

---

## 📝 用户回复模板

```
我（用户）已经完成以下 blockers：
✅ B01 _r1342_git_push_all.cmd 运行成功，4 仓库全部 push
✅ B03 canonical .gitignore 已复制
✅ B06 已轮换 GitHub PAT / Stripe / Feishu 凭证
✅ B10 已开启 4 仓库分支保护

未完成（如有）：
⚠️ B05 远端 .git-mirror 大文件：正在联系 GitHub Support
⚠️ B07 加密备份：等下次会话决策
```

收到后我会立即跑 ls-remote 验证 + 写 FINAL_STATUS.json = PASS + NEXT_HANDOFF_ALLOWED=YES

---

**当前诚实状态**: PARTIAL · B01-B06 全部需要用户拍板 + 沙箱外执行 · CC 在沙箱内做完了所有可做的工作（摸底 + 文档 + 本地 commit + 持续同步脚本）