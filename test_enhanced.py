"""
Test Enhanced CRM Features
===========================
Verifies all P0/P1 gap fixes work correctly.
"""
import json, sys, os, csv as csv_mod
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from crm_integration import CustomerManager, _hash_phone
from crm_deep import DeepCRM, get_pending_tasks, complete_task

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    status = "✓" if condition else "✗"
    if condition: passed += 1
    else: failed += 1
    print(f"  {status} {name}" + (f": {detail}" if detail else ""))

print("=" * 60)
print("ENHANCED FEATURES VERIFICATION")
print("=" * 60)

mgr = CustomerManager()
crm = DeepCRM()

# Pre-clean: remove all test customers added by tests
TEST_NAMES = ["去重测试", "重复测试", "删除测试", "CSV导入测试", "批量导入"]
all_custs = mgr._load()
to_delete = [c["id"] for c in all_custs if any(t in c.get("name", "") for t in TEST_NAMES)]
for cid in to_delete:
    mgr.delete_customer(cid)
if to_delete:
    print(f"[pre-clean] Removed {len(to_delete)} stale test customers")

# ════ 1. Phone Dedup ════
print("\n[1] Phone Dedup")
# Create a fresh customer via add_customer so phone_hash is correct
fresh = mgr.add_customer("去重测试A", "136xxxx7777", "douyin", "漳州", 90, 10, "现代简约", "首次添加")
test("first add succeeds", fresh.get("ok") is True)

# Try adding same phone again
dup_result = mgr.add_customer("去重测试B", "136xxxx7777", "douyin", "漳州", 90, 10, "现代简约", "重复尝试")
test("Duplicate phone rejected", dup_result.get("ok") is False)
test("Shows '手机号已存在'", "手机号已存在" in dup_result.get("error", ""))
test("Returns existing_customer", "existing_customer" in dup_result)

# Force add (dedup=False)
force_result = mgr.add_customer("去重测试C", "136xxxx7777", "douyin", "漳州", 90, 10, "现代简约", "强制添加", dedup=False)
test("dedup=False forces add", force_result.get("ok") is True)

# Cleanup: delete test duplicates
for c in mgr._load():
    if c.get("name", "").startswith("去重测试"):
        mgr.delete_customer(c["id"])

# ════ 2. Search/Filter ════
print("\n[2] Customer Search & Filter")

# Keyword search
kw_result = mgr.list_customers(keyword="陈振华")
test("keyword='陈振华' finds match", kw_result["total"] >= 1, f"found {kw_result['total']}")
test("Result contains '陈振华'", any("陈振华" in c["name"] for c in kw_result["customers"]))

# Tag filter
tag_result = mgr.list_customers(tags=["contacted"])
test("tag filter works", tag_result.get("ok") is True)

# Date range filter
date_result = mgr.list_customers(date_from="2026-08-01", date_to="2026-08-07")
test("date range filter works", date_result["total"] > 0, f"found {date_result['total']}")

# Budget range filter
budget_result = mgr.list_customers(min_budget=20, max_budget=50)
test("budget range filter works", budget_result["total"] > 0, f"found {budget_result['total']}")
test("All results in budget range", all(20 <= c.get("budget", 0) <= 50 for c in budget_result["customers"]))

# Combined filters
combined_result = mgr.list_customers(keyword="林", stage="lead", limit=5)
test("combined filter (keyword+stage) works", combined_result["ok"] is True)

# ════ 3. Pagination ════
print("\n[3] Pagination")
page1 = mgr.list_customers(limit=5, offset=0)
test("page1 returns 5", page1["count"] == 5)
test("page1 has_more=True", page1["has_more"] is True)

page2 = mgr.list_customers(limit=5, offset=5)
test("page2 returns 5", page2["count"] == 5)
test("page1 != page2 ids", page1["customers"][0]["id"] != page2["customers"][0]["id"])

page_last = mgr.list_customers(limit=10, offset=25)
test("last page has_more=False", page_last["has_more"] is False or page_last["count"] < 10)

# ════ 4. update_customer ════
print("\n[4] update_customer")
custs = mgr._load()
test_id = custs[0]["id"]
test_name = custs[0]["name"]

update_r = mgr.update_customer(test_id, name="更新后名字", budget=99)
test("update_customer returns OK", update_r.get("ok") is True)
test("name updated", update_r["customer"]["name"] == "更新后名字")
test("budget updated", update_r["customer"]["budget"] == 99)
test("updated_fields listed", "name" in update_r["updated_fields"])

# Revert
mgr.update_customer(test_id, name=test_name)

# Invalid field
inv_update = mgr.update_customer(test_id, nonexist_field="test")
test("invalid field rejected", inv_update.get("ok") is False)

# ════ 5. delete_customer ════
print("\n[5] delete_customer")
# Create fresh test customer for delete test
del_test = mgr.add_customer("删除测试X", "135xxxx9998", "offline", "漳州", 80, 8, "极简风", "待删除")
test("delete test: create succeeds", del_test.get("ok") is True)
del_id = del_test["customer"]["id"]

del_result = mgr.delete_customer(del_id)
test("delete_customer returns OK", del_result.get("ok") is True)
test("deleted customer returned", del_result["deleted"]["name"] == "删除测试X")

# Verify gone
check = mgr.get_customer(del_id)
test("deleted customer not found", check.get("ok") is False)

# Delete non-existent
del_inv = mgr.delete_customer("nonexistent-id")
test("delete non-existent returns False", del_inv.get("ok") is False)

