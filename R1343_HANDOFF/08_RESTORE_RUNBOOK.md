# RESTORE_RUNBOOK.md · R1343 指令一第 5 节
**生成时间**: 2026-10-09 20:08 UTC+8

---

## 🎯 目标

在 **不触碰生产数据** 的前提下，独立临时目录独立权限范围：
- 验证 4 仓库可 clone
- 检查代码文件数量 + hash + LFS
- 尝试 install / build / 关键 smoke test
- 验证加密备份的解包完整性

---

## 📋 步骤 1: GitHub 远端验证（沙箱外执行）

```bash
# 在沙箱外的 PowerShell / Git Bash

# 1. 验证 CloudTech 远端
git ls-remote https://github.com/macxiaxia-boop/cloudtech-spa-v2.git master
# 期望: <SHA>\t\trefs/heads/master
# 比对: 本地 d0dcd392

# 2. 验证 AIOS 远端
git ls-remote https://github.com/macxiaxia-boop/aios-sovereignty-v.git main
# 比对: 本地 4e5447f
# 注: 远端 main 可能被 forced update 改变 SHA · 需 git log 看远端 commits

# 3. 验证 round45-aios-rebuild 远端 (private)
gh auth status
git ls-remote https://github.com/macxiaxia-boop/round45-aios-rebuild.git master
# 比对: 本地 e5beb002 / abc88f86
```

---

## 📋 步骤 2: clone + checkout（沙箱外执行）

```bash
# 创建独立临时目录（不在 D:\CloudTech-Portable 或 D:\AIOS）
mkdir C:\restore_test_20261009
cd C:\restore_test_20261009

# 1. CloudTech clone
git clone https://github.com/macxiaxia-boop/cloudtech-spa-v2.git cloudtech_test
cd cloudtech_test
git checkout d0dcd392
# 文件数检查
find . -type f -not -path "./.git/*" | wc -l
# 期望: ~1000+ files

# 2. AIOS Sovereignty clone
cd ..
git clone https://github.com/macxiaxia-boop/aios-sovereignty-v.git aios_test
cd aios_test
git checkout 4e5447f
find . -type f -not -path "./.git/*" | wc -l
# 期望: ~500 files

# 3. round45-aios-rebuild clone
cd ..
gh repo clone macxiaxia-boop/round45-aios-rebuild round45_test
cd round45_test
git checkout 8eaaa7f7  # 24 commits 中任一 baseline
find . -type f -not -path "./.git/*" | wc -l
# 期望: ~5000+ files
```

---

## 📋 步骤 3: hash 验证（关键 smoke test）

```bash
# 对比本地 + 远端 + clone 三方 hash
cd C:\restore_test_20261009\cloudtech_test
git rev-parse HEAD
# 期望: d0dcd392...  (与本地 + 远端一致)

cd ..\aios_test
git rev-parse HEAD
# 期望: 4e5447f...  (与本地 + 远端一致)

# 若三方一致 → RESTORE_VERIFIED
# 若不一致 → 标 BACKUP_SECONDARY_BLOCKED
```

---

## 📋 步骤 4: 代码完整性 + LFS 检查

```bash
cd C:\restore_test_20261009\cloudtech_test
# 检查 LFS 对象
git lfs ls-files | wc -l
# 期望: 0 (CloudTech 无 LFS)

# 关键 smoke test
cd web/vite-spa  # 或类似入口
npm ci
npm run build
# 期望: build 成功 + dist-v45/ 产物

cd ../..
python -c "import flask, waitress; print('deps OK')"
# 期望: deps 安装成功
```

---

## 📋 步骤 5: 加密备份解包（独立测试）

```bash
# 待 L4 拍板加密目标后补
# 当前: BLOCKED
echo "Encryption backup target: TBD (B07 L4 user decision required)"
```

---

## 🚨 异常处理

### 异常 1: ls-remote 与本地 SHA 不一致
- **可能原因**: 远端历史被 force update · 或本地未 push
- **处理**: 用 `git log --all` + `git reflog` 看本地历史 · 与远端比对
- **恢复**: `git pull --rebase` 或 `git pull --no-rebase --allow-unrelated-histories`

### 异常 2: clone 后文件数差异
- **可能原因**: LFS 对象缺失 / submodule 未初始化
- **处理**: `git lfs fetch` + `git submodule update --init --recursive`

### 异常 3: build 失败
- **可能原因**: .env / .venv 缺失（gitignore 排除）
- **处理**: 重建 .venv / 复制 .env.example 到 .env（不放真值）

---

## ✅ 完成标志

```
CLAUDE_GITHUB_HANDOFF: PARTIAL → PASS
CloudTech: https://github.com/macxiaxia-boop/cloudtech-spa-v2 | master=d0dcd392 | local=D:\CloudTech-Portable | sync=PASS | restore=PASS
AIOS: https://github.com/macxiaxia-boop/aios-sovereignty-v | main=4e5447f | local=D:\AIOS | sync=PASS | restore=PASS
round45-aios-rebuild (shared): ... | sync=PASS | restore=PASS
Security scan: PASS (after secret rotation)
Remote check: PASS (after ls-remote verification)
Automation: R1342_AutoPush_Daemon schtask Ready
Handoff index local: D:\个人文件\AI\Operator\GITHUB_HANDOFF_20261009\
Handoff index GitHub: (待 commit 到 4 仓库)
Outstanding blockers: NONE
NEXT_HANDOFF_ALLOWED: YES
```

**当前**: PARTIAL（待 B01-B06 全部解决才能 PASS）