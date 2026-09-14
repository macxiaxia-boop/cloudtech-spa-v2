-- CloudTech SaaS Phase 45 D13-16 — PostgreSQL init
-- ====================================================
-- Docker entrypoint 自动执行（仅首次启动）
-- 11 张核心表由 alembic upgrade head 管理（D13-16 迁移动作）

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 模糊搜索

-- 注：实际建表由 alembic upgrade head 自动生成 DDL 执行
-- 这里仅放扩展初始化，避免与 alembic 冲突
