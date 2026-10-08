# CURRENT_REAL_FLOW.md — CloudTech 当前真实代码流

**Date**: 2026-10-08T16:30:00+08:00

## 入口点 (`python cloudtech_main.py` 或类似)

推测入口: `cloudtech_main.py` 或 `cloudtech_app.py` 或 `gateway_v22.py` (227 个 Python 文件命名混乱)
需要真正 audit 后确认。

## 实际 API 路径

`api/` 目录存在但内容未 audit。SPEC 要求 68 features / 32 pages / 87 acceptance tests 全部映射到真实 API + DB。

## 实际 DB 模型

`db/` + `schemas.py` + `database.py` 存在。SPEC 要求 38 AIOS 验收 + 87 CloudTech 验收 全部能在真实 PG/SQLite 上跑通。

## 实际运行链路 (推测, 未验证)

```
http request → cloudtech_main.py
       ↓
   auth.py (身份/会话)
       ↓
   api/ (REST routes)
       ↓
   database.py + db/ (ORM)
       ↓
   billing.py (用量计费)
   crm_*/ (CRM)
   content_*/ (营销内容)
   knowledge.py (知识库)
       ↓
   AIOS (via shengji_agent.py / OpenHands)
       ↓
   ledger / chargeback / audit
```

**注意**: 推测需在真正运行一次 `python cloudtech_main.py` 后验证。当前未启动。

## 当前 risk

1. **入口混乱**: 多个 _v22_*, *_v23_* bak 文件, 不知真正入口
2. **未 running**: 未在 fresh shell 启动过 cloudtech_main.py
3. **API 映射未知**: spec vs reality 未通
5. **测试未跑过**: 30 个 test_*.py 文件全部 NOT_TESTED

## 真实运行环境

`D:\CloudTech-Portable\.env` 含 API keys (高敏感, 不入 git)
Docker 配好 (`docker-compose.yml`, `Dockerfile`)
PG migration script `pg_init.sql`, `pg_migrate.py` 存在

## 待补 (Phase 0 audit)

- 真实入口确认 (运行 `python -m py_compile cloudtech_main.py` 看是否编译)
- 跑 5 个 test 文件看真实通过率
- 真实 DB 连接测试
- 真实 RAG/知识库 flow 测试
