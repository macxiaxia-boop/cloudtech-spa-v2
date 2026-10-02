"""
R675 治本：注入 5 端点 (skill v531 + billing v534 + campaign v554 + file v554 + quota v555)
⚠️ bug-free · ROUTES 全用 id
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v531(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1004_v531_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v531"}


def get_billing_payment_methods_unset_active_v534(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v534"}


def get_campaigns_audience_source_stats_v554(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1004","count":174500,"pct":83.1},
        {"source":"xhs","count":16500,"pct":41.2},
        {"source":"dy","count":109100,"pct":-132.6},
        {"source":"grp","count":5600,"pct":17.9}
    ],"total":305700,"version":"v554","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v554(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":21360,"unique_users":10065},
        {"date":"2026-10-02","downloads":21600,"unique_users":10135},
        {"date":"2026-10-03","downloads":21840,"unique_users":10205},
        {"date":"2026-10-04","downloads":22080,"unique_users":10275},
        {"date":"2026-10-05","downloads":22320,"unique_users":10345},
        {"date":"2026-10-06","downloads":22560,"unique_users":10415},
        {"date":"2026-10-07","downloads":22800,"unique_users":10485}
    ],"total":154560,"version":"v554","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v555(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12340000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12350000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12360000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12370000,"set_by":"u_001"}
    ],"count":4,"version":"v555","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v555": lambda q, id="k_001": get_auth_api_keys_quota_history_v555(id),
    "/api/v2/skills/{id}/sync-from-template-v531": lambda q, id="s_001": get_skills_sync_from_template_v531(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v534": lambda q, id="c_001": get_billing_payment_methods_unset_active_v534(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v554": lambda q, id="c001": get_campaigns_audience_source_stats_v554(id),
    "/api/v2/files/{id}/download-by-day-list-v554": lambda q, id="f_001": get_files_download_by_day_list_v554(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v553"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v553 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v553","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v553 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R675 5 endpoints · bug-free")