"""WF-G-015 知识导入及 ACL 验证 — 通用
====================================
输入: tenant_id, knowledge_docs[] (含 doc_id + content + acl_tags), user_roles[]
输出: imported_docs[], rejected_docs[] (ACL 拒绝), audit_log[]
"""
from __future__ import annotations
import hashlib
from typing import List, Set
from pydantic import BaseModel, Field
from ..base import run_workflow, validate_workflow_json, validate_workflow_yaml, WorkflowError


class KnowledgeDoc(BaseModel):
    doc_id: str
    title: str
    content: str = Field(..., min_length=1, max_length=100000)
    acl_tags: List[str] = Field(default_factory=lambda: ["public"])
    category: str = "general"


class ACLCheck(BaseModel):
    user_role: str
    allowed_tags: List[str]


class ACLInput(BaseModel):
    tenant_id: str = Field(..., min_length=2)
    knowledge_docs: List[KnowledgeDoc] = Field(..., min_length=1, max_length=200)
    user_roles: List[ACLCheck] = Field(..., min_length=1, max_length=20)
    role_to_query: str  # 谁来查
    workflow_id: str = Field(default="WF-G-015", pattern=r"^WF-G-\d{3}$")


class AuditEntry(BaseModel):
    doc_id: str
    title: str
    decision: str  # imported/rejected
    reason: str


class ACLOutput(BaseModel):
    total_docs: int
    imported: int
    rejected: int
    imported_docs: List[str]
    rejected_docs: List[str]
    audit_log: List[AuditEntry]


def _match(doc_tags: List[str], allowed: Set[str]) -> bool:
    return any(t in allowed for t in doc_tags)


@run_workflow(workflow_id="WF-G-015", tenant_field="tenant_id")
def run_acl(inp: ACLInput) -> ACLOutput:
    role_obj = next((r for r in inp.user_roles if r.user_role == inp.role_to_query), None)
    if role_obj is None:
        raise WorkflowError("WF-G015-ROLE", f"未注册角色 {inp.role_to_query}")

    allowed = set(role_obj.allowed_tags)
    imported: List[str] = []
    rejected: List[str] = []
    audit: List[AuditEntry] = []

    for d in inp.knowledge_docs:
        ok = _match(d.acl_tags, allowed)
        if ok:
            imported.append(d.doc_id)
            audit.append(AuditEntry(doc_id=d.doc_id, title=d.title, decision="imported",
                                    reason=f"命中 {set(d.acl_tags) & allowed}"))
        else:
            rejected.append(d.doc_id)
            audit.append(AuditEntry(doc_id=d.doc_id, title=d.title, decision="rejected",
                                    reason=f"未匹配 allowed {sorted(allowed)}"))

    return ACLOutput(
        total_docs=len(inp.knowledge_docs),
        imported=len(imported),
        rejected=len(rejected),
        imported_docs=imported,
        rejected_docs=rejected,
        audit_log=audit,
    )


validate_json = lambda s: validate_workflow_json(s, ACLInput)
validate_yaml = lambda s: validate_workflow_yaml(s, ACLInput)