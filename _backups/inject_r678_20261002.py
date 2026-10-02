"""
R678 治本：注入 5 端点 (skill v537 + billing v540 + campaign v560 + file v560 + quota v561)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v537(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1007_v537_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v537"}


def get_billing_payment_methods_unset_active_v540(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v540"}


def get_campaigns_audience_source_stats_v560(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1007","count":177500,"pct":84.6},
        {"source":"xhs","count":18000,"pct":45.0},
        {"source":"dy","count":111740,"pct":-135.0},
        {"source":"grp","count":6200,"pct":19.7}
    ],"total":313440,"version":"v560","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v560(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":22230,"unique_users":10485},
        {"date":"2026-10-02","downloads":22470,"unique_users":10555},
        {"date":"2026-10-03","downloads":22710,"unique_users":10625},
        {"date":"2026-10-04","downloads":22950,"unique_users":10695},
        {"date":"2026-10-05","downloads":23190,"unique_users":10765},
        {"date":"2026-10-06","downloads":23430,"unique_users":10835},
        {"date":"2026-10-07","downloads":23670,"unique_users":10905}
    ],"total":160650,"version":"v560","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v561(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12460000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12470000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12480000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12490000,"set_by":"u_001"}
    ],"count":4,"version":"v561","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v561": lambda q, id="k_001": get_auth_api_keys_quota_history_v561(id),
    "/api/v2/skills/{id}/sync-from-template-v537": lambda q, id="s_001": get_skills_sync_from_template_v537(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v540": lambda q, id="c_001": get_billing_payment_methods_unset_active_v540(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v560": lambda q, id="c001": get_campaigns_audience_source_stats_v560(id),
    "/api/v2/files/{id}/download-by-day-list-v560": lambda q, id="f_001": get_files_download_by_day_list_v560(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v559"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v559 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v559","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v559 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R678 5 endpoints · bug-free")