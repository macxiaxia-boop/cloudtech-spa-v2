"""
R1259 接续推进：注入 5 端点 (skill v1039 + billing v1042 + campaign v1063 + file v1063 + quota v1064)
端点累计 R1260 (R1258+2)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v1039(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1260_v1039_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1039"}


def get_billing_payment_methods_unset_active_v1042(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1042"}


def get_campaigns_audience_source_stats_v1063(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1260","count":278100,"pct":134.7},
        {"source":"xhs","count":67800,"pct":169.5},
        {"source":"dy","count":199400,"pct":-214.4},
        {"source":"grp","count":26400,"pct":80.3}
    ],"total":571700,"version":"v1063","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v1063(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":56940,"unique_users":25965},
        {"date":"2026-10-02","downloads":57180,"unique_users":26035},
        {"date":"2026-10-03","downloads":57420,"unique_users":26105},
        {"date":"2026-10-04","downloads":57660,"unique_users":26175},
        {"date":"2026-10-05","downloads":57900,"unique_users":26245},
        {"date":"2026-10-06","downloads":58140,"unique_users":26315},
        {"date":"2026-10-07","downloads":58380,"unique_users":26385}
    ],"total":403620,"version":"v1063","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v1064(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-03T03:45:00Z","quota":16600000,"set_by":"u_001"},
        {"at":"2026-10-03T04:00:00Z","quota":16610000,"set_by":"u_001"},
        {"at":"2026-10-03T04:15:00Z","quota":16620000,"set_by":"u_001"},
        {"at":"2026-10-03T04:30:00Z","quota":16630000,"set_by":"u_001"}
    ],"count":4,"version":"v1064","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth-api-keys/{id}/quota-history-v1064": lambda q, id="k_001": get_auth_api_keys_quota_history_v1064(id),
    "/api/v2/skills/{id}/sync-from-template-v1039": lambda q, id="s_001": get_skills_sync_from_template_v1039(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v1042": lambda q, id="c_001": get_billing_payment_methods_unset_active_v1042(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v1063": lambda q, id="c001": get_campaigns_audience_source_stats_v1063(id),
    "/api/v2/files/{id}/download-by-day-list-v1063": lambda q, id="f_001": get_files_download_by_day_list_v1063(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth-api-keys/{id}/quota-history-v1062"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v1062 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v1062","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v1062 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R1259 5 endpoints · R1260 endpoints cumulative")
