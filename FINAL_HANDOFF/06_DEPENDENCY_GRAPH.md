# DEPENDENCY_GRAPH.md — 真实依赖

**Date**: 2026-10-08T16:30:00+08:00

## Critical Path

```
T00 (Reality Audit)
  ├── T01 (ADR-PRODUCT-001: 旧 CloudTech 命名冲突)
  ├── T02 (UI/API/DB 三方映射)
  ├── T03 (Git/DB Baseline freeze)
  │     └── T04 (施工分支)
  │     └── T05 (Tenant/Identity/Session)
  │           ├── T06 (RBAC/Audit)
  │           │     └── T17 (Connector auth/revoke)
  │           │           └── T11 (Provider adapter registry)
  │           │                 └── T12-T15 (Pricing + Credits + Bill)
  │           │                       └── T16 (Real Provider Golden Task)
  │           ├── T07 (Digital Employee template/instance)
  │           ├── T08 (Workflow DAG/version)
  │           │     └── T09 (Workflow Runner + Evidence)
  │           │           └── T33 (CloudTech→AIOS contract)
  │           ├── T10 (Tenant knowledge ACL)
  │           └── T20 (Growth metric baseline)
  │                 └── T19 (CRM lead ingest/dedup/assign)
  │                       └── T18 (Marketing profile/topic)
  ├── T22 (UI Design System)
  └── T23-T28 (E2E/SEC/fail-inject/backup-rollback/pilot-deploy)
        └── T29 (First business diagnose/baseline)
              └── T30 (First business goal closed-loop)
                          └── T31 (Second customer migration)
                                └── T32 (Industry SOP + Skill candidate)
                                      └── T34 (Business→AIOS evol feedback)
                                            └── T37 (Case public approval)
                                                  └── T38-T39 (Private deploy / channel mgmt)
```

## Bottleneck Risks

1. **T03 (Baseline)**: 必需, 否则无法防 rollback
2. **T16 (Real Provider Golden Task)**: 需真实 API key, BLOCKED if no contract
4. **T29-T30 (Pilot)**: 需真实企业授权, BLOCKED_EXTERNAL
5. **T38 (Private deploy)**: 需用户单独批准, 不可自动

## Internal Constraint

Phase A (P0) → T05~T10 必打通企业 + 工作流 + Knowledge 安全
Phase B (P0) → T11~T16 真实供应商 + 计费 + Golden Task
Phase C (P1) → T29~T34 真实企业 + 业务闭环
Phase D (P2) → T38~T39 私有部署
