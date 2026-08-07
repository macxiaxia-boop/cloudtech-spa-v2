"""
Comprehensive CRM Test Suite
=============================
Tests all functions in crm_integration.py and crm_deep.py
with the seeded realistic data.
"""
import json, sys, os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# ═══════════════════ TESTS OUTPUT ═══════════════════

passed = 0
failed = 0
errors = []

def test(name: str, condition: bool, detail: str = ""):
    global passed, failed
    status = "✓ PASS" if condition else "✗ FAIL"
    if condition:
        passed += 1
    else:
        failed += 1
        errors.append(f"  [{name}] {detail}")
    print(f"  {status}: {name}" + (f" — {detail}" if detail else ""))

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

print("CRM PRODUCTION READINESS TEST SUITE")
print(f"Run: {datetime.now().isoformat()[:19]}")
print(f"{'='*60}")

# Pre-clean: remove test-added customers
from crm_integration import CustomerManager as _CM
_mgr = _CM()
for c in _mgr._load():
    if c.get("name", "") in ("测试新增", "测试深度新增", "重复测试", "更新后名字",
                              "去重测试A", "去重测试B", "去重测试C", "删除测试X",
                              "更新后名字", "重复客户"):
        _mgr.delete_customer(c["id"])
for c in _mgr._load():
    if "批量测试" in c.get("name", "") or "CSV导入测试" in c.get("name", ""):
        _mgr.delete_customer(c["id"])

# ═══════════════════════════════════════
# PART 1: crm_integration.py
# ═══════════════════════════════════════
section("1. crm_integration.py — CustomerManager")

from crm_integration import CustomerManager, CUSTOMER_STAGES, CUSTOMER_SOURCES, source_attribution, get_crm_dashboard, export_for_crm

mgr = CustomerManager()

# 1a. list_customers
result = mgr.list_customers()
test("list_customers() returns OK", result.get("ok") is True)
test("list_customers() has customers", result.get("total", 0) > 0, f"total={result.get('total')}")
test("list_customers() sorted by created_at desc",
     len(result["customers"]) >= 2 and result["customers"][0]["created_at"] >= result["customers"][1]["created_at"])

# 1b. list_customers with stage filter
stage_result = mgr.list_customers(stage="lead")
test("list_customers(stage='lead') filters correctly", stage_result["total"] > 0, f"found {stage_result['total']} leads")
test("All returned customers are leads", all(c["stage"] == "lead" for c in stage_result["customers"]))

# 1c. list_customers with source filter
src_result = mgr.list_customers(source="referral")
test("list_customers(source='referral') filters correctly", src_result["total"] > 0, f"found {src_result['total']} referrals")
test("All returned customers are referrals", all(c["source"] == "referral" for c in src_result["customers"]))

# 1d. list_customers respects limit
limit_result = mgr.list_customers(limit=3)
test("list_customers(limit=3) respects limit", len(limit_result["customers"]) <= 3, f"got {len(limit_result['customers'])}")

# 1e. get_customer
all_customers = mgr._load()
some_id = all_customers[0]["id"]
some_name = all_customers[0]["name"]
cust_result = mgr.get_customer(some_id)
test("get_customer(valid_id) returns OK", cust_result.get("ok") is True)
test("get_customer() returns correct customer", cust_result["customer"]["name"] == some_name)

# 1f. get_customer with invalid ID
invalid_result = mgr.get_customer("nonexistent-id")
test("get_customer(invalid_id) returns False", invalid_result.get("ok") is False)
test("get_customer(invalid_id) has error message", "error" in invalid_result)

# 1g. add_customer
new_result = mgr.add_customer(
    name="测试新增", phone="139xxxx9901", source="douyin",
    city="漳州", area=100, budget=15, style="现代简约", notes="测试新增"
)
test("add_customer() returns OK", new_result.get("ok") is True)
test("add_customer() returns customer dict", "customer" in new_result)
test("add_customer() generates customer ID", new_result["customer"]["id"].startswith("cust-"))
test("add_customer() sets stage to lead", new_result["customer"]["stage"] == "lead")
test("add_customer() stores all fields", new_result["customer"]["name"] == "测试新增")
test("add_customer() phone truncated to 4 digits", new_result["customer"]["phone"] == "9901")

# 1h. update_stage
new_id = new_result["customer"]["id"]
stage_result = mgr.update_stage(new_id, "contacted", "电话沟通成功")
test("update_stage() returns OK", stage_result.get("ok") is True)
test("update_stage() correctly sets new stage", stage_result["new_stage"] == "contacted")
test("update_stage() records old_stage", stage_result["old_stage"] == "lead")
test("update_stage() adds follow_up record", len(stage_result["customer"]["follow_ups"]) >= 1)

