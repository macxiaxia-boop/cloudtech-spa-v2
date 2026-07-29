"""
User Feedback System — In-app widget + API
Collects: bug reports, feature requests, NPS scores
"""
import json, os, hashlib
from datetime import datetime
from pathlib import Path
from database import get_db

FEEDBACK_DB = Path(__file__).parent / "data" / "feedback.jsonl"


def _ensure_store():
    FEEDBACK_DB.parent.mkdir(parents=True, exist_ok=True)


def submit_feedback(user_id: str, category: str, message: str,
                    email: str = "", url: str = "", screenshot: str = "") -> dict:
    """Submit user feedback (bug/feature/nps)"""
    _ensure_store()

    entry = {
        "id": hashlib.md5(f"{user_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
        "user_id": user_id,
        "category": category,  # bug, feature, nps, other
        "message": message[:2000],
        "email": email,
        "url": url,
        "screenshot": screenshot[:500] if screenshot else "",
        "status": "new",  # new, acknowledged, in_progress, resolved, closed
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
    }

    with open(FEEDBACK_DB, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Also store in main DB if available
    try:
        db = get_db()
        db.insert("feedback", {
            "feedback_id": entry["id"],
            "user_id": user_id,
            "category": category,
            "message": message[:500],
            "status": "new",
            "created_at": entry["created_at"],
        })
    except Exception:
        pass

    return entry


def submit_nps(user_id: str, score: int, comment: str = "") -> dict:
    """Submit NPS score (0-10)"""
    if not 0 <= score <= 10:
        raise ValueError("NPS score must be 0-10")

    category = "promoter" if score >= 9 else "passive" if score >= 7 else "detractor"
    message = f"NPS={score} [{category}] {comment}" if comment else f"NPS={score} [{category}]"

    return submit_feedback(user_id, "nps", message)


def get_feedback_stats() -> dict:
    """Get aggregated feedback statistics"""
    if not FEEDBACK_DB.exists():
        return {"total": 0, "by_category": {}, "by_status": {}, "nps_score": None, "recent": []}

    by_cat = {}
    by_status = {}
    nps_scores = []
    recent = []

    with open(FEEDBACK_DB, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                cat = e.get("category", "other")
                st = e.get("status", "new")
                by_cat[cat] = by_cat.get(cat, 0) + 1
                by_status[st] = by_status.get(st, 0) + 1

                if cat == "nps":
                    import re
                    match = re.search(r"NPS=(\d+)", e.get("message", ""))
                    if match:
                        nps_scores.append(int(match.group(1)))

                recent.append(e)
            except Exception:
                continue

    nps = round(sum(nps_scores) / len(nps_scores), 1) if nps_scores else None

    return {
        "total": sum(by_cat.values()),
        "by_category": by_cat,
        "by_status": by_status,
        "nps_score": nps,
        "nps_responses": len(nps_scores),
        "recent": recent[-20:],
    }


def update_feedback_status(feedback_id: str, status: str) -> bool:
    """Update feedback ticket status"""
    if not FEEDBACK_DB.exists():
        return False

    lines = []
    updated = False
    with open(FEEDBACK_DB, "r", encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line.strip())
                if e.get("id") == feedback_id:
                    e["status"] = status
                    if status == "resolved":
                        e["resolved_at"] = datetime.now().isoformat()
                    updated = True
                lines.append(e)
            except Exception:
                lines.append(line.strip())

    if updated:
        with open(FEEDBACK_DB, "w", encoding="utf-8") as f:
            for e in lines:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    return updated
