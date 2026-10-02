"""
R667 治本：注入 5 端点 (skill v515 + billing v518 + campaign v538 + file v538 + quota v539)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v515(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R996_v515_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v515"}


def get_billing_payment_methods_unset_active_v518(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v518"}


def get_campaigns_audience_source_stats_v538(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R996","count":166500,"pct":79.1},
        {"source":"xhs","count":12500,"pct":31.2},
        {"source":"dy","count":102060,"pct":-126.2},
        {"source":"grp","count":4000,"pct":13.1}
    ],"total":285060,"version":"v538","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v538(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":19040,"unique_users":8945},
        {"date":"2026-10-02","downloads":19280,"unique_users":9015},
        {"date":"2026-10-03","downloads":19520,"unique_users":9085},
        {"date":"2026-10-04","downloads":19760,"unique_users":9155},
        {"date":"2026-10-05","downloads":20000,"unique_users":9225},
        {"date":"2026-10-06","downloads":20240,"unique_users":9295},
        {"date":"2026-10-07","downloads":20480,"unique_users":9365}
    ],"total":138320,"version":"v538","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v539(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12020000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12030000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12040000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12050000,"set_by":"u_001"}
    ],"count":4,"version":"v539","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v539": lambda q, id="k_001": get_auth_api_keys_quota_history_v539(id),
    "/api/v2/skills/{id}/sync-from-template-v515": lambda q, id="s_001": get_skills_sync_from_template_v515(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v518": lambda q, id="c_001": get_billing_payment_methods_unset_active_v518(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v538": lambda q, id="c001": get_campaigns_audience_source_stats_v538(id),
    "/api/v2/files/{id}/download-by-day-list-v538": lambda q, id="f_001": get_files_download_by_day_list_v538(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v537"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v537 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v537","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v537 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R667 5 endpoints (10 ROUTES + 5 defs)")