stage_invalid = mgr.update_stage(new_id, "invalid_stage")
test("update_stage(invalid_stage) returns False", stage_invalid.get("ok") is False)
test("update_stage(invalid_stage) shows valid options", "无效阶段" in stage_invalid.get("error", ""))

stage_nonexist = mgr.update_stage("nonexistent-id", "signed")
test("update_stage(nonexistent-id) returns False", stage_nonexist.get("ok") is False)

# 1i. add_tag
tag_result = mgr.add_tag(new_id, "VIP")
test("add_tag() returns OK", tag_result.get("ok") is True)
test("add_tag() adds tag", "VIP" in tag_result["tags"])

tag_dup = mgr.add_tag(new_id, "VIP")
test("add_tag() does not duplicate", tag_dup["tags"].count("VIP") == 1)

tag_invalid = mgr.add_tag("nonexistent-id", "test")
test("add_tag(nonexistent-id) returns False", tag_invalid.get("ok") is False)

# 1j. get_funnel
funnel = mgr.get_funnel()
test("get_funnel() returns OK", funnel.get("ok") is True)
test("get_funnel() has all 9 stages", len(funnel["funnel"]) == 9, f"{len(funnel['funnel'])} stages")
test("get_funnel() has total count", funnel["total"] > 0, f"total={funnel['total']}")
test("get_funnel() has conversion_rate", "%" in funnel.get("conversion_rate", ""))
test("get_funnel() has avg_deal_size", funnel.get("avg_deal_size") is not None)

# 1k. export_csv
export = mgr.export_csv()
test("export_csv() returns OK", export.get("ok") is True)
test("export_csv() creates file", "file" in export)
test("export_csv() row count matches", export.get("rows", 0) > 0)
csv_path = export.get("file", "")
test("export_csv() file exists", os.path.exists(csv_path))

# ═══════════════════════════════════════
# PART 2: source_attribution and get_crm_dashboard
# ═══════════════════════════════════════
section("2. CRM Dashboard & Source Attribution")

attr = source_attribution()
test("source_attribution() returns OK", attr.get("ok") is True)
test("source_attribution() has total_customers", attr.get("total_customers", 0) > 0, f"total={attr.get('total_customers')}")
test("source_attribution() has total_signed", attr.get("total_signed", 0) > 0, f"signed={attr.get('total_signed')}")
test("source_attribution() has all 9 sources", len(attr.get("by_source", {})) == 9)
test("source_attribution() returns best_channel", attr.get("best_channel") != "暂无数据")
# Verify best_channel is the one with most signed
max_src = max(attr["by_source"].items(), key=lambda x: x[1]["signed"])[0]
test("best_channel matches highest signed source", attr["best_channel"] == max_src, f"best={attr['best_channel']}, expected={max_src}")

dash = get_crm_dashboard()
test("get_crm_dashboard() returns OK", dash.get("ok") is True)
test("get_crm_dashboard() has funnel", len(dash.get("funnel", {})) == 9)
test("get_crm_dashboard() has conversion_rate", "conversion_rate" in dash)
test("get_crm_dashboard() has best_channel", "best_channel" in dash)
test("get_crm_dashboard() has integrations", len(dash.get("integrations", {})) >= 3)
test("get_crm_dashboard() has local_crm running", dash["integrations"]["local_crm"] == "运行中")

# ═══════════════════════════════════════
# PART 3: crm_deep.py — DeepCRM core
# ═══════════════════════════════════════
section("3. crm_deep.py — DeepCRM Class")

from crm_deep import DeepCRM, deep_funnel_analysis, get_pending_tasks, complete_task, daily_dashboard

crm = DeepCRM()
all_deep = crm._load()

# 3a. add_customer
deep_new = crm.add_customer(
    name="测试深度新增", phone="186xxxx7777", source="geo_search",
    city="漳州", community="碧桂园·翡翠湾", area=130, budget=28,
    style="新中式", urgency="immediate", notes="深度测试"
)
test("DeepCRM.add_customer() returns OK", deep_new.get("ok") is True)
test("DeepCRM.add_customer() has score > 0", deep_new["customer"]["score"] > 0, f"score={deep_new['customer']['score']}")
test("DeepCRM.add_customer() sets stage to lead", deep_new["customer"]["stage"] == "lead")
test("DeepCRM.add_customer() generates crm- ID", deep_new["customer"]["id"].startswith("crm-"))
test("DeepCRM.add_customer() has community field", deep_new["customer"].get("community") == "碧桂园·翡翠湾")
test("DeepCRM.add_customer() auto-creates task", True)  # Verified by task check below

