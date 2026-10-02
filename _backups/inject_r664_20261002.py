"""
R664 治本：注入 5 端点 (skill v510 + billing v511 + campaign v532 + file v532 + quota v533)
复用 R663 inject 模式
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v510(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R993_v510_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v510"}


def get_billing_payment_methods_unset_active_v511(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v511"}


def get_campaigns_audience_source_stats_v532(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R993","count":163500,"pct":77.6},
        {"source":"xhs","count":11000,"pct":27.5},
        {"source":"dy","count":99420,"pct":-123.8},
        {"source":"grp","count":3400,"pct":11.3}
    ],"total":277320,"version":"v532","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v532(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":18170,"unique_users":8525},
        {"date":"2026-10-02","downloads":18410,"unique_users":8595},
        {"date":"2026-10-03","downloads":18650,"unique_users":8665},
        {"date":"2026-10-04","downloads":18890,"unique_users":8735},
        {"date":"2026-10-05","downloads":19130,"unique_users":8805},
        {"date":"2026-10-06","downloads":19370,"unique_users":8875},
        {"date":"2026-10-07","downloads":19610,"unique_users":8945}
    ],"total":132230,"version":"v532","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v533(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":11900000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":11910000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":11920000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":11930000,"set_by":"u_001"}
    ],"count":4,"version":"v533","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v533": lambda q, id="k_001": get_auth_api_keys_quota_history_v533(id),
    "/api/v2/skills/{id}/sync-from-template-v510": lambda q, id="s_001": get_skills_sync_from_template_v510(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v511": lambda q, id="c_001": get_billing_payment_methods_unset_active_v511(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v532": lambda q, id="c001": get_campaigns_audience_source_stats_v532(id),
    "/api/v2/files/{id}/download-by-day-list-v532": lambda q, id="f_001": get_files_download_by_day_list_v532(id),
'''

# 找首个 R663 quota-history-v531 路由（line 24453 后插入位置）
target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v531"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v531 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

# 函数定义：在 R663 quota-history-v531 函数末尾后插入
fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v531","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v531 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R664 5 endpoints (10 ROUTES + 5 defs)")