"""
Token计费系统 — Billing & Usage Engine
========================================
筷子科技对标: 按Token计量内容生产·套餐配额·用量追踪·自动限流
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

BASE = Path(__file__).parent
BILLING_DIR = Path("D:/个人文件/AI/云数科技/billing")
BILLING_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 套餐定义
# ═══════════════════════════════════

PLANS = {
    "starter": {
        "name": "入门版",
        "price_monthly": 299,
        "price_yearly": 2990,
        "monthly_quota": 50,  # 篇/月
        "token_rate": 0.5,     # ¥/Token
        "cities": 1,
        "accounts_per_city": 3,
        "features": ["内容生产", "基础GEO", "1城市"],
        "video_modes": [],
    },
    "pro": {
        "name": "专业版",
        "price_monthly": 999,
        "price_yearly": 9990,
        "monthly_quota": 150,
        "token_rate": 0.3,
        "cities": 3,
        "accounts_per_city": 5,
        "features": ["内容生产", "GEO优化", "多城市", "质量评分", "知识转化"],
        "video_modes": ["before_after", "room_tour"],
    },
    "enterprise": {
        "name": "企业版",
        "price_monthly": 2999,
        "price_yearly": 29990,
        "monthly_quota": 300,
        "token_rate": 0.2,
        "cities": 5,
        "accounts_per_city": 7,
        "features": ["全部功能", "全视频模式", "矩阵调度", "客户仪表盘", "API接入", "专属支持"],
        "video_modes": ["before_after", "material_review", "room_tour", "construction_diary"],
    },
}

# 内容Token换算表
TOKEN_COSTS = {
    "article": 8,        # 图文内容
    "voiceover": 12,     # 口播脚本
    "persona": 10,       # 人设IP
    "storytelling": 15,  # 故事叙事
    "mashup": 10,        # 混剪
    "short_video": 6,    # 短视频
    "video_generation": 50,  # AI视频生成
    "geo_research": 5,   # GEO研究
    "geo_content": 8,    # GEO内容
    "repurpose": 5,      # 二创
}


def get_plan(plan_id: str) -> dict:
    return PLANS.get(plan_id, PLANS["starter"])


def get_usage(tid: str, month: str = None) -> dict:
    """获取租户本月用量"""
    if not month:
        month = datetime.now().strftime("%Y-%m")
    usage_file = BILLING_DIR / f"{tid}_{month}.json"
    if usage_file.exists():
        return json.loads(usage_file.read_text(encoding="utf-8"))
    return {"tenant_id": tid, "month": month, "total_tokens": 0, "items": []}


def record_usage(tid: str, content_type: str, topic: str, tokens: int = None) -> dict:
    """记录一次内容生产消耗"""
    if tokens is None:
        tokens = TOKEN_COSTS.get(content_type, 8)

    month = datetime.now().strftime("%Y-%m")
    usage = get_usage(tid, month)

    usage["total_tokens"] += tokens
    usage["items"].append({
        "time": datetime.now().isoformat()[:19],
        "type": content_type,
        "topic": topic[:80],
        "tokens": tokens,
    })

    usage_file = BILLING_DIR / f"{tid}_{month}.json"
    usage_file.write_text(json.dumps(usage, ensure_ascii=False, indent=2), encoding="utf-8")

    return usage


def check_quota(tid: str) -> dict:
    """检查租户配额是否充足"""
    from tenant_platform import get_tenant
    tenant = get_tenant(tid)
    if not tenant:
        return {"ok": False, "error": "租户不存在"}

    plan = get_plan(tenant.get("plan", "starter"))
    usage = get_usage(tid)
    used = usage["total_tokens"]
    quota = plan["monthly_quota"] * 10  # 转换为Token

    remaining = quota - used
    pct = round(used / max(quota, 1) * 100)

    return {
        "ok": remaining > 0,
        "plan": plan["name"],
        "quota_tokens": quota,
        "used_tokens": used,
        "remaining_tokens": remaining,
        "usage_pct": pct,
        "unit_price": plan["token_rate"],
        "estimated_cost": round(used * plan["token_rate"]),
        "status": "exceeded" if remaining <= 0 else "warning" if pct > 80 else "ok",
    }


def get_billing_summary(tid: str) -> dict:
    """获取租户计费总览（含历史月份）"""
    summary = {"tenant_id": tid, "months": [], "total_spent": 0}
    for f in sorted(BILLING_DIR.glob(f"{tid}_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            summary["months"].append({
                "month": data["month"],
                "tokens": data["total_tokens"],
                "items": len(data["items"]),
            })
            summary["total_spent"] += data["total_tokens"]
        except:
            pass
    return summary
