"""
审批工作流 — Content Approval Workflow
对标: Synthesia brand kits + approval workflows + 角色权限
"""
import json, secrets
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
APPROVAL_DIR = Path("D:/个人文件/AI/云数科技/approvals")
APPROVAL_DIR.mkdir(parents=True, exist_ok=True)

STAGES = ["draft", "review", "approved", "published", "rejected"]


def submit_for_review(tid: str, content_id: str, title: str, submitter: str) -> dict:
    """提交审批"""
    aid = f"apr-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"
    approval = {
        "id": aid, "tenant_id": tid, "content_id": content_id, "title": title,
        "status": "review", "submitter": submitter, "reviewer": "", "comments": [],
        "submitted_at": datetime.now().isoformat()[:19], "resolved_at": None,
        "history": [{"stage": "draft", "by": submitter, "at": datetime.now().isoformat()[:19]}],
    }
    af = APPROVAL_DIR / f"{aid}.json"
    af.write_text(json.dumps(approval, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "approval": approval}


def approve(aid: str, reviewer: str, comment: str = "") -> dict:
    """批准"""
    return _resolve(aid, "approved", reviewer, comment)


def reject(aid: str, reviewer: str, comment: str = "") -> dict:
    """驳回"""
    return _resolve(aid, "rejected", reviewer, comment)


def _resolve(aid: str, status: str, reviewer: str, comment: str) -> dict:
    af = APPROVAL_DIR / f"{aid}.json"
    if not af.exists(): return {"ok": False, "error": "审批不存在"}
    a = json.loads(af.read_text(encoding="utf-8"))
    a["status"] = status
    a["reviewer"] = reviewer
    a["resolved_at"] = datetime.now().isoformat()[:19]
    a["history"].append({"stage": status, "by": reviewer, "at": datetime.now().isoformat()[:19], "comment": comment})
    if comment: a["comments"].append({"by": reviewer, "at": datetime.now().isoformat()[:19], "text": comment})
    af.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    # 通知
    try:
        from notifications import notify
        notify(a["tenant_id"], "approval", f"内容{'已通过' if status == 'approved' else '已驳回'}: {a['title'][:30]}",
               f"审核人: {reviewer}" + (f" - {comment}" if comment else ""), "success" if status == "approved" else "warning")
    except Exception: pass
    return {"ok": True, "approval": a}


def get_approvals(tid: str, status: str = "") -> list:
    """列出审批"""
    approvals = []
    for f in sorted(APPROVAL_DIR.glob("apr-*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
            if a.get("tenant_id") != tid: continue
            if status and a["status"] != status: continue
            approvals.append(a)
        except Exception: pass
    return approvals


def get_approval_stats(tid: str) -> dict:
    """审批统计"""
    all_a = get_approvals(tid)
    return {
        "total": len(all_a),
        "pending": sum(1 for a in all_a if a["status"] == "review"),
        "approved": sum(1 for a in all_a if a["status"] == "approved"),
        "rejected": sum(1 for a in all_a if a["status"] == "rejected"),
    }