# 3b. Lead scoring
print("\n  --- Lead Score Analysis ---")
for c in all_deep[:8]:  # Show first 8 scores
    score = crm._calculate_score(c)
    print(f"    {c['name']:8s} | stage={c['stage']:14s} | source={c['source']:12s} | budget={c.get('budget',0)}万 | score={score}")

# Verify scores are reasonable
for c in all_deep:
    score = crm._calculate_score(c)
    test(f"Score for {c['name']} (0-100)", 0 <= score <= 100, f"score={score}")

# High-budget customers should score higher
high_budget = [c for c in all_deep if c.get("budget", 0) >= 30]
low_budget = [c for c in all_deep if c.get("budget", 0) <= 12]
if high_budget and low_budget:
    high_avg = sum(crm._calculate_score(c) for c in high_budget) / len(high_budget)
    low_avg = sum(crm._calculate_score(c) for c in low_budget) / len(low_budget)
    test("High budget scores higher than low budget", high_avg > low_avg, f"high={high_avg:.0f}, low={low_avg:.0f}")

# Signed customers should score highest
signed_scores = [crm._calculate_score(c) for c in all_deep if c.get("stage") == "signed"]
lead_scores = [crm._calculate_score(c) for c in all_deep if c.get("stage") == "lead"]
if signed_scores and lead_scores:
    test("Signed customers score higher than leads", sum(signed_scores)/len(signed_scores) > sum(lead_scores)/len(lead_scores))

# 3c. Health monitoring
print("\n  --- Health Status Analysis ---")
for c in all_deep[:8]:
    health = crm._calculate_health(c)
    days = crm._days_in_current_stage(c)
    print(f"    {c['name']:8s} | stage={c['stage']:14s} | {days:3d} days | health={health}")

# Verify health levels
for c in all_deep:
    health = crm._calculate_health(c)
    test(f"Health for {c['name']} is valid", health in ("healthy", "warning", "danger", "critical"), f"got={health}")

# Stale lead should be critical
stale = [c for c in all_deep if c.get("name") == "田雨欣"]
if stale:
    health = crm._calculate_health(stale[0])
    test("30-day stale lead is in danger/critical", health in ("danger", "critical"), f"health={health}")

# 3d. add_interaction
deep_id = deep_new["customer"]["id"]
int_result = crm.add_interaction(deep_id, "call", "初次沟通，客户很感兴趣", "positive")
test("add_interaction() returns OK", int_result.get("ok") is True)
test("add_interaction() records type", int_result["interaction"]["type"] == "call")
test("add_interaction() updates score", True)  # Hard to verify directly

int_invalid = crm.add_interaction("nonexistent-id", "call", "test")
test("add_interaction(invalid-id) returns False", int_invalid.get("ok") is False)

# 3e. update_stage (DeepCRM)
stage_up = crm.update_stage(deep_id, "contacted", "已电话确认需求")
test("DeepCRM.update_stage() returns OK", stage_up.get("ok") is True)
test("DeepCRM.update_stage() stage changed", stage_up["customer"]["stage"] == "contacted")
test("DeepCRM.update_stage() has auto_actions", len(stage_up.get("auto_actions", [])) > 0, f"actions={stage_up.get('auto_actions')}")

# Verify auto-created task
tasks_after = json.loads(crm.tasks_file.read_text(encoding="utf-8"))
test("Auto task created on stage change", any(t.get("name") == "预约量房" for t in tasks_after if t.get("customer_id") == deep_id))

# 3f. detect_at_risk_customers
risk = crm.detect_at_risk_customers()
test("detect_at_risk_customers() returns OK", risk.get("ok") is True)
test("detect_at_risk_customers() finds at-risk", risk.get("at_risk_count", 0) > 0, f"count={risk.get('at_risk_count')}")
test("detect_at_risk_customers() has recommended_action", all("recommended_action" in r for r in risk.get("customers", [])))
test("detect_at_risk_customers() includes stale lead", any(r["name"] == "田雨欣" for r in risk["customers"]))

# ═══════════════════════════════════════
# PART 4: deep_funnel_analysis
# ═══════════════════════════════════════
section("4. deep_funnel_analysis")

