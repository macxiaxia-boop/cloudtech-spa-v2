"""
R1258 接续推进：注入 5 端点 (skill v1037 + billing v1040 + campaign v1061 + file v1061 + quota v1062)
端点累计 R1259 (R1257+2)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v1037(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1259_v1037_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1037"}


def get_billing_payment_methods_unset_active_v1040(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v1040"}


def get_campaigns_audience_source_stats_v1061(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1259","count":277200,"pct":134.3},
        {"source":"xhs","count":67500,"pct":168.8},
        {"source":"dy","count":198800,"pct":-213.9},
        {"source":"grp","count":26200,"pct":79.7}
    ],"total":569700,"version":"v1061","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v1061(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":55260,"unique_users":25515},
        {"date":"2026-10-02","downloads":55500,"unique_users":25585},
        {"date":"2026-10-03","downloads":55740,"unique_users":25655},
        {"date":"2026-10-04","downloads":55980,"unique_users":25725},
        {"date":"2026-10-05","downloads":56220,"unique_users":25795},
        {"date":"2026-10-06","downloads":56460,"unique_users":25865},
        {"date":"2026-10-07","downloads":56700,"unique_users":25935}
    ],"total":391860,"version":"v1061","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v1062(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-03T02:45:00Z","quota":16540000,"set_by":"u_001"},
        {"at":"2026-10-03T03:00:00Z","quota":16550000,"set_by":"u_001"},
        {"at":"2026-10-03T03:15:00Z","quota":16560000,"set_by":"u_001"},
        {"at":"2026-10-03T03:30:00Z","quota":16570000,"set_by":"u_001"}
    ],"count":4,"version":"v1062","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth-api-keys/{id}/quota-history-v1062": lambda q, id="k_001": get_auth_api_keys_quota_history_v1062(id),
    "/api/v2/skills/{id}/sync-from-template-v1037": lambda q, id="s_001": get_skills_sync_from_template_v1037(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v1040": lambda q, id="c_001": get_billing_payment_methods_unset_active_v1040(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v1061": lambda q, id="c001": get_campaigns_audience_source_stats_v1061(id),
    "/api/v2/files/{id}/download-by-day-list-v1061": lambda q, id="f_001": get_files_download_by_day_list_v1061(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth-api-keys/{id}/quota-history-v1060"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v1060 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v1060","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v1060 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R1258 5 endpoints · R1259 endpoints cumulative")
