-- CloudTech v2.1 — PostgreSQL Migration
-- Usage: psql -U cloudtech -d cloudtech -f 001_initial_schema.sql

BEGIN;

-- ═══════════════════════════════════
-- Tenants
-- ═══════════════════════════════════
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    company TEXT DEFAULT '',
    plan TEXT DEFAULT 'starter' CHECK (plan IN ('starter', 'pro', 'enterprise')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'cancelled')),
    api_key TEXT NOT NULL,
    api_key_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deactivated_at TIMESTAMPTZ
);

-- ═══════════════════════════════════
-- Users
-- ═══════════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'manager', 'user', 'viewer')),
    is_active INTEGER DEFAULT 1,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ═══════════════════════════════════
-- API Keys
-- ═══════════════════════════════════
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT DEFAULT 'Default',
    permissions TEXT DEFAULT 'read',
    enabled INTEGER DEFAULT 1,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_apikeys_tenant ON api_keys(tenant_id);

-- ═══════════════════════════════════
-- Prompts
-- ═══════════════════════════════════
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT DEFAULT 'default' REFERENCES tenants(id),
    name TEXT NOT NULL,
    scene TEXT DEFAULT 'custom',
    system_prompt TEXT,
    user_prompt TEXT,
    model TEXT DEFAULT 'DeepSeek V4 Pro',
    tags TEXT,
    variables TEXT,
    effect_score REAL,
    usage_count INTEGER DEFAULT 0,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    scene TEXT,
    system_prompt TEXT,
    user_prompt TEXT,
    model TEXT DEFAULT 'DeepSeek V4 Pro',
    is_preset INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prompt_deploy_history (
    id SERIAL PRIMARY KEY,
    prompt_id INTEGER REFERENCES prompts(id),
    model TEXT,
    input_variables TEXT,
    output TEXT,
    response_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════
-- Content Production
-- ═══════════════════════════════════
CREATE TABLE IF NOT EXISTS content_productions (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT DEFAULT 'default' REFERENCES tenants(id),
    topic TEXT NOT NULL,
    content_form TEXT,
    creator_style TEXT,
    platform TEXT,
    title TEXT,
    body TEXT,
    word_count INTEGER,
    research_brief TEXT,
    deai_report TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════
-- Audit Log
-- ═══════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT,
    user_id TEXT,
    action TEXT NOT NULL,
    resource TEXT,
    ip_address TEXT,
    user_agent TEXT,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

-- ═══════════════════════════════════
-- Default tenant + admin
-- ═══════════════════════════════════
INSERT INTO tenants (id, name, email, company, plan, status, api_key, api_key_hash)
VALUES ('default', '云数科技', 'admin@cloudtech.com', '云数科技', 'enterprise', 'active',
        'ak-default-admin-key', 'hash-placeholder')
ON CONFLICT (id) DO NOTHING;

COMMIT;
