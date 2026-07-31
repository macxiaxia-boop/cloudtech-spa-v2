"""
数字人版权中心 — Digital Human & Asset Rights Management
对标筷子科技: 明星肖像/声音/表演权益合规管理
装企版: 设计师IP·业主授权·素材版权·AI生成物确权
"""
import json, hashlib, secrets
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

BASE = Path(__file__).parent
RIGHTS_DIR = Path("D:/个人文件/AI/云数科技/rights")
RIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════
# 版权资产类型
# ═══════════════════════════════════════

ASSET_TYPES = {
    "portrait": {"name": "肖像权", "desc": "人物出镜/照片/视频中的可识别肖像", "expiry_years": 3},
    "voice": {"name": "声音权", "desc": "AI语音克隆/配音/口播声音样本", "expiry_years": 2},
    "property": {"name": "业主案例授权", "desc": "业主装修案例拍摄/发布授权", "expiry_years": 1},
    "music": {"name": "音乐版权", "desc": "BGM/背景音乐使用授权", "expiry_years": 1},
    "footage": {"name": "素材版权", "desc": "航拍/空镜/施工过程等素材授权", "expiry_years": 2},
    "design": {"name": "设计版权", "desc": "设计师方案/IP/效果图版权", "expiry_years": 5},
    "ai_generated": {"name": "AI生成物", "desc": "AI生成内容的版权声明与溯源", "expiry_years": 0},
}

# ═══════════════════════════════════════
# 版权资产管理
# ═══════════════════════════════════════

def register_asset(asset_type: str, title: str, owner: str, source_url: str = "",
                   license_info: dict = None, tags: list = None) -> dict:
    """注册版权资产"""
    if asset_type not in ASSET_TYPES:
        return {"ok": False, "error": f"未知资产类型: {asset_type}"}

    aid = f"ra-{secrets.token_hex(6)}"
    now = datetime.now().isoformat()[:19]
    expiry_years = ASSET_TYPES[asset_type]["expiry_years"]

    asset = {
        "id": aid,
        "type": asset_type,
        "type_name": ASSET_TYPES[asset_type]["name"],
        "title": title,
        "owner": owner,
        "source_url": source_url,
        "license": license_info or {},
        "tags": tags or [],
        "status": "active",
        "registered_at": now,
        "expires_at": (datetime.now() + timedelta(days=expiry_years * 365)).isoformat()[:10] if expiry_years > 0 else None,
        "usage_count": 0,
        "fingerprint": hashlib.sha256(f"{asset_type}:{title}:{owner}:{now}".encode()).hexdigest()[:16],
    }

    # 持久化
    asset_file = RIGHTS_DIR / f"{aid}.json"
    asset_file.write_text(json.dumps(asset, ensure_ascii=False, indent=2), encoding="utf-8")

    # 索引
    _update_index(aid, asset)

    return {"ok": True, "asset": asset}


