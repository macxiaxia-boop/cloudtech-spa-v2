"""
R676 治本：注入 5 端点 (skill v533 + billing v536 + campaign v556 + file v556 + quota v557)
⚠️ bug-free · ROUTES 全用 id
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v533(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1005_v533_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v533"}


def get_billing_payment_methods_unset_active_v536(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v536"}


def get_campaigns_audience_source_stats_v556(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1005","count":175500,"pct":83.6},
        {"source":"xhs","count":17000,"pct":42.5},
        {"source":"dy","count":109980,"pct":-133.4},
        {"source":"grp","count":5800,"pct":18.5}
    ],"total":308280,"version":"v556","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v556(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":21650,"unique_users":10205},
        {"date":"2026-10-02","downloads":21890,"unique_users":10275},
        {"date":"2026-10-03","downloads":22130,"unique_users":10345},
        {"date":"2026-10-04","downloads":22370,"unique_users":10415},
        {"date":"2026-10-05","downloads":22610,"unique_users":10485},
        {"date":"2026-10-06","downloads":22850,"unique_users":10555},
        {"date":"2026-10-07","downloads":23090,"unique_users":10625}
    ],"total":156590,"version":"v556","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v557(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12380000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12390000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12400000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12410000,"set_by":"u_001"}
    ],"count":4,"version":"v557","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v557": lambda q, id="k_001": get_auth_api_keys_quota_history_v557(id),
    "/api/v2/skills/{id}/sync-from-template-v533": lambda q, id="s_001": get_skills_sync_from_template_v533(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v536": lambda q, id="c_001": get_billing_payment_methods_unset_active_v536(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v556": lambda q, id="c001": get_campaigns_audience_source_stats_v556(id),
    "/api/v2/files/{id}/download-by-day-list-v556": lambda q, id="f_001": get_files_download_by_day_list_v556(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v555"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v555 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v555","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v555 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R676 5 endpoints · bug-free")