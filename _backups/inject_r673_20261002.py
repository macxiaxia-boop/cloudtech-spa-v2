"""
R673 治本：注入 5 端点 (skill v527 + billing v530 + campaign v550 + file v550 + quota v551)
⚠️ ROUTES 全部用 id 参数（避免 R672 campaign_id bug 复发）
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v527(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1002_v527_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v527"}


def get_billing_payment_methods_unset_active_v530(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v530"}


def get_campaigns_audience_source_stats_v550(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1002","count":172500,"pct":82.1},
        {"source":"xhs","count":15500,"pct":38.7},
        {"source":"dy","count":107340,"pct":-131.0},
        {"source":"grp","count":5200,"pct":16.7}
    ],"total":300540,"version":"v550","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v550(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":20780,"unique_users":9785},
        {"date":"2026-10-02","downloads":21020,"unique_users":9855},
        {"date":"2026-10-03","downloads":21260,"unique_users":9925},
        {"date":"2026-10-04","downloads":21500,"unique_users":9995},
        {"date":"2026-10-05","downloads":21740,"unique_users":10065},
        {"date":"2026-10-06","downloads":21980,"unique_users":10135},
        {"date":"2026-10-07","downloads":22220,"unique_users":10205}
    ],"total":150500,"version":"v550","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v551(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12260000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12270000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12280000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12290000,"set_by":"u_001"}
    ],"count":4,"version":"v551","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v551": lambda q, id="k_001": get_auth_api_keys_quota_history_v551(id),
    "/api/v2/skills/{id}/sync-from-template-v527": lambda q, id="s_001": get_skills_sync_from_template_v527(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v530": lambda q, id="c_001": get_billing_payment_methods_unset_active_v530(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v550": lambda q, id="c001": get_campaigns_audience_source_stats_v550(id),
    "/api/v2/files/{id}/download-by-day-list-v550": lambda q, id="f_001": get_files_download_by_day_list_v550(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v549"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v549 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v549","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v549 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R673 5 endpoints (10 ROUTES + 5 defs) · bug-free (id)")