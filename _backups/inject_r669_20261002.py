"""
R669 治本：注入 5 端点 (skill v519 + billing v522 + campaign v542 + file v542 + quota v543)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v519(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R998_v519_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v519"}


def get_billing_payment_methods_unset_active_v522(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v522"}


def get_campaigns_audience_source_stats_v542(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R998","count":168500,"pct":80.1},
        {"source":"xhs","count":13500,"pct":33.7},
        {"source":"dy","count":103820,"pct":-127.8},
        {"source":"grp","count":4400,"pct":14.3}
    ],"total":290220,"version":"v542","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v542(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":19620,"unique_users":9225},
        {"date":"2026-10-02","downloads":19860,"unique_users":9295},
        {"date":"2026-10-03","downloads":20100,"unique_users":9365},
        {"date":"2026-10-04","downloads":20340,"unique_users":9435},
        {"date":"2026-10-05","downloads":20580,"unique_users":9505},
        {"date":"2026-10-06","downloads":20820,"unique_users":9575},
        {"date":"2026-10-07","downloads":21060,"unique_users":9645}
    ],"total":142380,"version":"v542","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v543(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12100000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12110000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12120000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12130000,"set_by":"u_001"}
    ],"count":4,"version":"v543","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v543": lambda q, id="k_001": get_auth_api_keys_quota_history_v543(id),
    "/api/v2/skills/{id}/sync-from-template-v519": lambda q, id="s_001": get_skills_sync_from_template_v519(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v522": lambda q, id="c_001": get_billing_payment_methods_unset_active_v522(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v542": lambda q, id="c001": get_campaigns_audience_source_stats_v542(id),
    "/api/v2/files/{id}/download-by-day-list-v542": lambda q, id="f_001": get_files_download_by_day_list_v542(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v541"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v541 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v541","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v541 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R669 5 endpoints (10 ROUTES + 5 defs)")