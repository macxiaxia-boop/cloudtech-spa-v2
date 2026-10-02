"""
R670 治本：注入 5 端点 (skill v521 + billing v524 + campaign v544 + file v544 + quota v545)
🎯 R670 = V23 第 1358 端点 (R999)
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v521(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R999_v521_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v521"}


def get_billing_payment_methods_unset_active_v524(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v524"}


def get_campaigns_audience_source_stats_v544(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R999","count":169500,"pct":80.6},
        {"source":"xhs","count":14000,"pct":35.0},
        {"source":"dy","count":104700,"pct":-128.6},
        {"source":"grp","count":4600,"pct":14.9}
    ],"total":292800,"version":"v544","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v544(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":19910,"unique_users":9365},
        {"date":"2026-10-02","downloads":20150,"unique_users":9435},
        {"date":"2026-10-03","downloads":20390,"unique_users":9505},
        {"date":"2026-10-04","downloads":20630,"unique_users":9575},
        {"date":"2026-10-05","downloads":20870,"unique_users":9645},
        {"date":"2026-10-06","downloads":21110,"unique_users":9715},
        {"date":"2026-10-07","downloads":21350,"unique_users":9785}
    ],"total":144410,"version":"v544","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v545(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12140000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12150000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12160000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12170000,"set_by":"u_001"}
    ],"count":4,"version":"v545","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v545": lambda q, id="k_001": get_auth_api_keys_quota_history_v545(id),
    "/api/v2/skills/{id}/sync-from-template-v521": lambda q, id="s_001": get_skills_sync_from_template_v521(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v524": lambda q, id="c_001": get_billing_payment_methods_unset_active_v524(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v544": lambda q, id="c001": get_campaigns_audience_source_stats_v544(id),
    "/api/v2/files/{id}/download-by-day-list-v544": lambda q, id="f_001": get_files_download_by_day_list_v544(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v543"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v543 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v543","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v543 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R670 5 endpoints (10 ROUTES + 5 defs)")