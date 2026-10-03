"""
R1257 接续推进：注入 5 端点 (skill v1035 + billing v1038 + campaign v1059 + file v1059 + quota v1060)
端点累计 R1258 (R1256+2)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v1035(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1258_v1035_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1035"}


def get_billing_payment_methods_unset_active_v1038(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1038"}


def get_campaigns_audience_source_stats_v1059(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1258","count":276300,"pct":133.9},
        {"source":"xhs","count":67200,"pct":168.0},
        {"source":"dy","count":198200,"pct":-213.4},
        {"source":"grp","count":26000,"pct":79.1}
    ],"total":567700,"version":"v1059","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v1059(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":53580,"unique_users":25065},
        {"date":"2026-10-02","downloads":53820,"unique_users":25135},
        {"date":"2026-10-03","downloads":54060,"unique_users":25205},
        {"date":"2026-10-04","downloads":54300,"unique_users":25275},
        {"date":"2026-10-05","downloads":54540,"unique_users":25345},
        {"date":"2026-10-06","downloads":54780,"unique_users":25415},
        {"date":"2026-10-07","downloads":55020,"unique_users":25485}
    ],"total":380100,"version":"v1059","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v1060(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-03T01:45:00Z","quota":16500000,"set_by":"u_001"},
        {"at":"2026-10-03T02:00:00Z","quota":16510000,"set_by":"u_001"},
        {"at":"2026-10-03T02:15:00Z","quota":16520000,"set_by":"u_001"},
        {"at":"2026-10-03T02:30:00Z","quota":16530000,"set_by":"u_001"}
    ],"count":4,"version":"v1060","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth-api-keys/{id}/quota-history-v1060": lambda q, id="k_001": get_auth_api_keys_quota_history_v1060(id),
    "/api/v2/skills/{id}/sync-from-template-v1035": lambda q, id="s_001": get_skills_sync_from_template_v1035(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v1038": lambda q, id="c_001": get_billing_payment_methods_unset_active_v1038(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v1059": lambda q, id="c001": get_campaigns_audience_source_stats_v1059(id),
    "/api/v2/files/{id}/download-by-day-list-v1059": lambda q, id="f_001": get_files_download_by_day_list_v1059(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth-api-keys/{id}/quota-history-v1058"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v1058 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v1058","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v1058 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R1257 5 endpoints · R1258 endpoints cumulative")