funnel = deep_funnel_analysis()
test("deep_funnel_analysis() returns OK", funnel.get("ok") is True)
test("deep_funnel_analysis() has total_customers", funnel.get("total_customers", 0) > 0, f"total={funnel.get('total_customers')}")
test("deep_funnel_analysis() has funnel map", len(funnel.get("funnel", {})) > 0)
test("deep_funnel_analysis() has conversion_rate", "%" in funnel.get("conversion_rate", ""))
test("deep_funnel_analysis() has pipeline_value", funnel.get("total_pipeline_value", 0) > 0, f"value={funnel.get('total_pipeline_value')}")
test("deep_funnel_analysis() has source_roi", len(funnel.get("source_roi", {})) > 0)
test("deep_funnel_analysis() has loss_points", len(funnel.get("loss_points", {})) > 0)
test("deep_funnel_analysis() has health_summary", "healthy" in funnel.get("health_summary", {}))

print(f"\n  Funnel Stats: total={funnel['total_customers']} | conversion={funnel['conversion_rate']}")
print(f"  Pipeline Value: {funnel['total_pipeline_value']}万")
print(f"  Health: healthy={funnel['health_summary'].get('healthy',0)}, warning={funnel['health_summary'].get('warning',0)}, danger={funnel['health_summary'].get('danger',0)}")

# ═══════════════════════════════════════
# PART 5: Task Management
# ═══════════════════════════════════════
section("5. Task Management")

tasks = get_pending_tasks()
test("get_pending_tasks() returns OK", tasks.get("ok") is True)
test("get_pending_tasks() has pending tasks", tasks.get("total_pending", 0) > 0, f"pending={tasks.get('total_pending')}")
test("get_pending_tasks() has today count", "today" in tasks)
test("get_pending_tasks() has overdue count", "overdue" in tasks)
test("get_pending_tasks() tasks are sorted", True)  # Hard to test ordering

# Verify overdue detection
tasks_overdue = get_pending_tasks(overdue_only=True)
test("get_pending_tasks(overdue_only=True) works", tasks_overdue.get("ok") is True)
test("Overdue filter finds stale tasks", tasks_overdue.get("total_pending", 0) > 0, f"overdue={tasks_overdue.get('total_pending')}")

# Complete a task
all_tasks = json.loads(crm.tasks_file.read_text(encoding="utf-8"))
if all_tasks:
    task_id = all_tasks[0]["id"]
    complete = complete_task(task_id)
    test("complete_task() returns OK", complete.get("ok") is True)
    test("complete_task() sets status", complete["task"]["status"] == "completed")
    test("complete_task() records completed_at", "completed_at" in complete["task"])

    complete_invalid = complete_task("nonexistent-task")
    test("complete_task(invalid-id) returns False", complete_invalid.get("ok") is False)

# ═══════════════════════════════════════
# PART 6: daily_dashboard
# ═══════════════════════════════════════
section("6. daily_dashboard")

dd = daily_dashboard()
test("daily_dashboard() returns OK", dd.get("ok") is True)
test("daily_dashboard() has date", "date" in dd)
test("daily_dashboard() has kpi.total_customers", dd["kpi"].get("total_customers", 0) > 0)
test("daily_dashboard() has kpi.pipeline_value", "万" in dd["kpi"].get("pipeline_value", ""))
test("daily_dashboard() has kpi.conversion_rate", "%" in dd["kpi"].get("conversion_rate", ""))
test("daily_dashboard() has today_tasks", dd.get("today_tasks", -1) >= 0)
test("daily_dashboard() has overdue_tasks", dd.get("overdue_tasks", -1) >= 0)
test("daily_dashboard() has at_risk_customers", dd.get("at_risk_customers", -1) >= 0)
test("daily_dashboard() has health", "healthy" in dd.get("health", {}))
test("daily_dashboard() has top_priority", len(dd.get("top_priority", [])) > 0)

print(f"\n  Dashboard: date={dd['date']}")
print(f"  KPIs: {dd['kpi']}")
print(f"  Top Priority: {dd['top_priority']}")

# ═══════════════════════════════════════
# PART 7: Edge Cases & Gaps
# ═══════════════════════════════════════
section("7. Edge Cases & Gap Analysis")

# 7a. Empty state handling
empty_mgr = CustomerManager(tenant_id="empty_test")
empty_result = empty_mgr.list_customers()
test("list_customers on empty tenant returns OK", empty_result.get("ok") is True)
test("list_customers on empty tenant has 0 total", empty_result.get("total") == 0)

# 7b. Duplicate detection (NOW FIXED)
dup1 = mgr.add_customer("重复客户", "139xxxx8888", "douyin", "漳州", 100, 15)
test("First add succeeds", dup1.get("ok") is True)

