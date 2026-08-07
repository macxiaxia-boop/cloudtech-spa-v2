"""
Seed realistic CRM test data
=============================
Generates realistic customers, tasks for CRM and DeepCRM modules.
Uses real 漳州 communities, Chinese names, realistic budgets.
"""
import json, sys, os
from pathlib import Path
from datetime import datetime, timedelta

# Ensure we can import local modules
sys.path.insert(0, str(Path(__file__).parent))

from crm_integration import CustomerManager, CUSTOMER_STAGES, CUSTOMER_SOURCES
from crm_deep import DeepCRM, STAGE_TIMELINE

# ── Realistic Data ──

COMMUNITIES = [
    "碧桂园·翡翠湾", "万科城·滨江", "龙湖春江天境", "融信澜天",
    "中骏雍景湾", "建发央著", "保利天汇", "招商兰溪谷",
    "联发君领首府", "中海寰宇天下", "大唐印象", "国贸天成",
    "正荣悦璟台", "阳光城翡丽湾", "恒大御景半岛", "特房锦绣碧湖",
    "万科·金域滨江", "龙湖·春江郦城", "世茂璀璨天城", "融创玖峯台",
]

NAMES = [
    "陈振华", "林雅婷", "黄建国", "吴小芳", "郑志强",
    "王美丽", "刘建明", "赵丽华", "周永康", "许佳琪",
    "苏海峰", "郭晓燕", "杨文龙", "马秀兰", "朱明辉",
    "沈秋月", "卢志远", "谢小云", "韩建军", "高美玲",
    "唐立新", "于洋", "蔡雪梅", "叶伟明", "田雨欣",
]

SOURCES = ["xiaohongshu", "douyin", "shipinhao", "referral", "offline", "geo_search", "wechat_mp", "paid_ads"]

STYLES = ["现代简约", "奶油风", "新中式", "轻奢风", "北欧风", "工业风", "日式原木", "法式复古", "极简风"]

STAGES = [
    "lead", "contacted", "measured", "quoted", "negotiating",
    "signed", "constructing", "completed", "maintenance"
]

URGENCIES = ["immediate", "1_month", "3_months", "exploring"]

def now():
    return datetime.now()

