"""
统一的租户服务层 — Unified Tenant Service
合并 multi_tenant_manager.py + tenant_platform.py → 单一数据源
"""
import json, secrets
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

BASE = Path(__file__).parent
TENANTS_DIR = Path("D:/个人文件/AI/云数科技/tenants")
TENANTS_DIR.mkdir(parents=True, exist_ok=True)

PLANS = {
    "starter": {
        "name": "入门版", "price_monthly": 299, "price_annual": 2990,
        "monthly_quota": 50, "token_rate": 0.5, "cities": 1,
        "accounts_per_city": 3, "video_modes": [],
        "features": ["内容生产", "基础GEO", "1城市"],
    },
    "pro": {
        "name": "专业版", "price_monthly": 999, "price_annual": 9990,
        "monthly_quota": 150, "token_rate": 0.3, "cities": 3,
        "accounts_per_city": 5, "video_modes": ["before_after", "room_tour"],
        "features": ["内容生产", "GEO优化", "多城市", "质量评分", "知识转化"],
    },
    "enterprise": {
        "name": "企业版", "price_monthly": 2999, "price_annual": 29990,
        "monthly_quota": 300, "token_rate": 0.2, "cities": 5,
        "accounts_per_city": 7, "video_modes": ["before_after", "material_review", "room_tour", "construction_diary"],
        "features": ["全部功能", "全视频模式", "矩阵调度", "客户仪表盘", "API接入", "专属支持"],
    },
}

TOKEN_COSTS = {
    "article": 8, "voiceover": 12, "persona": 10, "storytelling": 15,
    "mashup": 10, "short_video": 6, "video_generation": 50,
    "geo_research": 5, "geo_content": 8, "repurpose": 5,
}

PLATFORM_NAMES = {"xiaohongshu": "小红书", "douyin": "抖音", "wechat": "公众号", "shipinhao": "视频号"}


def create_tenant(name: str, cities: list, plan_id: str = "pro", company: str = "", email: str = "", tid: str = "") -> dict:
    """创建新租户"""
    plan = PLANS.get(plan_id, PLANS["pro"])
    tid = tid or f"zq-{secrets.token_hex(4)}"

    accounts = {}
    for city in cities[:plan["cities"]]:
        n = plan["accounts_per_city"]
        accounts[city] = {"xiaohongshu": min(n, 3), "douyin": min(n, 2), "wechat": 1}

    tenant = {
        "id": tid, "name": name, "company": company, "email": email,
        "plan": plan_id, "plan_name": plan["name"],
        "cities": cities[:plan["cities"]],
        "accounts": accounts,
        "monthly_quota": plan["monthly_quota"],
        "monthly_used": 0, "total_produced": 0, "avg_score": 0,
        "total_tokens": 0, "token_rate": plan["token_rate"],
        "status": "active", "created": datetime.now().isoformat()[:19],
    }

    tenant_file = TENANTS_DIR / f"{tid}.json"
    tenant_file.write_text(json.dumps(tenant, ensure_ascii=False, indent=2), encoding="utf-8")

    # 同步到SQL数据库
    try:
        from database import Database
        db = Database().connect()
        db.insert("tenants", {
            "id": tid, "name": name, "email": email or f"{tid}@cloudtech.com",
            "company": company or name, "plan": plan_id, "status": "active",
            "api_key": f"ak-{secrets.token_hex(16)}", "api_key_hash": secrets.token_hex(32),
        })
    except Exception:
        pass

    return tenant


def get_tenant(tid: str) -> Optional[dict]:
    f = TENANTS_DIR / f"{tid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def get_all_tenants() -> list:
    tenants = []
    for f in sorted(TENANTS_DIR.glob("zq-*.json")):
        try:
            tenants.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return tenants


def update_tenant(tid: str, updates: dict) -> Optional[dict]:
    tenant = get_tenant(tid)
    if not tenant:
        return None
    tenant.update(updates)
    tenant_file = TENANTS_DIR / f"{tid}.json"
    tenant_file.write_text(json.dumps(tenant, ensure_ascii=False, indent=2), encoding="utf-8")
    return tenant


def deactivate_tenant(tid: str) -> bool:
    return update_tenant(tid, {"status": "inactive"}) is not None


def get_plan(plan_id: str) -> dict:
    return PLANS.get(plan_id, PLANS["starter"])


def get_account_matrix(tid: str) -> dict:
    """完整账号矩阵"""
    tenant = get_tenant(tid)
    if not tenant:
        return {}

    total = 0
    cities_info = {}
    for city, platforms in tenant["accounts"].items():
        city_total = sum(platforms.values())
        total += city_total
        accounts_list = _generate_account_names(tenant["name"], city, platforms)
        cities_info[city] = {"total": city_total, "platforms": platforms, "accounts": accounts_list}

    return {"tenant": tenant["name"], "total_accounts": total, "cities": cities_info}


