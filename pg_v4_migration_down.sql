-- CloudTech V4.0 migration DOWN — 回滚
-- 2026-10-13 R1536
-- 执行前必须确认 workpath_run/workflow_node_run 全部清空

DROP TABLE IF EXISTS audit_evidence;
DROP TABLE IF EXISTS approvals;
DROP TABLE IF EXISTS provider_usage;
DROP TABLE IF EXISTS derivative_lineage;
DROP TABLE IF EXISTS content_source;
DROP TABLE IF EXISTS budget_reservation;
DROP TABLE IF EXISTS alias_snapshot;
DROP TABLE IF EXISTS asset_role_binding;
DROP TABLE IF EXISTS workflow_node_run;
DROP TABLE IF EXISTS workpath_run;
DROP TABLE IF EXISTS workpath_definition;