# ════ 6. CSV Import ════
print("\n[6] CSV Bulk Import")
# Create a test CSV with unique phones
import random
rand_suffix = random.randint(10000, 99999)
csv_path = Path(__file__).parent / "data" / "crm" / "test_import.csv"
with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
    w = csv_mod.writer(f)
    w.writerow(["姓名", "电话", "城市", "面积", "预算", "风格", "备注", "来源"])
    w.writerow([f"CSV导入测试{rand_suffix}A", f"139xxxx{rand_suffix}1", "漳州", "95", "12", "奶油风", "CSV批量测试1", "offline"])
    w.writerow([f"CSV导入测试{rand_suffix}B", f"139xxxx{rand_suffix}2", "漳州", "110", "18", "现代简约", "CSV批量测试2", "xiaohongshu"])
    w.writerow([f"CSV导入测试{rand_suffix}C", f"139xxxx{rand_suffix}3", "漳州", "125", "25", "新中式", "CSV批量测试3", "referral"])

import_r = mgr.import_from_csv(str(csv_path))
test("import_from_csv returns OK", import_r.get("ok") is True)
test("imported 3 customers", import_r.get("imported") == 3, f"imported={import_r.get('imported')}, skipped={import_r.get('skipped')}")

# Verify they exist
check_import = mgr.list_customers(keyword=f"CSV导入测试{rand_suffix}")
test("imported customers found", check_import["total"] >= 3, f"found {check_import['total']}")

# Re-import (should be skipped due to dedup)
import2 = mgr.import_from_csv(str(csv_path))
test("re-import with dedup skips all", import2.get("skipped", 0) >= 3,
     f"imported={import2.get('imported')}, skipped={import2.get('skipped')}")

# Cleanup
for c in mgr._load():
    if f"CSV导入测试{rand_suffix}" in c.get("name", ""):
        mgr.delete_customer(c["id"])

# ════ 7. DeepCRM Search ════
print("\n[7] DeepCRM Search & Filter")
deep_search = crm.list_customers(keyword="碧桂园")
test("deep keyword search works", deep_search["total"] >= 1, f"found {deep_search['total']}")

deep_stage = crm.list_customers(stage="negotiating")
test("deep stage filter works", deep_stage["total"] >= 1, f"found {deep_stage['total']}")

deep_score = crm.list_customers(min_score=80)
test("deep min_score filter", deep_score["total"] > 0, f"found {deep_score['total']}")
test("all have score >= 80", all(c["score"] >= 80 for c in deep_score["customers"]))

deep_health = crm.list_customers(health=["danger", "critical"])
test("deep health filter (danger+critical)", deep_health["total"] > 0, f"found {deep_health['total']}")

# ════ 8. add_task (public API) ════
print("\n[8] add_task (Public API)")
dc = crm._load()
if dc:
    target_name = dc[0]["name"]
    target_id = dc[0]["id"]

    task_r = crm.add_task(
        customer_id=target_id,
        customer_name=target_name,
        name="手动创建的测试任务",
        stage="lead",
        due_days=3,
        priority="high"
    )
    test("add_task returns OK", task_r.get("ok") is True)
    test("task has ID", task_r["task"]["id"].startswith("task-"))
    test("task has correct name", task_r["task"]["name"] == "手动创建的测试任务")
    test("task priority is high", task_r["task"]["priority"] == "high")

    # Verify it appears in pending tasks
    all_pending = get_pending_tasks()
    test("new task appears in pending", any(t["name"] == "手动创建的测试任务" for t in all_pending["tasks"]))

# ════ 9. Task Filtering ════
print("\n[9] Enhanced Task Filtering")
high_tasks = get_pending_tasks(priority="high")
test("priority filter (high)", high_tasks["total_pending"] > 0, f"found {high_tasks['total_pending']}")

stage_tasks = get_pending_tasks(stage="lead")
test("stage filter (lead)", stage_tasks.get("ok") is True)

name_tasks = get_pending_tasks(customer_name="田雨欣")
test("customer_name filter", name_tasks.get("ok") is True)

# ════ 10. get_interactions ════
print("\n[10] get_interactions (Interaction Timeline)")
int_customers = [c for c in dc if len(c.get("interactions", [])) > 0]
if int_customers:
    int_id = int_customers[0]["id"]
    int_name = int_customers[0]["name"]
    int_result = crm.get_interactions(int_id)
    test("get_interactions returns OK", int_result.get("ok") is True)
    test("has interactions", int_result.get("total_interactions", 0) > 0)
    test("customer name correct", int_result["customer_name"] == int_name)
    test("has follow_ups count", "total_follow_ups" in int_result)
    print(f"    Example: {int_name} has {int_result['total_interactions']} interactions, {int_result['total_follow_ups']} follow-ups")

inv_int = crm.get_interactions("nonexistent-id")
test("get_interactions invalid id returns False", inv_int.get("ok") is False)

# ════ FINAL SUMMARY ════
print("\n" + "=" * 60)
print("ENHANCEMENT TEST SUMMARY")
print("=" * 60)
total = passed + failed
print(f"  {passed}/{total} passed" + (f" ({passed/total*100:.0f}%)" if total > 0 else ""))
if failed:
    print(f"  {failed} FAILED!")
else:
    print("  ✓ ALL ENHANCED FEATURES VERIFIED")

# Cleanup
if csv_path.exists():
    csv_path.unlink()

print(f"\nFinal CRM customers: {mgr.list_customers()['total']}")
print(f"Final DeepCRM customers: {len(crm._load())}")
print(f"Final tasks: {len(json.loads(crm.tasks_file.read_text(encoding='utf-8')))}")
