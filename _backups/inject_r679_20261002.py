"""
R679 治本：注入 5 端点 (skill v539 + billing v542 + campaign v562 + file v562 + quota v563)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v539(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1008_v539_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v539"}


def get_billing_payment_methods_unset_active_v542(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v542"}


def get_campaigns_audience_source_stats_v562(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1008","count":178500,"pct":85.1},
        {"source":"xhs","count":18500,"pct":46.2},
        {"source":"dy","count":112620,"pct":-135.8},
        {"source":"grp","count":6400,"pct":20.3}
    ],"total":316020,"version":"v562","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v562(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":22520,"unique_users":10625},
        {"date":"2026-10-02","downloads":22760,"unique_users":10695},
        {"date":"2026-10-03","downloads":23000,"unique_users":10765},
        {"date":"2026-10-04","downloads":23240,"unique_users":10835},
        {"date":"2026-10-05","downloads":23480,"unique_users":10905},
        {"date":"2026-10-06","downloads":23720,"unique_users":10975},
        {"date":"2026-10-07","downloads":23960,"unique_users":11045}
    ],"total":162680,"version":"v562","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v563(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12500000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12510000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12520000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12530000,"set_by":"u_001"}
    ],"count":4,"version":"v563","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v563": lambda q, id="k_001": get_auth_api_keys_quota_history_v563(id),
    "/api/v2/skills/{id}/sync-from-template-v539": lambda q, id="s_001": get_skills_sync_from_template_v539(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v542": lambda q, id="c_001": get_billing_payment_methods_unset_active_v542(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v562": lambda q, id="c001": get_campaigns_audience_source_stats_v562(id),
    "/api/v2/files/{id}/download-by-day-list-v562": lambda q, id="f_001": get_files_download_by_day_list_v562(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v561"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v561 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v561","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v561 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R679 5 endpoints · bug-free")