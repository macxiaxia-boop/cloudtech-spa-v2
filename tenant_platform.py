"""
多租户平台引擎 — Multi-Tenant Platform
========================================
每家装企 = 独立租户 = 独立品牌 + 独立账号矩阵 + 独立数据看板
模型: 总部管控 → 城市分发 → 账号执行 → 数据回流
"""
import json, secrets, time
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE = Path(__file__).parent
TENANTS_DIR = Path("D:/个人文件/AI/云数科技/tenants")
TENANTS_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 装企画像
# ═══════════════════════════════════

ZHUANGQI_TENANT = {
    "id": "zq-001",
    "name": "闽南装饰集团",
    "brand": {
        "logo": "闽南装饰",
        "slogan": "让每个家都有闽南温度",
        "colors": {"primary": "#c9a96e", "secondary": "#2d3436"},
        "tone": "专业·温馨·可信赖",
    },
    "cities": ["厦门", "泉州", "漳州", "福州"],
    "accounts": {
        "厦门": {"xiaohongshu": 3, "douyin": 2, "wechat": 1, "shipinhao": 1},
        "泉州": {"xiaohongshu": 2, "douyin": 2, "wechat": 1},
        "漳州": {"xiaohongshu": 2, "douyin": 1, "wechat": 1},
        "福州": {"xiaohongshu": 2, "douyin": 1, "wechat": 1},
    },
    "content_matrix": {
        "A-案例故事": 10, "B-知识教育": 10, "C-本地型": 6,
        "D-工具型": 2, "E-个人IP": 5, "F-避坑型": 3, "G-好物推荐": 3,
    },
    "plan": "enterprise",
    "monthly_quota": 300,  # 每月内容配额
    "created": "2026-07-30",
}

# ═══════════════════════════════════
# 租户管理
# ═══════════════════════════════════

def create_tenant(name: str, cities: list, plan: str = "pro") -> dict:
    """创建新装企租户"""
    tid = f"zq-{secrets.token_hex(4)}"

    # 平台账号矩阵
    accounts = {}
    for city in cities[:5]:  # 最多5个城市
        if plan == "enterprise":
            accounts[city] = {"xiaohongshu": 3, "douyin": 2, "wechat": 1, "shipinhao": 1}
        elif plan == "pro":
            accounts[city] = {"xiaohongshu": 2, "douyin": 1, "wechat": 1}
        else:
            accounts[city] = {"xiaohongshu": 1, "douyin": 1}

    # 内容配额
    monthly_quota = {"enterprise": 300, "pro": 150, "starter": 50}.get(plan, 50)

    tenant = {
        "id": tid,
        "name": name,
        "cities": cities,
        "accounts": accounts,
        "plan": plan,
        "monthly_quota": monthly_quota,
        "monthly_used": 0,
        "total_produced": 0,
        "avg_score": 0,
        "created": datetime.now().isoformat()[:19],
        "status": "active",
    }

    # 持久化
    tenant_file = TENANTS_DIR / f"{tid}.json"
    tenant_file.write_text(json.dumps(tenant, ensure_ascii=False, indent=2), encoding="utf-8")

    # 同步到数据库
    try:
        from database import Database
        db = Database().connect()
        db.insert("tenants", {
            "id": tid, "name": name, "email": f"{tid}@cloudtech.com",
            "company": name, "plan": plan, "status": "active",
            "api_key": f"ak-{secrets.token_hex(16)}", "api_key_hash": secrets.token_hex(32),
        })
    except:
        pass

    return tenant


def get_tenant(tid: str) -> Optional[dict]:
    """获取租户信息"""
    f = TENANTS_DIR / f"{tid}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return None


def get_all_tenants() -> list:
    """列出所有装企租户"""
    tenants = []
    for f in sorted(TENANTS_DIR.glob("zq-*.json")):
        try:
            tenants.append(json.loads(f.read_text(encoding="utf-8")))
        except:
            pass
    return tenants


# ═══════════════════════════════════
# 账号矩阵调度
# ═══════════════════════════════════

