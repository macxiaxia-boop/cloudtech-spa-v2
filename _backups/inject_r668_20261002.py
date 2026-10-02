"""
R668 治本：注入 5 端点 (skill v517 + billing v520 + campaign v540 + file v540 + quota v541)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v517(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R997_v517_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v517"}


def get_billing_payment_methods_unset_active_v520(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v520"}


def get_campaigns_audience_source_stats_v540(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R997","count":167500,"pct":79.6},
        {"source":"xhs","count":13000,"pct":32.5},
        {"source":"dy","count":102940,"pct":-127.0},
        {"source":"grp","count":4200,"pct":13.7}
    ],"total":287640,"version":"v540","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v540(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":19330,"unique_users":9085},
        {"date":"2026-10-02","downloads":19570,"unique_users":9155},
        {"date":"2026-10-03","downloads":19810,"unique_users":9225},
        {"date":"2026-10-04","downloads":20050,"unique_users":9295},
        {"date":"2026-10-05","downloads":20290,"unique_users":9365},
        {"date":"2026-10-06","downloads":20530,"unique_users":9435},
        {"date":"2026-10-07","downloads":20770,"unique_users":9505}
    ],"total":140350,"version":"v540","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v541(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12060000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12070000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12080000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12090000,"set_by":"u_001"}
    ],"count":4,"version":"v541","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v541": lambda q, id="k_001": get_auth_api_keys_quota_history_v541(id),
    "/api/v2/skills/{id}/sync-from-template-v517": lambda q, id="s_001": get_skills_sync_from_template_v517(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v520": lambda q, id="c_001": get_billing_payment_methods_unset_active_v520(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v540": lambda q, id="c001": get_campaigns_audience_source_stats_v540(id),
    "/api/v2/files/{id}/download-by-day-list-v540": lambda q, id="f_001": get_files_download_by_day_list_v540(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v539"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v539 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v539","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v539 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R668 5 endpoints (10 ROUTES + 5 defs)")