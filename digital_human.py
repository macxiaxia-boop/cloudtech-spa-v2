"""
数字人/虚拟角色注册中心 — Digital Human & Avatar Registry
对标: HeyGen 700-1100+ avatars·Synthesia 230+ avatars·AI Twins·LiveAvatar
"""
import json, secrets
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
AVATAR_DIR = Path("D:/个人文件/AI/云数科技/avatars")
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

AVATAR_TYPES = {
    "stock": "平台内置", "custom": "定制数字人", "clone": "真人克隆",
    "character": "虚拟角色", "mascot": "品牌吉祥物",
}

def register_avatar(tid: str, name: str, avatar_type: str, config: dict = None) -> dict:
    """注册数字人/虚拟角色"""
    if avatar_type not in AVATAR_TYPES: return {"ok": False, "error": f"无效类型: {avatar_type}"}
    aid = f"av-{secrets.token_hex(6)}"
    avatar = {
        "id": aid, "tenant_id": tid, "name": name, "type": avatar_type,
        "type_name": AVATAR_TYPES[avatar_type],
        "config": config or {},
        "appearances": [],  # 外观变体
        "voices": [],       # 关联声音
        "gestures": [],     # 手势/动作
        "status": "active", "created_at": datetime.now().isoformat()[:19],
        "usage_count": 0,
    }
    af = AVATAR_DIR / f"{aid}.json"
    af.write_text(json.dumps(avatar, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "avatar": avatar}


def add_voice(avatar_id: str, voice_name: str, voice_uri: str, language: str = "zh-CN") -> dict:
    """为数字人添加声音"""
    af = AVATAR_DIR / f"{avatar_id}.json"
    if not af.exists(): return {"ok": False, "error": "数字人不存在"}
    a = json.loads(af.read_text(encoding="utf-8"))
    vid = f"vc-{secrets.token_hex(4)}"
    voice = {"id": vid, "name": voice_name, "uri": voice_uri, "language": language, "added_at": datetime.now().isoformat()[:19]}
    a["voices"].append(voice)
    af.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "voice": voice}


def list_avatars(tid: str = "", avatar_type: str = "") -> list:
    avatars = []
    for f in AVATAR_DIR.glob("av-*.json"):
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
            if tid and a.get("tenant_id") != tid: continue
            if avatar_type and a.get("type") != avatar_type: continue
            avatars.append(a)
        except Exception: pass
    return avatars


def get_avatar_stats(tid: str = "") -> dict:
    avatars = list_avatars(tid)
    by_type = {}
    for a in avatars:
        t = a.get("type", "stock")
        by_type[t] = by_type.get(t, 0) + 1
    return {"total": len(avatars), "by_type": by_type, "total_usage": sum(a.get("usage_count", 0) for a in avatars)}
