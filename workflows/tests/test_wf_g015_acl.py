"""Tests for WF-G-015 知识导入及 ACL 验证 (>=5 cases)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError
from workflows.base import RunHistoryTracker
from workflows.impl.wf_g015_acl import (
    run_acl, ACLInput, KnowledgeDoc, ACLCheck, validate_json,
)


@pytest.fixture(autouse=True)
def _reset():
    RunHistoryTracker.instance().reset()


def test_acl_all_public_match():
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[
            KnowledgeDoc(doc_id="d1", title="公开文章", content="public content", acl_tags=["public"]),
            KnowledgeDoc(doc_id="d2", title="另一篇", content="more content", acl_tags=["public"]),
        ],
        user_roles=[ACLCheck(user_role="viewer", allowed_tags=["public"])],
        role_to_query="viewer",
    )
    out = run_acl(inp)
    assert out["status"] == "success"
    o = out["output"]
    assert o["total_docs"] == 2
    assert o["imported"] == 2
    assert o["rejected"] == 0
    assert set(o["imported_docs"]) == {"d1", "d2"}


def test_acl_partial_match():
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[
            KnowledgeDoc(doc_id="d1", title="公开", content="x", acl_tags=["public"]),
            KnowledgeDoc(doc_id="d2", title="内部", content="y", acl_tags=["internal"]),
            KnowledgeDoc(doc_id="d3", title="机密", content="z", acl_tags=["confidential"]),
        ],
        user_roles=[ACLCheck(user_role="staff", allowed_tags=["public", "internal"])],
        role_to_query="staff",
    )
    out = run_acl(inp)
    o = out["output"]
    assert o["imported"] == 2
    assert o["rejected"] == 1
    assert "d3" in o["rejected_docs"]


def test_acl_role_not_registered_fails():
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[KnowledgeDoc(doc_id="d1", title="x", content="y")],
        user_roles=[ACLCheck(user_role="viewer", allowed_tags=["public"])],
        role_to_query="ghost",  # 未注册
    )
    out = run_acl(inp)
    assert out["status"] == "failed"
    assert "WF-G015-ROLE" in out["error"]["code"]


def test_acl_empty_docs_rejected():
    with pytest.raises(ValidationError):
        ACLInput(
            tenant_id="zq-1",
            knowledge_docs=[],
            user_roles=[ACLCheck(user_role="viewer", allowed_tags=["public"])],
            role_to_query="viewer",
        )


def test_acl_audit_log_present():
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[KnowledgeDoc(doc_id="d1", title="x", content="y")],
        user_roles=[ACLCheck(user_role="admin", allowed_tags=["public"])],
        role_to_query="admin",
    )
    out = run_acl(inp)
    audit = out["output"]["audit_log"]
    assert len(audit) == 1
    assert audit[0]["decision"] == "imported"
    assert "d1" == audit[0]["doc_id"]


def test_acl_rejection_audit_reason():
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[KnowledgeDoc(doc_id="d1", title="机密文件", content="x", acl_tags=["confidential"])],
        user_roles=[ACLCheck(user_role="viewer", allowed_tags=["public"])],
        role_to_query="viewer",
    )
    out = run_acl(inp)
    audit = out["output"]["audit_log"]
    assert audit[0]["decision"] == "rejected"
    assert "confidential" not in audit[0]["reason"]  # reason 用 sorted(allowed)


def test_acl_multi_tag_match():
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[KnowledgeDoc(doc_id="d1", title="x", content="y", acl_tags=["public", "internal"])],
        user_roles=[ACLCheck(user_role="staff", allowed_tags=["internal"])],
        role_to_query="staff",
    )
    out = run_acl(inp)
    assert out["output"]["imported"] == 1


def test_acl_large_content_allowed():
    """content max_length=100000"""
    big = "x" * 50000
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[KnowledgeDoc(doc_id="big", title="大", content=big, acl_tags=["public"])],
        user_roles=[ACLCheck(user_role="v", allowed_tags=["public"])],
        role_to_query="v",
    )
    out = run_acl(inp)
    assert out["output"]["imported"] == 1


def test_acl_empty_content_rejected():
    with pytest.raises(ValidationError):
        KnowledgeDoc(doc_id="d1", title="x", content="")


def test_acl_default_tags_public():
    inp = ACLInput(
        tenant_id="zq-1",
        knowledge_docs=[KnowledgeDoc(doc_id="d1", title="x", content="y")],  # default public
        user_roles=[ACLCheck(user_role="v", allowed_tags=["public"])],
        role_to_query="v",
    )
    out = run_acl(inp)
    assert out["output"]["imported"] == 1


def test_validate_json_ok():
    res = validate_json('{"tenant_id":"zq-1","knowledge_docs":[{"doc_id":"d1","title":"x","content":"y"}],"user_roles":[{"user_role":"v","allowed_tags":["public"]}],"role_to_query":"v"}')
    assert res["ok"] is True
