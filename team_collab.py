"""
团队协作 — Team Collaboration & Role-Based Access
对标筷子: 多团队协同资产库·多角色协作·权限管理
"""
import json, secrets
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
TEAM_DIR = Path("D:/个人文件/AI/云数科技/teams")
TEAM_DIR.mkdir(parents=True, exist_ok=True)

ROLES = {
    "owner": {"name": "所有者", "perms": ["manage_team", "manage_billing", "create_content", "approve_content", "publish", "view_analytics", "manage_brand"]},
    "admin": {"name": "管理员", "perms": ["create_content", "approve_content", "publish", "view_analytics", "manage_brand"]},
    "editor": {"name": "编辑", "perms": ["create_content", "view_analytics"]},
    "viewer": {"name": "观察者", "perms": ["view_analytics"]},
}

def create_team(tid: str, name: str) -> dict:
    """创建团队"""
    team_id = f"team-{secrets.token_hex(4)}"
    team = {"id": team_id, "tenant_id": tid, "name": name, "members": [],
            "created_at": datetime.now().isoformat()[:19]}
    tf = TEAM_DIR / f"{team_id}.json"
    tf.write_text(json.dumps(team, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "team": team}

def add_member(team_id: str, user_email: str, role: str = "editor") -> dict:
    """添加团队成员"""
    if role not in ROLES: return {"ok": False, "error": f"无效角色: {role}"}
    tf = TEAM_DIR / f"{team_id}.json"
    if not tf.exists(): return {"ok": False, "error": "团队不存在"}
    team = json.loads(tf.read_text(encoding="utf-8"))
    if any(m["email"] == user_email for m in team["members"]):
        return {"ok": False, "error": "已存在"}
    member = {"email": user_email, "role": role, "role_name": ROLES[role]["name"],
              "perms": ROLES[role]["perms"], "joined_at": datetime.now().isoformat()[:19]}
    team["members"].append(member)
    tf.write_text(json.dumps(team, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "member": member}

def remove_member(team_id: str, user_email: str) -> dict:
    tf = TEAM_DIR / f"{team_id}.json"
    if not tf.exists(): return {"ok": False, "error": "团队不存在"}
    team = json.loads(tf.read_text(encoding="utf-8"))
    team["members"] = [m for m in team["members"] if m["email"] != user_email]
    tf.write_text(json.dumps(team, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}

def check_permission(team_id: str, user_email: str, perm: str) -> bool:
    """检查权限"""
    tf = TEAM_DIR / f"{team_id}.json"
    if not tf.exists(): return False
    team = json.loads(tf.read_text(encoding="utf-8"))
    for m in team["members"]:
        if m["email"] == user_email and perm in m.get("perms", []):
            return True
    return False

def get_team(team_id: str) -> dict:
    tf = TEAM_DIR / f"{team_id}.json"
    return json.loads(tf.read_text(encoding="utf-8")) if tf.exists() else None
