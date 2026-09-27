-- CloudTech PostgreSQL schema · 2026-09-25 R288
-- 与 SQLite schema 100% 对齐, 字段名/类型一致 (TEXT -> TEXT/VARCHAR, INTEGER -> INTEGER, REAL -> NUMERIC)
-- 执行顺序: docker compose up 自动跑 (init script)

-- 1. Auth & users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(128) NOT NULL,
    password_salt VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    industry VARCHAR(32) DEFAULT 'decoration',
    role VARCHAR(32) DEFAULT 'user',
    plan VARCHAR(32) DEFAULT 'free',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

-- 2. CRM leads
CREATE TABLE IF NOT EXISTS leads (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(64),
    industry VARCHAR(32),
    source VARCHAR(64),
    stage VARCHAR(32) DEFAULT 'consult',
    owner_user_id VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_leads_tenant ON leads(tenant_id);
CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads(industry);

-- 3. 数字员工
CREATE TABLE IF NOT EXISTS employees (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    preset VARCHAR(64) NOT NULL,
    name VARCHAR(255),
    industry VARCHAR(32),
    config_json TEXT,
    status VARCHAR(32) DEFAULT 'deployed',
    deployed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_invoked_at TIMESTAMP,
    invoke_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_emp_tenant ON employees(tenant_id);

-- 4. AI 内容历史
CREATE TABLE IF NOT EXISTS content_history (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    tenant_id VARCHAR(64),
    industry VARCHAR(32),
    preset VARCHAR(64),
    prompt TEXT,
    result_text TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0.0,
    provider VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    platform VARCHAR(32),
    topic TEXT
);
CREATE INDEX IF NOT EXISTS idx_content_tenant ON content_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_content_created ON content_history(created_at DESC);

-- 5. Quota 月度配额
CREATE TABLE IF NOT EXISTS quota (
    tenant_id VARCHAR(64) PRIMARY KEY,
    monthly_calls_limit INTEGER DEFAULT 5000,
    monthly_calls_used INTEGER DEFAULT 0,
    monthly_tokens_limit INTEGER DEFAULT 2000000,
    monthly_tokens_used INTEGER DEFAULT 0,
    plan VARCHAR(32) DEFAULT 'free',
    reset_at TIMESTAMP
);

-- 6. Invoice 计费流水
CREATE TABLE IF NOT EXISTS invoice (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64),
    amount_usd NUMERIC(10,6),
    calls INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    provider VARCHAR(64),
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_invoice_tenant ON invoice(tenant_id);

-- 7. AIOS §8 桥接 — aios_user
CREATE TABLE IF NOT EXISTS aios_user (
    user_id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(128),
    password_salt VARCHAR(64),
    tenant_id VARCHAR(64) NOT NULL,
    industry VARCHAR(32) NOT NULL,
    role VARCHAR(32) DEFAULT 'employee',
    jwt_token TEXT,
    jwt_expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_aios_user_tenant ON aios_user(tenant_id);

-- 8. AIOS §8 桥接 — aios_subscription
CREATE TABLE IF NOT EXISTS aios_subscription (
    subscription_id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    industry VARCHAR(32) NOT NULL,
    plan VARCHAR(32) NOT NULL,
    sku_code VARCHAR(64) NOT NULL,
    amount_cny NUMERIC(10,2),
    status VARCHAR(32) DEFAULT 'pending',
    session_id VARCHAR(64),
    stripe_sig VARCHAR(255),
    activated_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_aios_sub_tenant ON aios_subscription(tenant_id);

-- 9. 桥接故障记录
CREATE TABLE IF NOT EXISTS bridge_incident (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    target VARCHAR(255),
    error TEXT,
    fallback_used INTEGER DEFAULT 1
);

-- pgvector 占位 (后续可加 embedding)
-- CREATE EXTENSION IF NOT EXISTS vector;

COMMENT ON TABLE users IS 'CloudTech SaaS 用户表 (4 行业 tenant)';
COMMENT ON TABLE leads IS 'CRM 线索表 (含软删 deleted_at)';
COMMENT ON TABLE employees IS '数字员工表 (8 大 preset × 4 行业)';
COMMENT ON TABLE content_history IS 'AI 内容生成历史';
COMMENT ON TABLE quota IS '租户月度配额';
COMMENT ON TABLE invoice IS '计费流水 (L1 mock,L5 接 Stripe)';
COMMENT ON TABLE aios_user IS 'AIOS §8.6 桥接用户表 (5 角色)';
COMMENT ON TABLE aios_subscription IS 'AIOS §8.7 订阅表 (3 套餐 × 4 行业 = 12 SKU)';
COMMENT ON TABLE bridge_incident IS '桥接故障记录 (L1 fallback 标志)';