def get_asset(aid: str) -> Optional[dict]:
    f = RIGHTS_DIR / f"{aid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def list_assets(asset_type: str = "", status: str = "active", limit: int = 50) -> list:
    """列出资产"""
    assets = []
    for f in sorted(RIGHTS_DIR.glob("ra-*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
            if asset_type and a.get("type") != asset_type:
                continue
            if status and a.get("status") != status:
                continue
            assets.append(a)
            if len(assets) >= limit:
                break
        except Exception:
            pass
    return assets


def record_usage(aid: str, usage_context: str, tenant_id: str = "") -> dict:
    """记录版权资产使用"""
    asset = get_asset(aid)
    if not asset:
        return {"ok": False, "error": "资产不存在"}

    asset["usage_count"] = asset.get("usage_count", 0) + 1
    asset["last_used"] = datetime.now().isoformat()[:19]

    # 使用日志
    usage_entry = {
        "time": datetime.now().isoformat()[:19],
        "context": usage_context,
        "tenant_id": tenant_id,
    }
    asset.setdefault("usage_log", []).append(usage_entry)

    asset_file = RIGHTS_DIR / f"{aid}.json"
    asset_file.write_text(json.dumps(asset, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True, "usage_count": asset["usage_count"]}


def revoke_asset(aid: str, reason: str = "") -> dict:
    """撤销版权授权"""
    asset = get_asset(aid)
    if not asset:
        return {"ok": False, "error": "资产不存在"}

    asset["status"] = "revoked"
    asset["revoked_at"] = datetime.now().isoformat()[:19]
    asset["revoke_reason"] = reason

    asset_file = RIGHTS_DIR / f"{aid}.json"
    asset_file.write_text(json.dumps(asset, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True}


# ═══════════════════════════════════════
# 合规检查
# ═══════════════════════════════════════

def compliance_check(content_type: str, assets_used: list = None) -> dict:
    """
    发布前合规检查
    检查项: 肖像授权·音乐版权·业主授权·AI生成声明
    """
    issues = []
    warnings = []
    assets_used = assets_used or []

    # 检查内容类型
    if content_type in ("voiceover", "persona"):
        # 口播/人设内容需检查肖像和声音授权
        portrait_ok = any(a.get("type") == "portrait" for a in assets_used)
        if not portrait_ok:
            warnings.append("建议确认出镜人物肖像授权")

    if content_type in ("voiceover", "video_generation"):
        # 视频内容需检查音乐版权
        music_ok = any(a.get("type") == "music" for a in assets_used)
        if not music_ok:
            warnings.append("请确认BGM版权状态")

    # 检查过期资产
    for a in assets_used:
        if a.get("status") == "expired":
            issues.append(f"资产 {a.get('title','?')} 已过期")
        if a.get("expires_at") and a["expires_at"] < datetime.now().strftime("%Y-%m-%d"):
            issues.append(f"资产 {a.get('title','?')} 授权已到期({a['expires_at']})")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "risk_level": "high" if issues else "medium" if warnings else "low",
    }


def get_compliance_report() -> dict:
    """版权合规总览"""
    assets = list_assets(limit=1000)
    total = len(assets)
    active = sum(1 for a in assets if a.get("status") == "active")
    expired = sum(1 for a in assets if a.get("status") == "expired")
    revoked = sum(1 for a in assets if a.get("status") == "revoked")

    # 即将过期（30天内）
    soon_expired = []
    cutoff = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    for a in assets:
        if a.get("expires_at") and a["expires_at"] <= cutoff and a.get("status") == "active":
            soon_expired.append({"id": a["id"], "title": a["title"], "expires": a["expires_at"]})

    return {
        "total_assets": total,
        "active": active, "expired": expired, "revoked": revoked,
        "by_type": {t: sum(1 for a in assets if a.get("type") == t) for t in ASSET_TYPES},
        "soon_expired": soon_expired,
        "total_usage": sum(a.get("usage_count", 0) for a in assets),
    }


# ── 内部工具 ──

def _update_index(aid: str, asset: dict):
    """更新资产索引"""
    idx_file = RIGHTS_DIR / "_index.json"
    idx = {}
    if idx_file.exists():
        try:
            idx = json.loads(idx_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    idx[aid] = {
        "type": asset["type"], "title": asset["title"],
        "owner": asset["owner"], "status": asset["status"],
        "registered_at": asset["registered_at"],
    }
    idx_file.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def rebuild_index():
    """重建索引"""
    idx = {}
    for f in RIGHTS_DIR.glob("ra-*.json"):
        try:
            a = json.loads(f.read_text(encoding="utf-8"))
            idx[a["id"]] = {
                "type": a["type"], "title": a["title"],
                "owner": a["owner"], "status": a["status"],
                "registered_at": a["registered_at"],
            }
        except Exception:
            pass
    (RIGHTS_DIR / "_index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(idx)