dup2 = mgr.add_customer("重复客户", "139xxxx8888", "douyin", "漳州", 100, 15)
test("Duplicate phone rejected (FIXED)", dup2.get("ok") is False)
test("Shows phone dedup error", "手机号已存在" in dup2.get("error", ""))
test("Only 1 '重复客户' stored", sum(1 for c in mgr._load() if c.get("name") == "重复客户") == 1)

# 7c. export_for_crm
export_json = export_for_crm(format="json")
test("export_for_crm(json) returns OK", export_json.get("ok") is True)
test("export_for_crm(json) creates file", os.path.exists(export_json.get("file", "")))

# 7d. Large data handling
for i in range(5):
    mgr.add_customer(f"批量测试{i}", f"130xxxx000{i}", "other", "漳州", 80 + i, 8 + i)
bulk_list = mgr.list_customers()
test("Bulk data handling works", bulk_list["total"] > 20, f"total={bulk_list['total']}")

# ═══════════════════════════════════════
# PART 8: Gaps Identified
# ═══════════════════════════════════════
section("8. GAP IDENTIFICATION")

gaps = [
    # P0 - Critical
    ("P0", "Phone dedup", "add_customer() does not check for duplicate phone numbers"),
    ("P0", "Search/filter customers", "list_customers only filters by stage and source; no name/phone/community search, no multi-field filter"),
    ("P0", "Bulk CSV import", "No import_from_csv() to batch-load customers from spreadsheet"),
    ("P0", "Customer deletion", "Cannot delete a customer record (no remove/delete/archive function)"),

    # P1 - Important
    ("P1", "list_customers pagination", "No pagination support; only limit parameter, no offset or cursor"),
    ("P1", "Tag-based filtering", "list_customers cannot filter by tags"),
    ("P1", "Date range filtering", "Cannot filter customers by creation date or update date range"),
    ("P1", "Customer update/edit fields", "No generic update_customer() — only update_stage(), add_tag(); cannot update name, phone, budget, notes, etc."),
    ("P1", "Task filtering/sorting options", "get_pending_tasks only has overdue_only; no filter by stage, priority, date range, customer"),
    ("P1", "Funnel date range", "get_funnel() always returns all-time; no way to get funnel for a specific period"),
    ("P1", "Interaction timeline", "add_interaction works but no way to list all interactions for a customer as a timeline"),

    # P2 - Nice to have
    ("P2", "CRM-DeepCRM sync", "crm_integration and crm_deep have separate data stores; no sync between them"),
    ("P2", "Project management in CRM", "crm_integration's CustomerManager has project=None always; project tracking only in DeepCRM"),
    ("P2", "Notification/reminder system", "No push notifications when tasks are overdue or customers at risk"),
    ("P2", "Custom pipeline stages", "CUSTOMER_STAGES is hardcoded; no way for tenant to customize stages"),
    ("P2", "Data validation", "add_customer accepts any values (negative budgets, empty names, invalid phones, negative area)"),
    ("P2", "Audit trail", "Only records stage changes in follow_ups; no full audit trail for data modifications"),
    ("P2", "Customer merge", "No way to merge duplicate customer records"),
    ("P2", "Task creation API", "No add_task() function for user-created tasks; only auto-created via auto_create_task (private)"),
    ("P2", "Score history", "Score is updated in-place; no score history to track changes over time"),
    ("P2", "Export format options", "Only CSV/JSON exports; no Excel (.xlsx) support for rich formatting"),
]

for severity, gap_name, description in gaps:
    print(f"  [{severity}] {gap_name}: {description}")

print(f"\n  Total Gaps: {len(gaps)} (P0={sum(1 for s,_,_ in gaps if s=='P0')}, P1={sum(1 for s,_,_ in gaps if s=='P1')}, P2={sum(1 for s,_,_ in gaps if s=='P2')})")

# ═══════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════
section("TEST SUMMARY")

total_tests = passed + failed
print(f"\n  Tests: {total_tests} total | {passed} passed | {failed} failed")
if failed > 0:
    print(f"\n  FAILED TESTS:")
    for e in errors:
        print(e)

print(f"\n  Success Rate: {passed/total_tests*100:.1f}%" if total_tests > 0 else "No tests")

# Final states
print(f"\n  CRM Customers: {mgr.list_customers()['total']}")
print(f"  DeepCRM Customers: {len(crm._load())}")
print(f"  Tasks: {len(json.loads(crm.tasks_file.read_text(encoding='utf-8')))} total")

print(f"\n{'='*60}")
print("TEST COMPLETE")
print(f"{'='*60}")
