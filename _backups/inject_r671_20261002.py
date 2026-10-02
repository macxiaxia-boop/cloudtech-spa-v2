"""
R671 治本：注入 5 端点 (skill v523 + billing v526 + campaign v546 + file v546 + quota v547)
🎯🎯 R671 = V23 R1000 = 1000 端点大里程碑!
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

func_defs = '''
def get_skills_sync_from_template_v523(skill_id: str):
    return {"status":"ok","data":{"skill_id":skill_id,"synced_at":datetime.utcnow().isoformat()+"Z","template_id":"tpl_v23_R1000_v523_"+skill_id,"synced_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v523"}


def get_billing_payment_methods_unset_active_v526(method_id: str):
    return {"status":"ok","data":{"method_id":method_id,"is_active":False,"unset_at":datetime.utcnow().isoformat()+"Z","unset_by":"u_001"},"source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z","version":"v526"}


def get_campaigns_audience_source_stats_v546(campaign_id: str):
    return {"status":"ok","data":[
        {"source":"ch_R1000","count":170500,"pct":81.1},
        {"source":"xhs","count":14500,"pct":36.2},
        {"source":"dy","count":105580,"pct":-129.4},
        {"source":"grp","count":4800,"pct":15.5}
    ],"total":295380,"version":"v546","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_files_download_by_day_list_v546(file_id: str):
    return {"status":"ok","data":[
        {"date":"2026-10-01","downloads":20200,"unique_users":9505},
        {"date":"2026-10-02","downloads":20440,"unique_users":9575},
        {"date":"2026-10-03","downloads":20680,"unique_users":9645},
        {"date":"2026-10-04","downloads":20920,"unique_users":9715},
        {"date":"2026-10-05","downloads":21160,"unique_users":9785},
        {"date":"2026-10-06","downloads":21400,"unique_users":9855},
        {"date":"2026-10-07","downloads":21640,"unique_users":9925}
    ],"total":146440,"version":"v546","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}


def get_auth_api_keys_quota_history_v547(key_id: str):
    return {"status":"ok","data":[
        {"at":"2026-10-01T00:00:00Z","quota":12180000,"set_by":"u_001"},
        {"at":"2026-10-01T01:00:00Z","quota":12190000,"set_by":"u_001"},
        {"at":"2026-10-01T02:00:00Z","quota":12200000,"set_by":"u_001"},
        {"at":"2026-10-01T03:00:00Z","quota":12210000,"set_by":"u_001"}
    ],"count":4,"version":"v547","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}

'''

route_block = '''    "/api/v2/auth/api-keys/{id}/quota-history-v547": lambda q, id="k_001": get_auth_api_keys_quota_history_v547(id),
    "/api/v2/skills/{id}/sync-from-template-v523": lambda q, id="s_001": get_skills_sync_from_template_v523(id),
    "/api/v2/billing/payment-methods/{id}/unset-active-v526": lambda q, id="c_001": get_billing_payment_methods_unset_active_v526(id),
    "/api/v2/campaigns/{id}/audience-source-stats-v546": lambda q, id="c001": get_campaigns_audience_source_stats_v546(id),
    "/api/v2/files/{id}/download-by-day-list-v546": lambda q, id="f_001": get_files_download_by_day_list_v546(id),
'''

target_lines = []
for i, ln in enumerate(src):
    if '"/api/v2/auth/api-keys/{id}/quota-history-v545"' in ln:
        target_lines.append(i)
        if len(target_lines) == 2:
            break

if len(target_lines) != 2:
    raise SystemExit(f"[ABORT] expect 2 occurrences of v545 routes, got {len(target_lines)}")

new_lines = src[:]
for idx in reversed(target_lines):
    new_lines = new_lines[:idx] + [route_block] + new_lines[idx:]

fn_anchor = -1
for i, ln in enumerate(new_lines):
    if '"version":"v545","source":"demo_seed","ts":datetime.utcnow().isoformat()+"Z"}' in ln:
        fn_anchor = i
        break
if fn_anchor < 0:
    raise SystemExit("[ABORT] could not find v545 quota-history function end")

class_line = -1
for i in range(fn_anchor + 1, len(new_lines)):
    if 'class Handler' in new_lines[i]:
        class_line = i
        break
if class_line < 0:
    raise SystemExit("[ABORT] could not find class Handler")

new_lines = new_lines[:class_line] + [func_defs] + new_lines[class_line:]
src_path.write_text("".join(new_lines), encoding="utf-8")
print(f"[INJECTED] R671 5 endpoints (10 ROUTES + 5 defs)")