def get_account_matrix(tid: str) -> dict:
    """获取租户的完整账号矩阵"""
    tenant = get_tenant(tid)
    if not tenant:
        return {}

    matrix = {"tenant": tenant["name"], "total_accounts": 0, "cities": {}}

    for city, platforms in tenant["accounts"].items():
        city_total = sum(platforms.values())
        matrix["total_accounts"] += city_total
        matrix["cities"][city] = {
            "total": city_total,
            "platforms": platforms,
            "accounts": _generate_account_names(tenant["name"], city, platforms),
        }

    return matrix


def _generate_account_names(brand: str, city: str, platforms: dict) -> dict:
    """生成账号名称"""
    short = brand[:4]
    accounts = {}
    for platform, count in platforms.items():
        names = {
            "xiaohongshu": "小红书",
            "douyin": "抖音",
            "wechat": "公众号",
            "shipinhao": "视频号",
        }
        pname = names.get(platform, platform)
        if count == 1:
            accounts[platform] = [f"{short}-{city}装修·{pname}"]
        else:
            suffixes = ["案例库", "知识号", "本地号", "IP号", "避坑号"][:count]
            accounts[platform] = [f"{short}-{city}{s}·{pname}" for s in suffixes]
    return accounts


# ═══════════════════════════════════
# 内容分发策略
# ═══════════════════════════════════

def distribute_content(tid: str, topic: str, content_type: str = "article") -> dict:
    """将一个话题分发到租户的所有账号矩阵"""
    matrix = get_account_matrix(tid)
    plan = []

    for city, info in matrix["cities"].items():
        for platform, accounts in info["accounts"].items():
            for account in accounts:
                plan.append({
                    "account": account,
                    "city": city,
                    "platform": platform,
                    "topic": topic,
                    "content_type": content_type,
                    "scheduled": None,  # 待定时调度
                    "status": "queued",
                })

    return {
        "tenant": matrix["tenant"],
        "total_distributions": len(plan),
        "plan": plan,
    }


# ═══════════════════════════════════
# 客户仪表盘数据
# ═══════════════════════════════════

def get_client_dashboard(tid: str) -> dict:
    """装企客户看到的仪表盘数据"""
    tenant = get_tenant(tid)
    if not tenant:
        return {"error": "租户不存在"}

    # 统计产出
    content_dir = Path("D:/个人文件/AI/05 项目生产系统/内容生产")
    produced = 0
    total_score = 0
    scored_count = 0

    for f in content_dir.rglob("*.md"):
        try:
            text = f.read_text(encoding="utf-8")[:500]
            import re
            sm = re.search(r'评分[：:]\s*(\d+)/10', text)
            if sm:
                total_score += int(sm.group(1))
                scored_count += 1
            produced += 1
        except:
            pass

    avg_score = round(total_score / max(scored_count, 1), 1)

    return {
        "tenant": tenant["name"],
        "plan": tenant["plan"],
        "monthly_quota": tenant["monthly_quota"],
        "monthly_used": produced,
        "quota_pct": round(produced / max(tenant["monthly_quota"], 1) * 100),
        "avg_score": avg_score,
        "total_produced": produced,
        "cities": len(tenant["cities"]),
        "total_accounts": sum(sum(v.values()) for v in tenant["accounts"].values()),
        "matrix": get_account_matrix(tid),
    }


# ═══════════════════════════════════
# Token计量 (对标筷子科技)
# ═══════════════════════════════════

def calculate_tokens(tid: str, month: str = None) -> dict:
    """计算租户的Token消耗（内容生产计量）"""
    tenant = get_tenant(tid)
    if not tenant:
        return {}

    # 1篇图文 ≈ 10 Token
    # 1条口播脚本 ≈ 15 Token
    # 1条视频 ≈ 50 Token
    # 1次GEO检测 ≈ 5 Token

    produced = tenant.get("total_produced", 0)
    tokens = produced * 12  # 平均12 Token/篇

    return {
        "tenant": tenant["name"],
        "monthly_quota_tokens": tenant["monthly_quota"] * 10,
        "used_tokens": tokens,
        "remaining": tenant["monthly_quota"] * 10 - tokens,
        "unit_cost": {"starter": 0.5, "pro": 0.3, "enterprise": 0.2}.get(tenant["plan"], 0.5),
        "estimated_cost": round(tokens * {"starter": 0.5, "pro": 0.3, "enterprise": 0.2}.get(tenant["plan"], 0.5)),
    }
