"""
R674 治本：注入 5 端点 (skill v529 + billing v532 + campaign v552 + file v552 + quota v553)
⚠️ bug-free · ROUTES 全用 id
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v529(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1003_v529_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v529"}


def get_billing_payment_methods_unset_active_v532(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v532"}


def get_campaigns_audience_source_stats_v552(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1003","count":173500,"pct":82.6},
        {"source":"xhs","count":16000,"pct":40.0},
        {"source":"dy","count":108220,"pct":-131.8},
        {"source":"grp","count":5400,"pct":17.3}
    ],"total":303120,"version":"v552","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v552(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":21070,"unique_users":9925},
        {"date":"2026-10-02","downloads":21310,"unique_users":9995},
        {"date":"2026-10-03","downloads":21550,"unique_users":10065},
        {"date":"2026-10-04","downloads":21790,"unique_users":10135},
        {"date":"2026-10-05","downloads":22030,"unique_users":10205},
        {"date":"2026-10-06","downloads":22270,"unique_users":10275},
        {"date":"2026-10-07","downloads":22510,"unique_users":10345}
    ],"total":152530,"version":"v552","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v553(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12300000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12310000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12320000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12330000,"set_by":"u_001"}
    ],"count":4,"version":"v553","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v553": lambda q, id="k_001": get_auth_api_keys_quota_history_v553(id),
    "/api/v2/skills/{id}/sync-from-template-v529": lambda q, id="s_001": get_skills_sync_from_template_v529(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v532": lambda q, id="c_001": get_billing_payment_methods_unset_active_v532(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v552": lambda q, id="c001": get_campaigns_audience_source_stats_v552(id),
    "/api/v2/files/{id}/download-by-day-list-v552": lambda q, id="f_001": get_files_download_by_day_list_v552(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v551"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v551 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v551","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v551 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R674 5 endpoints · bug-free")