"""
品牌资产管理 — Brand Asset Management
对标筷子: 自定义品牌素材库·角色市场·音色市场·IP资源库
"""
import json, secrets
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
BRAND_DIR = Path("D:/个人文件/AI/云数科技/brands")
BRAND_DIR.mkdir(parents=True, exist_ok=True)

ASSET_TYPES = {
    "logo": "品牌Logo", "color": "品牌色板", "font": "品牌字体",
    "avatar": "虚拟角色", "voice": "声音样本", "character": "人设档案",
    "template": "内容模板", "material": "素材库", "guideline": "品牌手册",
}

def create_brand(tid: str, name: str, config: dict = None) -> dict:
    """创建品牌档案"""
    bid = f"brand-{secrets.token_hex(4)}"
    brand = {
        "id": bid, "tenant_id": tid, "name": name,
        "config": config or {},
        "assets": {"logo": [], "color": [], "font": [], "avatar": [], "voice": [], "character": [], "template": [], "material": [], "guideline": []},
        "created_at": datetime.now().isoformat()[:19], "updated_at": datetime.now().isoformat()[:19],
    }
    bf = BRAND_DIR / f"{bid}.json"
    bf.write_text(json.dumps(brand, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "brand": brand}

def get_brand(bid: str) -> dict:
    f = BRAND_DIR / f"{bid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

def list_brands(tid: str = "") -> list:
    brands = []
    for f in BRAND_DIR.glob("brand-*.json"):
        try:
            b = json.loads(f.read_text(encoding="utf-8"))
            if tid and b.get("tenant_id") != tid: continue
            brands.append(b)
        except Exception: pass
    return brands

def add_asset(bid: str, asset_type: str, name: str, uri: str, meta: dict = None) -> dict:
    """添加品牌资产(角色/音色/素材)"""
    if asset_type not in ASSET_TYPES:
        return {"ok": False, "error": f"不支持的类型: {asset_type}"}
    brand = get_brand(bid)
    if not brand: return {"ok": False, "error": "品牌不存在"}
    asset = {"id": f"as-{secrets.token_hex(4)}", "type": asset_type, "type_name": ASSET_TYPES[asset_type],
             "name": name, "uri": uri, "meta": meta or {}, "added_at": datetime.now().isoformat()[:19]}
    brand["assets"][asset_type].append(asset)
    brand["updated_at"] = datetime.now().isoformat()[:19]
    (BRAND_DIR / f"{bid}.json").write_text(json.dumps(brand, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "asset": asset}

def remove_asset(bid: str, asset_type: str, aid: str) -> dict:
    brand = get_brand(bid)
    if not brand: return {"ok": False, "error": "品牌不存在"}
    brand["assets"][asset_type] = [a for a in brand["assets"][asset_type] if a["id"] != aid]
    (BRAND_DIR / f"{bid}.json").write_text(json.dumps(brand, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True}

def get_brand_stats(tid: str) -> dict:
    """品牌资产统计"""
    brands = list_brands(tid)
    total = {"logos": 0, "avatars": 0, "voices": 0, "templates": 0, "materials": 0}
    for b in brands:
        for atype, items in b.get("assets", {}).items():
            total[atype + "s" if not atype.endswith("s") else atype] = total.get(atype + "s" if not atype.endswith("s") else atype, 0) + len(items)
    return {"brand_count": len(brands), "assets": total}
