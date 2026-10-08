# AIOS VNEXT_REAL_CLOSED_LOOP × CLOUDTECH 联合工程 V2.0
# Reality Map — 基于真实审计

**生成时间**: 2026-10-08T16:30:00+08:00
**Codex Supervisor**: 本机 WINDOWS_LOCAL (DESKTOP-0JKD1FQ, user xinzh)
**EXECUTION_HOST**: WINDOWS_LOCAL (确认)
**EXECUTION_BRIDGE**: 本地 Direct FS access to `D:\CloudTech-Portable\` (无 cc-switch 桥限制)
**Authorization scope**: 全权限读写 `D:\CloudTech-Portable\` (用户指定为本工程根目录)

## 顶层架构身份核验 (3 个真实对象)

| 身份 | 路径 | Git remote | HEAD | 工作区状态 |
|---|---|---|---|---|
| **AIOS_PERSONAL** | `D:\AIOS\kernel\` | (no remote, local only) | `ab37b07` | clean (Phase A+B+C+D+E complete) |
| **CLOUDTECH_ENTERPRISE_PRODUCT** | `D:\CloudTech-Portable\` | `github.com/macxiaxia-boop/cloudtech-spa-v2.git` | `6ce295c8` | modified (3 deleted, 70+ untracked) |
| **HISTORICAL_CLOUDTECH_RUNTIME** | `D:\CloudTech-Portable\_HANDOFF_V2_UNZIPPED\references\CLOUDTECH_MASTER_ARCHITECTURE_AND_BUILD_COMMAND_v1.0.md` | (archived, not in main) | n/a | read-only history |

## CloudTech 实际状态 (228 个 .py files)

| 类别 | 数量 | 备注 |
|---|---|---|
| 顶层 Python 文件 | 228 | 含 _v23*, _v22*, _patch* |
| 顶层 _v23_*.py | 67 | 历史 watchdog/patch 系列, 多 bak |
| 测试文件 | 30 | `test_*.py` 在 tests/ |
| __pycache__ | many | 大部分 _v23 系列未 clean |
| _archived 目录 | multiple | 历史归档 |

## CloudTech 实际可跑测试 (初步)

| 测试 | 命令 | 当前状态 |
|---|---|---|
| `tests/test_models.py` | `python -m pytest tests/test_models.py -v` | NOT_TESTED |
| `tests/test_modules.py` | `python -m pytest tests/test_modules.py -v` | NOT_TESTED |
| `tests/test_integration.py` | `python -m pytest tests/test_integration.py -v` | NOT_TESTED |
| `tests/test_api.py` | `python -m pytest tests/test_api.py -v` | NOT_TESTED |
| `tests/test_crm.py` | `python -m pytest tests/test_crm.py -v` | NOT_TESTED |
| `tests/test_d13_16_postgres_migration.py` | `python -m pytest tests/test_d13_16_postgres_migration.py -v` | NOT_TESTED |

## 已知运行进程 (初步 scan)

待补: `ps aux | grep -E "cloudtech|ai_|ai-"` 详细列表

## 已知网络/外部依赖

- `proxy = http://127.0.0.1:7897` (gitconfig)
- GitHub credential helper configured (gh auth)
- Gitee credential configured
- .env 在 `D:\CloudTech-Portable\.env` (含 API keys - 高敏感, 不入 git)

## 现实证据根

**REALITY_MAP.csv** + **REPO_MAP.csv** + **CURRENT_REAL_FLOW.md** + **GAP_MATRIX.csv** 在同一目录下生成。
