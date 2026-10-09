# EXCLUSIONS.md · R1343 指令一第 5 节
**生成时间**: 2026-10-09 20:08 UTC+8

---

## 🚫 C 类绝不提交（指令一第 2 节）

| 路径模式 | 风险类型 | 等级 |
|---|---|---|
| `.env` | production env file | HIGH |
| `.env.local` / `.env.*.local` | local override | HIGH |
| `*.key` | RSA/ED25519 private key | **CRITICAL** |
| `*.pem` / `*.p12` / `*.pfx` / `*.crt` / `*.cer` | cert files | **CRITICAL** |
| `secrets/` / `credentials/` | auth tokens | **CRITICAL** |
| `*.credentials` / `jwt_secret*` / `api_token*` / `oauth_token*` | auth credentials | **CRITICAL** |
| `mcp_credentials.env` | GitHub PAT + Stripe + Feishu | **CRITICAL** |
| `feishu_*` / `wechat_*` / `stripe_*` / `langfuse_*` | API tokens | **CRITICAL** |
| `codex_supervisor.ed25519.key` | sovereignty key | **CRITICAL** |
| `openclaw/dist/credentials-*.mjs` | openclaw internal | HIGH |

---

## 📦 B 类按容量跳过（LFS / artifact / 加密备份）

| 路径模式 | 容量 | 建议 |
|---|---|---|
| `.venv/` | ~50MB per repo | 本地保留 · 不上传 |
| `node_modules/` | ~500MB+ | 本地保留 · 不上传 |
| `.git-mirror/codex-home.git/objects/*.pack` | ~120MB+ | **必须从 git 历史剥离**（B04）|
| `*.tar.gz` / `*.zip` / `*.7z` / `*.iso` / `*.dmg` | variable | 加密离线备份 |
| `*.exe` / `*.dylib` / `*.so` / `*.whl` | variable | build artifacts · 不上传 |
| `models/*.bin` / `models/*.pt` / `models/*.onnx` / `models/*.safetensors` | variable | Git LFS |

---

## 🗑️ A 类但 gitignore 跳过

| 路径模式 | 类型 | 理由 |
|---|---|---|
| `__pycache__/` / `*.pyc` | Python | bytecode cache |
| `*.py[cod]` / `*.so` | Python | compiled artifacts |
| `.pytest_cache/` / `.mypy_cache/` / `.ruff_cache/` | Python | test/lint cache |
| `htmlcov/` / `.coverage` | Python | coverage reports |
| `.tox/` | Python | tox virtual envs |
| `.vscode/` / `.idea/` | IDE | personal IDE config |
| `*.swp` / `*.swo` / `*~` | Vim | backup files |
| `.DS_Store` / `Thumbs.db` | OS | platform junk |
| `*.tmp` / `*.log` / `.cache/` / `tmp/` / `temp/` | tmp | runtime |
| `*.db` / `*.sqlite` / `*.sqlite3` / `*.bak` / `*.dump` | database | runtime data |

---

## 📊 排除统计

| 类别 | 文件数估算 | 节省空间 |
|---|---|---|
| C 类 secrets | 30+ | 防凭证泄露 |
| B 类容量 | 100+ | 防仓库膨胀 |
| A 类缓存 | 10000+ | 防 git 性能下降 |
| **总** | **~10000+** | **~5GB+** |

---

## 🛡️ 验证

每个 commit 前必须：
1. `git status --porcelain` 列出待提交文件
2. 检查所有路径匹配本 EXCLUSIONS.md
3. 若有任何 C 类路径命中 → **STOP** → 报告用户 → 不 commit
4. daemon 已自动 git add -u（不 add untracked）→ 减少风险

---

## ⚠️ 历史例外

**已 commit 的 .git-mirror 巨型 pack**（Round 45 series 2026-09-27 ~ 10-09）：
- 历史 commit **不应** rewrite（红线 #59 不可逆）
- 但需 **B04 cleanup**：rebase 剥离 .git-mirror + 加 .gitignore
- 建议用户拍板 rebase vs force-push vs 远端支持删除历史