def random_days_ago(min_d, max_d):
    """Random datetime between min_d and max_d days ago"""
    import random
    days = random.randint(min_d, max_d)
    return (now() - timedelta(days=days, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat()[:19]


def main():
    import random
    random.seed(42)

    # ═══════════════════════════════════════
    # 1. Clear old test data
    # ═══════════════════════════════════════
    crm_dir = Path(__file__).parent / "data" / "crm"
    crm_deep_dir = Path(__file__).parent / "data" / "crm_deep"
    crm_file = crm_dir / "customers_zq-5bb59623.json"
    crm_deep_file = crm_deep_dir / "customers_zq-5bb59623.json"
    tasks_file = crm_deep_dir / "tasks_zq-5bb59623.json"

    # Backup old data
    backup_suffix = now().strftime("%Y%m%d_%H%M%S")
    if crm_file.exists():
        crm_file.rename(crm_dir / f"customers_zq-5bb59623_backup_{backup_suffix}.json")
    if crm_deep_file.exists():
        crm_deep_file.rename(crm_deep_dir / f"customers_zq-5bb59623_backup_{backup_suffix}.json")
    if tasks_file.exists():
        tasks_file.rename(crm_deep_dir / f"tasks_zq-5bb59623_backup_{backup_suffix}.json")

    # Initialize empty files
    crm_file.write_text("[]", encoding="utf-8")
    crm_deep_file.write_text("[]", encoding="utf-8")
    tasks_file.write_text("[]", encoding="utf-8")

    print("✓ Cleaned old data (backed up)")

    # ═══════════════════════════════════════
    # 2. Seed CRM (crm_integration) - 18 customers across all stages
    # ═══════════════════════════════════════
    mgr = CustomerManager()

    # Define customer staging: (name, phone, source, area, budget, style, stage, days_since_creation)
    crm_customers = [
        # Lead (线索) - 3
        ("陈振华", "13906061234", "xiaohongshu", 90, 12, "奶油风", "lead", 0),
        ("林雅婷", "13805961235", "douyin", 120, 22, "现代简约", "lead", 1),
        ("黄建国", "13706061236", "geo_search", 85, 9, "北欧风", "lead", 0),

        # Contacted (已联系) - 3
        ("吴小芳", "13605961237", "xiaohongshu", 105, 15, "新中式", "contacted", 2),
        ("郑志强", "13506061238", "referral", 130, 28, "轻奢风", "contacted", 1),
        ("王美丽", "13405961239", "shipinhao", 95, 11, "日式原木", "contacted", 3),

        # Measured (已量房) - 2
        ("刘建明", "13306061240", "douyin", 115, 20, "现代简约", "measured", 5),
        ("赵丽华", "13205961241", "wechat_mp", 140, 35, "法式复古", "measured", 4),

        # Quoted (已报价) - 2
        ("周永康", "13106061242", "geo_search", 125, 25, "轻奢风", "quoted", 8),
        ("许佳琪", "13005961243", "xiaohongshu", 108, 18, "奶油风", "quoted", 7),

        # Negotiating (谈判中) - 2
        ("苏海峰", "18906061244", "referral", 150, 45, "新中式", "negotiating", 15),
        ("郭晓燕", "18805961245", "paid_ads", 110, 16, "极简风", "negotiating", 12),

        # Signed (已签约) - 2
        ("杨文龙", "18706061246", "geo_search", 135, 30, "现代简约", "signed", 20),
        ("马秀兰", "18605961247", "referral", 98, 14, "北欧风", "signed", 18),

        # Constructing (施工中) - 2
        ("朱明辉", "18506061248", "xiaohongshu", 145, 38, "轻奢风", "constructing", 45),
        ("沈秋月", "18405961249", "douyin", 118, 22, "奶油风", "constructing", 40),

        # Completed (已完工) - 1
        ("卢志远", "18306061250", "referral", 128, 26, "新中式", "completed", 90),

        # Maintenance (售后) - 1
        ("谢小云", "18205961251", "geo_search", 106, 17, "日式原木", "maintenance", 120),
    ]

    for (name, phone, source, area, budget, style, stage, days_ago) in crm_customers:
        c = mgr._load()
        cid = f"cust-{now().strftime('%Y%m%d')}-{len(c)+1:04d}"

        customer = {
            "id": cid,
            "name": name,
            "phone": phone[-4:],
            "phone_hash": f"hash_{name}_{phone[-4:]}",
            "source": source,
            "city": "漳州",
            "area": area,
            "budget": budget,
            "style": style,
            "stage": stage,
            "notes": f"测试客户-{name}",
            "created_at": (now() - timedelta(days=days_ago)).isoformat()[:19],
            "updated_at": (now() - timedelta(days=max(0, days_ago - 1))).isoformat()[:19],
            "tags": [stage] if stage in ("signed", "constructing", "completed") else [],
            "follow_ups": [],
            "project": None,
        }

        # Add follow_ups for customers advanced beyond lead
        stage_idx = STAGES.index(stage)
        for i in range(1, min(stage_idx + 1, len(STAGES))):
            prev_stage = STAGES[i - 1]
            cur_stage = STAGES[i]
            customer["follow_ups"].append({
                "time": (now() - timedelta(days=days_ago + (stage_idx - i))).isoformat()[:19],
                "from_stage": prev_stage,
                "to_stage": cur_stage,
                "notes": f"{name} 阶段推进: {prev_stage} → {cur_stage}",
            })

        # Add follow_up if they have follow_ups
        c.append(customer)
        mgr._save(c)

    print(f"✓ CRM: Seeded {len(crm_customers)} customers")

    # ═══════════════════════════════════════
    # 3. Seed DeepCRM - 14 customers with varied scores
    # ═══════════════════════════════════════
    crm_deep = DeepCRM()

    deep_customers = [
        # (name, phone, source, city, community, area, budget, style, urgency, stage, days_ago, interactions)
        ("陈振华", "13906061234", "xiaohongshu", "漳州", "碧桂园·翡翠湾", 90, 12, "奶油风", "1_month", "lead", 0, []),
        ("韩建军", "18105961252", "geo_search", "漳州", "万科城·滨江", 125, 25, "现代简约", "immediate", "lead", 0, []),
        ("林雅婷", "13805961235", "douyin", "漳州", "龙湖春江天境", 120, 22, "现代简约", "3_months", "contacted", 2, [("call", "电话沟通需求", "positive")]),
        ("高美玲", "18005961253", "referral", "漳州", "建发央著", 110, 18, "新中式", "1_month", "contacted", 1, [("call", "朋友介绍，兴趣浓厚", "positive")]),
        ("吴小芳", "13605961237", "xiaohongshu", "漳州", "融信澜天", 105, 15, "新中式", "1_month", "measured", 5, [("call", "电话联系", "positive"), ("measure", "量房完成", "positive")]),
        ("唐立新", "17906061254", "paid_ads", "漳州", "中骏雍景湾", 135, 28, "轻奢风", "immediate", "measured", 4, [("call", "电话沟通", "positive"), ("measure", "量房", "positive")]),
        ("郑志强", "13506061238", "referral", "漳州", "保利天汇", 130, 28, "轻奢风", "1_month", "quoted", 8, [("call", "初次沟通", "positive"), ("measure", "量房", "positive"), ("quote", "已报价", "positive")]),
        ("于洋", "17805961255", "douyin", "漳州", "招商兰溪谷", 145, 35, "法式复古", "immediate", "quoted", 7, [("call", "沟通", "positive"), ("visit", "到店看方案", "positive"), ("quote", "出报价", "positive")]),
        ("赵丽华", "13205961241", "wechat_mp", "漳州", "联发君领首府", 140, 35, "法式复古", "3_months", "negotiating", 15, [("call", "沟通", "positive"), ("measure", "量房", "positive"), ("quote", "报价", "positive"), ("call", "跟进谈判", "neutral")]),
        ("苏海峰", "18906061244", "referral", "漳州", "大唐印象", 150, 45, "新中式", "1_month", "negotiating", 12, [("call", "沟通", "positive"), ("measure", "量房", "positive"), ("visit", "到店看工地", "positive"), ("quote", "出报价", "positive")]),
        ("杨文龙", "18706061246", "geo_search", "漳州", "国贸天成", 135, 30, "现代简约", "1_month", "signed", 20, [("call", "沟通", "positive"), ("measure", "量房", "positive"), ("quote", "报价", "positive"), ("call", "谈判", "positive"), ("contract", "签约", "positive")]),
        ("蔡雪梅", "17706061256", "xiaohongshu", "漳州", "正荣悦璟台", 120, 20, "奶油风", "1_month", "signed", 18, [("call", "沟通", "positive"), ("measure", "量房", "positive"), ("quote", "报价", "positive"), ("visit", "看方案", "positive"), ("contract", "签约", "positive")]),
        ("叶伟明", "17605961257", "referral", "漳州", "恒大御景半岛", 155, 42, "轻奢风", "3_months", "constructing", 50, [("call", "沟通", "positive"), ("measure", "量房", "positive"), ("quote", "报价", "positive"), ("contract", "签约", "positive")]),
        ("田雨欣", "17506061258", "geo_search", "漳州", "特房锦绣碧湖", 108, 16, "日式原木", "exploring", "lead", 30, []),  # Stale lead for churn detection
        ("沈秋月", "18405961249", "douyin", "漳州", "阳光城翡丽湾", 118, 22, "奶油风", "1_month", "constructing", 45, [("call", "沟通", "positive"), ("measure", "量房", "positive"), ("contract", "签约", "positive")]),
        ("卢志远", "18306061250", "referral", "漳州", "龙湖·春江郦城", 128, 26, "新中式", "3_months", "completed", 95, [("call", "沟通", "positive"), ("measure", "量房", "positive"), ("contract", "签约", "positive")]),
    ]

    for (name, phone, source, city, community, area, budget, style, urgency, stage, days_ago, interactions) in deep_customers:
        customers = crm_deep._load()
        cid = f"crm-{now().strftime('%Y%m%d')}-{len(customers)+1:04d}"

        customer = {
            "id": cid,
            "name": name,
            "phone": phone[-4:],
            "source": source,
            "city": city,
            "community": community,
            "area": area,
            "budget": budget,
            "style": style,
            "urgency": urgency,
            "stage": stage,
            "stage_entered_at": (now() - timedelta(days=days_ago)).isoformat()[:19],
            "created_at": (now() - timedelta(days=days_ago)).isoformat()[:19],
            "updated_at": (now() - timedelta(days=max(0, days_ago - 1))).isoformat()[:19],
            "tags": [stage, source],
            "notes": f"深度CRM测试-{name}-{community}",
            "interactions": [
                {
                    "time": (now() - timedelta(days=days_ago - idx)).isoformat()[:19],
                    "type": int_type,
                    "notes": notes,
                    "outcome": outcome,
                }
                for idx, (int_type, notes, outcome) in enumerate(interactions)
            ],
            "follow_ups": [],
            "score": 0,
            "health": "neutral",
            "lost_risk": False,
            "project": {
                "start_date": None,
                "end_date": None,
                "current_phase": None,
                "manager": None,
                "budget_actual": 0,
                "issues": [],
                "progress_pct": 0,
            },
        }

        # Set up project for signed/constructing/completed
        if stage in ("signed", "constructing", "completed"):
            customer["project"]["start_date"] = (now() - timedelta(days=days_ago)).isoformat()[:10]
            customer["project"]["current_phase"] = {
                "signed": "preparation",
                "constructing": "construction",
                "completed": "finished",
            }.get(stage, None)
            customer["project"]["manager"] = "项目经理-张工"
            customer["project"]["progress_pct"] = {
                "signed": 5,
                "constructing": random.randint(30, 80),
                "completed": 100,
            }.get(stage, 0)

        # Calculate score
        customer["score"] = crm_deep._calculate_score(customer)
        customer["health"] = crm_deep._calculate_health(customer)

        customers.append(customer)
        crm_deep._save(customers)

    print(f"✓ DeepCRM: Seeded {len(deep_customers)} customers")

    # ═══════════════════════════════════════
    # 4. Seed Tasks - 15 realistic tasks
    # ═══════════════════════════════════════
    tasks = [
        # Follow-up calls
        {"name": "首次联系-陈振华", "customer_name": "陈振华", "stage": "lead", "due_days": 0, "priority": "high", "status": "pending"},
        {"name": "首次联系-韩建军", "customer_name": "韩建军", "stage": "lead", "due_days": 0, "priority": "high", "status": "pending"},
        {"name": "预约量房-林雅婷", "customer_name": "林雅婷", "stage": "contacted", "due_days": 1, "priority": "high", "status": "pending"},
        {"name": "跟进量房安排-高美玲", "customer_name": "高美玲", "stage": "contacted", "due_days": 2, "priority": "normal", "status": "pending"},
        {"name": "出方案报价-吴小芳", "customer_name": "吴小芳", "stage": "measured", "due_days": 2, "priority": "high", "status": "pending"},
        {"name": "出方案报价-唐立新", "customer_name": "唐立新", "stage": "measured", "due_days": 3, "priority": "high", "status": "pending"},
        {"name": "谈判跟进-郑志强", "customer_name": "郑志强", "stage": "quoted", "due_days": 3, "priority": "high", "status": "pending"},
        {"name": "催促签约-于洋", "customer_name": "于洋", "stage": "quoted", "due_days": 5, "priority": "high", "status": "pending"},
        {"name": "最终谈判-赵丽华", "customer_name": "赵丽华", "stage": "negotiating", "due_days": 5, "priority": "high", "status": "pending"},
        {"name": "老板出面-苏海峰", "customer_name": "苏海峰", "stage": "negotiating", "due_days": 3, "priority": "high", "status": "pending"},
        {"name": "开工准备-杨文龙", "customer_name": "杨文龙", "stage": "signed", "due_days": 5, "priority": "normal", "status": "pending"},
        {"name": "施工巡检-叶伟明", "customer_name": "叶伟明", "stage": "constructing", "due_days": 7, "priority": "normal", "status": "pending"},
        {"name": "阶段验收-沈秋月", "customer_name": "沈秋月", "stage": "constructing", "due_days": 3, "priority": "normal", "status": "pending"},
        {"name": "回访-田雨欣(流失预警)", "customer_name": "田雨欣", "stage": "lead", "due_days": -5, "priority": "high", "status": "pending"},  # Overdue
        {"name": "老客户回访-卢志远", "customer_name": "卢志远", "stage": "completed", "due_days": 10, "priority": "normal", "status": "pending"},
        # Some completed tasks
        {"name": "初次联系-高美玲", "customer_name": "高美玲", "stage": "lead", "due_days": -1, "priority": "normal", "status": "completed"},
        {"name": "量房-吴小芳", "customer_name": "吴小芳", "stage": "measured", "due_days": -3, "priority": "high", "status": "completed"},
        {"name": "报价-郑志强", "customer_name": "郑志强", "stage": "quoted", "due_days": -5, "priority": "high", "status": "completed"},
    ]

    existing_tasks = []
    task_counter = 0
    for t_data in tasks:
        task_counter += 1
        task = {
            "id": f"task-{task_counter:04d}",
            "customer_id": f"deep-{t_data['customer_name']}",
            "customer_name": t_data["customer_name"],
            "name": t_data["name"],
            "stage": t_data["stage"],
            "created_at": (now() - timedelta(days=max(0, abs(t_data.get("due_days", 0)) + 1))).isoformat()[:19],
            "due_at": (now() + timedelta(days=t_data["due_days"])).isoformat()[:19],
            "status": t_data["status"],
            "priority": t_data["priority"],
        }
        if t_data.get("status") == "completed":
            task["completed_at"] = (now() - timedelta(days=1)).isoformat()[:19]
        existing_tasks.append(task)

    tasks_file.write_text(json.dumps(existing_tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Tasks: Seeded {len(existing_tasks)} tasks (15 pending, 3 completed)")

    # ═══════════════════════════════════════
    # 5. Summary
    # ═══════════════════════════════════════
    print("\n" + "="*60)
    print("SEED DATA SUMMARY")
    print("="*60)
    print(f"CRM customers (crm_integration): {len(crm_customers)}")
    stage_counts = {}
    for _, _, _, _, _, _, stage, _ in crm_customers:
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    for stage, count in stage_counts.items():
        print(f"  {stage}: {count}")

    print(f"\nDeepCRM customers: {len(deep_customers)}")
    deep_stages = {}
    for _, _, _, _, _, _, _, _, _, stage, _, _ in deep_customers:
        deep_stages[stage] = deep_stages.get(stage, 0) + 1
    for stage, count in deep_stages.items():
        print(f"  {stage}: {count}")

    print(f"\nTasks: {len(existing_tasks)} total ({sum(1 for t in existing_tasks if t['status']=='pending')} pending, {sum(1 for t in existing_tasks if t['status']=='completed')} completed)")

    print("\n✓ Seed complete!")


if __name__ == "__main__":
    main()
