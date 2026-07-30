#!/usr/bin/env python3
"""
装企入驻流程 — Tenant Onboarding
=================================
1. 创建租户 → 2. 配置账号矩阵 → 3. 生成首批内容 → 4. 打开客户仪表盘
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tenant_platform import create_tenant, get_account_matrix, distribute_content, get_client_dashboard
from billing import record_usage, PLANS

def onboard(name: str, cities: list, plan: str = "pro"):
    """一站式装企入驻"""
    print(f"🏗️ 装企入驻: {name}")
    print(f"   套餐: {PLANS[plan]['name']} (¥{PLANS[plan]['price_monthly']}/月)")
    print(f"   城市: {', '.join(cities)}")

    # Step 1: 创建租户
    tenant = create_tenant(name, cities, plan)
    tid = tenant["id"]
    total_accounts = sum(sum(v.values()) for v in tenant["accounts"].values())
    print(f"   ✅ 租户已创建: {tid}")
    print(f"   ✅ 账号矩阵: {total_accounts} 个账号")

    # Step 2: 展示账号矩阵
    matrix = get_account_matrix(tid)
    for city, info in matrix["cities"].items():
        names = []
        for p, accts in info["accounts"].items():
            names.extend(accts[:2])
        print(f"      {city}: {info['total']}个 — {' | '.join(names[:3])}")

    # Step 3: 生成首批内容(免费赠送5篇)
    print(f"   🎁 首批5篇内容生产中...")
    from admin_dashboard import _deepseek_call, CREATOR_STYLES, CONTENT_FORMS, PLATFORMS

    topics = [f"{cities[0]}装修避坑指南", f"{cities[0]}旧房翻新案例",
              f"{cities[0]}小户型空间利用", f"{cities[0]}厨房改造方案",
              f"{cities[0]}装修报价怎么算"]

    for i, topic in enumerate(topics):
        try:
            creator = CREATOR_STYLES["zhinan"]
            form = CONTENT_FORMS["article"]
            sys_p = f"对标{creator['name']}: {creator['tone']}。为装企「{name}」写一篇小红书文案。600-800字。"
            content = _deepseek_call(sys_p, topic, max_tokens=1500)
            title = content.split("\n")[0][:60]
            record_usage(tid, "article", topic, 8)
            print(f"      ✅ #{i+1} {title[:40]} (8T)")
        except Exception as e:
            print(f"      ❌ #{i+1} {topic[:20]}: {str(e)[:50]}")

    # Step 4: 展示仪表盘
    dash = get_client_dashboard(tid)
    quota = check_quota(tid)
    print(f"\n   📊 仪表盘: http://localhost:5099/client?tid={tid}")
    print(f"   📊 配额: {quota['used_tokens']}/{quota['quota_tokens']}T ({quota['usage_pct']}%)")
    print(f"   📊 预估月费: ¥{quota['estimated_cost']}")

    return {"tenant_id": tid, "name": name, "plan": plan, "accounts": total_accounts, "dashboard_url": f"http://localhost:5099/client?tid={tid}"}


if __name__ == "__main__":
    from billing import check_quota
    # Demo: onboard a new 装企
    result = onboard("福州好家装", ["福州", "厦门"], "pro")
    print(f"\n✅ 入驻完成! {result['dashboard_url']}")