def _generate_account_names(brand: str, city: str, platforms: dict) -> dict:
    short = brand[:4]
    result = {}
    suffixes = ["案例库", "知识号", "本地号", "IP号", "避坑号"]
    for platform, count in platforms.items():
        pname = PLATFORM_NAMES.get(platform, platform)
        if count == 1:
            result[platform] = [f"{short}-{city}装修·{pname}"]
        else:
            result[platform] = [f"{short}-{city}{s}·{pname}" for s in suffixes[:count]]
    return result


def distribute_content(tid: str, topic: str, content_type: str = "article") -> dict:
    """内容分发到所有账号"""
    matrix = get_account_matrix(tid)
    plan = []
    for city, info in matrix.get("cities", {}).items():
        for platform, accounts in info["accounts"].items():
            for account in accounts:
                plan.append({
                    "account": account, "city": city, "platform": platform,
                    "topic": topic, "content_type": content_type,
                    "scheduled": None, "status": "queued",
                })
    return {"tenant": matrix.get("tenant", ""), "total_distributions": len(plan), "plan": plan}


def get_client_dashboard(tid: str) -> dict:
    """租户仪表盘"""
    tenant = get_tenant(tid)
    if not tenant:
        return {"error": "租户不存在"}

    content_dir = Path(f"D:/个人文件/AI/云数科技/tenants/{tid}/content")
    produced, total_score, scored_count, recent = 0, 0, 0, []

    if content_dir.exists():
        import re
        files = sorted(content_dir.rglob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")[:500]
                title = text.split("\n")[0].replace("# ", "").strip()[:50]
                sm = re.search(r'评分[：:]\s*(\d+)/10', text)
                score = int(sm.group(1)) if sm else None
                if score:
                    total_score += score
                    scored_count += 1
                produced += 1
                if len(recent) < 10:
                    recent.append({"title": title, "score": score, "file": f.name})
            except Exception:
                pass

    avg = round(total_score / max(scored_count, 1), 1)
    total_accounts = sum(sum(v.values()) for v in tenant["accounts"].values())

    return {
        "tenant": tenant["name"], "plan": tenant["plan"], "plan_name": tenant.get("plan_name", ""),
        "monthly_quota": tenant["monthly_quota"], "monthly_used": produced,
        "quota_pct": round(produced / max(tenant["monthly_quota"], 1) * 100),
        "avg_score": avg, "total_produced": produced,
        "cities": len(tenant["cities"]), "total_accounts": total_accounts,
        "matrix": get_account_matrix(tid), "recent_content": recent,
    }


# ── Billing / Token ──

def record_usage(tid: str, content_type: str, topic: str, tokens: int = None) -> dict:
    """记录Token消耗并更新租户用量"""
    if tokens is None:
        tokens = TOKEN_COSTS.get(content_type, 8)

    tenant = get_tenant(tid)
    if not tenant:
        return {"ok": False, "error": "租户不存在"}

    tenant["total_tokens"] = tenant.get("total_tokens", 0) + tokens
    tenant["monthly_used"] = tenant.get("monthly_used", 0) + 1
    tenant["total_produced"] = tenant.get("total_produced", 0) + 1

    tenant_file = TENANTS_DIR / f"{tid}.json"
    tenant_file.write_text(json.dumps(tenant, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True, "tokens_used": tokens, "total_tokens": tenant["total_tokens"]}


def check_quota(tid: str) -> dict:
    """检查租户配额"""
    tenant = get_tenant(tid)
    if not tenant:
        return {"ok": False, "error": "租户不存在"}

    plan = PLANS.get(tenant["plan"], PLANS["starter"])
    used = tenant["monthly_used"]
    quota = plan["monthly_quota"]
    pct = round(used / max(quota, 1) * 100)

    return {
        "ok": used < quota,
        "plan": plan["name"], "quota": quota, "used": used,
        "remaining": quota - used, "usage_pct": pct,
        "unit_price": plan["token_rate"],
        "estimated_cost": round(tenant.get("total_tokens", 0) * plan["token_rate"]),
        "status": "exceeded" if used >= quota else "warning" if pct > 80 else "ok",
    }


def get_platform_summary() -> dict:
    """平台总览（超管视图）"""
    tenants = get_all_tenants()
    total_mrr = 0
    tenant_list = []

    for t in tenants:
        plan = PLANS.get(t["plan"], PLANS["starter"])
        total_mrr += plan["price_monthly"]
        dash = get_client_dashboard(t["id"])
        q = check_quota(t["id"])
        tenant_list.append({
            "id": t["id"], "name": t["name"], "plan": t["plan"],
            "monthly_used": dash["monthly_used"], "avg_score": dash["avg_score"],
            "accounts": dash["total_accounts"], "mrr": plan["price_monthly"],
            "quota_pct": dash["quota_pct"], "token_used": q.get("used", 0),
        })

    return {
        "tenants": tenant_list, "total_mrr": total_mrr,
        "tenant_count": len(tenants),
        "active_count": sum(1 for t in tenants if t.get("status") == "active"),
    }
