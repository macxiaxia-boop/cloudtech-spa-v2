"""Tenant-scoped V4 request guards; shared by existing API, not a new auth subsystem."""
from __future__ import annotations
import hashlib
import json
from typing import Any, Dict, Iterable
from fastapi import HTTPException

def get_owned_run(orchestrator: Any, run_id: str, tenant_id: str) -> Any:
    record = orchestrator.get_run(run_id)
    if record is None or record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="run 不存在")
    return record

def scoped_idempotency_key(tenant_id: str, user_key: str | None) -> str | None:
    if user_key is None:
        return None
    if not isinstance(user_key, str) or not 1 <= len(user_key) <= 128:
        raise HTTPException(status_code=422, detail="idempotency_key 长度必须为 1..128")
    raw = json.dumps([tenant_id, "v4.workpath.create", user_key],
                     ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "v4:" + hashlib.sha256(raw).hexdigest()

def compatible_run_request(run: Any, req: Any) -> bool:
    return (run.path_id == req.path_id
            and run.path_revision == req.revision
            and run.project_id == req.project_id
            and run.conversation_id == req.conversation_id
            and run.budget_cap_cents == req.budget_cap_cents
            and run.input_bindings == req.input_bindings
            and req.scope == "tenant")

def collect_role_values(refs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    roles: Dict[str, list] = {}
    for ref in refs:
        role = ref.get("role")
        if not isinstance(role, str) or not role:
            continue
        value = ref.get("value")
        if isinstance(value, list):
            roles.setdefault(role, []).extend(value)
        else:
            roles.setdefault(role, []).append(value)
    return roles
