-- CloudTech V4.0 横向基础设施 migration (2026-10-13)
-- 新增表 — 不修改 pg_init.sql 中已有 9 表，保留兼容
-- 配合 pg_v4_migration_down.sql 回滚

-- 1. 工作路径定义 (typed contract registry)
CREATE TABLE IF NOT EXISTS workpath_definition (
    id                  VARCHAR(64) PRIMARY KEY,
    revision            INTEGER NOT NULL DEFAULT 1,
    domain              VARCHAR(32) NOT NULL,
    title               VARCHAR(255) NOT NULL,
    goal                TEXT NOT NULL,
    triggers_json       TEXT NOT NULL DEFAULT '[]',
    preconditions_json  TEXT NOT NULL DEFAULT '[]',
    planner             VARCHAR(64) NOT NULL DEFAULT 'default',
    steps_json          TEXT NOT NULL DEFAULT '[]',
    quality_gates_json  TEXT NOT NULL DEFAULT '[]',
    exported_artifacts_json TEXT NOT NULL DEFAULT '[]',
    recovery_json       TEXT NOT NULL DEFAULT '{}',
    privacy_class       VARCHAR(32) NOT NULL DEFAULT 'public',
    permissions_json    TEXT NOT NULL DEFAULT '[]',
    billing_policy      VARCHAR(64) NOT NULL DEFAULT 'FREE_LOCAL',
    evidence_template   TEXT NOT NULL DEFAULT '{}',
    version_hash        VARCHAR(64) NOT NULL,
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_wp_def_domain ON workpath_definition(domain);
CREATE INDEX IF NOT EXISTS idx_wp_def_enabled ON workpath_definition(enabled);

-- 2. 工作路径运行实例
CREATE TABLE IF NOT EXISTS workpath_run (
    id                  VARCHAR(64) PRIMARY KEY,
    tenant_id           VARCHAR(64) NOT NULL,
    project_id          VARCHAR(64),
    conversation_id     VARCHAR(64),
    path_id             VARCHAR(64) NOT NULL,
    path_revision       INTEGER NOT NULL,
    input_bindings_json TEXT NOT NULL DEFAULT '{}',
    status              VARCHAR(32) NOT NULL DEFAULT 'PLANNED',
    -- PLANNED/INPUT_BOUND/READY/RUNNING/REVIEW_REQUIRED/APPROVED/COMPLETED/BLOCKED_PERMISSION/BLOCKED_BUDGET/RETRY_WAIT/FAILED/CANCELED/PARTIAL
    scope               VARCHAR(32) NOT NULL DEFAULT 'tenant',
    budget_cap_cents    INTEGER NOT NULL DEFAULT 0,
    budget_spent_cents  INTEGER NOT NULL DEFAULT 0,
    idempotency_key     VARCHAR(128) UNIQUE,
    last_node_id        VARCHAR(64),
    error_code          VARCHAR(64),
    error_message       TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_wp_run_tenant ON workpath_run(tenant_id);
CREATE INDEX IF NOT EXISTS idx_wp_run_status ON workpath_run(status);
CREATE INDEX IF NOT EXISTS idx_wp_run_idem ON workpath_run(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_wp_run_path ON workpath_run(path_id);

-- 3. 工作流节点运行（每 step 一行）
CREATE TABLE IF NOT EXISTS workflow_node_run (
    id                  VARCHAR(64) PRIMARY KEY,
    run_id              VARCHAR(64) NOT NULL REFERENCES workpath_run(id),
    node_id             VARCHAR(64) NOT NULL,
    node_kind           VARCHAR(32) NOT NULL,
    -- TRANSFORM/FETCH_PUBLIC/MODEL_REASON/MEDIA_GENERATE/HUMAN_REVIEW/EXPORT/PUBLISH_WITH_AUTH
    operation           VARCHAR(128) NOT NULL,
    requires_json       TEXT,
    produces_json       NULL,
    input_hash          VARCHAR(64) NOT NULL,
    output_ref          TEXT,
    provider_req_id     VARCHAR(128),
    provider_name       VARCHAR(64),
    retry_count         INTEGER NOT NULL DEFAULT 0,
    max_retries         INTEGER NOT NULL DEFAULT 3,
    status              VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    cost_cents          INTEGER NOT NULL DEFAULT 0,
    cost_class          VARCHAR(32) NOT NULL DEFAULT 'FREE_LOCAL',
    error_code          VARCHAR(64),
    error_message       TEXT,
    started_at          TIMESTAMP,
    finished_at         TIMESTAMP,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_node_run_run ON workflow_node_run(run_id);
CREATE INDEX IF NOT EXISTS idx_node_run_status ON workflow_node_run(status);
CREATE INDEX IF NOT EXISTS idx_node_run_provider ON workflow_node_run(provider_name);

-- 4. 资产角色绑定（图 1/图 6 = alias → asset_version）
CREATE TABLE IF NOT EXISTS asset_role_binding (
    id                  VARCHAR(64) PRIMARY KEY,
    tenant_id           VARCHAR(64) NOT NULL,
    project_id          VARCHAR(64),
    conversation_id     VARCHAR(64) NOT NULL,
    alias               VARCHAR(32) NOT NULL,
    role                VARCHAR(32) NOT NULL,
    asset_id            VARCHAR(64) NOT NULL,
    version_id          VARCHAR(64) NOT NULL,
    message_id          VARCHAR(64),
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_asset_role_convo ON asset_role_binding(conversation_id, alias);
CREATE INDEX IF NOT EXISTS idx_asset_role_tenant ON asset_role_binding(tenant_id);

-- 5. 别名快照（防止覆盖历史）
CREATE TABLE IF NOT EXISTS alias_snapshot (
    id                  VARCHAR(64) PRIMARY KEY,
    conversation_id     VARCHAR(64) NOT NULL,
    message_id          VARCHAR(64) NOT NULL,
    alias               VARCHAR(32) NOT NULL,
    asset_id            VARCHAR(64) NOT NULL,
    version_id          VARCHAR(64) NOT NULL,
    snapshot_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alias_snap_convo ON alias_snapshot(conversation_id, alias);
CREATE INDEX IF NOT EXISTS idx_alias_snap_message ON alias_snapshot(message_id);

-- 6. 预算预占 (FREE_LOCAL/METERED_NONMEDIA/METERED_MEDIA/EXTERNAL_WRITE)
CREATE TABLE IF NOT EXISTS budget_reservation (
    id                  VARCHAR(64) PRIMARY KEY,
    tenant_id           VARCHAR(64) NOT NULL,
    run_id              VARCHAR(64) NOT NULL,
    node_id             VARCHAR(64),
    cost_class          VARCHAR(32) NOT NULL,
    reserved_cents      INTEGER NOT NULL,
    settled_cents       INTEGER NOT NULL DEFAULT 0,
    released_cents      INTEGER NOT NULL DEFAULT 0,
    status              VARCHAR(32) NOT NULL DEFAULT 'reserved',
    -- reserved/settled/released/over
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    settled_at          TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_budget_tenant ON budget_reservation(tenant_id);
CREATE INDEX IF NOT EXISTS idx_budget_run ON budget_reservation(run_id);

-- 7. 内容来源溯源 (provenance)
CREATE TABLE IF NOT EXISTS content_source (
    id                  VARCHAR(64) PRIMARY KEY,
    asset_id            VARCHAR(64) NOT NULL,
    source_platform     VARCHAR(32),
    source_url          TEXT,
    source_author       VARCHAR(255),
    source_time         TIMESTAMP,
    retrieval_policy    VARCHAR(32),
    rights_status       VARCHAR(32) NOT NULL DEFAULT 'unknown',
    extraction_method   VARCHAR(64),
    reference_ids       TEXT,
    version_hash        VARCHAR(64),
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_source_asset ON content_source(asset_id);

-- 8. 二创谱系
CREATE TABLE IF NOT EXISTS derivative_lineage (
    id                  VARCHAR(64) PRIMARY KEY,
    derivative_asset_id VARCHAR(64) NOT NULL,
    source_asset_id     VARCHAR(64),
    parent_run_id       VARCHAR(64),
    operation           VARCHAR(64) NOT NULL,
    similarity_score    NUMERIC(4,3),
    notes               TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_derivative ON derivative_lineage(derivative_asset_id);

-- 9. Provider 用量审计
CREATE TABLE IF NOT EXISTS provider_usage (
    id                  VARCHAR(64) PRIMARY KEY,
    tenant_id           VARCHAR(64) NOT NULL,
    run_id              VARCHAR(64),
    node_id             VARCHAR(64),
    provider_name       VARCHAR(64) NOT NULL,
    operation           VARCHAR(128) NOT NULL,
    cost_cents          INTEGER NOT NULL DEFAULT 0,
    cost_class          VARCHAR(32) NOT NULL,
    external_request_id VARCHAR(128),
    input_hash          VARCHAR(64),
    started_at          TIMESTAMP,
    finished_at         TIMESTAMP,
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    error_code          VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_usage_tenant ON provider_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON provider_usage(provider_name);

-- 10. 审批
CREATE TABLE IF NOT EXISTS approvals (
    id                  VARCHAR(64) PRIMARY KEY,
    run_id              VARCHAR(64) NOT NULL,
    checkpoint_id       VARCHAR(64) NOT NULL,
    approver_user_id    VARCHAR(64),
    decision            VARCHAR(32) NOT NULL,
    -- approved/rejected/pending
    approved_budget_cents INTEGER,
    notes               TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_approvals_run ON approvals(run_id);

-- 11. 审计证据
CREATE TABLE IF NOT EXISTS audit_evidence (
    id                  VARCHAR(64) PRIMARY KEY,
    run_id              VARCHAR(64) NOT NULL,
    node_id             VARCHAR(64),
    evidence_kind       VARCHAR(32) NOT NULL,
    -- input/output/decision/provider_response/rollback
    payload_json        TEXT NOT NULL,
    evidence_hash       VARCHAR(64) NOT NULL,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON audit_evidence(run_id);

COMMENT ON TABLE workpath_definition IS 'V4 工作路径定义 (typed contract)';
COMMENT ON TABLE workpath_run IS 'V4 运行实例 + 幂等键';
COMMENT ON TABLE workflow_node_run IS 'V4 单节点运行 + provider_req_id (防双扣费)';
COMMENT ON TABLE asset_role_binding IS '会话级 alias → asset_version (图1/图6)';
COMMENT ON TABLE alias_snapshot IS '别名快照 (历史不可覆盖)';
COMMENT ON TABLE budget_reservation IS '预算预占 → settle → release';
COMMENT ON TABLE content_source IS '内容来源溯源 (公开/授权/私有)';
COMMENT ON TABLE derivative_lineage IS '二创谱系 + 相似性分数';
COMMENT ON TABLE provider_usage IS '供应商调用审计';
COMMENT ON TABLE approvals IS '人工审批记录';
COMMENT ON TABLE audit_evidence IS '审计证据 (input/output/rollback)';
